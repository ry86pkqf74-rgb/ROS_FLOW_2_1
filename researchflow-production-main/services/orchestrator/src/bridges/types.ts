/**
 * Type definitions for AI Router Bridge
 */

export interface AgentMetadata {
  agentId: string;
  projectId: string;
  runId: string;
  threadId: string;
  stageRange: [number, number];
  currentStage: number;
}

export interface LLMRequest {
  prompt: string;
  options: ModelOptions;
  metadata: AgentMetadata;
}

export interface ModelOptions {
  taskType: string;
  stageId?: number;
  modelTier?: 'ECONOMY' | 'STANDARD' | 'PREMIUM';
  governanceMode?: 'DEMO' | 'LIVE';
  requirePhiCompliance?: boolean;
  budgetLimit?: number;
  maxTokens?: number;
  temperature?: number;
  streamResponse?: boolean;
}

export interface LLMResponse {
  content: string;
  usage: TokenUsage;
  cost: CostBreakdown;
  model: string;
  tier: string;
  finishReason: string;
  metadata?: Record<string, any>;
}

export interface TokenUsage {
  totalTokens: number;
  promptTokens: number;
  completionTokens: number;
}

export interface CostBreakdown {
  total: number;
  input: number;
  output: number;
}

export interface RoutingResponse {
  selectedTier: string;
  model: string;
  tierConfig: {
    name: string;
    description: string;
    maxTokens: number;
    phiCompliant: boolean;
  };
  costEstimate: CostBreakdown;
  allTierCosts: Record<string, CostBreakdown>;
  recommendation: {
    taskType: string;
    recommendedTier: string;
    minimumTier: string;
    reason: string;
  };
  constraints: {
    budgetLimit?: number;
    requirePhiCompliance?: boolean;
    governanceMode: string;
  };
}

export interface BridgeConfig {
  orchestratorUrl: string;
  defaultTier: 'ECONOMY' | 'STANDARD' | 'PREMIUM';
  phiCompliantOnly: boolean;
  maxRetries: number;
  timeoutMs: number;
  costTrackingEnabled: boolean;
  streamingEnabled: boolean;
}

export interface BridgeHealthStatus {
  status: 'healthy' | 'unhealthy';
  orchestratorReachable: boolean;
  aiRouterAvailable: boolean;
  latencyMs: number;
}

export interface CostStatistics {
  totalCost: number;
  requestCount: number;
  averageCostPerRequest: number;
}

export interface StreamingChunk {
  content: string;
  finishReason?: string;
  metadata?: Record<string, any>;
}

export interface BatchRequest {
  prompts: string[];
  options: ModelOptions;
  metadata: AgentMetadata;
}

export interface BatchResponse {
  responses: LLMResponse[];
  totalCost: number;
  averageLatency: number;
  successCount: number;
  errorCount: number;
}

// Error types
export class AIRouterBridgeError extends Error {
  constructor(
    message: string,
    public readonly code: string,
    public readonly details?: any
  ) {
    super(message);
    this.name = 'AIRouterBridgeError';
  }
}

export class RoutingError extends AIRouterBridgeError {
  constructor(message: string, details?: any) {
    super(message, 'ROUTING_ERROR', details);
  }
}

export class LLMCallError extends AIRouterBridgeError {
  constructor(message: string, details?: any) {
    super(message, 'LLM_CALL_ERROR', details);
  }
}

export class BudgetExceededError extends AIRouterBridgeError {
  constructor(estimatedCost: number, budgetLimit: number) {
    super(
      `Estimated cost ${estimatedCost} exceeds budget limit ${budgetLimit}`,
      'BUDGET_EXCEEDED',
      { estimatedCost, budgetLimit }
    );
  }
}

export class PHIComplianceError extends AIRouterBridgeError {
  constructor(modelTier: string) {
    super(
      `Model tier ${modelTier} is not PHI compliant`,
      'PHI_COMPLIANCE_ERROR',
      { modelTier }
    );
  }
}

// Agent-specific types
export interface IRBAgentContext {
  studyType: string;
  riskLevel: 'minimal' | 'low' | 'moderate' | 'high';
  phiInvolved: boolean;
  vulnerablePopulations: boolean;
  humanReviewRequired: boolean;
}

export interface ManuscriptAgentContext {
  manuscriptType: 'research_article' | 'review' | 'case_study';
  targetJournal?: string;
  wordLimit?: number;
  citationStyle: string;
  figuresRequired: boolean;
}

export interface QualityAgentContext {
  validationType: 'phi_scan' | 'citation_check' | 'fact_check';
  strictnessLevel: 'standard' | 'high' | 'maximum';
  requireHumanReview: boolean;
}

// Union type for agent contexts
export type AgentContext = 
  | IRBAgentContext
  | ManuscriptAgentContext
  | QualityAgentContext
  | Record<string, any>;

// Extended LLM request with agent context
export interface AgentLLMRequest extends LLMRequest {
  agentContext?: AgentContext;
}