/**
 * Helper to determine if the database is reachable before running DB-backed tests.
 * 
 * Returns false when:
 * - DATABASE_URL is not set
 * - Connection refused / host unreachable
 * - Authentication failure (treated as unavailable for local dev)
 * 
 * This prevents test suites from failing in beforeAll when Postgres is down.
 */

import { Pool } from 'pg';

let cachedResult: boolean | null = null;

export async function dbAvailable(): Promise<boolean> {
  // Return cached result to avoid multiple connection attempts
  if (cachedResult !== null) {
    return cachedResult;
  }

  // No DATABASE_URL means DB is not available
  if (!process.env.DATABASE_URL) {
    cachedResult = false;
    return false;
  }

  // Try to establish a connection
  const testPool = new Pool({
    connectionString: process.env.DATABASE_URL,
    connectionTimeoutMillis: 2000, // Fail fast
  });

  try {
    const client = await testPool.connect();
    await client.query('SELECT 1');
    client.release();
    await testPool.end();
    cachedResult = true;
    return true;
  } catch (error: any) {
    // Connection errors indicate DB is not available
    // ECONNREFUSED, ETIMEDOUT, EHOSTUNREACH, authentication failures, etc.
    cachedResult = false;
    return false;
  }
}
