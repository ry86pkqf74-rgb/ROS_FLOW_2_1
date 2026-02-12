/**
 * Commit endpoints tests (Agent C)
 *
 * - Stored diff: seed commits with stored diff fields; GET diff?diff_strategy=stored returns them.
 * - Audit: DIFF_REQUESTED and ROLLBACK_REQUESTED events exist after diff and rollback requests.
 * - DB-backed skip when DATABASE_URL not set.
 *
 * Integration tests: run only when DATABASE_URL is set.
 */

import express from 'express';
import request from 'supertest';
import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { randomUUID } from 'crypto';
import { createHash } from 'crypto';

import { pool, query } from '../../../db';
import commitsRoutes from '../commits.routes';

const hasDb = !!pool;
let dbAvailable = false;
const TEST_USER_ID = '00000000-0000-4000-8000-000000000099';

// Minimal app: inject user so requireRole passes, mount commits routes at /api/ros
function createApp() {
  const app = express();
  app.use(express.json());
  app.use((req, _res, next) => {
    (req as unknown as { user?: { id: string; role: string } }).user = { id: TEST_USER_ID, role: 'RESEARCHER' };
    next();
  });
  app.use('/api/ros', commitsRoutes);
  return app;
}

describe('commits endpoints (routes)', { skip: !hasDb }, () => {
  let app: ReturnType<typeof createApp>;
  let testBranchId: string;
  let testManuscriptId: string;
  let commit1Id: string;
  let commit2Id: string;
  let commitWithStoredId: string;
  let rev1Id: string;
  let rev2Id: string;

  beforeAll(async () => {
    if (!hasDb) return;
    try {
      await query('SELECT 1');
      dbAvailable = true;
    } catch {
      return;
    }
    app = createApp();
    testManuscriptId = randomUUID();
    const branchResult = await query(
      `INSERT INTO manuscript_branches (manuscript_id, branch_name, parent_branch, status)
       VALUES ($1, $2, 'main', 'active')
       ON CONFLICT (manuscript_id, branch_name) DO UPDATE SET status = 'active'
       RETURNING id`,
      [testManuscriptId, `test-commits-routes-${randomUUID().slice(0, 8)}`]
    );
    testBranchId = branchResult.rows[0]?.id;
    if (!testBranchId) throw new Error('Failed to create test branch');

    // Two revisions so we have two commits (commit1 = from, commit2 = to)
    const rev1Result = await query(
      `INSERT INTO manuscript_revisions (branch_id, revision_number, content, sections_changed, commit_message, created_by)
       VALUES ($1, 1, $2::jsonb, '{}', 'Rev 1', TEST_USER_ID)
       RETURNING id`,
      [testBranchId, JSON.stringify({ abstract: 'A1', intro: 'I1' })]
    );
    rev1Id = rev1Result.rows[0].id;
    const contentHash1 = createHash('sha256').update(JSON.stringify({ abstract: 'A1', intro: 'I1' })).digest('hex');
    const commitHash1 = createHash('sha256').update(JSON.stringify({ parent_commit_hash: null, content_hash: contentHash1 })).digest('hex');
    const commit1Row = await query(
      `INSERT INTO manuscript_branch_commits (branch_id, commit_hash, commit_message, revision_id, content_hash, created_by)
       VALUES ($1, $2, $3, $4, $5, $6)
       RETURNING id`,
      [testBranchId, commitHash1, 'Commit 1', rev1Id, contentHash1, TEST_USER_ID]
    );
    commit1Id = commit1Row.rows[0].id;

    const rev2Result = await query(
      `INSERT INTO manuscript_revisions (branch_id, revision_number, content, sections_changed, commit_message, created_by)
       VALUES ($1, 2, $2::jsonb, '{}', 'Rev 2', TEST_USER_ID)
       RETURNING id`,
      [testBranchId, JSON.stringify({ abstract: 'A2', intro: 'I2' })]
    );
    rev2Id = rev2Result.rows[0].id;
    const contentHash2 = createHash('sha256').update(JSON.stringify({ abstract: 'A2', intro: 'I2' })).digest('hex');
    const commitHash2 = createHash('sha256').update(JSON.stringify({ parent_commit_hash: commitHash1, content_hash: contentHash2 })).digest('hex');
    const commit2Row = await query(
      `INSERT INTO manuscript_branch_commits (branch_id, commit_hash, parent_commit_id, commit_message, revision_id, content_hash, created_by)
       VALUES ($1, $2, $3, $4, $5, $6, $7)
       RETURNING id`,
      [testBranchId, commitHash2, commit1Id, 'Commit 2', rev2Id, contentHash2, TEST_USER_ID]
    );
    commit2Id = commit2Row.rows[0].id;

    // Commit with stored diff (same branch, parent = commit1, revision = rev2, with diff_unified/diff_summary_json)
    const commitHashStored = createHash('sha256').update(`stored-${randomUUID()}`).digest('hex');
    const storedRow = await query(
      `INSERT INTO manuscript_branch_commits (branch_id, commit_hash, parent_commit_id, commit_message, revision_id, content_hash, created_by, diff_unified, diff_summary_json, diff_strategy)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9::jsonb, $10)
       RETURNING id`,
      [
        testBranchId,
        commitHashStored,
        commit1Id,
        'Stored diff commit',
        rev2Id,
        contentHash2,
        TEST_USER_ID,
        ' abstract\n+abstract updated\n',
        JSON.stringify([{ section: 'abstract', action: 'modified' }]),
        'stored',
      ]
    );
    commitWithStoredId = storedRow.rows[0].id;
  });

  afterAll(async () => {
    if (!dbAvailable || !testBranchId) return;
    await query('DELETE FROM manuscript_revisions WHERE branch_id = $1', [testBranchId]);
    try {
      await query('DELETE FROM manuscript_branches WHERE id = $1', [testBranchId]);
    } catch {
      // Branch delete may fail if CASCADE to immutable commits is blocked
    }
  });

  describe('GET /branches/:branchId/commits/diff (stored)', () => {
    it('returns stored diff when to_commit has diff_unified/diff_summary_json', async () => {
      if (!dbAvailable || !testBranchId || !commit1Id || !commitWithStoredId) return;

      const res = await request(app)
        .get(`/api/ros/branches/${testBranchId}/commits/diff`)
        .query({
          from_commit_id: commit1Id,
          to_commit_id: commitWithStoredId,
          diff_strategy: 'stored',
        });

      expect(res.status).toBe(200);
      expect(res.body).toMatchObject({
        from_commit_id: commit1Id,
        to_commit_id: commitWithStoredId,
        diff_strategy: 'stored',
      });
      expect(res.body.unified_diff).toBeDefined();
      expect(res.body.unified_diff).toContain('abstract');
      expect(res.body.section_summary).toBeDefined();
      expect(Array.isArray(res.body.section_summary)).toBe(true);
      expect(res.body.section_summary.length).toBeGreaterThanOrEqual(1);
    });

    it('returns 409 when stored requested but to_commit has no stored diff', async () => {
      if (!dbAvailable || !testBranchId || !commit1Id || !commit2Id) return;

      const res = await request(app)
        .get(`/api/ros/branches/${testBranchId}/commits/diff`)
        .query({
          from_commit_id: commit1Id,
          to_commit_id: commit2Id,
          diff_strategy: 'stored',
        });

      expect(res.status).toBe(409);
      expect(res.body.error).toMatch(/stored diff not available/i);
      expect(res.body.diff_strategy).toBe('stored');
    });
  });

  describe('GET /branches/:branchId/commits/diff (computed)', () => {
    it('returns computed diff and audit DIFF_REQUESTED exists', async () => {
      if (!dbAvailable || !testBranchId || !commit1Id || !commit2Id) return;

      const res = await request(app)
        .get(`/api/ros/branches/${testBranchId}/commits/diff`)
        .query({
          from_commit_id: commit1Id,
          to_commit_id: commit2Id,
          diff_strategy: 'computed',
        });

      expect(res.status).toBe(200);
      expect(res.body.diff_strategy).toBe('computed');
      expect(res.body.unified_diff).toBeDefined();
      expect(res.body.section_summary).toBeDefined();

      const streamRow = await query(
        `SELECT stream_id FROM audit_event_streams WHERE stream_type = $1 AND stream_key = $2`,
        ['MANUSCRIPT', testManuscriptId]
      );
      if (streamRow.rows.length === 0) throw new Error('Audit stream not found for manuscript');
      const streamId = streamRow.rows[0].stream_id;

      const events = await query(
        `SELECT action, resource_type, resource_id, payload_json
         FROM audit_events
         WHERE stream_id = $1 AND action = $2 AND resource_id = $3
         ORDER BY seq DESC LIMIT 1`,
        [streamId, 'DIFF_REQUESTED', commit2Id]
      );
      expect(events.rows.length).toBeGreaterThanOrEqual(1);
      const ev = events.rows[0];
      expect(ev.action).toBe('DIFF_REQUESTED');
      expect(ev.resource_type).toBe('COMMIT_DIFF');
      expect(ev.resource_id).toBe(commit2Id);
      const payload = ev.payload_json as Record<string, unknown>;
      expect(payload.diff_strategy).toBe('computed');
      expect(payload.from_commit_id).toBe(commit1Id);
      expect(payload.to_commit_id).toBe(commit2Id);
    });
  });

  describe('POST /branches/:branchId/rollback', () => {
    it('rollback returns 201 and audit ROLLBACK_REQUESTED exists', async () => {
      if (!dbAvailable || !testBranchId || !commit1Id) return;

      const res = await request(app)
        .post(`/api/ros/branches/${testBranchId}/rollback`)
        .send({ target_commit_id: commit1Id, message: 'Test rollback' });

      expect(res.status).toBe(201);
      expect(res.body.success).toBe(true);
      expect(res.body.rolled_back_to_commit_id).toBe(commit1Id);

      const streamRow = await query(
        `SELECT stream_id FROM audit_event_streams WHERE stream_type = $1 AND stream_key = $2`,
        ['MANUSCRIPT', testManuscriptId]
      );
      if (streamRow.rows.length === 0) throw new Error('Audit stream not found for manuscript');
      const streamId = streamRow.rows[0].stream_id;

      const events = await query(
        `SELECT action, resource_type, resource_id, payload_json
         FROM audit_events
         WHERE stream_id = $1 AND action = $2 AND resource_id = $3
         ORDER BY seq DESC LIMIT 1`,
        [streamId, 'ROLLBACK_REQUESTED', commit1Id]
      );
      expect(events.rows.length).toBeGreaterThanOrEqual(1);
      const ev = events.rows[0];
      expect(ev.action).toBe('ROLLBACK_REQUESTED');
      expect(ev.resource_type).toBe('COMMIT_ROLLBACK');
      expect(ev.resource_id).toBe(commit1Id);
      const payload = ev.payload_json as Record<string, unknown>;
      expect(payload.target_commit_id).toBe(commit1Id);
      expect(payload.branch_id).toBe(testBranchId);
    });
  });
});
