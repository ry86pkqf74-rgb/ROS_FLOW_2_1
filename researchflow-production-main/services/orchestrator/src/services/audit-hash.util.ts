/**
 * Deterministic hashing utilities for the tamper-evident audit ledger.
 *
 * These target the audit_events / audit_event_streams tables (migration 017).
 * All functions are pure and stateless — no I/O or database access.
 */

import { createHash } from 'crypto';

// ── Canonical JSON ──────────────────────────────────────────────────

/**
 * Produce a deterministic JSON string by recursively sorting object keys.
 * Handles nested objects, arrays, primitives, null, undefined, and Date.
 */
export function canonicalizeJson(obj: unknown): string {
  if (obj === null || obj === undefined) return 'null';
  if (typeof obj === 'number' || typeof obj === 'boolean') return JSON.stringify(obj);
  if (typeof obj === 'string') return JSON.stringify(obj);
  if (obj instanceof Date) return JSON.stringify(obj.toISOString());
  if (Array.isArray(obj)) {
    return '[' + obj.map(item => canonicalizeJson(item)).join(',') + ']';
  }
  if (typeof obj === 'object') {
    const record = obj as Record<string, unknown>;
    const keys = Object.keys(record).sort();
    const pairs = keys
      .filter(k => record[k] !== undefined)
      .map(k => JSON.stringify(k) + ':' + canonicalizeJson(record[k]));
    return '{' + pairs.join(',') + '}';
  }
  // Fallback for functions, symbols, etc.
  return 'null';
}

// ── SHA-256 ─────────────────────────────────────────────────────────

/** SHA-256 hex digest of a UTF-8 string. */
export function sha256Hex(input: string): string {
  return createHash('sha256').update(input, 'utf8').digest('hex');
}

// ── Payload Hash ────────────────────────────────────────────────────

/** SHA-256 of the canonicalized payload JSON. */
export function computePayloadHash(payloadJson: unknown): string {
  return sha256Hex(canonicalizeJson(payloadJson));
}

// ── Event Hash ──────────────────────────────────────────────────────

export interface EventHashFields {
  stream_id: string;
  seq: number;
  prev_event_hash: string | null;
  payload_hash: string;
  before_hash: string | null;
  after_hash: string | null;
  actor_type: string;
  actor_id: string | null;
  service: string;
  action: string;
  resource_type: string;
  resource_id: string;
}

/**
 * Compute the event hash as SHA-256 of a pipe-delimited concatenation
 * of stable event fields. `created_at` is intentionally excluded so
 * hashes are deterministic and reproducible independent of wall-clock time.
 *
 * Field order matches the migration 017 comment recommendation
 * (minus created_at).
 */
export function computeEventHash(fields: EventHashFields): string {
  const parts = [
    fields.prev_event_hash ?? '',
    fields.payload_hash,
    fields.before_hash ?? '',
    fields.after_hash ?? '',
    fields.actor_type,
    fields.actor_id ?? '',
    fields.service,
    fields.action,
    fields.resource_type,
    fields.resource_id,
    fields.stream_id,
    String(fields.seq),
  ];
  return sha256Hex(parts.join('|'));
}
