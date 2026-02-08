/**
 * AI Router Routes (Tasks 64-68)
 *
 * Provides intelligent AI model routing with:
 * - Model tier selection based on task complexity and budget
 * - Cost estimation and budget tracking
 * - Governance mode aware routing (DEMO vs LIVE)
 * - PHI-compliant model selection
 */

import { Router, type Request, type Response, type NextFunction } from 'express';
import * as z from 'zod';

import { asyncHandler } from '../middleware/asyncHandler';
import { requirePermission } from '../middleware/rbac';
import { logAction } from '../services/audit-service';

const router = Router();

/** Allow ANALYZE permission or allowlisted service token (dispatch only). */
function requireAnalyzeOrServiceToken(req: Request, res: Response, next: NextFunction): void {
  if ((req as { auth?: { isServiceToken?: boolean } }).auth?.isServiceToken === true) {
    return next();
  }
  requirePermission('ANALYZE')(req, res, next);
}

// Model tier definitions
const MODEL_TIERS = {
  economy: {
    id: 'economy',
    name: 'Economy',
    description: 'Fast and cost-effective for simple tasks',
    costPerInputToken: 0.0001,
    costPerOutputToken: 0.00015,
    maxTokens: 4096,
    latency: 'low',
    quality: 'good',
    capabilities: ['text_generation', 'basic_analysis', 'summarization'],
    phiCompliant: false,
    models: ['claude-3-haiku-20240307'],
  },
  standard: {
    id: 'standard',
    name: 'Standard',
    description: 'Balanced performance for most research tasks',
    costPerInputToken: 0.001,
    costPerOutputToken: 0.0015,
    maxTokens: 32768,
    latency: 'medium',
    quality: 'better',
    capabilities: ['advanced_analysis', 'code_generation', 'research_synthesis', 'citation_analysis'],
    phiCompliant: true,
    models: ['claude-3-5-sonnet-20241022'],
  },
  premium: {
    id: 'premium',
    name: 'Premium',
    description: 'Maximum capability for complex research',
    costPerInputToken: 0.01,
    costPerOutputToken: 0.015,
    maxTokens: 200000,
    latency: 'high',
    quality: 'best',
    capabilities: ['deep_analysis', 'multi_step_reasoning', 'creative_synthesis', 'phi_processing', 'long_context'],
    phiCompliant: true,
    models: ['claude-3-5-opus-20240620'],
  },
} as const;

type ModelTier = keyof typeof MODEL_TIERS;

// Task type to recommended tier mapping
const TASK_TIER_MAPPING: Record<string, { recommended: ModelTier; minimum: ModelTier }> = {
  hypothesis_generation: { recommended: 'standard', minimum: 'economy' },
  literature_search: { recommended: 'economy', minimum: 'economy' },
  data_analysis: { recommended: 'standard', minimum: 'standard' },
  statistical_analysis: { recommended: 'premium', minimum: 'standard' },
  manuscript_drafting: { recommended: 'standard', minimum: 'standard' },
  manuscript_revision: { recommended: 'standard', minimum: 'economy' },
  citation_formatting: { recommended: 'economy', minimum: 'economy' },
  phi_redaction: { recommended: 'premium', minimum: 'premium' },
  ethical_review: { recommended: 'premium', minimum: 'standard' },
  claim_verification: { recommended: 'standard', minimum: 'standard' },
  summarization: { recommended: 'economy', minimum: 'economy' },
  code_generation: { recommended: 'standard', minimum: 'economy' },
  figure_generation: { recommended: 'standard', minimum: 'standard' },
};

// Schemas
const RouteRequestSchema = z.object({
  taskType: z.string(),
  estimatedInputTokens: z.number().positive(),
  estimatedOutputTokens: z.number().positive().optional(),
  governanceMode: z.enum(['DEMO', 'LIVE']),
  preferredTier: z.enum(['economy', 'standard', 'premium']).optional(),
  budgetLimit: z.number().positive().optional(),
  requirePhiCompliance: z.boolean().optional(),
  stageId: z.number().int().positive().optional(),
  // Approval tracking fields
  approvalId: z.string().optional(),
  approvedBy: z.string().optional(),
  approvalTimestamp: z.string().datetime().optional(),
});

