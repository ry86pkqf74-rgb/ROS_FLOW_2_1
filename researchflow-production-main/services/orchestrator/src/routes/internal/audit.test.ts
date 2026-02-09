/**
 * Internal audit ingest route integration tests.
 * Covers GET /internal/audit/ping and POST /internal/audit/events with auth and shape.
 */

import express from 'express';
import request from 'supertest';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

import internalRoutes from './index';

const TEST_KEY = 'test-internal-key-12345';

vi.mock('../../../db.js', () => ({
  pool: {
    connect: vi.fn(),
  },
}));

vi.mock('../../services/audit.service', () => ({
  appendEvent: vi.fn(),
}));

function createTestApp() {
  const app = express();
  app.use(express.json());
  app.use('/internal', internalRoutes);
  return app;
}

describe('Internal audit ingest routes', () => {
  let app: express.Application;
  const origInternalKey = process.env.INTERNAL_API_KEY;

  beforeEach(() => {
    app = createTestApp();
    process.env.INTERNAL_API_KEY = TEST_KEY;
    vi.clearAllMocks();
  });

  afterEach(() => {
    if (origInternalKey !== undefined) process.env.INTERNAL_API_KEY = origInternalKey;
    else delete process.env.INTERNAL_API_KEY;
  });

  describe('GET /internal/audit/ping', () => {
    it('returns ok and audit_ingest_enabled when INTERNAL_API_KEY is set', async () => {
      const res = await request(app)
        .get('/internal/audit/ping')
        .expect(200);

      expect(res.body).toMatchObject({ ok: true, audit_ingest_enabled: true });
    });

    it('returns audit_ingest_enabled false when INTERNAL_API_KEY is unset', async () => {
      delete process.env.INTERNAL_API_KEY;
      const res = await request(app)
        .get('/internal/audit/ping')
        .expect(200);

      expect(res.body).toMatchObject({ ok: true, audit_ingest_enabled: false });
    });
  });

  describe('POST /internal/audit/events', () => {
    const validBody = {
      stream_type: 'MANUSCRIPT',
      stream_key: 'ms-123',
      actor_type: 'USER',
      actor_id: 'user-1',
      service: 'orchestrator',
      action: 'test',
      resource_type: 'manuscript',
      resource_id: 'ms-123',
    };

    it('returns 401 when x-internal-api-key header is missing', async () => {
      const res = await request(app)
        .post('/internal/audit/events')
        .send(validBody)
        .expect(401);

      expect(res.body).toMatchObject({ ok: false, error: 'unauthorized' });
    });

    it('returns 401 when x-internal-api-key is wrong', async () => {
      const res = await request(app)
        .post('/internal/audit/events')
        .set('x-internal-api-key', 'wrong-key')
        .send(validBody)
        .expect(401);

      expect(res.body).toMatchObject({ ok: false, error: 'unauthorized' });
    });

    it('returns 503 when INTERNAL_API_KEY is unset', async () => {
      delete process.env.INTERNAL_API_KEY;
      const res = await request(app)
        .post('/internal/audit/events')
        .set('x-internal-api-key', TEST_KEY)
        .send(validBody);

      expect(res.status).toBe(503);
      expect(res.body).toMatchObject({ ok: false, message: expect.any(String) });
    });

    it('returns 200 and ok/audit_event_id/stream_id/seq/event_hash with valid key and body', async () => {
      const { pool } = await import('../../../db.js');
      const AuditService = await import('../../services/audit.service');

      const mockClient = {
        query: vi.fn()
          .mockResolvedValueOnce(undefined)  // BEGIN
          .mockResolvedValueOnce(undefined)  // COMMIT
          .mockResolvedValue(undefined),
        release: vi.fn(),
      };
      (pool as any).connect.mockResolvedValue(mockClient);
      (AuditService.appendEvent as ReturnType<typeof vi.fn>).mockResolvedValue({
        id: 'evt-uuid-1',
        stream_id: 'stream-uuid-1',
        seq: 1,
        event_hash: 'hash-abc',
      });

      const res = await request(app)
        .post('/internal/audit/events')
        .set('x-internal-api-key', TEST_KEY)
        .send(validBody)
        .expect(200);

      expect(res.body).toMatchObject({
        ok: true,
        audit_event_id: 'evt-uuid-1',
        stream_id: 'stream-uuid-1',
        seq: 1,
        event_hash: 'hash-abc',
      });
    });
  });
});
