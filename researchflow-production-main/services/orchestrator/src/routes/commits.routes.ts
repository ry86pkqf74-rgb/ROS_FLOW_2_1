/**
 * Commit endpoints (Agent C)
 *
 * New routes only: list commits, diff (stored or computed), rollback-as-commit.
 * Diff strategy: explicit choice via query param diff_strategy=stored|computed.
 * Uses manuscript_branch_commits + manuscript_revisions (branch-persistence).
 */

import { Router, Request, Response } from 'express';
import * as z from 'zod';

import { query as dbQuery, pool } from '../../db';
import { appendEvent } from '../services/audit.service';
import { requireRole } from '../middleware/rbac';
import branchPersistenceService from '../services/branch-persistence.service';
import * as diffService from '../services/diffService';
import { asString } from '../utils/asString';

const router = Router();

const DiffStrategySchema = z.enum(['stored', 'computed']);
const ListCommitsQuerySchema = z.object({
  limit: z.coerce.number().int().min(1).max(100).optional().default(50),
  offset: z.coerce.number().int().min(0).optional().default(0),
});

const DiffQuerySchema = z.object({
  from_commit_id: z.string().uuid(),
  to_commit_id: z.string().uuid(),
  diff_strategy: DiffStrategySchema.default('computed'),
});

const RollbackBodySchema = z.object({
  target_commit_id: z.string().uuid(),
  message: z.string().max(500).optional(),
});

/**
 * GET /api/ros/branches/:branchId/commits
 * List commits for a branch (newest first).
 */
router.get(
  '/branches/:branchId/commits',
  requireRole('VIEWER'),
  async (req: Request, res: Response) => {
    try {
      const branchId = asString(req.params.branchId);
      const parsed = ListCommitsQuerySchema.safeParse(req.query);
      if (!parsed.success) {
        return res.status(400).json({ error: 'Invalid query', details: parsed.error.flatten() });
      }
      const { limit, offset } = parsed.data;

      const branchCheck = await dbQuery(
        'SELECT id FROM manuscript_branches WHERE id = $1',
        [branchId]
      );
      if (branchCheck.rows.length === 0) {
        return res.status(404).json({ error: 'Branch not found' });
      }

      const commitsResult = await dbQuery(
        `SELECT id, branch_id, commit_hash, parent_commit_id, commit_message, revision_id, content_hash, created_by, created_at
         FROM manuscript_branch_commits
         WHERE branch_id = $1
         ORDER BY created_at DESC, id DESC
         LIMIT $2 OFFSET $3`,
        [branchId, limit, offset]
      );

      const totalResult = await dbQuery(
        'SELECT COUNT(*)::int AS total FROM manuscript_branch_commits WHERE branch_id = $1',
        [branchId]
      );
      const total = totalResult.rows[0]?.total ?? 0;

      const commits = commitsResult.rows.map((row: Record<string, unknown>) => ({
        id: row.id,
        branch_id: row.branch_id,
        commit_hash: row.commit_hash,
        parent_commit_id: row.parent_commit_id,
        commit_message: row.commit_message,
        revision_id: row.revision_id,
        content_hash: row.content_hash,
        created_by: row.created_by,
        created_at: row.created_at,
      }));

      return res.json({ branch_id: branchId, commits, total, limit, offset });
    } catch (err) {
      console.error('[commits] List commits error:', err);
      return res.status(500).json({ error: 'Failed to list commits' });
    }
  }
);

/**
 * GET /api/ros/branches/:branchId/commits/diff
 * Diff between two commits. diff_strategy=computed (default) or stored.
 * Stored is not implemented (no stored unified_diff column); returns 501 when requested.
 */
router.get(
  '/branches/:branchId/commits/diff',
  requireRole('VIEWER'),
  async (req: Request, res: Response) => {
    try {
      const branchId = asString(req.params.branchId);
      const parsed = DiffQuerySchema.safeParse(req.query);
      if (!parsed.success) {
        return res.status(400).json({ error: 'Invalid query', details: parsed.error.flatten() });
      }
      const { from_commit_id, to_commit_id, diff_strategy } = parsed.data;

      if (diff_strategy === 'stored') {
        return res.status(501).json({
          error: 'Stored diff not available',
          message: 'Use diff_strategy=computed for on-demand diff.',
          diff_strategy: 'stored',
        });
      }

      const branchCheck = await dbQuery(
        'SELECT id FROM manuscript_branches WHERE id = $1',
        [branchId]
      );
      if (branchCheck.rows.length === 0) {
        return res.status(404).json({ error: 'Branch not found' });
      }

      const commitsResult = await dbQuery(
        `SELECT id, revision_id FROM manuscript_branch_commits
         WHERE branch_id = $1 AND id IN ($2, $3)`,
        [branchId, from_commit_id, to_commit_id]
      );
      if (commitsResult.rows.length !== 2) {
        return res.status(404).json({ error: 'One or both commits not found for this branch' });
      }

      const fromRow = commitsResult.rows.find((r: { id: string }) => r.id === from_commit_id);
      const toRow = commitsResult.rows.find((r: { id: string }) => r.id === to_commit_id);
      if (!fromRow?.revision_id || !toRow?.revision_id) {
        return res.status(404).json({ error: 'Commit has no linked revision; diff not available' });
      }

      const revsResult = await dbQuery(
        `SELECT id, content FROM manuscript_revisions WHERE id IN ($1, $2)`,
        [fromRow.revision_id, toRow.revision_id]
      );
      const fromRev = revsResult.rows.find((r: { id: string }) => r.id === fromRow.revision_id);
      const toRev = revsResult.rows.find((r: { id: string }) => r.id === toRow.revision_id);
      if (!fromRev || !toRev) {
        return res.status(404).json({ error: 'Revision content not found' });
      }

      const fromContent = typeof fromRev.content === 'string' ? JSON.parse(fromRev.content) : fromRev.content;
      const toContent = typeof toRev.content === 'string' ? JSON.parse(toRev.content) : toRev.content;
      const fromText = JSON.stringify(fromContent, null, 2);
      const toText = JSON.stringify(toContent, null, 2);

      const lineDiff = diffService.computeLineDiff(fromText, toText);
      const unifiedLines: string[] = [];
      for (const op of lineDiff.operations) {
        if (op.operation === 'equal') unifiedLines.push(' ' + op.text);
        else if (op.operation === 'insert') unifiedLines.push('+' + op.text);
        else unifiedLines.push('-' + op.text);
      }
      const unified_diff = unifiedLines.join('\n');

      const allKeys = new Set([...Object.keys(fromContent), ...Object.keys(toContent)]);
      const section_summary: Array<{ section: string; action: 'added' | 'deleted' | 'modified' | 'unchanged' }> = [];
      for (const key of allKeys) {
        const inFrom = key in fromContent;
        const inTo = key in toContent;
        const fromVal = inFrom ? JSON.stringify(fromContent[key]) : '';
        const toVal = inTo ? JSON.stringify(toContent[key]) : '';
        if (!inFrom) section_summary.push({ section: key, action: 'added' });
        else if (!inTo) section_summary.push({ section: key, action: 'deleted' });
        else if (fromVal !== toVal) section_summary.push({ section: key, action: 'modified' });
        else section_summary.push({ section: key, action: 'unchanged' });
      }

      return res.json({
        from_commit_id,
        to_commit_id,
        diff_strategy: 'computed',
        unified_diff,
        section_summary,
        added_lines: lineDiff.addedLines,
        removed_lines: lineDiff.removedLines,
      });
    } catch (err) {
      console.error('[commits] Diff error:', err);
      return res.status(500).json({ error: 'Failed to compute diff' });
    }
  }
);

