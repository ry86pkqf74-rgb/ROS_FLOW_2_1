/**
 * Edit Session Service
 * Phase 3: HITL edit sessions — draft → submit → approve/reject → merge.
 * All state transitions emit canonical audit ledger events (PHI-min, idempotent via dedupe_key).
 */

import crypto from 'crypto';

import { pool, query as dbQuery } from '../../db';
import { appendAuditEvent } from './audit-ledger.service';
import { type DbClient } from './audit.service';

const STREAM_TYPE_EDIT_SESSION = 'EDIT_SESSION';
const SERVICE_ORCHESTRATOR = 'orchestrator';
const REDACTED_NOTE = '[REDACTED]';

/** Deterministic stream key for edit-session ledger: one stream per session. */
function streamKeyForSession(sessionId: string): string {
  return `edit_session:${sessionId}`;
}

export type EditSessionStatus = 'draft' | 'submitted' | 'approved' | 'rejected' | 'merged';

export interface EditSession {
  id: string;
  branch_id: string;
  manuscript_id: string;
  status: EditSessionStatus;
  submitted_at: Date | null;
  approved_at: Date | null;
  rejected_at: Date | null;
  merged_at: Date | null;
  created_by: string | null;
  submitted_by: string | null;
  approved_by: string | null;
  rejected_by: string | null;
  merged_by: string | null;
  rejection_reason: string | null;
  created_at: Date;
  updated_at: Date;
}

function mapRow(row: any): EditSession {
  return {
    id: row.id,
    branch_id: row.branch_id,
    manuscript_id: row.manuscript_id,
    status: row.status,
    submitted_at: row.submitted_at,
    approved_at: row.approved_at,
    rejected_at: row.rejected_at,
    merged_at: row.merged_at,
    created_by: row.created_by,
    submitted_by: row.submitted_by,
    approved_by: row.approved_by,
    rejected_by: row.rejected_by,
    merged_by: row.merged_by,
    rejection_reason: row.rejection_reason,
    created_at: row.created_at,
    updated_at: row.updated_at,
  };
}

function sessionStateHash(s: EditSession): string {
  const canonical = JSON.stringify({
    id: s.id,
    branch_id: s.branch_id,
    manuscript_id: s.manuscript_id,
    status: s.status,
    submitted_at: s.submitted_at?.toISOString() ?? null,
    approved_at: s.approved_at?.toISOString() ?? null,
    rejected_at: s.rejected_at?.toISOString() ?? null,
    merged_at: s.merged_at?.toISOString() ?? null,
  });
  return crypto.createHash('sha256').update(canonical).digest('hex').substring(0, 16);
}

function redactNote(reason?: string | null): {
  storedReason: string | null;
  noteLength: number;
  noteRedacted: boolean;
} {
  if (!reason) return { storedReason: null, noteLength: 0, noteRedacted: false };
  const trimmed = reason.trim();
  if (!trimmed) return { storedReason: null, noteLength: 0, noteRedacted: false };
  return { storedReason: REDACTED_NOTE, noteLength: trimmed.length, noteRedacted: true };
}

async function runWithTransaction<T>(fn: (tx: DbClient) => Promise<T>): Promise<T> {
  if (!pool) throw new Error('Database pool not initialized');
  const client = await pool.connect();
  try {
    await client.query('BEGIN');
    const result = await fn(client as DbClient);
    await client.query('COMMIT');
    return result;
  } catch (err) {
    await client.query('ROLLBACK').catch(() => {});
    throw err;
  } finally {
    client.release();
  }
}