const CostEstimateSchema = z.object({
  tier: z.enum(['economy', 'standard', 'premium']),
  inputTokens: z.number().positive(),
  outputTokens: z.number().positive(),
});

const DispatchRequestSchema = z.object({
  task_type: z.string().min(1),
  request_id: z.string().min(1),
  workflow_id: z.string().optional(),
  user_id: z.string().optional(),
  mode: z.enum(['DEMO', 'LIVE']).optional(),
  risk_tier: z.enum(['PHI', 'SENSITIVE', 'NON_SENSITIVE']).optional(),
  domain_id: z.string().optional(),
  inputs: z.record(z.any()).optional(),
  budgets: z.record(z.any()).optional(),
});

/**
 * Parse and validate AGENT_ENDPOINTS_JSON at module initialization.
 * Format: {"agent-stage2-lit": "http://agent-stage2-lit:8000", ...}
 * This is the SINGLE SOURCE OF TRUTH for all agent routing.
 * 
 * Validation rules:
 * 1. Must be valid JSON object
 * 2. All values must be valid http:// or https:// URLs
 * 3. All values must not have trailing slashes (normalized automatically)
 */
function getAgentEndpoints(): Record<string, string> {
  const envVar = process.env.AGENT_ENDPOINTS_JSON;
  
  if (!envVar) {
    throw new Error(
      'AGENT_ENDPOINTS_JSON environment variable is missing. ' +
      'Add it to docker-compose.yml orchestrator environment and restart.'
    );
  }

  let parsed: unknown;
  try {
    parsed = JSON.parse(envVar);
  } catch (error) {
    throw new Error(
      `AGENT_ENDPOINTS_JSON is not valid JSON: ${error instanceof Error ? error.message : String(error)}. ` +
      'Fix the JSON syntax in docker-compose.yml orchestrator environment.'
    );
  }

  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
    throw new Error(
      'AGENT_ENDPOINTS_JSON must be a JSON object (e.g., {"agent-name":"http://..."}), ' +
      `but got: ${typeof parsed}. Fix in docker-compose.yml orchestrator environment.`
    );
  }

  const endpoints = parsed as Record<string, unknown>;
  const invalidUrls: string[] = [];
  const normalizedEndpoints: Record<string, string> = {};

  for (const [agentKey, url] of Object.entries(endpoints)) {
    if (typeof url !== 'string') {
      invalidUrls.push(`${agentKey}: not a string (got ${typeof url})`);
      continue;
    }

    // Validate URL format (must be http:// or https://)
    if (!url.match(/^https?:\/\//)) {
      invalidUrls.push(`${agentKey}: "${url}" (must start with http:// or https://)`);
      continue;
    }

    // Normalize by trimming trailing slash
    normalizedEndpoints[agentKey] = url.replace(/\/+$/, '');
  }

  if (invalidUrls.length > 0) {
    throw new Error(
      'AGENT_ENDPOINTS_JSON contains invalid URLs:\n' +
      invalidUrls.map(err => `  - ${err}`).join('\n') +
      '\nFix these entries in docker-compose.yml orchestrator environment.'
    );
  }

  console.log(`[ai-router] ✓ Loaded ${Object.keys(normalizedEndpoints).length} agent endpoints from AGENT_ENDPOINTS_JSON`);
  return normalizedEndpoints;
}

// Initialize agent endpoints at module load (fail-fast)
const AGENT_ENDPOINTS_STATE: { endpoints: Record<string, string>; error?: string } = (() => {
  try {
    const endpoints = getAgentEndpoints();
    return { endpoints };
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    console.error('[ai-router] CRITICAL:', errorMessage);
    return { endpoints: {}, error: errorMessage };
  }
})();

/**
 * Resolve agent base URL from AGENT_ENDPOINTS_JSON registry.
 * 
 * @param agentKey - The agent key to resolve (must match a key in AGENT_ENDPOINTS_JSON)
 * @returns The base URL for the agent (without trailing slash)
 * @throws Error with detailed remediation if agent is not configured
 */
