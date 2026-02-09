import { describe, it, expect, beforeEach, vi } from 'vitest';
import { appendEvent, verifyStreamIntegrity, type DbClient } from '../../../../services/orchestrator/src/services/audit.service';
import { computePayloadHash, computeEventHash } from '../../../../services/orchestrator/src/services/audit-hash.util';

/** Create a mock DbClient whose query fn can be programmed per-call. */
function createMockTx() {
  return { query: vi.fn() } as any;
}

describe('appendEvent', () => {
  let tx: ReturnType<typeof createMockTx>;

  beforeEach(() => {
    tx = createMockTx();
  });

  it('creates first event in a new stream (seq=1, prev_event_hash=null)', async () => {
    const streamId = 'stream-uuid-1';

    // INSERT stream → new row returned
    tx.query.mockResolvedValueOnce({ rows: [{ stream_id: streamId }], rowCount: 1 });
    // SELECT last event → empty (first event)
    tx.query.mockResolvedValueOnce({ rows: [], rowCount: 0 });
    // INSERT event
    tx.query.mockResolvedValueOnce({
      rows: [{
        id: 'evt-1', stream_id: streamId, seq: 1,
        created_at: new Date(), run_id: null, trace_id: null, node_id: null,
        actor_type: 'SYSTEM', actor_id: null, service: 'orchestrator',
        action: 'CREATE', resource_type: 'MANUSCRIPT', resource_id: 'ms-1',
        before_hash: null, after_hash: null,
        payload_json: {}, payload_hash: 'ph', prev_event_hash: null, event_hash: 'eh',
      }],
      rowCount: 1,
    });

    const result = await appendEvent(tx, {
      stream_type: 'MANUSCRIPT',
      stream_key: 'ms-1',
      actor_type: 'SYSTEM',
      service: 'orchestrator',
      action: 'CREATE',
      resource_type: 'MANUSCRIPT',
      resource_id: 'ms-1',
    });

    expect(result.stream_id).toBe(streamId);

    // Verify query calls: INSERT stream, SELECT last (FOR UPDATE), INSERT event
    expect(tx.query).toHaveBeenCalledTimes(3);

    // First call: INSERT stream
    expect(tx.query.mock.calls[0][0]).toContain('INSERT INTO audit_event_streams');

    // Second call: SELECT … FOR UPDATE
    expect(tx.query.mock.calls[1][0]).toContain('FOR UPDATE');

    // Third call: INSERT event with parameterized values
    expect(tx.query.mock.calls[2][0]).toContain('INSERT INTO audit_events');
    const insertValues = tx.query.mock.calls[2][1];
    expect(insertValues[0]).toBe(streamId); // stream_id
    expect(insertValues[1]).toBe(1);        // seq
    expect(insertValues[15]).toBeNull();     // prev_event_hash
  });

  it('appends second event with chained prev_event_hash', async () => {
    const streamId = 'stream-uuid-1';
    const prevHash = 'abc123def456';

    // INSERT stream → conflict, no rows returned
    tx.query.mockResolvedValueOnce({ rows: [], rowCount: 0 });
    // SELECT stream (fallback)
    tx.query.mockResolvedValueOnce({ rows: [{ stream_id: streamId }], rowCount: 1 });
    // SELECT last event → existing with seq=1
    tx.query.mockResolvedValueOnce({
      rows: [{ seq: 1, event_hash: prevHash }],
      rowCount: 1,
    });
    // INSERT event
    tx.query.mockResolvedValueOnce({
      rows: [{
        id: 'evt-2', stream_id: streamId, seq: 2,
        created_at: new Date(), run_id: null, trace_id: null, node_id: null,
        actor_type: 'USER', actor_id: 'u-1', service: 'orchestrator',
        action: 'UPDATE', resource_type: 'MANUSCRIPT', resource_id: 'ms-1',
        before_hash: 'bh', after_hash: 'ah',
        payload_json: {}, payload_hash: 'ph', prev_event_hash: prevHash, event_hash: 'eh2',
      }],
      rowCount: 1,
    });

    const result = await appendEvent(tx, {
      stream_type: 'MANUSCRIPT',
      stream_key: 'ms-1',
      actor_type: 'USER',
      actor_id: 'u-1',
      service: 'orchestrator',
      action: 'UPDATE',
      resource_type: 'MANUSCRIPT',
      resource_id: 'ms-1',
      before_hash: 'bh',
      after_hash: 'ah',
    });

    expect(result.seq).toBe(2);

    // 4 queries: INSERT stream, SELECT stream, SELECT last, INSERT event
    expect(tx.query).toHaveBeenCalledTimes(4);

    // INSERT event values
    const insertValues = tx.query.mock.calls[3][1];
    expect(insertValues[1]).toBe(2);         // seq
    expect(insertValues[15]).toBe(prevHash);  // prev_event_hash
  });

  it('returns existing event on dedupe_key match (idempotency)', async () => {
    const streamId = 'stream-uuid-1';
    const existingRow = {
      id: 'evt-existing', stream_id: streamId, seq: 1,
      payload_json: { dedupe_key: 'dkey-1' },
    };

    // INSERT stream → new
    tx.query.mockResolvedValueOnce({ rows: [{ stream_id: streamId }], rowCount: 1 });
    // Dedupe SELECT → found
    tx.query.mockResolvedValueOnce({ rows: [existingRow], rowCount: 1 });

    const result = await appendEvent(tx, {
      stream_type: 'RUN',
      stream_key: 'run-1',
      actor_type: 'SYSTEM',
      service: 'worker',
      action: 'EXECUTE',
      resource_type: 'STAGE',
      resource_id: 's-1',
      dedupe_key: 'dkey-1',
    });

    expect(result.id).toBe('evt-existing');
    // Only 2 queries: INSERT stream + dedupe SELECT (no FOR UPDATE, no INSERT event)
    expect(tx.query).toHaveBeenCalledTimes(2);
  });

  it('sanitizes payload in HIPAA mode', async () => {
    const streamId = 'stream-uuid-1';

    // INSERT stream
    tx.query.mockResolvedValueOnce({ rows: [{ stream_id: streamId }], rowCount: 1 });
    // SELECT last event
    tx.query.mockResolvedValueOnce({ rows: [], rowCount: 0 });
    // INSERT event
    tx.query.mockResolvedValueOnce({
      rows: [{
        id: 'evt-h', stream_id: streamId, seq: 1,
        payload_json: { user_id: 'u-1' },
      }],
      rowCount: 1,
    });

    await appendEvent(
      tx,
      {
        stream_type: 'GLOBAL',
        stream_key: 'global',
        actor_type: 'USER',
        service: 'orchestrator',
        action: 'VIEW',
        resource_type: 'PATIENT',
        resource_id: 'p-1',
        payload: { user_id: 'u-1', notes: 'patient has condition X' },
      },
      { hipaaMode: true },
    );

    // Check the payload_json passed to INSERT
    const insertValues = tx.query.mock.calls[2][1];
    const payloadJson = JSON.parse(insertValues[13]); // payload_json is param 14 (index 13)
    expect(payloadJson.user_id).toBe('u-1');
    expect(payloadJson.notes).toBeUndefined();
  });

  it('uses parameterized queries (no string interpolation)', async () => {
    const streamId = 'stream-uuid-1';

    tx.query.mockResolvedValueOnce({ rows: [{ stream_id: streamId }], rowCount: 1 });
    tx.query.mockResolvedValueOnce({ rows: [], rowCount: 0 });
    tx.query.mockResolvedValueOnce({ rows: [{ id: 'evt' }], rowCount: 1 });

    await appendEvent(tx, {
      stream_type: 'GLOBAL',
      stream_key: 'global',
      actor_type: 'SYSTEM',
      service: 'orchestrator',
      action: 'TEST',
      resource_type: 'TEST',
      resource_id: 'test-1',
    });

    // Every query should use $N placeholders
    for (const call of tx.query.mock.calls) {
      const sql = call[0] as string;
      if (call[1] && (call[1] as any[]).length > 0) {
        expect(sql).toMatch(/\$\d/);
      }
    }
  });
});

