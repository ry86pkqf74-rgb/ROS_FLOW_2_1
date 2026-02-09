/**
 * Audit Ledger Service - DB-backed integration tests
 *
 * Direct integration test for ledger writer invariants: seq monotonicity,
 * deterministic stream, hash fields present, and DB cleanup.
 * Skips automatically when the database is unavailable.
 */

import { describe, it, expect, beforeAll } from 'vitest';
import { randomUUID } from 'crypto';

import { pool, query } from '../../../db';
import { dbAvailable as checkDbAvailable } from '../../__tests__/helpers/dbAvailable';
import { appendAuditEvent } from '../audit-ledger.service';

const hasDb = !!pool;
let dbReady = false;

/** SHA-256 hex is 64 lowercase hex chars */
const HEX_HASH_REGEX = /^[a-f0-9]{64}$/;

describe('AuditLedger service (integration)', {
  skip: !hasDb ? 'DATABASE_URL not set' : false,
}, () => {
  beforeAll(async () => {
    if (!hasDb) return;
    dbReady = await checkDbAvailable();
  });

  it('appends two events to a unique stream and enforces monotonic seq and hash shape', async () => {
    if (!dbReady) return;

    const streamKey = `ledger-test:${randomUUID()}`;
    const streamType = 'LEDGER_TEST';
    let streamId: string | null = null;

    const client = await pool!.connect();
    try {
      await client.query('BEGIN');

      const streamResult = await client.query(
        `INSERT INTO audit_event_streams (stream_type, stream_key)
         VALUES ($1, $2)
         ON CONFLICT (stream_type, stream_key) DO NOTHING
         RETURNING stream_id`,
        [streamType, streamKey],
      );
      if (streamResult.rows.length === 0) {
        const sel = await client.query(
          `SELECT stream_id FROM audit_event_streams WHERE stream_type = $1 AND stream_key = $2`,
          [streamType, streamKey],
        );
        streamId = sel.rows[0]?.stream_id ?? null;
      } else {
        streamId = streamResult.rows[0].stream_id;
      }
      expect(streamId).toBeTruthy();

      const baseInput = {
        streamId: streamId!,
        action: 'LEDGER_TEST_EVENT',
        resourceType: 'LEDGER_TEST',
        resourceId: randomUUID(),
        payload: { test: true, id: randomUUID() },
      };

      const row1 = await appendAuditEvent(client, { ...baseInput, payload: { ...baseInput.payload, seq: 1 } });
      const row2 = await appendAuditEvent(client, { ...baseInput, payload: { ...baseInput.payload, seq: 2 } });

      expect(row1.seq).toBe(1);
      expect(row2.seq).toBe(2);
      expect(row1.payload_hash).toBeTruthy();
      expect(row2.payload_hash).toBeTruthy();
      expect(row1.event_hash).toBeTruthy();
      expect(row2.event_hash).toBeTruthy();
      expect(row1.payload_hash).toMatch(HEX_HASH_REGEX);
      expect(row2.payload_hash).toMatch(HEX_HASH_REGEX);
      expect(row1.event_hash).toMatch(HEX_HASH_REGEX);
      expect(row2.event_hash).toMatch(HEX_HASH_REGEX);
      expect(row1.prev_event_hash).toBeNull();
      expect(row2.prev_event_hash).toBe(row1.event_hash);

      await client.query('COMMIT');
    } catch (e) {
      await client.query('ROLLBACK');
      throw e;
    } finally {
      client.release();
    }

    const readResult = await query(
      `SELECT seq, payload_hash, event_hash, prev_event_hash
       FROM audit_events
       WHERE stream_id = $1
       ORDER BY seq ASC`,
      [streamId],
    );
    const rows = readResult.rows;

    expect(rows.length).toBe(2);
    expect(Number(rows[0].seq)).toBe(1);
    expect(Number(rows[1].seq)).toBe(2);
    expect(rows[0].payload_hash).toBeTruthy();
    expect(rows[1].payload_hash).toBeTruthy();
    expect(rows[0].event_hash).toBeTruthy();
    expect(rows[1].event_hash).toBeTruthy();
    expect(rows[0].payload_hash).toMatch(HEX_HASH_REGEX);
    expect(rows[1].payload_hash).toMatch(HEX_HASH_REGEX);
    expect(rows[0].event_hash).toMatch(HEX_HASH_REGEX);
    expect(rows[1].event_hash).toMatch(HEX_HASH_REGEX);
    expect(rows[0].prev_event_hash).toBeNull();
    expect(rows[1].prev_event_hash).toBe(rows[0].event_hash);

    await query('DELETE FROM audit_events WHERE stream_id = $1', [streamId]);
    await query('DELETE FROM audit_event_streams WHERE stream_id = $1', [streamId]);

    const afterCleanup = await query(
      'SELECT 1 FROM audit_events WHERE stream_id = $1',
      [streamId],
    );
    expect(afterCleanup.rows.length).toBe(0);
  });
});