async function resolveStreamId(tx: DbClient, streamType: string, streamKey: string): Promise<string> {
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

/**
 * Single path for edit-session audit: routes all state-transition audit
 * through the ledger service (appendAuditEvent) with stream resolution and dedupe.
 */
async function routeEditSessionAuditThroughLedger(
  tx: DbClient,
  input: {
    stream_type: string;
    stream_key: string;
    action: string;
    resource_type: string;
    resource_id: string;
    payload?: Record<string, unknown>;
    dedupe_key?: string;
    actor_type: string;
    actor_id?: string | null;
    service: string;
    before_hash?: string | null;
    after_hash?: string | null;
  },
): Promise<void> {
  const streamId = await resolveStreamId(tx, input.stream_type, input.stream_key);

  // NOTE: dedupe must be enforced under the stream lock in appendAuditEvent; do not add pre-lock checks here.

  const payload = input.dedupe_key
    ? { ...(input.payload ?? {}), dedupe_key: input.dedupe_key }
    : (input.payload ?? {});

  await appendAuditEvent(tx, {
    streamId,
    action: input.action,
    resourceType: input.resource_type,
    resourceId: input.resource_id,
    payload,
    actorType: input.actor_type,
    actorId: input.actor_id ?? null,
    service: input.service,
    beforeHash: input.before_hash ?? null,
    afterHash: input.after_hash ?? null,
  });
}

/**
 * Create a new edit session in draft for a branch.
 */
export async function createEditSession(params: {
  branchId: string;
  manuscriptId: string;
  createdBy?: string | null;
}): Promise<EditSession> {
  return runWithTransaction(async (tx) => {
    const existing = await tx.query(
      'SELECT id FROM edit_sessions WHERE branch_id = $1',
      [params.branchId]
    );
    if (existing.rows.length > 0) {
      throw new Error('Edit session already exists for this branch');
    }

    const result = await tx.query(
      `INSERT INTO edit_sessions (branch_id, manuscript_id, status, created_by)
       VALUES ($1, $2, 'draft', $3)
       RETURNING *`,
      [params.branchId, params.manuscriptId, params.createdBy ?? null]
    );
    const session = mapRow(result.rows[0]);
    const afterHash = sessionStateHash(session);

    await routeEditSessionAuditThroughLedger(tx, {
      stream_type: STREAM_TYPE_EDIT_SESSION,
      stream_key: streamKeyForSession(session.id),
      actor_type: 'USER',
      actor_id: params.createdBy ?? null,
      service: SERVICE_ORCHESTRATOR,
      action: 'EDIT_SESSION_CREATE',
      resource_type: 'EDIT_SESSION',
      resource_id: session.id,
      before_hash: null,
      after_hash: afterHash,
      payload: {
        edit_session_id: session.id,
        branch_id: params.branchId,
        manuscript_id: params.manuscriptId,
        status_from: null,
        status_to: 'draft',
      },
      dedupe_key: `edit_session:${session.id}:create`,
    });

    return session;
  });
}

/**
 * Submit draft for review (draft → submitted).
 */
export async function submitEditSession(sessionId: string, submittedBy?: string | null): Promise<EditSession> {
  return runWithTransaction(async (tx) => {
    const current = await tx.query(
      'SELECT * FROM edit_sessions WHERE id = $1 FOR UPDATE',
      [sessionId]
    );
    if (current.rows.length === 0) throw new Error('Edit session not found');
    const row = current.rows[0];
    if (row.status !== 'draft') throw new Error(`Cannot submit: session status is ${row.status}`);

    const beforeHash = sessionStateHash(mapRow(row));

    await tx.query(
      `UPDATE edit_sessions SET status = 'submitted', submitted_at = NOW(), submitted_by = $1, updated_at = NOW() WHERE id = $2`,
      [submittedBy ?? null, sessionId]
    );
    const updated = await tx.query('SELECT * FROM edit_sessions WHERE id = $1', [sessionId]);
    const session = mapRow(updated.rows[0]);
    const afterHash = sessionStateHash(session);

    await routeEditSessionAuditThroughLedger(tx, {
      stream_type: STREAM_TYPE_EDIT_SESSION,
      stream_key: streamKeyForSession(sessionId),
      actor_type: 'USER',
      actor_id: submittedBy ?? null,
      service: SERVICE_ORCHESTRATOR,
      action: 'EDIT_SESSION_SUBMIT',
      resource_type: 'EDIT_SESSION',
      resource_id: sessionId,
      before_hash: beforeHash,
      after_hash: afterHash,
      payload: {
        edit_session_id: sessionId,
        branch_id: row.branch_id,
        manuscript_id: row.manuscript_id,
        status_from: 'draft',
        status_to: 'submitted',
      },
      dedupe_key: `edit_session:${sessionId}:submit`,
    });

    return session;
  });
}

/**
 * Approve submitted session (submitted → approved).
 */
export async function approveEditSession(sessionId: string, approvedBy?: string | null): Promise<EditSession> {
  return runWithTransaction(async (tx) => {
    const current = await tx.query(
      'SELECT * FROM edit_sessions WHERE id = $1 FOR UPDATE',
      [sessionId]
    );
    if (current.rows.length === 0) throw new Error('Edit session not found');
    const row = current.rows[0];
    if (row.status !== 'submitted') throw new Error(`Cannot approve: session status is ${row.status}`);

    const beforeHash = sessionStateHash(mapRow(row));

    await tx.query(
      `UPDATE edit_sessions SET status = 'approved', approved_at = NOW(), approved_by = $1, updated_at = NOW() WHERE id = $2`,
      [approvedBy ?? null, sessionId]
    );
    const updated = await tx.query('SELECT * FROM edit_sessions WHERE id = $1', [sessionId]);
    const session = mapRow(updated.rows[0]);
    const afterHash = sessionStateHash(session);

    await routeEditSessionAuditThroughLedger(tx, {
      stream_type: STREAM_TYPE_EDIT_SESSION,
      stream_key: streamKeyForSession(sessionId),
      actor_type: 'USER',
      actor_id: approvedBy ?? null,
      service: SERVICE_ORCHESTRATOR,
      action: 'EDIT_SESSION_APPROVE',
      resource_type: 'EDIT_SESSION',
      resource_id: sessionId,
      before_hash: beforeHash,
      after_hash: afterHash,
      payload: {
        edit_session_id: sessionId,
        branch_id: row.branch_id,
        manuscript_id: row.manuscript_id,
        status_from: 'submitted',
        status_to: 'approved',
      },
      dedupe_key: `edit_session:${sessionId}:approve`,
    });

    return session;
  });
}

/**
 * Reject submitted session (submitted → rejected).
 */
export async function rejectEditSession(
  sessionId: string,
  opts: { rejectedBy?: string | null; reason?: string | null }
): Promise<EditSession> {
  return runWithTransaction(async (tx) => {
    const current = await tx.query(
      'SELECT * FROM edit_sessions WHERE id = $1 FOR UPDATE',
      [sessionId]
    );
    if (current.rows.length === 0) throw new Error('Edit session not found');
    const row = current.rows[0];
    if (row.status !== 'submitted') throw new Error(`Cannot reject: session status is ${row.status}`);

    const beforeHash = sessionStateHash(mapRow(row));

    const redacted = redactNote(opts.reason);

    await tx.query(
      `UPDATE edit_sessions SET status = 'rejected', rejected_at = NOW(), rejected_by = $1, rejection_reason = $2, updated_at = NOW() WHERE id = $3`,
      [opts.rejectedBy ?? null, redacted.storedReason, sessionId]
    );
    const updated = await tx.query('SELECT * FROM edit_sessions WHERE id = $1', [sessionId]);
    const session = mapRow(updated.rows[0]);
    const afterHash = sessionStateHash(session);

    await routeEditSessionAuditThroughLedger(tx, {
      stream_type: STREAM_TYPE_EDIT_SESSION,
      stream_key: streamKeyForSession(sessionId),
      actor_type: 'USER',
      actor_id: opts.rejectedBy ?? null,
      service: SERVICE_ORCHESTRATOR,
      action: 'EDIT_SESSION_REJECT',
      resource_type: 'EDIT_SESSION',
      resource_id: sessionId,
      before_hash: beforeHash,
      after_hash: afterHash,
      payload: {
        edit_session_id: sessionId,
        branch_id: row.branch_id,
        manuscript_id: row.manuscript_id,
        status_from: 'submitted',
        status_to: 'rejected',
        note_length: redacted.noteLength,
        note_redacted: redacted.noteRedacted,
      },
      dedupe_key: `edit_session:${sessionId}:reject`,
    });

    return session;
  });
}

/**
 * Merge approved session (approved → merged). Caller is responsible for performing the actual branch merge;
 * this only updates edit session state and emits audit event.
 */
export async function mergeEditSession(sessionId: string, mergedBy?: string | null): Promise<EditSession> {
  return runWithTransaction(async (tx) => {
    const current = await tx.query(
      'SELECT * FROM edit_sessions WHERE id = $1 FOR UPDATE',
      [sessionId]
    );
    if (current.rows.length === 0) throw new Error('Edit session not found');
    const row = current.rows[0];
    if (row.status !== 'approved') throw new Error(`Cannot merge: session status is ${row.status}`);

    const beforeHash = sessionStateHash(mapRow(row));

    await tx.query(
      `UPDATE edit_sessions SET status = 'merged', merged_at = NOW(), merged_by = $1, updated_at = NOW() WHERE id = $2`,
      [mergedBy ?? null, sessionId]
    );
    const updated = await tx.query('SELECT * FROM edit_sessions WHERE id = $1', [sessionId]);
    const session = mapRow(updated.rows[0]);
    const afterHash = sessionStateHash(session);

    await routeEditSessionAuditThroughLedger(tx, {
      stream_type: STREAM_TYPE_EDIT_SESSION,
      stream_key: streamKeyForSession(sessionId),
      actor_type: 'USER',
      actor_id: mergedBy ?? null,
      service: SERVICE_ORCHESTRATOR,
      action: 'EDIT_SESSION_MERGE',
      resource_type: 'EDIT_SESSION',
      resource_id: sessionId,
      before_hash: beforeHash,
      after_hash: afterHash,
      payload: {
        edit_session_id: sessionId,
        branch_id: row.branch_id,
        manuscript_id: row.manuscript_id,
        status_from: 'approved',
        status_to: 'merged',
      },
      dedupe_key: `edit_session:${sessionId}:merge`,
    });

    return session;
  });
}

export async function getEditSession(sessionId: string): Promise<EditSession | null> {
  const result = await dbQuery('SELECT * FROM edit_sessions WHERE id = $1', [sessionId]);
  if (result.rows.length === 0) return null;
  return mapRow(result.rows[0]);
}

export async function getEditSessionByBranchId(branchId: string): Promise<EditSession | null> {
  const result = await dbQuery('SELECT * FROM edit_sessions WHERE branch_id = $1', [branchId]);
  if (result.rows.length === 0) return null;
  return mapRow(result.rows[0]);
}

export async function listEditSessionsByManuscript(manuscriptId: string): Promise<EditSession[]> {
  const result = await dbQuery(
    'SELECT * FROM edit_sessions WHERE manuscript_id = $1 ORDER BY updated_at DESC',
    [manuscriptId]
  );
  return result.rows.map(mapRow);
}
