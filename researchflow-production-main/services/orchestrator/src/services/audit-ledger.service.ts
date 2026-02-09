/**
 * Append-only audit ledger writer for audit_events (migration 017_audit_ledger.sql).
 *
 * Requires the caller to supply a pg client and transaction boundary.
 * Locks the stream row to serialize concurrent writers per stream.
 */

import { computeEventHash, computePayloadHash } from './audit-hash.util';
import { sanitizeAuditPayload } from './audit-redaction.util';
import type { DbClient } from './audit.service';

export interface AppendAuditEventInput {
  streamId: string;
  traceId?: string | null;
  nodeId?: string | null;
  action: string;
  resourceType: string;
  resourceId: string;
  payload?: unknown;
  runId?: string | null;
  actorType?: string;
  actorId?: string | null;
  service?: string;
  beforeHash?: string | null;
  afterHash?: string | null;
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

const DEFAULT_ACTOR_TYPE = 'SYSTEM';
const DEFAULT_SERVICE = 'orchestrator';

async function lockStream(tx: DbClient, streamId: string): Promise<void> {
  const result = await tx.query(
    `SELECT stream_id
     FROM audit_event_streams
     WHERE stream_id = $1
     FOR UPDATE`,
    [streamId],
  );

  if (result.rows.length === 0) {
    throw new Error(`audit stream not found for stream_id=${streamId}`);
  }
}

/**
 * Append a hash-chained audit event to an existing stream.
 *
 * Payloads are sanitized in HIPAA mode by default to keep only IDs/hashes.
 */
export async function appendAuditEvent(
  tx: DbClient,
  input: AppendAuditEventInput,
): Promise<AuditEventRow> {
  await lockStream(tx, input.streamId);

  const lastResult = await tx.query(
    `SELECT seq, event_hash
     FROM audit_events
     WHERE stream_id = $1
     ORDER BY seq DESC
     LIMIT 1
     FOR UPDATE`,
    [input.streamId],
  );

  const prevSeq = lastResult.rows.length > 0 ? Number(lastResult.rows[0].seq) : 0;
  const prevEventHash: string | null =
    lastResult.rows.length > 0 ? lastResult.rows[0].event_hash : null;
  const nextSeq = prevSeq + 1;

  const rawPayload = input.payload ?? {};
  const sanitizedPayload = sanitizeAuditPayload(rawPayload, {
    hipaaMode: input.hipaaMode ?? true,
  });

  const payloadHash = computePayloadHash(sanitizedPayload);

  const eventHash = computeEventHash({
    stream_id: input.streamId,
    seq: nextSeq,
    prev_event_hash: prevEventHash,
    payload_hash: payloadHash,
    before_hash: input.beforeHash ?? null,
    after_hash: input.afterHash ?? null,
    actor_type: input.actorType ?? DEFAULT_ACTOR_TYPE,
    actor_id: input.actorId ?? null,
    service: input.service ?? DEFAULT_SERVICE,
    action: input.action,
    resource_type: input.resourceType,
    resource_id: input.resourceId,
  });

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
      input.streamId,
      nextSeq,
      input.runId ?? null,
      input.traceId ?? null,
      input.nodeId ?? null,
      input.actorType ?? DEFAULT_ACTOR_TYPE,
      input.actorId ?? null,
      input.service ?? DEFAULT_SERVICE,
      input.action,
      input.resourceType,
      input.resourceId,
      input.beforeHash ?? null,
      input.afterHash ?? null,
      JSON.stringify(sanitizedPayload),
      payloadHash,
      prevEventHash,
      eventHash,
    ],
  );

  return insertResult.rows[0] as AuditEventRow;
}
