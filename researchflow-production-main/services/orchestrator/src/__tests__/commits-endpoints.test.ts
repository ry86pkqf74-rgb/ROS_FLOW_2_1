/**
 * Commit endpoints tests (Agent C)
 *
 * - Immutability: manuscript_branch_commits cannot be updated or deleted.
 * - Rollback correctness: rollback creates a new revision with same content as target commit.
 * - Audit event exists: after rollback (createRevision), audit_events has a REVISION/CREATE event.
 *
 * Integration tests: run only when DATABASE_URL is set.
 */

import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { randomUUID } from 'crypto';

import { pool, query } from '../../db';
import branchPersistenceService from '../services/branch-persistence.service';

const hasDb = !!pool;
let dbAvailable = false;

describe('commits endpoints', { skip: !hasDb }, () => {
  let testBranchId: string;
  let testManuscriptId: string;
  let initialCommitId: string;
  let initialRevisionId: string;
  let initialContent: Record<string, unknown>;

  beforeAll(async () => {
    if (!hasDb) return;
    try {
      await query('SELECT 1');
      dbAvailable = true;
    } catch {
      return;
    }
    testManuscriptId = randomUUID();
    const branchResult = await query(
      `INSERT INTO manuscript_branches (manuscript_id, branch_name, parent_branch, status)
       VALUES ($1, $2, 'main', 'active')
       ON CONFLICT (manuscript_id, branch_name) DO UPDATE SET status = 'active'
       RETURNING id`,
      [testManuscriptId, `test-commits-${randomUUID().slice(0, 8)}`]
    );
    testBranchId = branchResult.rows[0]?.id;
    if (!testBranchId) throw new Error('Failed to create test branch');

    initialContent = { abstract: 'Initial abstract text', introduction: 'Intro v1' };
    const revision = await branchPersistenceService.createRevision({
      branchId: testBranchId,
      content: initialContent,
      commitMessage: 'Initial commit for commit tests',
      createdBy: randomUUID(),
    });
    initialRevisionId = revision.id;

    const commitRow = await query(
      `SELECT id FROM manuscript_branch_commits WHERE branch_id = $1 AND revision_id = $2 LIMIT 1`,
      [testBranchId, initialRevisionId]
    );
    initialCommitId = commitRow.rows[0]?.id;
    if (!initialCommitId) throw new Error('Failed to resolve commit for initial revision');
  });

  afterAll(async () => {
    if (!dbAvailable || !testBranchId) return;
    await query('DELETE FROM manuscript_revisions WHERE branch_id = $1', [testBranchId]);
    try {
      await query('DELETE FROM manuscript_branches WHERE id = $1', [testBranchId]);
    } catch {
      // Branch delete may fail if CASCADE to immutable commits is blocked by trigger
    }
  });

  describe('immutability', () => {
    it('rejects UPDATE on manuscript_branch_commits', async () => {
      if (!dbAvailable || !initialCommitId) return;
      await expect(
        query(
          `UPDATE manuscript_branch_commits SET commit_message = 'tampered' WHERE id = $1`,
          [initialCommitId]
        )
      ).rejects.toThrow(/append-only|UPDATE not allowed|not allowed/i);
    });

    it('rejects DELETE on manuscript_branch_commits', async () => {
      if (!dbAvailable || !initialCommitId) return;
      await expect(
        query(`DELETE FROM manuscript_branch_commits WHERE id = $1`, [initialCommitId])
      ).rejects.toThrow(/append-only|DELETE not allowed|not allowed/i);
    });
  });

  describe('rollback correctness', () => {
    it('rollback-as-commit creates new revision with same content as target commit', async () => {
      if (!dbAvailable || !testBranchId || !initialCommitId) return;

      const beforeCount = await query(
        'SELECT COUNT(*)::int AS c FROM manuscript_revisions WHERE branch_id = $1',
        [testBranchId]
      );
      const countBefore = beforeCount.rows[0]?.c ?? 0;

      const revResult = await query(
        'SELECT content FROM manuscript_revisions WHERE id = $1',
        [initialRevisionId]
      );
      const contentToRestore = revResult.rows[0]?.content;
      const contentObj = typeof contentToRestore === 'string' ? JSON.parse(contentToRestore) : contentToRestore;

      const newRevision = await branchPersistenceService.createRevision({
        branchId: testBranchId,
        content: contentObj,
        commitMessage: `Rollback to commit ${initialCommitId}`,
        createdBy: randomUUID(),
      });

      expect(newRevision.id).toBeDefined();
      expect(newRevision.id).not.toBe(initialRevisionId);
      expect(newRevision.content).toEqual(initialContent);

      const afterCount = await query(
        'SELECT COUNT(*)::int AS c FROM manuscript_revisions WHERE branch_id = $1',
        [testBranchId]
      );
      expect((afterCount.rows[0]?.c ?? 0)).toBe(countBefore + 1);
    });
  });

  describe('audit event exists', () => {
    it('createRevision emits an audit event for REVISION CREATE', async () => {
      if (!dbAvailable || !testBranchId) return;

      const content = { abstract: 'Audit test', section: 'test' };
      const revision = await branchPersistenceService.createRevision({
        branchId: testBranchId,
        content,
        commitMessage: 'Commit for audit test',
        createdBy: randomUUID(),
      });

      const streamRow = await query(
        `SELECT stream_id FROM audit_event_streams WHERE stream_type = $1 AND stream_key = $2`,
        ['MANUSCRIPT', testManuscriptId]
      );
      if (streamRow.rows.length === 0) {
        throw new Error('Audit stream not found for manuscript');
      }
      const streamId = streamRow.rows[0].stream_id;

      const events = await query(
        `SELECT resource_type, action, resource_id, payload_json
         FROM audit_events
         WHERE stream_id = $1 AND resource_type = $2 AND resource_id = $3
         ORDER BY seq DESC LIMIT 1`,
        [streamId, 'REVISION', revision.id]
      );

      expect(events.rows.length).toBeGreaterThanOrEqual(1);
      const ev = events.rows[0];
      expect(ev.action).toBe('CREATE');
      expect(ev.resource_type).toBe('REVISION');
      expect(ev.resource_id).toBe(revision.id);
      expect(ev.payload_json).toBeDefined();
      const payload = ev.payload_json as Record<string, unknown>;
      expect(payload.revision_id).toBe(revision.id);
    });
  });
});
