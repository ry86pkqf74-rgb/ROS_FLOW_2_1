/**
 * Append-only audit event writer for the tamper-evident ledger.
 *
 * Targets audit_events / audit_event_streams (migration 017_audit_ledger.sql).
 * All functions accept a raw pg client (PoolClient) so the caller owns the
 * transaction boundary (BEGIN / COMMIT / ROLLBACK).
 *
 * This is distinct from the older auditService.ts / audit-service.ts which
 * target the auditLogs Drizzle table.
 */

import { computePayloadHash, computeEventHash } from './audit-hash.util';
import { sanitizeAuditPayload } from './audit-redaction.util';

// ── Types ───────────────────────────────────────────────────────────

/** Minimal interface for a pg client (PoolClient or transaction client). */
export interface DbClient {
  query(text: string, values?: any[]): Promise<{ rows: any[]; rowCount: number }>;
}

export interface AuditEventInput {
  stream_type: string;
  stream_key: string;
  run_id?: string | null;
  trace_id?: string | null;
  node_id?: string | null;
  actor_type: string;
  actor_id?: string | null;
  service: string;
  action: string;
  resource_type: string;
  resource_id: string;
  before_hash?: string | null;
  after_hash?: string | null;
  payload?: unknown;
  dedupe_key?: string;
}

export interface AppendEventOptions {
  hipaaMode?: boolean;
}

export interface AuditEventRow {
  id: string;
  stream_id: string;
  seq: number;
  created_at: Date;
  run_id: string | null;
  trace_id: string | null;
  node_id: string | null;
  actor_type: string;
  actor_id: string | null;
  service: string;
  action: string;
  resource_type: string;
  resource_id: string;
  before_hash: string | null;
  after_hash: string | null;
  payload_json: unknown;
  payload_hash: string;
  prev_event_hash: string | null;
  event_hash: string;
}

// ── Stream Resolution ───────────────────────────────────────────────

/**
 * Resolve or create a stream row. Uses INSERT ON CONFLICT DO NOTHING
 * then falls back to SELECT (ON CONFLICT DO NOTHING does not RETURN
 * on conflict in PostgreSQL).
 */
async function resolveStream(
  tx: DbClient,
  streamType: string,
  streamKey: string,
): Promise<string> {
  const insertResult = await tx.query(
    `INSERT INTO audit_event_streams (stream_type, stream_key)
     VALUES ($1, $2)
     ON CONFLICT (stream_type, stream_key) DO NOTHING
     RETURNING stream_id`,
    [streamType, streamKey],
  );

  if (insertResult.rows.length > 0) {
    return insertResult.rows[0].stream_id;
  }

  const selectResult = await tx.query(
    `SELECT stream_id FROM audit_event_streams
     WHERE stream_type = $1 AND stream_key = $2`,
    [streamType, streamKey],
  );

  return selectResult.rows[0].stream_id;
}

// ── Append Event ────────────────────────────────────────────────────

/**
 * Append a hash-chained audit event to a stream.
 *
 * Must be called within an existing transaction (the caller owns
 * BEGIN / COMMIT / ROLLBACK). Uses SELECT … FOR UPDATE to serialize
 * concurrent writers to the same stream.
 *
 * If `dedupe_key` is provided, checks for an existing event with that
 * key in payload_json and returns it instead of inserting (idempotency).
 */
