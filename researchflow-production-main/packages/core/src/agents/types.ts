/**
 * LangGraph Agent Types for ResearchFlow
 *
 * This module defines TypeScript types for the LangGraph chat agents,
 * including state management, improvement loops, and quality gates.
 *
 * These types mirror the Python TypedDict definitions in:
 * services/worker/src/agents/base/state.py
 */

import * as z from 'zod';

// =============================================================================
// Agent Identifiers and Enums
// =============================================================================

export const AgentIdSchema = z.enum([
  'dataprep',
  'analysis',
  'quality',
  'irb',
  'manuscript',
]);

export type AgentId = z.infer<typeof AgentIdSchema>;

export const GovernanceModeSchema = z.enum([
  'DEMO',
  'REVIEW',
  'LIVE',
]);

export type GovernanceMode = z.infer<typeof GovernanceModeSchema>;

export const GateStatusSchema = z.enum([
  'pending',
  'passed',
  'failed',
  'needs_human',
]);

export type GateStatus = z.infer<typeof GateStatusSchema>;

export const ImprovementStatusSchema = z.enum([
  'active',
  'complete',
  'reverted',
]);

export type ImprovementStatus = z.infer<typeof ImprovementStatusSchema>;

// =============================================================================
// Agent Stage Ranges
// =============================================================================

/**
 * Maps each agent to its workflow stage range.
 */
export const AGENT_STAGE_RANGES: Record<AgentId, [number, number]> = {
  dataprep: [1, 5],
  analysis: [6, 9],
  quality: [10, 12],
  irb: [13, 14],
  manuscript: [15, 20],
};

// =============================================================================
// Message Types
// =============================================================================

export const MessageRoleSchema = z.enum(['user', 'assistant', 'system', 'tool']);
export type MessageRole = z.infer<typeof MessageRoleSchema>;

export const MessageSchema = z.object({
  id: z.string().uuid(),
  role: MessageRoleSchema,
  content: z.string(),
  timestamp: z.string().datetime(),
  metadata: z.record(z.unknown()).optional(),
});

export type Message = z.infer<typeof MessageSchema>;

// =============================================================================
// Version Snapshot (for improvement loops)
// =============================================================================

export const VersionSnapshotSchema = z.object({
  versionId: z.string().uuid(),
  timestamp: z.string().datetime(),
  output: z.string(),
  qualityScore: z.number().min(0).max(1),
  improvementRequest: z.string().optional(),
  changes: z.array(z.string()),
});

export type VersionSnapshot = z.infer<typeof VersionSnapshotSchema>;

// =============================================================================
// Quality Gate Result
// =============================================================================

export const QualityGateResultSchema = z.object({
  passed: z.boolean(),
  score: z.number().min(0).max(1),
  criteria: z.record(z.object({
    name: z.string(),
    passed: z.boolean(),
    actual: z.unknown(),
    expected: z.unknown(),
    message: z.string().optional(),
  })),
  recommendations: z.array(z.string()),
  requiresHuman: z.boolean(),
});

export type QualityGateResult = z.infer<typeof QualityGateResultSchema>;

// =============================================================================
// Agent State
// =============================================================================

export const AgentStateSchema = z.object({
  // Identity
  agentId: AgentIdSchema,
  projectId: z.string().uuid(),
  runId: z.string().uuid(),
  threadId: z.string().uuid(),

  // Workflow position
  currentStage: z.number().int().min(1).max(20),
  stageRange: z.tuple([z.number().int(), z.number().int()]),

  // Governance
  governanceMode: GovernanceModeSchema,

  // Messages (conversation history)
  messages: z.array(MessageSchema),

  // Artifacts
  inputArtifactIds: z.array(z.string().uuid()),
  outputArtifactIds: z.array(z.string().uuid()),

  // Improvement loop
  iteration: z.number().int().min(0),
  maxIterations: z.number().int().min(1).default(5),
  previousVersions: z.array(VersionSnapshotSchema),

  // Quality gate
  gateStatus: GateStatusSchema,
  gateScore: z.number().min(0).max(1),
  gateResult: QualityGateResultSchema.nullable(),

  // Control flow
  improvementEnabled: z.boolean().default(true),
  feedback: z.string().nullable(),
  humanApproved: z.boolean().nullable(),
  errorMessage: z.string().nullable(),

  // Metrics
  tokenCount: z.number().int().min(0).default(0),
  startedAt: z.string().datetime().nullable(),
  completedAt: z.string().datetime().nullable(),
});

export type AgentState = z.infer<typeof AgentStateSchema>;

// =============================================================================
// Improvement Loop
// =============================================================================

export const ImprovementLoopSchema = z.object({
  id: z.string().uuid(),
  artifactId: z.string().uuid(),
  agentId: AgentIdSchema,
  currentVersionId: z.string().uuid(),
  versions: z.array(VersionSnapshotSchema),
  maxIterations: z.number().int().min(1),
  currentIteration: z.number().int().min(0),
  status: ImprovementStatusSchema,
  createdAt: z.string().datetime(),
  updatedAt: z.string().datetime(),
});

export type ImprovementLoop = z.infer<typeof ImprovementLoopSchema>;

// =============================================================================
// Checkpoint Metadata
// =============================================================================

export const CheckpointMetadataSchema = z.object({
  threadId: z.string().uuid(),
  runId: z.string().uuid(),
  agentId: AgentIdSchema,
  checkpointId: z.string().uuid(),
  parentCheckpointId: z.string().uuid().nullable(),
  timestamp: z.string().datetime(),
  stepCount: z.number().int().min(0),
  metadata: z.record(z.unknown()).optional(),
});