function resolveAgentBaseUrl(agentKey: string): string {
  // Check if registry is misconfigured
  if (AGENT_ENDPOINTS_STATE.error) {
    throw new Error(
      `Agent registry is misconfigured: ${AGENT_ENDPOINTS_STATE.error}\n` +
      'Fix AGENT_ENDPOINTS_JSON in docker-compose.yml orchestrator environment and restart.'
    );
  }

  const url = AGENT_ENDPOINTS_STATE.endpoints[agentKey];
  if (!url) {
    const availableKeys = Object.keys(AGENT_ENDPOINTS_STATE.endpoints);
    const sortedKeys = availableKeys.sort();
    
    throw new Error(
      `Missing agent endpoint for key: ${agentKey}\n\n` +
      `Available agents (${availableKeys.length}):\n` +
      sortedKeys.map(k => `  - ${k}: ${AGENT_ENDPOINTS_STATE.endpoints[k]}`).join('\n') + '\n\n' +
      `Remediation:\n` +
      `  1. Add "${agentKey}":"http://${agentKey}:8000" to AGENT_ENDPOINTS_JSON in docker-compose.yml\n` +
      `  2. Ensure the compose service "${agentKey}" is defined\n` +
      `  3. Restart orchestrator: docker compose up -d --force-recreate orchestrator`
    );
  }

  return url;
}

/**
 * GET /api/ai/router/tiers
 * Get available model tiers and their configurations
 */
router.get(
  '/tiers',
  asyncHandler(async (req: Request, res: Response) => {
    const { governanceMode } = req.query;

    let tiers = Object.values(MODEL_TIERS);

    // Filter by PHI compliance if in LIVE mode
    if (governanceMode === 'LIVE') {
      tiers = tiers.filter((tier) => tier.phiCompliant);
    }

    res.json({
      tiers: tiers.map((tier) => ({
        id: tier.id,
        name: tier.name,
        description: tier.description,
        costPerInputToken: tier.costPerInputToken,
        costPerOutputToken: tier.costPerOutputToken,
        maxTokens: tier.maxTokens,
        latency: tier.latency,
        quality: tier.quality,
        capabilities: tier.capabilities,
        phiCompliant: tier.phiCompliant,
      })),
      defaultTier: governanceMode === 'LIVE' ? 'standard' : 'economy',
    });
  })
);

/**
 * POST /api/ai/router/dispatch
 * Route task to appropriate agent service (Milestone 1: Stage 2 only)
 */
