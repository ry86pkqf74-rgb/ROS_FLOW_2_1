/**
 * dbAvailable – lightweight probe for Postgres availability.
 *
 * Usage in tests:
 *   import { dbAvailable } from '../helpers/dbAvailable';
 *
 *   const canConnect = await dbAvailable();
 *   const describeDb = canConnect ? describe : describe.skip;
 *
 * Requires DATABASE_URL in the environment. Returns false (never throws)
 * when the database is unreachable, misconfigured, or the env var is absent.
 */

import pg from 'pg';

const { Client } = pg;

/**
 * Attempt a quick `SELECT 1` against DATABASE_URL.
 * Resolves `true` if the query succeeds, `false` otherwise.
 * Timeout is kept short (3 s) so test suites fail-fast when DB is down.
 */
export async function dbAvailable(
  url: string | undefined = process.env.DATABASE_URL,
): Promise<boolean> {
  if (!url) return false;

  const client = new Client({
    connectionString: url,
    connectionTimeoutMillis: 3_000,
    statement_timeout: 3_000,
  });

  try {
    await client.connect();
    await client.query('SELECT 1');
    return true;
  } catch {
    return false;
  } finally {
    try {
      await client.end();
    } catch {
      // ignore teardown errors
    }
  }
}
