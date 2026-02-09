/**
 * Tests for migration 020_edit_sessions.
 *
 * Validates:
 *  1. Inserting a draft edit session succeeds
 *  2. Invalid status values are rejected by the CHECK constraint
 *  3. Updating a row bumps updated_at via the trigger
 *
 * Skips the entire suite when DATABASE_URL is missing or the database
 * is unreachable (CI without Postgres, local offline, etc.).
 */

import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { readFileSync } from 'fs';
import { join } from 'path';
import pg from 'pg';
import { dbAvailable } from '../helpers/dbAvailable';

const { Client } = pg;

/* ------------------------------------------------------------------ */
/*  Gate: skip the whole file when the database is unavailable         */
/* ------------------------------------------------------------------ */
const DB_URL = process.env.DATABASE_URL;
const canConnect = await dbAvailable(DB_URL);
const describeDb = canConnect ? describe : describe.skip;

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

/** Path to the migration SQL (relative to repo root) */
const MIGRATION_SQL_PATH = join(
  __dirname,
  '../../../services/orchestrator/migrations/020_edit_sessions.sql',
);

/** Ensure the prerequisite table exists so the FK doesn't blow up. */
const SETUP_SQL = `
  CREATE TABLE IF NOT EXISTS manuscript_branches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL DEFAULT 'test-branch'
  );
`;

/** Clean up test artefacts (reverse order of dependency). */
const TEARDOWN_SQL = `
  DROP TABLE IF EXISTS edit_sessions CASCADE;
  DROP FUNCTION IF EXISTS update_edit_session_updated_at() CASCADE;
  DROP TABLE IF EXISTS manuscript_branches CASCADE;
`;

/* ------------------------------------------------------------------ */
/*  Test suite                                                         */
/* ------------------------------------------------------------------ */
describeDb('migration 020_edit_sessions', () => {
  let client: InstanceType<typeof Client>;
  let branchId: string;
  let manuscriptId: string;

  beforeAll(async () => {
    client = new Client({ connectionString: DB_URL });
    await client.connect();

    // Clean slate → prerequisite → migration
    await client.query(TEARDOWN_SQL);
    await client.query(SETUP_SQL);

    // Read and apply the migration
    const migrationSql = readFileSync(MIGRATION_SQL_PATH, 'utf8');
    await client.query(migrationSql);

    // Seed a branch row so FK succeeds
    const branchRes = await client.query(
      `INSERT INTO manuscript_branches (name) VALUES ('test-branch') RETURNING id`,
    );
    branchId = branchRes.rows[0].id;
    manuscriptId = '00000000-0000-4000-8000-000000000001';
  });

  afterAll(async () => {
    try {
      await client.query(TEARDOWN_SQL);
    } catch {
      // best-effort cleanup
    }
    await client.end();
  });

  /* ---- 1. Insert a draft session ---- */
  it('inserts a draft edit session', async () => {
    const res = await client.query(
      `INSERT INTO edit_sessions (branch_id, manuscript_id, status)
       VALUES ($1, $2, 'draft')
       RETURNING id, status, created_at, updated_at`,
      [branchId, manuscriptId],
    );

    expect(res.rows).toHaveLength(1);
    const row = res.rows[0];
    expect(row.status).toBe('draft');
    expect(row.created_at).toBeTruthy();
    expect(row.updated_at).toBeTruthy();
  });

  /* ---- 2. Invalid status is rejected ---- */
  it('rejects an invalid status value', async () => {
    // Need a new branch for UNIQUE(branch_id)
    const b = await client.query(
      `INSERT INTO manuscript_branches (name) VALUES ('bad-status-branch') RETURNING id`,
    );

    await expect(
      client.query(
        `INSERT INTO edit_sessions (branch_id, manuscript_id, status)
         VALUES ($1, $2, 'bogus')`,
        [b.rows[0].id, manuscriptId],
      ),
    ).rejects.toThrow(); // CHECK constraint violation
  });

  /* ---- 3. Updating status bumps updated_at ---- */
  it('updates updated_at when status changes', async () => {
    // Fetch the existing row (inserted in test 1)
    const before = await client.query(
      `SELECT id, updated_at FROM edit_sessions WHERE branch_id = $1`,
      [branchId],
    );
    expect(before.rows).toHaveLength(1);
    const oldUpdatedAt = before.rows[0].updated_at;

    // Small delay to ensure timestamp difference is measurable
    await new Promise((r) => setTimeout(r, 50));

    await client.query(
      `UPDATE edit_sessions SET status = 'submitted', submitted_at = NOW()
       WHERE id = $1`,
      [before.rows[0].id],
    );

    const after = await client.query(
      `SELECT updated_at FROM edit_sessions WHERE id = $1`,
      [before.rows[0].id],
    );

    expect(new Date(after.rows[0].updated_at).getTime()).toBeGreaterThan(
      new Date(oldUpdatedAt).getTime(),
    );
  });

  /* ---- 4. Migration is idempotent (re-run without error) ---- */
  it('can be applied again without error (idempotent)', async () => {
    const migrationSql = readFileSync(MIGRATION_SQL_PATH, 'utf8');
    // Should not throw
    await expect(client.query(migrationSql)).resolves.toBeDefined();
  });
});
