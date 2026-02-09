/**
 * Migration 018: manuscript_branch_commits
 *
 * - Migration applies without error.
 * - Insert/select invariants: one row insertible, select returns same commit_hash and created_at set.
 *
 * Integration tests: run only when DATABASE_URL is set (e.g. CI or local Postgres).
 */

import { describe, it, expect, beforeAll } from 'vitest';
import { readFileSync } from 'fs';
import { join } from 'path';
import { randomUUID } from 'crypto';
import { query } from '../../../db';
import { dbAvailable } from '../helpers/dbAvailable';

const hasDb = await dbAvailable();

describe('018_manuscript_branch_commits', { skip: !hasDb ? 'DB unavailable or unreachable' : false }, () => {
  let testBranchId: string;
  const testManuscriptId = randomUUID();

  beforeAll(async () => {
    if (!hasDb) return;
    // Ensure a branch exists for FK (manuscript_branches from migration 003)
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

  it('applies migration 018 without error', async () => {
    if (!hasDb) return;
    const migrationPath = join(__dirname, '../../../../migrations/018_manuscript_branch_commits.sql');
    const sql = readFileSync(migrationPath, 'utf-8');
    await expect(query(sql)).resolves.toBeDefined();
  });

  it('insert and select satisfy invariants', async () => {
    if (!hasDb || !testBranchId) return;
    const commitHash = `h${randomUUID().replace(/-/g, '').slice(0, 62)}`;
    const commitMessage = 'test commit';

    await query(
      `INSERT INTO manuscript_branch_commits (branch_id, commit_hash, commit_message, created_by)
       VALUES ($1, $2, $3, $4)`,
      [testBranchId, commitHash, commitMessage, null]
    );

    const selectResult = await query(
      `SELECT id, branch_id, commit_hash, commit_message, created_at
       FROM manuscript_branch_commits
       WHERE branch_id = $1`,
      [testBranchId]
    );

    expect(selectResult.rows.length).toBeGreaterThanOrEqual(1);
    const row = selectResult.rows.find((r: { commit_hash: string }) => r.commit_hash === commitHash);
    expect(row).toBeDefined();
    expect(row!.commit_hash).toBe(commitHash);
    expect(row!.commit_message).toBe(commitMessage);
    expect(row!.created_at).toBeDefined();
    expect(new Date(row!.created_at).getTime()).toBeLessThanOrEqual(Date.now() + 1000);
  });
});
