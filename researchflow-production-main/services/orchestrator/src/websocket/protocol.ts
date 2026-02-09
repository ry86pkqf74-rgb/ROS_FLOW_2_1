/**
 * WebSocket Protocol - PHI-Safe Message Types
 *
 * Defines the WebSocket protocol message types for real-time updates.
 * All messages are PHI-safe: containing only IDs, hashes, status enums, and counts.
 *
 * Event Types:
 * - RUN_STATUS: Research run status changes
 * - NODE_STATUS: Workflow node/stage status updates
 * - MANUSCRIPT_COMMIT_CREATED: New manuscript commit notifications
 * - EDIT_SESSION_UPDATED: Collaborative editing session updates
 *
 * HIPAA Compliance:
 * When APP_MODE=hipaa or HIPAA_MODE is enabled, payload fields are minimized
 * to essential metadata only. Content, free text, and detailed messages are excluded.
 *
 * @module websocket/protocol
 */

import { z } from 'zod';
import { getEnvBool, getEnvString } from '../config/env';

// =============================================================================
// HIPAA MODE DETECTION
// =============================================================================

/**
 * Determine if HIPAA mode is active
 */
export function isHipaaMode(): boolean {
  const appMode = getEnvString('APP_MODE', '');
  const hipaaMode = getEnvBool('HIPAA_MODE', false);
  return appMode.toLowerCase() === 'hipaa' || hipaaMode;
}

// =============================================================================
// BASE MESSAGE SCHEMA
// =============================================================================

/**
 * Base WebSocket protocol message
 */
export const BaseMessageSchema = z.object({
  type: z.string(),
  timestamp: z.string().datetime(),
  payload: z.record(z.unknown()),
});

export type BaseMessage = z.infer<typeof BaseMessageSchema>;

// =============================================================================
// RUN STATUS EVENTS
// =============================================================================

/**
 * Run status enum - PHI-safe status indicators
 */
export const RunStatusEnum = z.enum([
  'CREATED',
  'QUEUED',
  'RUNNING',
  'COMPLETED',
  'FAILED',
  'CANCELLED',
  'PAUSED',
]);

export type RunStatus = z.infer<typeof RunStatusEnum>;

/**
 * RUN_STATUS event payload
 * Contains only run ID, project ID, status enum, and timestamps
 */
export const RunStatusPayloadSchema = z.object({
  runId: z.string(),
  projectId: z.string(),
  status: RunStatusEnum,
  previousStatus: RunStatusEnum.optional(),
  timestamp: z.string().datetime(),
  // HIPAA-compliant: No run names, descriptions, or user-generated content
  // Only metadata and IDs
  errorCode: z.string().optional(), // Error codes only, never messages
  durationMs: z.number().int().min(0).optional(),
  stageCount: z.number().int().min(0).optional(),
});

export type RunStatusPayload = z.infer<typeof RunStatusPayloadSchema>;

export const RunStatusEventSchema = z.object({
  type: z.literal('RUN_STATUS'),
  timestamp: z.string().datetime(),
  payload: RunStatusPayloadSchema,
});

export type RunStatusEvent = z.infer<typeof RunStatusEventSchema>;

// =============================================================================
// NODE STATUS EVENTS
// =============================================================================

/**
 * Node/Stage status enum - PHI-safe status indicators
 */
export const NodeStatusEnum = z.enum([
  'PENDING',
  'RUNNING',
  'COMPLETED',
  'FAILED',
  'SKIPPED',
  'CANCELLED',
]);

export type NodeStatus = z.infer<typeof NodeStatusEnum>;

/**
 * NODE_STATUS event payload
 * Contains only node/stage IDs, run ID, status, and progress metrics
 */
export const NodeStatusPayloadSchema = z.object({
  runId: z.string(),
  nodeId: z.string(), // Stage ID or node ID
  status: NodeStatusEnum,
  previousStatus: NodeStatusEnum.optional(),
  timestamp: z.string().datetime(),
  // Progress indicator (0-100)
  progress: z.number().int().min(0).max(100).optional(),
  // HIPAA-compliant: No stage names, descriptions, or output content
  // Only IDs and numeric metrics
  errorCode: z.string().optional(),
  itemsProcessed: z.number().int().min(0).optional(),
  itemsTotal: z.number().int().min(0).optional(),
  durationMs: z.number().int().min(0).optional(),
});

export type NodeStatusPayload = z.infer<typeof NodeStatusPayloadSchema>;

export const NodeStatusEventSchema = z.object({
  type: z.literal('NODE_STATUS'),
  timestamp: z.string().datetime(),
  payload: NodeStatusPayloadSchema,
});

export type NodeStatusEvent = z.infer<typeof NodeStatusEventSchema>;

// =============================================================================
// MANUSCRIPT COMMIT EVENTS
// =============================================================================

