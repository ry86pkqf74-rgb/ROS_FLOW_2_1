import { timingSafeEqual } from 'crypto';

import { Router, Request, Response } from 'express';

import { pool } from '../../../db.js';
import * as AuditService from '../../services/audit.service';

type StreamType = 'GLOBAL' | 'RUN' | 'MANUSCRIPT';

type IngestAuditEventBody = {
  stream_type: StreamType;
  stream_key: string;
  run_id?: string;
  trace_id?: string;
  node_id?: string;
  actor_type: string;
  actor_id?: string;
  service: string;
  action: string;
  resource_type: string;
  resource_id: string;
  before_hash?: string;
  after_hash?: string;
  payload_json?: Record<string, unknown>;
  dedupe_key?: string;
};

function safeEq(a: string, b: string): boolean {
  const aBuf = Buffer.from(a);
  const bBuf = Buffer.from(b);
  if (aBuf.length !== bBuf.length) return false;
  return timingSafeEqual(aBuf, bBuf);
}

function badRequest(res: Response, message: string) {
  res.status(400).json({ ok: false, error: message });
}

function isNonEmptyString(v: unknown): v is string {
  return typeof v === 'string' && v.trim().length > 0;
}

function isStreamType(v: unknown): v is StreamType {
  return v === 'GLOBAL' || v === 'RUN' || v === 'MANUSCRIPT';
}

function validateBody(body: any): { ok: true; value: IngestAuditEventBody } | { ok: false; error: string } {
  if (!body || typeof body !== 'object') return { ok: false, error: 'invalid JSON body' };
  if (!isStreamType(body.stream_type)) return { ok: false, error: 'stream_type must be GLOBAL|RUN|MANUSCRIPT' };
  if (!isNonEmptyString(body.stream_key)) return { ok: false, error: 'stream_key is required' };
  if (!isNonEmptyString(body.actor_type)) return { ok: false, error: 'actor_type is required' };
  if (!isNonEmptyString(body.service)) return { ok: false, error: 'service is required' };
  if (!isNonEmptyString(body.action)) return { ok: false, error: 'action is required' };
  if (!isNonEmptyString(body.resource_type)) return { ok: false, error: 'resource_type is required' };
  if (!isNonEmptyString(body.resource_id)) return { ok: false, error: 'resource_id is required' };
  if (body.payload_json !== undefined && (body.payload_json === null || typeof body.payload_json !== 'object' || Array.isArray(body.payload_json))) {
    return { ok: false, error: 'payload_json must be an object if provided' };
  }
  if (body.dedupe_key !== undefined && !isNonEmptyString(body.dedupe_key)) return { ok: false, error: 'dedupe_key must be a non-empty string' };

  return { ok: true, value: body as IngestAuditEventBody };
}

const router = Router();

// GET /internal/audit/ping
router.get('/ping', (_req: Request, res: Response) => {
  res.json({ ok: true, audit_ingest_enabled: Boolean(process.env.INTERNAL_API_KEY) });
});

// POST /internal/audit/events
router.post('/events', async (req: Request, res: Response) => {
  const internalKey = process.env.INTERNAL_API_KEY;
  if (!internalKey) {
    res.status(503).json({ ok: false, message: 'internal audit ingest disabled' });
    return;
  }

  const headerKey = String(req.header('x-internal-api-key') || '');
  if (!headerKey || !safeEq(headerKey, internalKey)) {
    res.status(401).json({ ok: false, error: 'unauthorized' });
    return;
  }

  const validated = validateBody(req.body);
  if (!validated.ok) {
    badRequest(res, validated.error);
    return;
  }

  if (!pool) {
    res.status(500).json({ ok: false, error: 'database not initialized' });
    return;
  }

  const body = validated.value;
  const appMode = String(process.env.APP_MODE || '').toLowerCase();
  const hipaaMode =
    appMode === 'hipaa' ||
    String(process.env.HIPAA_MODE || '').toLowerCase() === 'true' ||
    String(process.env.HIPAA_MODE || '').toLowerCase() === '1';

  try {
    const client = await pool.connect();
    try {
      await client.query('BEGIN');
      const row = await AuditService.appendEvent(
        client,
        {
          stream_type: body.stream_type,
          stream_key: body.stream_key,
          run_id: body.run_id ?? null,
          trace_id: body.trace_id ?? null,
          node_id: body.node_id ?? null,
          actor_type: body.actor_type,
          actor_id: body.actor_id ?? null,
          service: body.service,
          action: body.action,
          resource_type: body.resource_type,
          resource_id: body.resource_id,
          before_hash: body.before_hash ?? null,
          after_hash: body.after_hash ?? null,
          payload: body.payload_json ?? {},
          dedupe_key: body.dedupe_key,
        },
        { hipaaMode },
      );
      await client.query('COMMIT');

      res.json({
        ok: true,
        audit_event_id: row.id,
        stream_id: row.stream_id,
        seq: Number(row.seq),
        event_hash: row.event_hash,
      });
    } catch (err) {
      await client.query('ROLLBACK');
      throw err;
    } finally {
      client.release();
    }
  } catch (err: any) {
    res.status(500).json({ ok: false, error: err?.message ?? 'internal error' });
  }
});

export default router;