export async function appendEvent(
  tx: DbClient,
  input: AuditEventInput,
  opts?: AppendEventOptions,
): Promise<AuditEventRow> {
  // Step 1: Resolve stream
  const streamId = await resolveStream(tx, input.stream_type, input.stream_key);

  // Step 2: Deduplication check
  if (input.dedupe_key) {
    const dupeResult = await tx.query(
      `SELECT * FROM audit_events
       WHERE stream_id = $1 AND payload_json->>'dedupe_key' = $2
       LIMIT 1`,
      [streamId, input.dedupe_key],
    );
    if (dupeResult.rows.length > 0) {
      return dupeResult.rows[0] as AuditEventRow;
    }
  }

  // Step 3: Lock chain head and read last event
  const lastResult = await tx.query(
    `SELECT seq, event_hash FROM audit_events
     WHERE stream_id = $1
     ORDER BY seq DESC LIMIT 1
     FOR UPDATE`,
    [streamId],
  );

  const prevSeq = lastResult.rows.length > 0 ? Number(lastResult.rows[0].seq) : 0;
  const prevEventHash: string | null =
    lastResult.rows.length > 0 ? lastResult.rows[0].event_hash : null;
  const nextSeq = prevSeq + 1;

  // Step 4: Sanitize payload and compute hashes
  const rawPayload = input.dedupe_key
    ? { ...((input.payload as Record<string, unknown>) ?? {}), dedupe_key: input.dedupe_key }
    : (input.payload ?? {});

  const sanitizedPayload = sanitizeAuditPayload(rawPayload, {
    hipaaMode: opts?.hipaaMode ?? false,
  });

  const payloadHash = computePayloadHash(sanitizedPayload);

  const eventHash = computeEventHash({
    stream_id: streamId,
    seq: nextSeq,
    prev_event_hash: prevEventHash,
    payload_hash: payloadHash,
    before_hash: input.before_hash ?? null,
    after_hash: input.after_hash ?? null,
    actor_type: input.actor_type,
    actor_id: input.actor_id ?? null,
    service: input.service,
    action: input.action,
    resource_type: input.resource_type,
    resource_id: input.resource_id,
  });

  // Step 5: Insert
  const insertResult = await tx.query(
    `INSERT INTO audit_events (
       stream_id, seq, run_id, trace_id, node_id,
       actor_type, actor_id, service, action,
       resource_type, resource_id,
       before_hash, after_hash,
       payload_json, payload_hash,
       prev_event_hash, event_hash
     ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17)
     RETURNING *`,
    [
      streamId,
      nextSeq,
      input.run_id ?? null,
      input.trace_id ?? null,
      input.node_id ?? null,
      input.actor_type,
      input.actor_id ?? null,
      input.service,
      input.action,
      input.resource_type,
      input.resource_id,
      input.before_hash ?? null,
      input.after_hash ?? null,
      JSON.stringify(sanitizedPayload),
      payloadHash,
      prevEventHash,
      eventHash,
    ],
  );

  return insertResult.rows[0] as AuditEventRow;
}

// ── Chain Verification ──────────────────────────────────────────────

/**
 * Walk a stream and verify every event's hash chain link and event hash.
 * Returns { valid: true } if intact, or { valid: false, brokenAtSeq }
 * if tampered.
 */
export async function verifyStreamIntegrity(
  tx: DbClient,
  streamId: string,
): Promise<{ valid: boolean; brokenAtSeq?: number }> {
  const result = await tx.query(
    `SELECT * FROM audit_events WHERE stream_id = $1 ORDER BY seq ASC`,
    [streamId],
  );

  let prevHash: string | null = null;

  for (const row of result.rows) {
    // Verify chain link
    if (row.prev_event_hash !== prevHash) {
      return { valid: false, brokenAtSeq: Number(row.seq) };
    }

    // Recompute and verify event hash
    const recomputed = computeEventHash({
      stream_id: row.stream_id,
      seq: Number(row.seq),
      prev_event_hash: row.prev_event_hash,
      payload_hash: row.payload_hash,
      before_hash: row.before_hash,
      after_hash: row.after_hash,
      actor_type: row.actor_type,
      actor_id: row.actor_id,
      service: row.service,
      action: row.action,
      resource_type: row.resource_type,
      resource_id: row.resource_id,
    });

    if (recomputed !== row.event_hash) {
      return { valid: false, brokenAtSeq: Number(row.seq) };
    }

    prevHash = row.event_hash;
  }

  return { valid: true };
}
