/**
 * Enhanced Audit Event Schema (v2)
 * Regulatory-grade audit logging with tamper-evident chain
 *
 * @module packages/shared/src/schemas/audit_event_v2
 * @version 2.0.0
 */

import * as z from 'zod';

// Governance Mode
export const GovernanceModeSchema = z.enum(['DEMO', 'LIVE']);

// Model Tier
export const ModelTierSchema = z.enum(['NANO', 'MINI', 'STANDARD', 'FRONTIER']);

// PHI Scan Result
export const PHIScanResultSchema = z.enum(['PASS', 'FAIL', 'SKIPPED', 'ERROR']);

// Audit Event Type
export const AuditEventTypeSchema = z.enum([
  'MODEL_INFERENCE',
  'MODEL_REGISTRATION',
  'MODEL_DEPLOYMENT',
  'MODEL_ROLLBACK',
  'DATA_ACCESS',
  'DATA_EXPORT',
  'CONFIG_CHANGE',
  'USER_ACTION',
  'SYSTEM_EVENT',
  'APPROVAL_REQUEST',
  'APPROVAL_GRANTED',
  'APPROVAL_DENIED',
  'PHI_DETECTED',
  'DRIFT_ALERT',
  'SAFETY_EVENT',
]);

// Actor Identity Schema
export const ActorIdentitySchema = z.object({
  user_id: z.string().uuid().optional(),
  service_account: z.string().optional(),
  system_component: z.string().optional(),
  ip_address: z.string().ip().optional(),
  user_agent: z.string().optional(),
}).refine(
  data => data.user_id || data.service_account || data.system_component,
  { message: 'At least one actor identifier required' }
);

// Model Identifier Schema
export const ModelIdentifierSchema = z.object({
  model_id: z.string().uuid(),
  model_name: z.string(),
  version: z.string(),
  tier: ModelTierSchema,
  container_digest: z.string().optional(),
});

// Approval Event Schema
export const ApprovalEventSchema = z.object({
  approval_id: z.string().uuid(),
  approved_by: z.string(),
  approved_at: z.string().datetime(),
  approval_type: z.enum(['DEPLOYMENT', 'DATA_ACCESS', 'CONFIG_CHANGE', 'OVERRIDE']),
  rationale: z.string().min(10),
  conditions: z.array(z.string()).optional(),
  expires_at: z.string().datetime().optional(),
});

// Hash Chain Link Schema
export const HashChainLinkSchema = z.object({
  previous_event_hash: z.string().length(64), // SHA-256
  sequence_number: z.number().int().nonnegative(),
  chain_id: z.string().uuid(),
});

// Enhanced Audit Event Schema (v2)
export const AuditEventV2Schema = z.object({
  // Core identifiers
  event_id: z.string().uuid(),
  request_id: z.string().uuid(), // Correlation ID across services
  timestamp: z.string().datetime(),
  event_type: AuditEventTypeSchema,

  // Actor information
  actor_identity: ActorIdentitySchema,
  actor_role: z.string(),

  // Organization scope
  organization_id: z.string().uuid(),
  project_id: z.string().uuid().optional(),
  governance_mode: GovernanceModeSchema,

  // Model information (if applicable)
  model_identifier: ModelIdentifierSchema.optional(),

  // Prompt/Template reference (not raw content for privacy)
  prompt_template_id: z.string().uuid().optional(),
  prompt_version: z.string().optional(),

  // Input/Output hashing (for reproducibility without storing PHI)
  input_hash: z.string().length(64).optional(), // SHA-256
  output_hash: z.string().length(64).optional(), // SHA-256
  input_token_count: z.number().int().nonnegative().optional(),
  output_token_count: z.number().int().nonnegative().optional(),

  // PHI scanning
  phi_scan_result: PHIScanResultSchema.optional(),
  phi_scan_rule_version: z.string().optional(),
  phi_categories_detected: z.array(z.string()).optional(),

  // Generated artifacts
  artifact_ids: z.array(z.string().uuid()).optional(),

  // Approval chain
  approval_events: z.array(ApprovalEventSchema).optional(),

  // Action details
  action: z.string(),
  action_details: z.record(z.unknown()).optional(),
  outcome: z.enum(['SUCCESS', 'FAILURE', 'PARTIAL', 'PENDING']),
  error_message: z.string().optional(),

  // Performance
  latency_ms: z.number().int().nonnegative().optional(),

  // Hash chain (tamper-evident)
  hash_chain: HashChainLinkSchema.optional(),
  event_hash: z.string().length(64).optional(), // SHA-256 of this event

  // Metadata
  schema_version: z.literal('2.0.0'),
  source_service: z.string(),
  environment: z.enum(['development', 'staging', 'production']),
});

