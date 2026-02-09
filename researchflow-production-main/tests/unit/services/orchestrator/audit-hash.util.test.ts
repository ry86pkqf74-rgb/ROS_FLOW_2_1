import { describe, it, expect } from 'vitest';
import {
  canonicalizeJson,
  sha256Hex,
  computePayloadHash,
  computeEventHash,
} from '../../../../services/orchestrator/src/services/audit-hash.util';

describe('canonicalizeJson', () => {
  it('sorts top-level keys', () => {
    expect(canonicalizeJson({ b: 1, a: 2 })).toBe('{"a":2,"b":1}');
  });

  it('sorts nested keys recursively', () => {
    expect(canonicalizeJson({ b: { d: 1, c: 2 }, a: 3 })).toBe(
      '{"a":3,"b":{"c":2,"d":1}}',
    );
  });

  it('preserves array order and recursively canonicalizes elements', () => {
    expect(canonicalizeJson([{ b: 1, a: 2 }])).toBe('[{"a":2,"b":1}]');
  });

  it('handles null', () => {
    expect(canonicalizeJson(null)).toBe('null');
  });

  it('handles undefined', () => {
    expect(canonicalizeJson(undefined)).toBe('null');
  });

  it('handles primitives', () => {
    expect(canonicalizeJson('hello')).toBe('"hello"');
    expect(canonicalizeJson(42)).toBe('42');
    expect(canonicalizeJson(true)).toBe('true');
    expect(canonicalizeJson(false)).toBe('false');
  });

  it('omits undefined values in objects', () => {
    expect(canonicalizeJson({ a: 1, b: undefined, c: 3 })).toBe('{"a":1,"c":3}');
  });

  it('handles empty objects and arrays', () => {
    expect(canonicalizeJson({})).toBe('{}');
    expect(canonicalizeJson([])).toBe('[]');
  });

  it('handles Date objects', () => {
    const date = new Date('2025-01-15T00:00:00.000Z');
    expect(canonicalizeJson(date)).toBe('"2025-01-15T00:00:00.000Z"');
  });

  it('handles deeply nested structures', () => {
    const input = { z: [{ y: { x: 1, w: 2 } }], a: null };
    expect(canonicalizeJson(input)).toBe('{"a":null,"z":[{"y":{"w":2,"x":1}}]}');
  });
});

describe('sha256Hex', () => {
  it('returns a 64-character hex string', () => {
    const hash = sha256Hex('test');
    expect(hash).toHaveLength(64);
    expect(hash).toMatch(/^[0-9a-f]{64}$/);
  });

  it('matches known vector for empty string', () => {
    expect(sha256Hex('')).toBe(
      'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
    );
  });

  it('is deterministic', () => {
    expect(sha256Hex('hello')).toBe(sha256Hex('hello'));
  });
});

describe('computePayloadHash', () => {
  it('returns sha256 of canonicalized JSON', () => {
    const hash = computePayloadHash({ a: 1 });
    expect(hash).toBe(sha256Hex(canonicalizeJson({ a: 1 })));
  });

  it('is key-order-independent', () => {
    expect(computePayloadHash({ a: 1, b: 2 })).toBe(
      computePayloadHash({ b: 2, a: 1 }),
    );
  });

  it('produces different hashes for different payloads', () => {
    expect(computePayloadHash({ a: 1 })).not.toBe(
      computePayloadHash({ a: 2 }),
    );
  });
});

describe('computeEventHash', () => {
  const baseFields = {
    stream_id: 'stream-1',
    seq: 1,
    prev_event_hash: null,
    payload_hash: 'ph-abc',
    before_hash: null,
    after_hash: null,
    actor_type: 'USER',
    actor_id: 'user-1',
    service: 'orchestrator',
    action: 'CREATE',
    resource_type: 'MANUSCRIPT',
    resource_id: 'ms-1',
  };

  it('returns a 64-character hex string', () => {
    const hash = computeEventHash(baseFields);
    expect(hash).toHaveLength(64);
    expect(hash).toMatch(/^[0-9a-f]{64}$/);
  });

  it('is deterministic', () => {
    expect(computeEventHash(baseFields)).toBe(computeEventHash(baseFields));
  });

  it('handles null fields (first event in stream)', () => {
    const hash = computeEventHash(baseFields);
    expect(hash).toBeTruthy();
  });

  it('differs when any field changes', () => {
    const hash1 = computeEventHash(baseFields);
    const hash2 = computeEventHash({ ...baseFields, action: 'DELETE' });
    expect(hash1).not.toBe(hash2);
  });

  it('differs when prev_event_hash changes', () => {
    const hash1 = computeEventHash(baseFields);
    const hash2 = computeEventHash({ ...baseFields, prev_event_hash: 'prev-abc' });
    expect(hash1).not.toBe(hash2);
  });
});
