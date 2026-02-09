/**
 * Migration 019: commit_diffs (stored diff fields on manuscript_branch_commits)
 *
 * - Migration applies cleanly.
 * - Can insert a commit row with diff_summary_json only (no unified diff) and read it back.
 * - Immutability trigger still rejects UPDATE/DELETE.
 *
 * Runs only when DATABASE_URL is set (e.g. CI or local Postgres).
 */

import { describe, it, expect, beforeAll } from 'vitest';
import { readFileSync } from 'fs';
import { join } from 'path';
import { randomUUID } from 'crypto';
import { pool, query } from '../../../db';

const hasDb = !!pool;

describe('019_commit_diffs', { skip: !hasDb ? 'DATABASE_URL not set' : false }, () => {
  let testBranchId: string;
  const testManuscriptId = randomUUID();

  beforeAll(async () => {
    if (!hasDb) return;
    const branchResult = await query(
      `INSERT INTO manuscript_branches (manuscript_id, branch_name, parent_branch, status)
       VALUES ($1, $2, 'main', 'active')
       ON CONFLICT (manuscript_id, branch_name) DO UPDATE SET status = 'active'
       RETURNING id`,
      [testManuscriptId, `test-branch-${randomUUID().slice(0, 8)}`]
    );
    testBranchId = branchResult.rows[0]?.id;
    if (!testBranchId) throw new Error('Failed to create test branch');
  });

  it('applies migration 019 without error', async () => {
    if (!hasDb) return;
    const migrationPath = join(__dirname, '../../../../migrations/019_commit_diffs.sql');
    const sql = readFileSync(migrationPath, 'utf-8');
    await expect(query(sql)).resolves.toBeDefined();
  });

  it('insert and select with diff_summary_json only (no unified diff)', async () => {
    if (!hasDb || !testBranchId) return;
    const commitHash = `h${randomUUID().replace(/-/g, '').slice(0, 62)}`;
    const summaryJson = {
      sections: [
        { sectionId: 'intro', changeType: 'edited', wordDelta: 12 },
        { sectionId: 'methods', changeType: 'unchanged', wordDelta: 0 },
      ],
    };

    await query(
      `INSERT INTO manuscript_branch_commits (branch_id, commit_hash, commit_message, diff_summary_json, diff_strategy)
       VALUES ($1, $2, $3, $4::jsonb, $5)`,
      [testBranchId, commitHash, 'test stored diff', JSON.stringify(summaryJson), 'stored']
    );

    const selectResult = await query(
      `SELECT id, branch_id, commit_hash, commit_message, diff_unified, diff_summary_json, diff_strategy
       FROM manuscript_branch_commits
       WHERE branch_id = $1 AND commit_hash = $2`,
      [testBranchId, commitHash]
    );

    expect(selectResult.rows.length).toBe(1);
    const row = selectResult.rows[0];
    expect(row.commit_hash).toBe(commitHash);
    expect(row.commit_message).toBe('test stored diff');
    expect(row.diff_unified).toBeNull();
    expect(row.diff_strategy).toBe('stored');
    expect(row.diff_summary_json).toEqual(summaryJson);
  });

  it('immutability trigger rejects UPDATE', async () => {
    if (!hasDb || !testBranchId) return;
    const commitHash = `h${randomUUID().replace(/-/g, '').slice(0, 62)}`;
    await query(
      `INSERT INTO manuscript_branch_commits (branch_id, commit_hash, commit_message)
       VALUES ($1, $2, $3)`,
      [testBranchId, commitHash, 'immutability test']
    );
    const idResult = await query(
      `SELECT id FROM manuscript_branch_commits WHERE branch_id = $1 AND commit_hash = $2 LIMIT 1`,
      [testBranchId, commitHash]
    );
    const commitId = idResult.rows[0]?.id;
    expect(commitId).toBeDefined();

    await expect(
      query(`UPDATE manuscript_branch_commits SET commit_message = 'tampered' WHERE id = $1`, [commitId])
    ).rejects.toThrow(/UPDATE not allowed|append-only/);
  });

  it('immutability trigger rejects DELETE', async () => {
    if (!hasDb || !testBranchId) return;
    const commitHash = `h${randomUUID().replace(/-/g, '').slice(0, 62)}`;
    await query(
      `INSERT INTO manuscript_branch_commits (branch_id, commit_hash, commit_message)
       VALUES ($1, $2, $3)`,
      [testBranchId, commitHash, 'delete test']
    );
    const idResult = await query(
      `SELECT id FROM manuscript_branch_commits WHERE branch_id = $1 AND commit_hash = $2 LIMIT 1`,
      [testBranchId, commitHash]
    );
    const commitId = idResult.rows[0]?.id;
    expect(commitId).toBeDefined();

    await expect(query(`DELETE FROM manuscript_branch_commits WHERE id = $1`, [commitId])).rejects.toThrow(
      /DELETE not allowed|append-only/
    );
  });
});