// Chain Verification Result
export const ChainVerificationResultSchema = z.object({
  chain_id: z.string().uuid(),
  verified: z.boolean(),
  events_checked: z.number().int().nonnegative(),
  first_event_sequence: z.number().int().nonnegative(),
  last_event_sequence: z.number().int().nonnegative(),
  verification_timestamp: z.string().datetime(),
  broken_at_sequence: z.number().int().optional(),
  error_message: z.string().optional(),
});

// Audit Query Parameters
export const AuditQueryParamsSchema = z.object({
  start_time: z.string().datetime().optional(),
  end_time: z.string().datetime().optional(),
  event_types: z.array(AuditEventTypeSchema).optional(),
  actor_id: z.string().uuid().optional(),
  model_id: z.string().uuid().optional(),
  organization_id: z.string().uuid().optional(),
  governance_mode: GovernanceModeSchema.optional(),
  phi_scan_result: PHIScanResultSchema.optional(),
  limit: z.number().int().min(1).max(1000).default(100),
  offset: z.number().int().nonnegative().default(0),
  order: z.enum(['asc', 'desc']).default('desc'),
});

// Export types
export type GovernanceMode = z.infer<typeof GovernanceModeSchema>;
export type ModelTier = z.infer<typeof ModelTierSchema>;
export type PHIScanResult = z.infer<typeof PHIScanResultSchema>;
export type AuditEventType = z.infer<typeof AuditEventTypeSchema>;
export type ActorIdentity = z.infer<typeof ActorIdentitySchema>;
export type ModelIdentifier = z.infer<typeof ModelIdentifierSchema>;
export type ApprovalEvent = z.infer<typeof ApprovalEventSchema>;
export type HashChainLink = z.infer<typeof HashChainLinkSchema>;
export type AuditEventV2 = z.infer<typeof AuditEventV2Schema>;
export type ChainVerificationResult = z.infer<typeof ChainVerificationResultSchema>;
export type AuditQueryParams = z.infer<typeof AuditQueryParamsSchema>;

// Validation helpers
export function validateAuditEventV2(data: unknown): AuditEventV2 {
  return AuditEventV2Schema.parse(data);
}

export function validateChainVerification(data: unknown): ChainVerificationResult {
  return ChainVerificationResultSchema.parse(data);
}

// Helper to compute event hash (for use in hash chain)
export function computeEventHashPayload(event: Omit<AuditEventV2, 'event_hash' | 'hash_chain'>): string {
  // Deterministic JSON serialization
  const payload = {
    event_id: event.event_id,
    request_id: event.request_id,
    timestamp: event.timestamp,
    event_type: event.event_type,
    actor_identity: event.actor_identity,
    action: event.action,
    outcome: event.outcome,
    input_hash: event.input_hash,
    output_hash: event.output_hash,
  };
  return JSON.stringify(payload, Object.keys(payload).sort());
}

// Severity levels for safety events
export const SAFETY_SEVERITY_LEVELS = {
  INFO: { level: 0, auto_pause: false, alert: false },
  WARNING: { level: 1, auto_pause: false, alert: true },
  ERROR: { level: 2, auto_pause: false, alert: true },
  CRITICAL: { level: 3, auto_pause: true, alert: true, linear_ticket: true, slack_alert: true },
} as const;