/**
 * MANUSCRIPT_COMMIT_CREATED event payload
 * Contains only manuscript ID, commit hash, and metadata
 */
export const ManuscriptCommitPayloadSchema = z.object({
  manuscriptId: z.string(),
  commitHash: z.string(), // Git-style hash for commit identification
  projectId: z.string(),
  userId: z.string(), // Author user ID
  timestamp: z.string().datetime(),
  // HIPAA-compliant: No commit messages, content, or diffs
  // Only hashes and IDs for correlation
  parentCommitHash: z.string().optional(),
  branchName: z.string().optional(), // Branch identifier, not content
  changeCount: z.number().int().min(0).optional(), // Number of changes (not content)
});

export type ManuscriptCommitPayload = z.infer<typeof ManuscriptCommitPayloadSchema>;

export const ManuscriptCommitEventSchema = z.object({
  type: z.literal('MANUSCRIPT_COMMIT_CREATED'),
  timestamp: z.string().datetime(),
  payload: ManuscriptCommitPayloadSchema,
});

export type ManuscriptCommitEvent = z.infer<typeof ManuscriptCommitEventSchema>;

// =============================================================================
// EDIT SESSION EVENTS
// =============================================================================

/**
 * Edit session status enum
 */
export const EditSessionStatusEnum = z.enum([
  'ACTIVE',
  'IDLE',
  'DISCONNECTED',
  'LOCKED',
]);

export type EditSessionStatus = z.infer<typeof EditSessionStatusEnum>;

/**
 * EDIT_SESSION_UPDATED event payload
 * Contains only session ID, manuscript ID, status, and active user count
 */
export const EditSessionPayloadSchema = z.object({
  sessionId: z.string(),
  manuscriptId: z.string(),
  status: EditSessionStatusEnum,
  timestamp: z.string().datetime(),
  // HIPAA-compliant: No user names, cursor positions, or content selections
  // Only user IDs and counts
  activeUserIds: z.array(z.string()), // User IDs only
  activeUserCount: z.number().int().min(0),
  lastActivityTimestamp: z.string().datetime().optional(),
  // No edit content or selection ranges transmitted via WebSocket
});

export type EditSessionPayload = z.infer<typeof EditSessionPayloadSchema>;

export const EditSessionEventSchema = z.object({
  type: z.literal('EDIT_SESSION_UPDATED'),
  timestamp: z.string().datetime(),
  payload: EditSessionPayloadSchema,
});

export type EditSessionEvent = z.infer<typeof EditSessionEventSchema>;

// =============================================================================
// PROTOCOL MESSAGE UNION
// =============================================================================

/**
 * Union of all protocol event types
 */
export const ProtocolEventSchema = z.discriminatedUnion('type', [
  RunStatusEventSchema,
  NodeStatusEventSchema,
  ManuscriptCommitEventSchema,
  EditSessionEventSchema,
]);

export type ProtocolEvent = z.infer<typeof ProtocolEventSchema>;

// =============================================================================
// CLIENT MESSAGES (Client → Server)
// =============================================================================

/**
 * Subscribe to specific event types
 */
export const SubscribeMessageSchema = z.object({
  type: z.literal('subscribe'),
  payload: z.object({
    eventTypes: z.array(z.enum([
      'RUN_STATUS',
      'NODE_STATUS',
      'MANUSCRIPT_COMMIT_CREATED',
      'EDIT_SESSION_UPDATED',
    ])),
    filters: z.object({
      runId: z.string().optional(),
      projectId: z.string().optional(),
      manuscriptId: z.string().optional(),
    }).optional(),
  }),
});

export type SubscribeMessage = z.infer<typeof SubscribeMessageSchema>;

/**
 * Unsubscribe from event types
 */
export const UnsubscribeMessageSchema = z.object({
  type: z.literal('unsubscribe'),
  payload: z.object({
    eventTypes: z.array(z.enum([
      'RUN_STATUS',
      'NODE_STATUS',
      'MANUSCRIPT_COMMIT_CREATED',
      'EDIT_SESSION_UPDATED',
    ])),
  }),
});

export type UnsubscribeMessage = z.infer<typeof UnsubscribeMessageSchema>;

/**
 * Authenticate client connection
 */
export const AuthMessageSchema = z.object({
  type: z.literal('auth'),
  payload: z.object({
    token: z.string(), // JWT or session token
    userId: z.string().optional(),
  }),
});

export type AuthMessage = z.infer<typeof AuthMessageSchema>;

/**
 * Ping/pong heartbeat
 */
export const PingMessageSchema = z.object({
  type: z.literal('ping'),
  payload: z.object({}).optional(),
});

export type PingMessage = z.infer<typeof PingMessageSchema>;

/**
 * Client message union
 */
