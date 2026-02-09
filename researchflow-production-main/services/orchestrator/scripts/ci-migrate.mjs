#!/usr/bin/env node
/**
 * ci-migrate.mjs — Apply all orchestrator SQL migrations in order using DATABASE_URL.
 *
 * Used by CI and local dev. Requires DATABASE_URL and psql on PATH.
 *
 * Usage:
 *   DATABASE_URL=postgresql://user:pass@host:5432/db node researchflow-production-main/services/orchestrator/scripts/ci-migrate.mjs
 *
 * Migrations directory: researchflow-production-main/services/orchestrator/migrations
 * Applies all *.sql in version order (sort -V). Exits on first error (ON_ERROR_STOP=1).
 */
import { readdirSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { spawnSync } from 'child_process';

const __dirname = dirname(fileURLToPath(import.meta.url));
const MIGRATIONS_DIR = join(__dirname, '..', 'migrations');

const DATABASE_URL = process.env.DATABASE_URL;
if (!DATABASE_URL || DATABASE_URL.trim() === '') {
  console.error('ci-migrate: DATABASE_URL is required. Set it and run again.');
  process.exit(1);
}

let files;
try {
  files = readdirSync(MIGRATIONS_DIR);
} catch (e) {
  console.error('ci-migrate: Migrations directory not found at', MIGRATIONS_DIR);
  process.exit(1);
}

files = files
  .filter(f => f.endsWith('.sql'))
  .sort((a, b) => a.localeCompare(b, undefined, { numeric: true }));

if (files.length === 0) {
  console.log('ci-migrate: No .sql files in', MIGRATIONS_DIR);
  process.exit(0);
}

for (const name of files) {
  const path = join(MIGRATIONS_DIR, name);
  console.log('Applying migration:', name);
  const result = spawnSync('psql', [DATABASE_URL, '-v', 'ON_ERROR_STOP=1', '-f', path], {
    stdio: 'inherit',
    env: process.env,
  });
  if (result.status !== 0) {
    console.error('ci-migrate: Failed applying', name);
    process.exit(result.status || 1);
  }
}

console.log('ci-migrate: All', files.length, 'migrations applied.');
