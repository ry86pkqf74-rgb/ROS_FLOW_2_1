/**
 * HIPAA-safe payload sanitizer for the audit ledger.
 *
 * Uses a structural allowlist approach (keep safe keys, drop the rest)
 * rather than regex-based PHI scanning (which is in phi-protection.ts).
 */

export interface SanitizeOptions {
  hipaaMode: boolean;
}

/**
 * Regex patterns for keys considered safe to retain in HIPAA mode.
 * These cover identifiers, hashes, counts, timestamps, and status fields.
 */
const SAFE_KEY_PATTERNS: RegExp[] = [
  /_id$/i,
  /Id$/,
  /_hash$/i,
  /Hash$/,
  /_count$/i,
  /Count$/,
  /_length$/i,
  /Length$/,
  /_at$/i,
  /At$/,
  /^(status|type|action|stage|seq|version|mode|level|code|success|duration|size|offset|limit)$/,
  /^(is_|has_)/i,
];

function isKeyAllowed(key: string): boolean {
  return SAFE_KEY_PATTERNS.some(pattern => pattern.test(key));
}

const MAX_STRING_LENGTH = 256;

function sanitizeValue(value: unknown): unknown {
  if (value === null || value === undefined) return value;
  if (typeof value === 'boolean' || typeof value === 'number') return value;
  if (typeof value === 'string') {
    return value.length > MAX_STRING_LENGTH
      ? `[TRUNCATED:${value.length}]`
      : value;
  }
  if (Array.isArray(value)) {
    return value.map(item => sanitizeValue(item));
  }
  if (typeof value === 'object') {
    const result: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(value as Record<string, unknown>)) {
      if (isKeyAllowed(k)) {
        result[k] = sanitizeValue(v);
      }
    }
    return result;
  }
  return undefined;
}

/**
 * Sanitize an audit payload for safe storage.
 *
 * - **Non-HIPAA mode**: pass through unchanged.
 * - **HIPAA mode**: keep only allowlisted keys (IDs, hashes, counts,
 *   timestamps, statuses). Drop free-text fields that could contain PHI.
 *   Truncate strings longer than 256 characters.
 */
export function sanitizeAuditPayload(payload: unknown, opts: SanitizeOptions): unknown {
  if (!opts.hipaaMode) return payload;
  if (payload === null || payload === undefined) return payload;
  if (typeof payload !== 'object') return payload;
  return sanitizeValue(payload);
}
