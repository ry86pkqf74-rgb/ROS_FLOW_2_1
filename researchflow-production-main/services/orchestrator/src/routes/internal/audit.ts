import { createHash, randomUUID, timingSafeEqual } from 'crypto';

import { sql } from 'drizzle-orm';
import { Router, Request, Response } from 'express';

import { db } from '../../../db.js';

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

function stableStringify(value: unknown): string {
  if (value === null || value === undefined) return 'null';
  if (typeof value === 'string') return JSON.stringify(value);
  if (typeof value === 'number' || typeof value === 'boolean') return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(stableStringify).join(',')}]`;
  if (typeof value === 'object') {
    const obj = value as Record<string, unknown>;
    const keys = Object.keys(obj).sort();
    return `{${keys.map(k => `${JSON.stringify(k)}:${stableStringify(obj[k])}`).join(',')}}`;
  }
  return JSON.stringify(String(value));
}

function sha256Hex(input: string): string {
  return createHash('sha256').update(input).digest('hex');
}

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

  if (!db) {
    res.status(500).json({ ok: false, error: 'database not initialized' });
    return;
  }

  const body = validated.value;
  const createdAtIso = new Date().toISOString();

  const payloadObj: Record<string, unknown> = { ...(body.payload_json ?? {}) };
  if (body.dedupe_key) payloadObj.dedupe_key = body.dedupe_key;

  const payloadHash = sha256Hex(stableStringify(payloadObj));

  try {
    const result = await (db as any).transaction(async (tx: any) => {
      await tx.execute(sql`
        INSERT INTO audit_event_streams (stream_type, stream_key)
        VALUES (${body.stream_type}, ${body.stream_key})
        ON CONFLICT (stream_type, stream_key) DO NOTHING
      `);

      const streamRows = await tx.execute(sql`
        SELECT stream_id
        FROM audit_event_streams
        WHERE stream_type = ${body.stream_type}
          AND stream_key = ${body.stream_key}
        FOR UPDATE
      `);
      const streamId = streamRows?.rows?.[0]?.stream_id as string | undefined;
      if (!streamId) {
        throw new Error('failed to resolve stream_id');
      }

      if (body.dedupe_key) {
        const existing = await tx.execute(sql`
          SELECT id, stream_id, seq, event_hash
          FROM audit_events
          WHERE stream_id = ${streamId}
            AND payload_json->>'dedupe_key' = ${body.dedupe_key}
          ORDER BY seq DESC
          LIMIT 1
        `);
        const row = existing?.rows?.[0];
        if (row?.id) {
          return {
            audit_event_id: row.id as string,
            stream_id: row.stream_id as string,
            seq: Number(row.seq),
            event_hash: row.event_hash as string,
          };
        }
      }

      const last = await tx.execute(sql`
        SELECT seq, event_hash
        FROM audit_events
        WHERE stream_id = ${streamId}
        ORDER BY seq DESC
        LIMIT 1
        FOR UPDATE
      `);
      const lastSeq = last?.rows?.[0]?.seq as number | string | undefined;
      const prevEventHash = (last?.rows?.[0]?.event_hash as string | undefined) ?? null;
      const nextSeq = (lastSeq ? Number(lastSeq) : 0) + 1;

      const auditEventId = randomUUID();

      const eventHashInput = [
        streamId,
        String(nextSeq),
        createdAtIso,
        body.run_id ?? 'null',
        body.trace_id ?? 'null',
        body.node_id ?? 'null',
        body.actor_type,
        body.actor_id ?? 'null',
        body.service,
        body.action,
        body.resource_type,
        body.resource_id,
        body.before_hash ?? 'null',
        body.after_hash ?? 'null',
        payloadHash,
        prevEventHash ?? 'null',
      ].join('|');
      const eventHash = sha256Hex(eventHashInput);

      await tx.execute(sql`
        INSERT INTO audit_events (
          id, stream_id, seq, created_at,
          run_id, trace_id, node_id,
          actor_type, actor_id,
          service, action,
          resource_type, resource_id,
          before_hash, after_hash,
          payload_json, payload_hash,
          prev_event_hash, event_hash
        ) VALUES (
          ${auditEventId}, ${streamId}, ${nextSeq}, ${createdAtIso}::timestamptz,
          ${body.run_id ?? null}, ${body.trace_id ?? null}, ${body.node_id ?? null},
          ${body.actor_type}, ${body.actor_id ?? null},
          ${body.service}, ${body.action},
          ${body.resource_type}, ${body.resource_id},
          ${body.before_hash ?? null}, ${body.after_hash ?? null},
          ${JSON.stringify(payloadObj)}::jsonb, ${payloadHash},
          ${prevEventHash}, ${eventHash}
        )
      `);

      return {
        audit_event_id: auditEventId as string,
        stream_id: streamId,
        seq: nextSeq,
        event_hash: eventHash,
      };
    });

    res.json({ ok: true, ...result });
  } catch (err: any) {
    res.status(500).json({ ok: false, error: err?.message ?? 'internal error' });
  }
});

export default router;
