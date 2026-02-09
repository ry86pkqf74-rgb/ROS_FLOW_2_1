/**
 * Edit Session Service - DB-backed integration tests
 *
 * Validates state transitions and audit ledger entries.
 * Skips automatically when the database is unavailable.
 */

import { describe, it, expect, beforeAll } from 'vitest';
import { randomUUID } from 'crypto';

import { pool, query } from '../../../db';
import { dbAvailable as checkDbAvailable } from '../../__tests__/helpers/dbAvailable';
import {
  approveEditSession,
  createEditSession,
  mergeEditSession,
  rejectEditSession,
  submitEditSession,
} from '../edit-session.service';

const hasDb = !!pool;
let dbReady = false;

async function createBranch(manuscriptId: string): Promise<string> {
  const result = await query(
    `INSERT INTO manuscript_branches (manuscript_id, branch_name, parent_branch, status)
     VALUES ($1, $2, 'main', 'active')
     RETURNING id`,
    [manuscriptId, `test-edit-session-${randomUUID().slice(0, 8)}`],
  );
  return result.rows[0]?.id;
}

async function fetchAuditEvents(manuscriptId: string) {
  const result = await query(
    `SELECT ae.action, ae.resource_type, ae.resource_id, ae.payload_json
     FROM audit_events ae
     JOIN audit_event_streams aes ON aes.stream_id = ae.stream_id
     WHERE aes.stream_type = 'MANUSCRIPT' AND aes.stream_key = $1
     ORDER BY ae.seq ASC`,
    [manuscriptId],
  );
  return result.rows;
}

async function cleanup(manuscriptId: string, branchId?: string | null) {
  if (branchId) {
    await query('DELETE FROM edit_sessions WHERE branch_id = $1', [branchId]);
  } else {
    await query('DELETE FROM edit_sessions WHERE manuscript_id = $1', [manuscriptId]);
  }
  await query(
    `DELETE FROM audit_events
     WHERE stream_id IN (
       SELECT stream_id FROM audit_event_streams
       WHERE stream_type = 'MANUSCRIPT' AND stream_key = $1
     )`,
    [manuscriptId],
  );
  await query(
    `DELETE FROM audit_event_streams
     WHERE stream_type = 'MANUSCRIPT' AND stream_key = $1`,
    [manuscriptId],
  );
  if (branchId) {
    await query('DELETE FROM manuscript_branches WHERE id = $1', [branchId]);
  }
}

describe('EditSession service (integration)', { skip: !hasDb ? 'DATABASE_URL not set' : false }, () => {
  beforeAll(async () => {
    if (!hasDb) return;
    dbReady = await checkDbAvailable();
  });

  it('create → submit → approve → merge emits audit events', async () => {
    if (!dbReady) return;
    const manuscriptId = randomUUID();
    const actorId = randomUUID();
    let branchId: string | null = null;

    try {
      branchId = await createBranch(manuscriptId);
      const session = await createEditSession({ branchId, manuscriptId, createdBy: actorId });
      await submitEditSession(session.id, actorId);
      await approveEditSession(session.id, actorId);
      const merged = await mergeEditSession(session.id, actorId);

      expect(merged.status).toBe('merged');

      const events = await fetchAuditEvents(manuscriptId);
      const actions = events.map(event => event.action);
      expect(actions).toEqual([
        'EDIT_SESSION_CREATE',
        'EDIT_SESSION_SUBMIT',
        'EDIT_SESSION_APPROVE',
        'EDIT_SESSION_MERGE',
      ]);

      const expectedDedupe: Record<string, string> = {
        EDIT_SESSION_CREATE: `edit_session:${session.id}:create`,
        EDIT_SESSION_SUBMIT: `edit_session:${session.id}:submit`,
        EDIT_SESSION_APPROVE: `edit_session:${session.id}:approve`,
        EDIT_SESSION_MERGE: `edit_session:${session.id}:merge`,
      };

      for (const event of events) {
        expect(event.resource_type).toBe('EDIT_SESSION');
        expect(event.resource_id).toBe(session.id);
        expect(event.payload_json?.dedupe_key).toBe(expectedDedupe[event.action]);
      }
    } finally {
      await cleanup(manuscriptId, branchId);
    }
  });

  it('create → submit → reject redacts notes and audits without free text', async () => {
    if (!dbReady) return;
    const manuscriptId = randomUUID();
    const actorId = randomUUID();
    const reason = 'Patient name John Doe should not be stored.';
    let branchId: string | null = null;

    try {
      branchId = await createBranch(manuscriptId);
      const session = await createEditSession({ branchId, manuscriptId, createdBy: actorId });
      await submitEditSession(session.id, actorId);
      await rejectEditSession(session.id, { rejectedBy: actorId, reason });

      const sessionRow = await query(
        'SELECT rejection_reason FROM edit_sessions WHERE id = $1',
        [session.id],
      );
      expect(sessionRow.rows[0]?.rejection_reason).toBe('[REDACTED]');

      const events = await fetchAuditEvents(manuscriptId);
      const rejectEvent = events.find(event => event.action === 'EDIT_SESSION_REJECT');
      expect(rejectEvent).toBeDefined();
      expect(rejectEvent?.payload_json?.note_length).toBe(reason.length);
      expect(rejectEvent?.payload_json?.note_redacted).toBe(true);
      expect(rejectEvent?.payload_json?.reason).toBeUndefined();
      expect(JSON.stringify(rejectEvent?.payload_json)).not.toContain(reason);
    } finally {
      await cleanup(manuscriptId, branchId);
    }
  });

  it('rejects invalid transitions without emitting audit events', async () => {
    if (!dbReady) return;
    const manuscriptId = randomUUID();
    const actorId = randomUUID();
    let branchId: string | null = null;

    try {
      branchId = await createBranch(manuscriptId);
      const session = await createEditSession({ branchId, manuscriptId, createdBy: actorId });

      await expect(approveEditSession(session.id, actorId)).rejects.toThrow('Cannot approve');
      await expect(mergeEditSession(session.id, actorId)).rejects.toThrow('Cannot merge');

      const events = await fetchAuditEvents(manuscriptId);
      expect(events.map(event => event.action)).toEqual(['EDIT_SESSION_CREATE']);
    } finally {
      await cleanup(manuscriptId, branchId);
    }
  });
});