router.post(
  '/dispatch',
  requireAnalyzeOrServiceToken,
  asyncHandler(async (req: Request, res: Response) => {
    // Debug: Log auth header presence and user context (dev only, PHI-safe, blocked in production)
    if (process.env.DEBUG_INTERNAL_AUTH === 'true' && process.env.NODE_ENV !== 'production') {
      const hasAuthHeader = typeof req.headers.authorization === 'string' && req.headers.authorization.startsWith('Bearer ');
      console.log('[DEBUG /api/ai/router/dispatch]', {
        path: req.path,
        method: req.method,
        hasAuthHeader,
        authHeaderLength: hasAuthHeader ? req.headers.authorization?.length : 0,
        hasReqUser: Boolean((req as any).user),
        reqUserId: (req as any).user?.id,
        reqUserRole: (req as any).user?.role,
      });
    }

    const user = req.user;

    if (!user) {
      return res.status(401).json({
        error: 'AUTHENTICATION_REQUIRED',
        message: 'Authentication required',
      });
    }

    const validation = DispatchRequestSchema.safeParse(req.body);
    if (!validation.success) {
      return res.status(400).json({
        error: 'VALIDATION_ERROR',
        message: 'Invalid request body',
        details: validation.error.flatten(),
      });
    }

    const { task_type, request_id, workflow_id, user_id, mode, risk_tier, domain_id, inputs, budgets } =
      validation.data;

    // Map task_type to agentKey (must match keys in AGENT_ENDPOINTS_JSON)
    // IMPORTANT: For LangSmith-backed agents, use the proxy service name (e.g., agent-X-proxy), not the logical name
    const TASK_TYPE_TO_AGENT: Record<string, string> = {
      // Native agents (FastAPI services with local execution)
      STAGE_2_LITERATURE_REVIEW: 'agent-stage2-lit',
      STAGE2_SCREEN: 'agent-stage2-screen',
      STAGE_2_EXTRACT: 'agent-stage2-extract',
      // Back-compat alias (some tools/tests use this variant)
      STAGE2_EXTRACT: 'agent-stage2-extract',
      STAGE2_SYNTHESIZE: 'agent-stage2-synthesize',
      LIT_RETRIEVAL: 'agent-lit-retrieval',
      LIT_TRIAGE: 'agent-lit-triage',
      POLICY_REVIEW: 'agent-policy-review',
      RAG_INGEST: 'agent-rag-ingest',
      RAG_RETRIEVE: 'agent-rag-retrieve',
      SECTION_WRITE_INTRO: 'agent-intro-writer',
      SECTION_WRITE_METHODS: 'agent-methods-writer',
      SECTION_WRITE_RESULTS: 'agent-results-writer',
      SECTION_WRITE_DISCUSSION: 'agent-discussion-writer',
      CLAIM_VERIFY: 'agent-verify',
      EVIDENCE_SYNTHESIS: 'agent-evidence-synthesis',
      
      // LangSmith-backed agents (use proxy service names as keys)
      CLINICAL_MANUSCRIPT_WRITE: 'agent-clinical-manuscript-proxy',
      CLINICAL_SECTION_DRAFT: 'agent-section-drafter-proxy',
      RESULTS_INTERPRETATION: 'agent-results-interpretation-proxy',
      STATISTICAL_ANALYSIS: 'agent-results-interpretation-proxy',  // Alias for results interpretation
      PEER_REVIEW_SIMULATION: 'agent-peer-review-simulator-proxy',
      CLINICAL_BIAS_DETECTION: 'agent-bias-detection-proxy',
      DISSEMINATION_FORMATTING: 'agent-dissemination-formatter-proxy',
      PERFORMANCE_OPTIMIZATION: 'agent-performance-optimizer-proxy',
      JOURNAL_GUIDELINES_CACHE: 'agent-journal-guidelines-cache-proxy',
      COMPLIANCE_AUDIT: 'agent-compliance-auditor-proxy',
      ARTIFACT_AUDIT: 'agent-artifact-auditor-proxy',
      RESILIENCE_ARCHITECTURE: 'agent-resilience-architecture-advisor-proxy',
      MULTILINGUAL_LITERATURE_PROCESSING: 'agent-multilingual-literature-processor-proxy',
      CLINICAL_MODEL_FINE_TUNING: 'agent-clinical-model-fine-tuner-proxy',
      HYPOTHESIS_REFINEMENT: 'agent-hypothesis-refiner-proxy',
    };
    const agent_name = TASK_TYPE_TO_AGENT[task_type];
    if (!agent_name) {
      const supportedTypes = Object.keys(TASK_TYPE_TO_AGENT);
      return res.status(400).json({
        error: 'UNSUPPORTED_TASK_TYPE',
        message: `Task type "${task_type}" is not supported. Allowed values: ${supportedTypes.join(', ')}`,
        supportedTypes,
      });
    }

    // Resolve agent URL from AGENT_ENDPOINTS_JSON (single source of truth - no fallbacks)
    let agent_url: string;
    try {
      agent_url = resolveAgentBaseUrl(agent_name);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      return res.status(500).json({
        error: 'AGENT_NOT_CONFIGURED',
        message: errorMessage,
        agent_key: agent_name,
        task_type,
      });
    }

    // Log dispatch decision
    await logAction({
      eventType: 'AI_ROUTING',
      action: 'DISPATCH_REQUESTED',
      userId: user.id,
      resourceType: 'ai_router',
      resourceId: request_id,
      details: {
        task_type,
        agent_name,
        request_id,
        workflow_id,
        mode,
        risk_tier,
        domain_id,
      },
    });

    res.json({
      dispatch_type: 'agent',
      agent_name,
      agent_url,
      budgets: budgets || {},
      rag_plan: {},
      request_id,
    });
  })
);

/**
 * POST /api/ai/router/route
 * Get routing recommendation for a task
 */