export const ClientMessageSchema = z.discriminatedUnion('type', [
  SubscribeMessageSchema,
  UnsubscribeMessageSchema,
  AuthMessageSchema,
  PingMessageSchema,
]);

export type ClientMessage = z.infer<typeof ClientMessageSchema>;

// =============================================================================
// SERVER MESSAGES (Server → Client)
// =============================================================================

/**
 * Connection established confirmation
 */
export const ConnectionEstablishedSchema = z.object({
  type: z.literal('connection.established'),
  timestamp: z.string().datetime(),
  payload: z.object({
    clientId: z.string(),
    serverVersion: z.string(),
    hipaaMode: z.boolean(),
  }),
});

export type ConnectionEstablished = z.infer<typeof ConnectionEstablishedSchema>;

/**
 * Authentication response
 */
export const AuthResponseSchema = z.object({
  type: z.enum(['auth.success', 'auth.failed']),
  timestamp: z.string().datetime(),
  payload: z.object({
    userId: z.string().optional(),
    message: z.string().optional(),
  }),
});

export type AuthResponse = z.infer<typeof AuthResponseSchema>;

/**
 * Subscription confirmation
 */
export const SubscriptionConfirmationSchema = z.object({
  type: z.literal('subscription.confirmed'),
  timestamp: z.string().datetime(),
  payload: z.object({
    eventTypes: z.array(z.string()),
    filters: z.record(z.unknown()).optional(),
  }),
});

export type SubscriptionConfirmation = z.infer<typeof SubscriptionConfirmationSchema>;

/**
 * Pong response
 */
export const PongMessageSchema = z.object({
  type: z.literal('pong'),
  timestamp: z.string().datetime(),
  payload: z.object({}).optional(),
});

export type PongMessage = z.infer<typeof PongMessageSchema>;

/**
 * Error message
 */
export const ErrorMessageSchema = z.object({
  type: z.literal('error'),
  timestamp: z.string().datetime(),
  payload: z.object({
    code: z.string(),
    message: z.string(),
  }),
});

export type ErrorMessage = z.infer<typeof ErrorMessageSchema>;

/**
 * Server message union (including protocol events)
 */
export const ServerMessageSchema = z.union([
  ConnectionEstablishedSchema,
  AuthResponseSchema,
  SubscriptionConfirmationSchema,
  PongMessageSchema,
  ErrorMessageSchema,
  ProtocolEventSchema,
]);

export type ServerMessage = z.infer<typeof ServerMessageSchema>;

// =============================================================================
// VALIDATION HELPERS
// =============================================================================

/**
 * Validate protocol event at runtime
 */
export function isValidProtocolEvent(event: unknown): event is ProtocolEvent {
  try {
    ProtocolEventSchema.parse(event);
    return true;
  } catch {
    return false;
  }
}

/**
 * Validate client message at runtime
 */
export function isValidClientMessage(message: unknown): message is ClientMessage {
  try {
    ClientMessageSchema.parse(message);
    return true;
  } catch {
    return false;
  }
}

/**
 * Sanitize payload for HIPAA mode
 * Strips any non-essential fields based on HIPAA requirements
 */
export function sanitizePayloadForHipaa(payload: Record<string, any>): Record<string, any> {
  if (!isHipaaMode()) {
    return payload;
  }

  // Allowed fields in HIPAA mode (whitelist approach)
  const allowedFields = new Set([
    // IDs and hashes
    'runId',
    'projectId',
    'nodeId',
    'manuscriptId',
    'commitHash',
    'sessionId',
    'userId',
    'parentCommitHash',
    // Status and timestamps
    'status',
    'previousStatus',
    'timestamp',
    'lastActivityTimestamp',
    // Numeric metrics only
    'progress',
    'durationMs',
    'itemsProcessed',
    'itemsTotal',
    'stageCount',
    'activeUserCount',
    'changeCount',
    // Error codes (not messages)
    'errorCode',
    // System identifiers
    'branchName',
    'activeUserIds',
  ]);

  const sanitized: Record<string, any> = {};

  for (const [key, value] of Object.entries(payload)) {
    if (allowedFields.has(key)) {
      sanitized[key] = value;
    }
  }

  return sanitized;
}

/**
 * Create a PHI-safe protocol event with automatic sanitization
 */
export function createProtocolEvent<T extends ProtocolEvent['type']>(
  type: T,
  payload: Record<string, any>
): ProtocolEvent {
  const sanitizedPayload = sanitizePayloadForHipaa(payload);

  const event = {
    type,
    timestamp: new Date().toISOString(),
    payload: sanitizedPayload,
  };

  // Validate the event matches the protocol
  const result = ProtocolEventSchema.safeParse(event);

  if (!result.success) {
    throw new Error(
      `Invalid protocol event: ${result.error.message}`
    );
  }

  return result.data;
}
