import { describe, it, expect } from 'vitest';
import { sanitizeAuditPayload } from '../../../../services/orchestrator/src/services/audit-redaction.util';

describe('sanitizeAuditPayload', () => {
  describe('non-HIPAA mode', () => {
    it('passes through unchanged', () => {
      const payload = { name: 'John', user_id: '123', notes: 'free text' };
      expect(sanitizeAuditPayload(payload, { hipaaMode: false })).toEqual(payload);
    });

    it('passes through null', () => {
      expect(sanitizeAuditPayload(null, { hipaaMode: false })).toBeNull();
    });
  });

  describe('HIPAA mode', () => {
    it('keeps *_id keys', () => {
      const result = sanitizeAuditPayload(
        { user_id: 'abc', name: 'John' },
        { hipaaMode: true },
      );
      expect(result).toEqual({ user_id: 'abc' });
    });

    it('keeps *Id keys (camelCase)', () => {
      const result = sanitizeAuditPayload(
        { userId: 'abc', patientName: 'Jane' },
        { hipaaMode: true },
      );
      expect(result).toEqual({ userId: 'abc' });
    });

    it('keeps *_hash keys', () => {
      const result = sanitizeAuditPayload(
        { entry_hash: 'deadbeef', content: 'sensitive' },
        { hipaaMode: true },
      );
      expect(result).toEqual({ entry_hash: 'deadbeef' });
    });

    it('keeps *_at timestamp keys', () => {
      const result = sanitizeAuditPayload(
        { created_at: '2025-01-01', description: 'text' },
        { hipaaMode: true },
      );
      expect(result).toEqual({ created_at: '2025-01-01' });
    });

    it('keeps *At camelCase timestamp keys', () => {
      const result = sanitizeAuditPayload(
        { updatedAt: '2025-01-01', body: 'text' },
        { hipaaMode: true },
      );
      expect(result).toEqual({ updatedAt: '2025-01-01' });
    });

    it('keeps exact-match safe keys', () => {
      const result = sanitizeAuditPayload(
        { status: 'active', type: 'RUN', action: 'CREATE', notes: 'PHI' },
        { hipaaMode: true },
      );
      expect(result).toEqual({ status: 'active', type: 'RUN', action: 'CREATE' });
    });

    it('keeps is_* and has_* boolean keys', () => {
      const result = sanitizeAuditPayload(
        { is_active: true, has_phi: false, description: 'text' },
        { hipaaMode: true },
      );
      expect(result).toEqual({ is_active: true, has_phi: false });
    });

    it('keeps *_count keys', () => {
      const result = sanitizeAuditPayload(
        { row_count: 42, summary: 'text' },
        { hipaaMode: true },
      );
      expect(result).toEqual({ row_count: 42 });
    });

    it('truncates long strings to [TRUNCATED:<length>]', () => {
      const longString = 'x'.repeat(300);
      const result = sanitizeAuditPayload(
        { user_id: longString },
        { hipaaMode: true },
      ) as any;
      expect(result.user_id).toBe('[TRUNCATED:300]');
    });

    it('does not truncate strings <= 256 chars', () => {
      const shortString = 'x'.repeat(256);
      const result = sanitizeAuditPayload(
        { user_id: shortString },
        { hipaaMode: true },
      ) as any;
      expect(result.user_id).toBe(shortString);
    });

    it('drops nested objects under non-allowed keys', () => {
      const result = sanitizeAuditPayload(
        { metadata: { user_id: '1', name: 'John' } },
        { hipaaMode: true },
      );
      expect(result).toEqual({});
    });

    it('keeps and recurses nested objects under allowed keys', () => {
      const result = sanitizeAuditPayload(
        { status: { user_id: '1', name: 'John' } },
        { hipaaMode: true },
      );
      expect(result).toEqual({ status: { user_id: '1' } });
    });

    it('handles arrays under allowed keys', () => {
      const result = sanitizeAuditPayload(
        { action: [{ user_id: '1', name: 'John' }] },
        { hipaaMode: true },
      );
      expect(result).toEqual({ action: [{ user_id: '1' }] });
    });

    it('handles null payload', () => {
      expect(sanitizeAuditPayload(null, { hipaaMode: true })).toBeNull();
    });

    it('handles undefined payload', () => {
      expect(sanitizeAuditPayload(undefined, { hipaaMode: true })).toBeUndefined();
    });

    it('passes through primitive payloads', () => {
      expect(sanitizeAuditPayload('hello', { hipaaMode: true })).toBe('hello');
      expect(sanitizeAuditPayload(42, { hipaaMode: true })).toBe(42);
    });
  });
});