describe('verifyStreamIntegrity', () => {
  it('returns valid for an empty stream', async () => {
    const tx = createMockTx();
    tx.query.mockResolvedValueOnce({ rows: [], rowCount: 0 });

    const result = await verifyStreamIntegrity(tx, 'stream-1');
    expect(result).toEqual({ valid: true });
  });

  it('returns valid for a correct chain', async () => {
    const tx = createMockTx();

    const payloadHash = computePayloadHash({ key: 'value' });

    const event1Hash = computeEventHash({
      stream_id: 's-1', seq: 1, prev_event_hash: null,
      payload_hash: payloadHash, before_hash: null, after_hash: null,
      actor_type: 'SYSTEM', actor_id: null, service: 'test',
      action: 'CREATE', resource_type: 'T', resource_id: 'r-1',
    });

    const event2Hash = computeEventHash({
      stream_id: 's-1', seq: 2, prev_event_hash: event1Hash,
      payload_hash: payloadHash, before_hash: null, after_hash: null,
      actor_type: 'SYSTEM', actor_id: null, service: 'test',
      action: 'UPDATE', resource_type: 'T', resource_id: 'r-1',
    });

    tx.query.mockResolvedValueOnce({
      rows: [
        {
          stream_id: 's-1', seq: 1, prev_event_hash: null,
          payload_hash: payloadHash, before_hash: null, after_hash: null,
          actor_type: 'SYSTEM', actor_id: null, service: 'test',
          action: 'CREATE', resource_type: 'T', resource_id: 'r-1',
          event_hash: event1Hash,
        },
        {
          stream_id: 's-1', seq: 2, prev_event_hash: event1Hash,
          payload_hash: payloadHash, before_hash: null, after_hash: null,
          actor_type: 'SYSTEM', actor_id: null, service: 'test',
          action: 'UPDATE', resource_type: 'T', resource_id: 'r-1',
          event_hash: event2Hash,
        },
      ],
      rowCount: 2,
    });

    const result = await verifyStreamIntegrity(tx, 's-1');
    expect(result).toEqual({ valid: true });
  });

  it('detects tampered event_hash', async () => {
    const tx = createMockTx();

    tx.query.mockResolvedValueOnce({
      rows: [
        {
          stream_id: 's-1', seq: 1, prev_event_hash: null,
          payload_hash: 'ph', before_hash: null, after_hash: null,
          actor_type: 'SYSTEM', actor_id: null, service: 'test',
          action: 'CREATE', resource_type: 'T', resource_id: 'r-1',
          event_hash: 'tampered-hash',
        },
      ],
      rowCount: 1,
    });

    const result = await verifyStreamIntegrity(tx, 's-1');
    expect(result.valid).toBe(false);
    expect(result.brokenAtSeq).toBe(1);
  });

  it('detects broken chain link', async () => {
    const tx = createMockTx();
    const payloadHash = computePayloadHash({});

    const event1Hash = computeEventHash({
      stream_id: 's-1', seq: 1, prev_event_hash: null,
      payload_hash: payloadHash, before_hash: null, after_hash: null,
      actor_type: 'SYSTEM', actor_id: null, service: 'test',
      action: 'CREATE', resource_type: 'T', resource_id: 'r-1',
    });

    tx.query.mockResolvedValueOnce({
      rows: [
        {
          stream_id: 's-1', seq: 1, prev_event_hash: null,
          payload_hash: payloadHash, before_hash: null, after_hash: null,
          actor_type: 'SYSTEM', actor_id: null, service: 'test',
          action: 'CREATE', resource_type: 'T', resource_id: 'r-1',
          event_hash: event1Hash,
        },
        {
          stream_id: 's-1', seq: 2, prev_event_hash: 'wrong-link',
          payload_hash: payloadHash, before_hash: null, after_hash: null,
          actor_type: 'SYSTEM', actor_id: null, service: 'test',
          action: 'UPDATE', resource_type: 'T', resource_id: 'r-1',
          event_hash: 'some-hash',
        },
      ],
      rowCount: 2,
    });

    const result = await verifyStreamIntegrity(tx, 's-1');
    expect(result.valid).toBe(false);
    expect(result.brokenAtSeq).toBe(2);
  });
});