/**
 * POST /api/ros/branches/:branchId/rollback
 * Rollback as a new commit: create a new revision with content from target commit (immutable history).
 * Appends ROLLBACK_REQUESTED audit event (MANUSCRIPT stream) in same transaction as validation read.
 * Then createRevision emits REVISION CREATE as before.
 */
router.post(
  '/branches/:branchId/rollback',
  requireRole('RESEARCHER'),
  async (req: Request, res: Response) => {
    try {
      const branchId = asString(req.params.branchId);
      const userId = (req as unknown as { user?: { id?: string } }).user?.id ?? 'system';
      const parsed = RollbackBodySchema.safeParse(req.body);
      if (!parsed.success) {
        return res.status(400).json({ error: 'Invalid body', details: parsed.error.flatten() });
      }
      const { target_commit_id, message } = parsed.data;

      if (!pool) {
        return res.status(503).json({ error: 'Database unavailable' });
      }

      let contentObj: Record<string, unknown>;
      const client = await pool.connect();
      try {
        await client.query('BEGIN');

        const branchRow = await client.query(
          'SELECT id, manuscript_id FROM manuscript_branches WHERE id = $1',
          [branchId]
        );
        if (branchRow.rows.length === 0) {
          await client.query('ROLLBACK');
          return res.status(404).json({ error: 'Branch not found' });
        }
        const manuscriptId: string = branchRow.rows[0].manuscript_id ?? branchId;

        const commitRow = await client.query(
          `SELECT id, revision_id, content_hash FROM manuscript_branch_commits
           WHERE branch_id = $1 AND id = $2`,
          [branchId, target_commit_id]
        );
        if (commitRow.rows.length === 0) {
          await client.query('ROLLBACK');
          return res.status(404).json({ error: 'Target commit not found for this branch' });
        }
        const revisionId = commitRow.rows[0].revision_id;
        const contentHash = commitRow.rows[0].content_hash ?? null;
        if (!revisionId) {
          await client.query('ROLLBACK');
          return res.status(400).json({ error: 'Target commit has no linked revision' });
        }

        const revResult = await client.query(
          'SELECT content FROM manuscript_revisions WHERE id = $1',
          [revisionId]
        );
        if (revResult.rows.length === 0) {
          await client.query('ROLLBACK');
          return res.status(404).json({ error: 'Revision not found' });
        }
        const content = revResult.rows[0].content;
        contentObj = typeof content === 'string' ? JSON.parse(content) : content;

        await appendEvent(client, {
          stream_type: 'MANUSCRIPT',
          stream_key: manuscriptId,
          actor_type: 'USER',
          actor_id: userId,
          service: 'orchestrator',
          action: 'ROLLBACK_REQUESTED',
          resource_type: 'COMMIT_ROLLBACK',
          resource_id: target_commit_id,
          payload: {
            branch_id: branchId,
            target_commit_id,
            content_hash: contentHash,
          },
          dedupe_key: `rollback:${branchId}:${target_commit_id}`,
        });

        await client.query('COMMIT');
      } finally {
        try {
          await client.query('ROLLBACK');
        } catch {
          // Ignore; connection may already be committed or closed
        }
        client.release();
      }

      const revision = await branchPersistenceService.createRevision({
        branchId,
        content: contentObj,
        commitMessage: message ?? `Rollback to commit ${target_commit_id}`,
        createdBy: userId,
      });

      return res.status(201).json({
        success: true,
        message: 'Rollback applied as new commit',
        revision_id: revision.id,
        revision_number: revision.revisionNumber,
        rolled_back_to_commit_id: target_commit_id,
      });
    } catch (err) {
      console.error('[commits] Rollback error:', err);
      return res.status(500).json({ error: 'Failed to rollback' });
    }
  }
);

export default router;