router.post(
  '/route',
  requirePermission('ANALYZE'),
  asyncHandler(async (req: Request, res: Response) => {
    const user = req.user;

    if (!user) {
      return res.status(401).json({
        error: 'AUTHENTICATION_REQUIRED',
        message: 'Authentication required',
      });
    }

    const validation = RouteRequestSchema.safeParse(req.body);
    if (!validation.success) {
      return res.status(400).json({
        error: 'VALIDATION_ERROR',
        message: 'Invalid request body',
        details: validation.error.flatten(),
      });
    }

    const {
      taskType,
      estimatedInputTokens,
      estimatedOutputTokens = Math.round(estimatedInputTokens * 0.5),
      governanceMode,
      preferredTier,
      budgetLimit,
      requirePhiCompliance,
      stageId,
      approvalId,
      approvedBy,
      approvalTimestamp,
    } = validation.data;

    // Get task mapping or use defaults
    const taskMapping = TASK_TIER_MAPPING[taskType] || {
      recommended: 'standard',
      minimum: 'economy',
    };

    // Determine effective minimum tier based on requirements
    let effectiveMinimumTier: ModelTier = taskMapping.minimum;

    // PHI compliance requirement
    if (requirePhiCompliance || governanceMode === 'LIVE') {
      if (!MODEL_TIERS[effectiveMinimumTier].phiCompliant) {
        effectiveMinimumTier = 'standard';
      }
    }

    // Calculate costs for each tier
    const tierCosts: Record<ModelTier, { inputCost: number; outputCost: number; totalCost: number }> = {} as any;

    for (const [tierId, tier] of Object.entries(MODEL_TIERS)) {
      const inputCost = estimatedInputTokens * tier.costPerInputToken;
      const outputCost = estimatedOutputTokens * tier.costPerOutputToken;
      tierCosts[tierId as ModelTier] = {
        inputCost,
        outputCost,
        totalCost: inputCost + outputCost,
      };
    }

    // Select recommended tier
    let selectedTier: ModelTier = preferredTier || taskMapping.recommended;

    // Check budget constraint
    if (budgetLimit && tierCosts[selectedTier].totalCost > budgetLimit) {
      // Find the highest tier within budget
      const tiersInBudget = (['economy', 'standard', 'premium'] as ModelTier[])
        .filter((tier) => tierCosts[tier].totalCost <= budgetLimit)
        .filter((tier) => MODEL_TIERS[tier].phiCompliant || !requirePhiCompliance);

      if (tiersInBudget.length > 0) {
        selectedTier = tiersInBudget[tiersInBudget.length - 1];
      } else {
        return res.status(400).json({
          error: 'BUDGET_INSUFFICIENT',
          message: 'Budget is insufficient for any compliant model tier',
          lowestCost: tierCosts[effectiveMinimumTier].totalCost,
          budgetLimit,
        });
      }
    }

    // Ensure minimum tier requirements are met
    const tierOrder: ModelTier[] = ['economy', 'standard', 'premium'];
    const selectedTierIndex = tierOrder.indexOf(selectedTier);
    const minimumTierIndex = tierOrder.indexOf(effectiveMinimumTier);

    if (selectedTierIndex < minimumTierIndex) {
      selectedTier = effectiveMinimumTier;
    }

    const selectedTierConfig = MODEL_TIERS[selectedTier];

    // Log routing decision with approval metadata
    await logAction({
      eventType: 'AI_ROUTING',
      action: 'ROUTE_SELECTED',
      userId: user.id,
      resourceType: 'ai_router',
      resourceId: `route_${Date.now()}`,
      details: {
        taskType,
        selectedTier,
        governanceMode,
        estimatedCost: tierCosts[selectedTier].totalCost,
        stageId,
        // Approval tracking
        approvalId,
        approvedBy,
        approvalTimestamp,
        approvalRequired: governanceMode === 'LIVE',
      },
    });

    res.json({
      selectedTier,
      model: selectedTierConfig.models[0],
      tierConfig: {
        name: selectedTierConfig.name,
        description: selectedTierConfig.description,
        maxTokens: selectedTierConfig.maxTokens,
        phiCompliant: selectedTierConfig.phiCompliant,
      },
      costEstimate: tierCosts[selectedTier],
      allTierCosts: tierCosts,
      recommendation: {
        taskType,
        recommendedTier: taskMapping.recommended,
        minimumTier: effectiveMinimumTier,
        reason: getRecommendationReason(taskType, selectedTier, taskMapping.recommended, governanceMode),
      },
      constraints: {
        budgetLimit,
        requirePhiCompliance,
        governanceMode,
      },
    });
  })
);

/**
 * POST /api/ai/router/estimate
 * Get cost estimate for a specific tier
 */
