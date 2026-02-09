#!/usr/bin/env node
/**
 * run-migration-020.mjs — Apply migration 020_edit_sessions.sql
 *
 * Usage:
 *   DATABASE_URL=postgres://user:pass@host:5432/db node scripts/run-migration-020.mjs
 *
 * Or, from the orchestrator directory with a .env file:
 *   node scripts/run-migration-020.mjs
 *
 * The script will:
 *   1. Read DATABASE_URL from env (or dotenv)
 *   2. Test connectivity (SELECT 1) with a 5-second timeout
 *   3. Apply the migration SQL
 *   4. Verify the edit_sessions table exists
 *   5. Print a summary and exit 0 on success
 *
 * Exit codes:
 *   0 — success
 *   1 — missing DATABASE_URL or migration file
 *   2 — cannot connect to database
 *   3 — migration SQL failed
 */
import 'dotenv/config';
import pg from 'pg';
import { readFileSync, existsSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

/* ---- paths ---- */
const __dirname = dirname(fileURLToPath(import.meta.url));
const sqlPath = join(__dirname, '../migrations/020_edit_sessions.sql');

/* ---- pre-flight checks ---- */
if (!existsSync(sqlPath)) {
  console.error(`❌  Migration file not found: ${sqlPath}`);
  process.exit(1);
}

const url = process.env.DATABASE_URL;
if (!url) {
  console.error(
    '❌  DATABASE_URL is not set.\n' +
      '\n' +
      'Set it in one of these ways:\n' +
      '  1. Export:  export DATABASE_URL=postgres://user:pass@host:5432/db\n' +
      '  2. Inline:  DATABASE_URL=... node scripts/run-migration-020.mjs\n' +
      '  3. .env:    Add DATABASE_URL to services/orchestrator/.env\n',
  );
  process.exit(1);
}

/* ---- read SQL ---- */
const sql = readFileSync(sqlPath, 'utf8');

/* ---- connect with timeout ---- */
const client = new pg.Client({
  connectionString: url,
  connectionTimeoutMillis: 5_000,
  statement_timeout: 30_000,
});

console.log('🔌  Connecting to database…');
try {
  await client.connect();
  await client.query('SELECT 1'); // quick probe
} catch (err) {
  console.error(
    `❌  Cannot connect to database.\n` +
      `    URL (masked): ${url.replace(/\/\/[^@]+@/, '//***:***@')}\n` +
      `    Error: ${err?.message || err}\n` +
      '\n' +
      'Check that:\n' +
      '  • The database server is running\n' +
      '  • DATABASE_URL credentials and host are correct\n' +
      '  • Network / firewall allows the connection\n',
  );
  process.exit(2);
}

/* ---- apply migration ---- */
console.log('📄  Applying migration 020_edit_sessions…');
try {
  await client.query(sql);
} catch (err) {
  console.error(
    `❌  Migration failed!\n` +
      `    Error: ${err?.message || err}\n` +
      (err?.detail ? `    Detail: ${err.detail}\n` : '') +
      (err?.hint ? `    Hint: ${err.hint}\n` : ''),
  );
  await client.end();
  process.exit(3);
}

/* ---- verify ---- */
try {
  const verify = await client.query(
    `SELECT column_name FROM information_schema.columns
     WHERE table_name = 'edit_sessions' ORDER BY ordinal_position`,
  );
  const cols = verify.rows.map((r) => r.column_name);
  console.log(`✅  Migration 020_edit_sessions applied successfully.`);
  console.log(`    Columns: ${cols.join(', ')}`);
} catch {
  // Verification is best-effort; migration itself succeeded.
  console.log('✅  Migration 020_edit_sessions applied (verification skipped).');
}

await client.end();
process.exit(0);
