import { createHash } from 'crypto';

import { auditLogs } from '@researchflow/core/schema';
import { desc } from 'drizzle-orm';
import { and, eq } from 'drizzle-orm';

import { db } from '../../db';

// NOTE: Audit logging must be best-effort and MUST NOT break primary request flows.
// In dev/service-auth flows we may have stateless JWT identities that are not present
// in the users table, which can cause FK violations (23503). We swallow those.

function isPgForeignKeyViolation(err: unknown): boolean {
  if (!err || typeof err !== 'object') return false;
  // pg uses `code` (string) for SQLSTATE.
  // 23503 = foreign_key_violation
   
  const code = (err as any).code;
  return code === '23503';
}

function safeAuditWarn(message: string, err: unknown): void {
  // Never log request bodies / PHI here.
  if (isPgForeignKeyViolation(err)) {
    console.warn(`[audit] ${message} (fk_violation_23503)`);
    return;
  }
  console.warn(`[audit] ${message}`);
}

interface AuditLogEntry {
  eventType: string;
  userId?: string;
  resourceType?: string;
  resourceId?: string;
  action: string;
  details?: Record<string, any>;
  ipAddress?: string;
  userAgent?: string;
  sessionId?: string;
  researchId?: string;
}

/**
 * Log an auditable action with hash chaining for tamper detection
 */
export async function logAction(entry: AuditLogEntry): Promise<void> {
  try {
    if (!db) {
      throw new Error('Database not initialized');
    }

    // Get the most recent audit log entry for hash chaining
    const [previousEntry] = await db
      .select()
      .from(auditLogs)
      .orderBy(desc(auditLogs.id))
      .limit(1);

  const previousHash = previousEntry?.entryHash || 'GENESIS';

    // Create hash of current entry
    const entryData = JSON.stringify({
      ...entry,
      previousHash,
      timestamp: new Date().toISOString()
    });

    const entryHash = createHash('sha256')
      .update(entryData)
      .digest('hex');

    // Insert audit log with hash chain
    await db.insert(auditLogs).values({
      ...entry,
      previousHash,
      entryHash,
      details: entry.details ? entry.details : undefined
    } as any);
  } catch (err) {
    safeAuditWarn('logAction failed', err);
    return;
  }
}

/**
 * Verify integrity of audit chain
 * Returns true if chain is intact, false if tampered
 */
export async function verifyAuditChain(): Promise<{
  valid: boolean;
  brokenAt?: number;
  totalEntries: number;
}> {
  if (!db) {
    throw new Error('Database not initialized');
  }

  const entries = await db
    .select()
    .from(auditLogs)
    .orderBy(auditLogs.id);

  if (entries.length === 0) {
    return { valid: true, totalEntries: 0 };
  }

  let previousHash = 'GENESIS';

  for (let i = 0; i < entries.length; i++) {
    const entry = entries[i];

    if (entry.previousHash !== previousHash) {
      return {
        valid: false,
        brokenAt: entry.id,
        totalEntries: entries.length
      };
    }

    // Recompute hash to verify
    const entryData = JSON.stringify({
      eventType: entry.eventType,
      userId: entry.userId,
      resourceType: entry.resourceType,
      resourceId: entry.resourceId,
      action: entry.action,
      details: entry.details,
      ipAddress: entry.ipAddress,
      userAgent: entry.userAgent,
      sessionId: entry.sessionId,
      researchId: entry.researchId,
      previousHash: entry.previousHash,
      timestamp: entry.createdAt?.toISOString()
    });

    const computedHash = createHash('sha256')
      .update(entryData)
      .digest('hex');

    if (computedHash !== entry.entryHash) {
      return {
        valid: false,
        brokenAt: entry.id,
        totalEntries: entries.length
      };
    }

    previousHash = entry.entryHash!;
  }

  return { valid: true, totalEntries: entries.length };
}

/**
 * Get audit logs for a specific resource
 */
export async function getAuditLogsForResource(
  resourceType: string,
  resourceId: string
) {
  if (!db) {
    throw new Error('Database not initialized');
  }

  return await db
    .select()
    .from(auditLogs)
    .where(
      and(
        eq(auditLogs.resourceType, resourceType),
        eq(auditLogs.resourceId, resourceId)
      )
    )
    .orderBy(desc(auditLogs.createdAt));
}

/**
 * Log an authentication event with full context
 */
export async function logAuthEvent(entry: {
  eventType: 'LOGIN_SUCCESS' | 'LOGIN_FAILURE' | 'LOGOUT' | 'REGISTRATION' | 'PASSWORD_RESET_REQUEST' | 'PASSWORD_RESET_SUCCESS' | 'SESSION_EXPIRATION' | 'TOKEN_REFRESH_SUCCESS' | 'TOKEN_REFRESH_FAILURE';
  userId?: string;
  ipAddress?: string;
  userAgent?: string;
  success: boolean;
  failureReason?: string;
  details?: Record<string, any>;
}): Promise<void> {
  try {
    if (!db) {
      throw new Error('Database not initialized');
    }

    // Get the most recent audit log entry for hash chaining
    const [previousEntry] = await db
      .select()
      .from(auditLogs)
      .orderBy(desc(auditLogs.id))
      .limit(1);

  const previousHash = previousEntry?.entryHash || 'GENESIS';

    // Prepare entry data for hashing
    const timestamp = new Date().toISOString();
    const auditDetails = {
      ...entry.details,
      success: entry.success,
      ...(entry.failureReason && { failureReason: entry.failureReason })
    };

    const entryData = JSON.stringify({
      eventType: entry.eventType,
      userId: entry.userId,
      ipAddress: entry.ipAddress,
      userAgent: entry.userAgent,
      details: auditDetails,
      previousHash,
      timestamp
    });

    const entryHash = createHash('sha256')
      .update(entryData)
      .digest('hex');

    // Insert auth event into audit logs
    await db.insert(auditLogs).values({
      eventType: entry.eventType,
      userId: entry.userId,
      action: entry.success ? 'SUCCESS' : 'FAILURE',
      ipAddress: entry.ipAddress,
      userAgent: entry.userAgent,
      previousHash,
      entryHash,
      details: auditDetails
    } as any);
  } catch (err) {
    safeAuditWarn('logAuthEvent failed', err);
    return;
  }
}