export type CheckpointMetadata = z.infer<typeof CheckpointMetadataSchema>;

// =============================================================================
// API Request/Response Types
// =============================================================================

export const AgentInvokeRequestSchema = z.object({
  agentId: AgentIdSchema,
  projectId: z.string().uuid(),
  artifactId: z.string().uuid().optional(),
  message: z.string().min(1),
  governanceMode: GovernanceModeSchema.default('DEMO'),
  threadId: z.string().uuid().optional(),
  maxIterations: z.number().int().min(1).max(10).default(5),
});

export type AgentInvokeRequest = z.infer<typeof AgentInvokeRequestSchema>;

export const AgentInvokeResponseSchema = z.object({
  runId: z.string().uuid(),
  threadId: z.string().uuid(),
  status: z.enum(['running', 'completed', 'failed', 'needs_human']),
  response: z.string().optional(),
  gateResult: QualityGateResultSchema.optional(),
  versionSnapshot: VersionSnapshotSchema.optional(),
  tokenCount: z.number().int().min(0).optional(),
});

export type AgentInvokeResponse = z.infer<typeof AgentInvokeResponseSchema>;

export const AgentResumeRequestSchema = z.object({
  threadId: z.string().uuid(),
  runId: z.string().uuid(),
  humanApproved: z.boolean().optional(),
  feedback: z.string().optional(),
});

export type AgentResumeRequest = z.infer<typeof AgentResumeRequestSchema>;

export const AgentImprovementRequestSchema = z.object({
  runId: z.string().uuid(),
  threadId: z.string().uuid(),
  feedback: z.string().min(1),
});

export type AgentImprovementRequest = z.infer<typeof AgentImprovementRequestSchema>;

export const AgentRevertRequestSchema = z.object({
  artifactId: z.string().uuid(),
  targetVersionId: z.string().uuid(),
});

export type AgentRevertRequest = z.infer<typeof AgentRevertRequestSchema>;

// =============================================================================
// SSE Event Types (for streaming)
// =============================================================================

export const AgentSSEEventTypeSchema = z.enum([
  'agent:started',
  'agent:message',
  'agent:tool_call',
  'agent:quality_gate',
  'agent:needs_human',
  'agent:iteration',
  'agent:version_saved',
  'agent:completed',
  'agent:failed',
  'agent:token_update',
]);

export type AgentSSEEventType = z.infer<typeof AgentSSEEventTypeSchema>;

export const AgentSSEEventSchema = z.object({
  type: AgentSSEEventTypeSchema,
  runId: z.string().uuid(),
  threadId: z.string().uuid(),
  agentId: AgentIdSchema,
  timestamp: z.string().datetime(),
  data: z.record(z.unknown()),
});

export type AgentSSEEvent = z.infer<typeof AgentSSEEventSchema>;

// =============================================================================
// LLM Bridge Types (for AI Router proxy)
// =============================================================================

export const LLMProxyRequestSchema = z.object({
  prompt: z.string().min(1),
  taskType: z.string(),
  stageId: z.number().int().min(1).max(20),
  modelTier: z.enum(['ECONOMY', 'STANDARD', 'PREMIUM']).default('STANDARD'),
  governanceMode: GovernanceModeSchema.default('DEMO'),
  maxTokens: z.number().int().min(1).max(16000).optional(),
  temperature: z.number().min(0).max(2).optional(),
  systemPrompt: z.string().optional(),
  metadata: z.record(z.unknown()).optional(),
});

export type LLMProxyRequest = z.infer<typeof LLMProxyRequestSchema>;

export const LLMProxyResponseSchema = z.object({
  content: z.string(),
  model: z.string(),
  tokenUsage: z.object({
    input: z.number().int().min(0),
    output: z.number().int().min(0),
    total: z.number().int().min(0),
  }),
  phiDetected: z.boolean(),
  phiCategories: z.array(z.string()).optional(),
  latencyMs: z.number().int().min(0),
  cached: z.boolean().optional(),
});

export type LLMProxyResponse = z.infer<typeof LLMProxyResponseSchema>;

// =============================================================================
// Utility Functions
// =============================================================================

/**
 * Get the agent ID responsible for a given workflow stage.
 */
export function getAgentForStage(stageId: number): AgentId | null {
  for (const [agentId, [start, end]] of Object.entries(AGENT_STAGE_RANGES)) {
    if (stageId >= start && stageId <= end) {
      return agentId as AgentId;
    }
  }
  return null;
}

/**
 * Check if a stage is within an agent's responsibility.
 */
export function isStageInAgentRange(agentId: AgentId, stageId: number): boolean {
  const [start, end] = AGENT_STAGE_RANGES[agentId];
  return stageId >= start && stageId <= end;
}

/**
 * Create initial agent state with defaults.
 */
export function createInitialAgentState(
  agentId: AgentId,
  projectId: string,
  runId: string,
  threadId: string,
  governanceMode: GovernanceMode = 'DEMO'
): AgentState {
  const [startStage, endStage] = AGENT_STAGE_RANGES[agentId];

  return {
    agentId,
    projectId,
    runId,
    threadId,
    currentStage: startStage,
    stageRange: [startStage, endStage],
    governanceMode,
    messages: [],
    inputArtifactIds: [],
    outputArtifactIds: [],
    iteration: 0,
    maxIterations: 5,
    previousVersions: [],
    gateStatus: 'pending',
    gateScore: 0,
    gateResult: null,
    improvementEnabled: true,
    feedback: null,
    humanApproved: null,
    errorMessage: null,
    tokenCount: 0,
    startedAt: null,
    completedAt: null,
  };
}