router.post(
  '/estimate',
  asyncHandler(async (req: Request, res: Response) => {
    const validation = CostEstimateSchema.safeParse(req.body);
    if (!validation.success) {
      return res.status(400).json({
        error: 'VALIDATION_ERROR',
        message: 'Invalid request body',
        details: validation.error.flatten(),
      });
    }

    const { tier, inputTokens, outputTokens } = validation.data;
    const tierConfig = MODEL_TIERS[tier];

    const inputCost = inputTokens * tierConfig.costPerInputToken;
    const outputCost = outputTokens * tierConfig.costPerOutputToken;

    res.json({
      tier,
      tokens: {
        input: inputTokens,
        output: outputTokens,
        total: inputTokens + outputTokens,
      },
      cost: {
        input: inputCost,
        output: outputCost,
        total: inputCost + outputCost,
      },
      rates: {
        inputPerToken: tierConfig.costPerInputToken,
        outputPerToken: tierConfig.costPerOutputToken,
      },
    });
  })
);

/**
 * GET /api/ai/router/task-types
 * Get supported task types and their tier mappings
 */
router.get(
  '/task-types',
  asyncHandler(async (req: Request, res: Response) => {
    res.json({
      taskTypes: Object.entries(TASK_TIER_MAPPING).map(([taskType, mapping]) => ({
        taskType,
        recommendedTier: mapping.recommended,
        minimumTier: mapping.minimum,
        description: getTaskTypeDescription(taskType),
      })),
    });
  })
);

/**
 * GET /api/ai/router/capabilities
 * Get capabilities by tier
 */
router.get(
  '/capabilities',
  asyncHandler(async (req: Request, res: Response) => {
    const allCapabilities = new Set<string>();
    const capabilityTiers: Record<string, ModelTier[]> = {};

    for (const [tierId, tier] of Object.entries(MODEL_TIERS)) {
      for (const capability of tier.capabilities) {
        allCapabilities.add(capability);
        if (!capabilityTiers[capability]) {
          capabilityTiers[capability] = [];
        }
        capabilityTiers[capability].push(tierId as ModelTier);
      }
    }

    res.json({
      capabilities: Array.from(allCapabilities).map((capability) => ({
        name: capability,
        availableIn: capabilityTiers[capability],
        minimumTier: capabilityTiers[capability][0],
      })),
    });
  })
);

// Helper functions
function getRecommendationReason(
  taskType: string,
  selectedTier: ModelTier,
  recommendedTier: ModelTier,
  governanceMode: string
): string {
  if (selectedTier === recommendedTier) {
    return `${MODEL_TIERS[selectedTier].name} tier is optimal for ${taskType.replace(/_/g, ' ')} tasks.`;
  }

  if (governanceMode === 'LIVE' && !MODEL_TIERS[recommendedTier].phiCompliant) {
    return `Upgraded to ${MODEL_TIERS[selectedTier].name} tier for PHI compliance in LIVE mode.`;
  }

  const tierOrder: ModelTier[] = ['economy', 'standard', 'premium'];
  if (tierOrder.indexOf(selectedTier) < tierOrder.indexOf(recommendedTier)) {
    return `Using ${MODEL_TIERS[selectedTier].name} tier due to budget constraints. Consider ${MODEL_TIERS[recommendedTier].name} for better results.`;
  }

  return `Using ${MODEL_TIERS[selectedTier].name} tier based on preference.`;
}

function getTaskTypeDescription(taskType: string): string {
  const descriptions: Record<string, string> = {
    hypothesis_generation: 'Generate and refine research hypotheses',
    literature_search: 'Search and analyze academic literature',
    data_analysis: 'Analyze research data and datasets',
    statistical_analysis: 'Perform statistical tests and analysis',
    manuscript_drafting: 'Draft manuscript sections',
    manuscript_revision: 'Revise and improve manuscript content',
    citation_formatting: 'Format and validate citations',
    phi_redaction: 'Detect and redact protected health information',
    ethical_review: 'Review content for ethical compliance',
    claim_verification: 'Verify research claims and statements',
    summarization: 'Summarize documents and content',
    code_generation: 'Generate analysis code and scripts',
    figure_generation: 'Generate data visualizations',
  };
  return descriptions[taskType] || 'General research task';
}

export default router;
