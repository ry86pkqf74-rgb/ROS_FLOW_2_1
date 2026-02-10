#!/usr/bin/env node
/**
 * ci-migrate.mjs — Apply all orchestrator SQL migrations in order using DATABASE_URL.
 *
 * Used by CI and local dev. Requires DATABASE_URL and psql on PATH.
 *
 * Usage (from researchflow-production-main/):
 *   DATABASE_URL=postgresql://user:pass@host:5432/db node services/orchestrator/scripts/ci-migrate.mjs
 *
 * Migrations directory: services/orchestrator/migrations
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

// Guard: detect duplicate numeric prefixes
const prefixMap = new Map();
for (const name of files) {
  const match = name.match(/^(\d+)/);
  if (match) {
    const prefix = match[1];
    if (!prefixMap.has(prefix)) {
      prefixMap.set(prefix, []);
    }
    prefixMap.get(prefix).push(name);
  }
}

for (const [prefix, names] of prefixMap) {
  if (names.length > 1) {
    console.error('ci-migrate: Duplicate numeric prefix detected:', prefix);
    console.error('Conflicting files:');
    names.forEach(n => console.error('  -', n));
    console.error('Each migration must have a unique numeric prefix.');
    process.exit(1);
  }
}

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
  
  // Handle spawn errors (e.g., psql not found)
  if (result.error) {
    console.error('ci-migrate: Failed to execute psql (spawn error):', result.error.message);
    if (result.error.code === 'ENOENT') {
      console.error('psql not found on PATH');
      console.error('');
      console.error('Install psql:');
      console.error('  Ubuntu/Debian (CI/local):');
      console.error('    sudo apt-get update && sudo apt-get install -y postgresql-client');
      console.error('  macOS (Homebrew):');
      console.error('    brew install libpq');
      console.error('    echo \'export PATH="$(brew --prefix libpq)/bin:$PATH"\' >> ~/.zshrc');
      console.error('    (then open a new shell)');
    }
    process.exit(1);
  }
  
  // Handle non-zero exit status
  if (result.status !== 0) {
    console.error('ci-migrate: Failed applying', name);
    console.error('Exit status:', result.status);
    if (result.signal) {
      console.error('Signal:', result.signal);
    }
    process.exit(result.status || 1);
  }
}

console.log('ci-migrate: All', files.length, 'migrations applied.');
