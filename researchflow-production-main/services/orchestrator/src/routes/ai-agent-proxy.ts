/**
 * AI Agent Proxy Route (Phase 5.5 Stream F - ROS-30)
 *
 * Provides a proxy endpoint for Python LangGraph agents to invoke the AI Router.
 * All LLM calls from the worker's agents route through this endpoint to ensure:
 * - PHI compliance via the existing PHI scanning pipeline
 * - Governance mode enforcement (DEMO/REVIEW/LIVE)
 * - Cost tracking and audit logging
 * - Model tier selection based on task type
 *
 * This is the TypeScript side of the LLM bridge:
 * Python AIRouterBridge (llm_bridge.py) → HTTP → This Route → ModelRouterService
 */

import { getModelRouter } from '@researchflow/ai-router';
import type { AITaskType, ModelTier, QualityCheck } from '@researchflow/ai-router';
import { Router, type Request, type Response } from 'express';
import * as z from 'zod';

import { getWorkerClient } from '../clients/workerClient';
import { asyncHandler } from '../middleware/asyncHandler';
import { requirePermission } from '../middleware/rbac';
import { logAction } from '../services/audit-service';
import { attachCostEnvelope } from '../utils/cost-envelope';

const router = Router();

// =================================================================================================
// Request Schemas
// =================================================================================================

/**
 * Map model tier strings from Python to TypeScript ModelTier enum values
 *
 * ModelTier values: 'NANO' | 'MINI' | 'FRONTIER'
 * - NANO: Fast, cheap tasks (classify, extract, policy check)
 * - MINI: Moderate complexity (summarize, draft, template fill)
 * - FRONTIER: Complex reasoning (protocol, synthesis, final pass)
 */
const MODEL_TIER_MAP: Record<string, ModelTier> = {
  // Python agent tiers
  ECONOMY: 'NANO',
  STANDARD: 'MINI',
  PREMIUM: 'FRONTIER',
  // Direct mappings
  NANO: 'NANO',
  MINI: 'MINI',
  FRONTIER: 'FRONTIER',
};

/**
 * Map agent task types to AI Router task types
 *
 * AITaskType values:
 * NANO tier: classify, extract_metadata, policy_check, phi_scan, format_validate
 * MINI tier: summarize, draft_section, template_fill, abstract_generate
 * FRONTIER tier: protocol_reasoning, complex_synthesis, final_manuscript_pass
 */
const AGENT_TASK_TYPE_MAP: Record<string, AITaskType> = {
  // DataPrep Agent tasks (Stages 1-5)
  data_validation: 'format_validate',
  variable_selection: 'classify',
  cohort_definition: 'extract_metadata',
  schema_validation: 'format_validate',

  // Analysis Agent tasks (Stages 6-9)
  statistical_analysis: 'complex_synthesis',
  assumption_checking: 'policy_check',
  result_interpretation: 'summarize',
  method_selection: 'classify',

  // Quality Agent tasks (Stages 10-12)
  figure_generation: 'draft_section',
  table_generation: 'draft_section',
  integrity_check: 'policy_check',
  sensitivity_analysis: 'complex_synthesis',
  bias_assessment: 'policy_check',

  // IRB Agent tasks (Stages 13-14)
  irb_protocol: 'protocol_reasoning',
  consent_form: 'template_fill',
  phi_detection: 'phi_scan',
  risk_assessment: 'protocol_reasoning',

  // Manuscript Agent tasks (Stages 15-20)
  introduction_drafting: 'draft_section',
  methods_drafting: 'draft_section',
  results_drafting: 'draft_section',
  discussion_drafting: 'draft_section',
  abstract_generation: 'abstract_generate',
  citation_formatting: 'extract_metadata',
  final_review: 'final_manuscript_pass',

  // Generic fallbacks
  agent_chat: 'summarize',
  quality_gate: 'policy_check',
};

/**
 * Schema for agent proxy request
 */
const AgentProxyRequestSchema = z.object({
  // Required fields
  prompt: z.string().min(1),
  taskType: z.string(),
  stageId: z.number().int().min(1).max(20),

  // Optional fields with defaults
  modelTier: z
    .enum(['ECONOMY', 'STANDARD', 'PREMIUM', 'NANO', 'MINI', 'FRONTIER'])
    .default('STANDARD'),
  governanceMode: z.enum(['DEMO', 'REVIEW', 'LIVE']).default('DEMO'),
  maxTokens: z.number().int().min(1).max(16000).optional(),
  temperature: z.number().min(0).max(2).optional(),
  systemPrompt: z.string().optional(),

  // Agent metadata for audit logging
  agentId: z.enum(['dataprep', 'analysis', 'quality', 'irb', 'manuscript']).optional(),
  runId: z.string().uuid().optional(),
  threadId: z.string().uuid().optional(),
  projectId: z.string().uuid().optional(),
  iteration: z.number().int().min(0).optional(),
});

// =================================================================================================
// Utility Functions
// =================================================================================================

/**
 * Convert Python model tier to TypeScript ModelTier
 */
function mapModelTier(tier: string): ModelTier {
  return MODEL_TIER_MAP[tier.toUpperCase()] || 'MINI';
}

/**
 * Convert agent task type to AI Router task type
 */
function mapTaskType(taskType: string): AITaskType {
  return AGENT_TASK_TYPE_MAP[taskType.toLowerCase()] || 'summarize';
}

/**
 * Build system prompt based on agent context
 */
function buildSystemPrompt(agentId?: string, stageId?: number, customPrompt?: string): string {
  const basePrompt = customPrompt || '';

  const agentPrompts: Record<string, string> = {
    dataprep: `You are a clinical data preparation specialist. Focus on data validation, variable selection, and cohort definition. Always cite specific data quality issues and propose concrete fixes.`,
    analysis: `You are a biostatistics expert. Focus on statistical method selection, assumption checking, and result interpretation. Always justify your statistical choices with references to methodology.`,
    quality: `You are a research quality assurance specialist. Focus on sensitivity analysis, bias assessment, and reproducibility. Apply STROBE/CONSORT guidelines where applicable.`,
    irb: `You are an IRB compliance specialist. Focus on protocol review, consent forms, and PHI protection. Always flag potential ethical concerns proactively.`,
    manuscript: `You are a scientific writing specialist. Focus on IMRaD structure, citation accuracy, and journal style guidelines. Maintain formal academic tone throughout.`,
  };

  const agentSpecificPrompt = agentId ? agentPrompts[agentId] || '' : '';
  const stageContext = stageId
    ? `\n\nYou are currently working on Stage ${stageId} of the research workflow.`
    : '';

  return [basePrompt, agentSpecificPrompt, stageContext].filter(Boolean).join('\n\n');
}

// =================================================================================================
// Routes
// =================================================================================================

/**
 * POST /api/ai/agent-proxy
 *
 * Main proxy endpoint for LangGraph agents to invoke the AI Router.
 * Handles all LLM calls from the Python worker, ensuring governance compliance.
 */
router.post(
  '/',
  requirePermission('ANALYZE'),
  asyncHandler(async (req: Request, res: Response) => {
    const user = (req as any).user;

    if (!user) {
      return res.status(401).json({
        error: 'AUTHENTICATION_REQUIRED',
        message: 'Authentication required for AI agent proxy',
      });
    }

    // Validate request
    const validation = AgentProxyRequestSchema.safeParse(req.body);
    if (!validation.success) {
      return res.status(400).json({
        error: 'VALIDATION_ERROR',
        message: 'Invalid request body',
        details: validation.error.flatten(),
      });
    }

    const {
      prompt,
      taskType,
      stageId,
      modelTier,
      governanceMode,
      maxTokens,
      temperature,
      systemPrompt,
      agentId,
      runId,
      threadId,
      projectId,
      iteration,
    } = validation.data;

    // Map Python types to TypeScript types
    const mappedTier = mapModelTier(modelTier);
    const mappedTaskType = mapTaskType(taskType);
    const effectiveSystemPrompt = buildSystemPrompt(agentId, stageId, systemPrompt);

    // Get model router instance
    const modelRouter = getModelRouter();

    // Invoke AI Router
    const startTime = Date.now();

    try {
      const response = await modelRouter.route({
        prompt,
        taskType: mappedTaskType,
        forceTier: mappedTier,
        maxTokens,
        temperature,
        systemPrompt: effectiveSystemPrompt,
        responseFormat: 'text',
        metadata: {
          stageId,
          sessionId: threadId,
          workflowStep: `agent:${agentId || 'unknown'}:iteration:${iteration || 0}`,
        },
      });

      // Check if PHI was detected in output
      const phiDetected = response.qualityGate.checks.some(
        (check: QualityCheck) => check.name === 'phi_output_scan' && !check.passed
      );

      const phiCategories = phiDetected
        ? response.qualityGate.checks
            .filter((c: QualityCheck) => c.name === 'phi_output_scan')
            .map((c: QualityCheck) => c.reason || 'Unknown PHI')
        : [];

      // Audit log the successful invocation
      await logAction({
        eventType: 'AI_AGENT_PROXY',
        action: 'INVOCATION_SUCCESS',
        userId: user.id,
        resourceType: 'ai_agent',
        resourceId: runId || `proxy_${Date.now()}`,
        details: {
          agentId,
          stageId,
          taskType,
          mappedTaskType,
          modelTier: mappedTier,
          model: response.routing.model,
          governanceMode,
          projectId,
          threadId,
          iteration,
          inputTokens: response.usage.inputTokens,
          outputTokens: response.usage.outputTokens,
          estimatedCostUsd: response.usage.estimatedCostUsd,
          latencyMs: response.metrics.latencyMs,
          qualityGatePassed: response.qualityGate.passed,
          escalated: response.routing.escalated,
          finalTier: response.routing.finalTier,
          phiDetected,
        },
      });

      // Set X-Ros-* cost headers for E2E test cost tracking
      attachCostEnvelope(res, {
        model: response.routing.model,
        tokensIn: response.usage.inputTokens,
        tokensOut: response.usage.outputTokens,
        latencyMs: response.metrics.latencyMs,
        costUsd: response.usage.estimatedCostUsd,
      });

      // Return response in format expected by Python AIRouterBridge
      return res.json({
        content: response.content,
        model: response.routing.model,
        tokenUsage: {
          input: response.usage.inputTokens,
          output: response.usage.outputTokens,
          total: response.usage.totalTokens,
        },
        phiDetected,
        phiCategories,
        latencyMs: response.metrics.latencyMs,
        cached: false,
        qualityGate: {
          passed: response.qualityGate.passed,
          checks: response.qualityGate.checks.map((c: QualityCheck) => ({
            name: c.name,
            passed: c.passed,
            reason: c.reason,
            severity: c.severity,
          })),
        },
        routing: {
          initialTier: response.routing.initialTier,
          finalTier: response.routing.finalTier,
          escalated: response.routing.escalated,
          escalationReason: response.routing.escalationReason,
        },
        estimatedCostUsd: response.usage.estimatedCostUsd,
      });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown AI Router error';

      await logAction({
        eventType: 'AI_AGENT_PROXY',
        action: 'INVOCATION_FAILED',
        userId: user.id,
        resourceType: 'ai_agent',
        resourceId: runId || `proxy_${Date.now()}`,
        details: {
          agentId,
          stageId,
          taskType,
          modelTier: mappedTier,
          governanceMode,
          error: errorMessage,
          latencyMs: Date.now() - startTime,
        },
      });

      return res.status(500).json({
        error: 'AI_INVOCATION_FAILED',
        message: errorMessage,
        content: '',
        tokenUsage: { input: 0, output: 0, total: 0 },
        phiDetected: false,
        latencyMs: Date.now() - startTime,
        cached: false,
      });
    }
  })
);

/**
 * GET /api/ai/agent-proxy/health
 *
 * Health check endpoint for the agent proxy.
 * Used by Python AIRouterBridge to verify connectivity.
 */
router.get(
  '/health',
  asyncHandler(async (_req: Request, res: Response) => {
    // Verify router is initialized
    const hasAnthropicKey = !!process.env.ANTHROPIC_API_KEY;
    const hasOpenAIKey = !!process.env.OPENAI_API_KEY;

    res.json({
      status: 'healthy',
      timestamp: new Date().toISOString(),
      providers: {
        anthropic: hasAnthropicKey,
        openai: hasOpenAIKey,
      },
      governanceMode: process.env.GOVERNANCE_MODE || 'DEMO',
      phiScanningEnabled: true,
    });
  })
);

/**
 * GET /api/ai/agent-proxy/task-types
 *
 * Returns the mapping of agent task types to AI Router task types.
 * Useful for debugging and documentation.
 */
router.get(
  '/task-types',
  asyncHandler(async (_req: Request, res: Response) => {
    res.json({
      taskTypeMapping: AGENT_TASK_TYPE_MAP,
      modelTierMapping: MODEL_TIER_MAP,
    });
  })
);

/**
 * POST /api/ai/agent-proxy/estimate
 *
 * Estimate cost for a potential agent invocation without making the actual call.
 */
router.post(
  '/estimate',
  requirePermission('ANALYZE'),
  asyncHandler(async (req: Request, res: Response) => {
    const { prompt, modelTier = 'STANDARD', maxOutputTokens = 2000 } = req.body;

    if (!prompt) {
      return res.status(400).json({
        error: 'VALIDATION_ERROR',
        message: 'Prompt is required for cost estimation',
      });
    }

    // Rough token estimate (4 chars ≈ 1 token)
    const estimatedInputTokens = Math.ceil(prompt.length / 4);
    const estimatedOutputTokens = maxOutputTokens;

    const mappedTier = mapModelTier(modelTier);
    const modelRouter = getModelRouter();
    const config = modelRouter.getModelConfig(mappedTier);

    const estimatedCostUsd =
      (estimatedInputTokens / 1_000_000) * config.costPerMToken.input +
      (estimatedOutputTokens / 1_000_000) * config.costPerMToken.output;

    res.json({
      tier: mappedTier,
      model: config.model,
      estimatedTokens: {
        input: estimatedInputTokens,
        output: estimatedOutputTokens,
        total: estimatedInputTokens + estimatedOutputTokens,
      },
      estimatedCostUsd,
      maxTokensAllowed: config.maxTokens,
    });
  })
);

// =========================================================================
// Agent Debugging Endpoints (Phase 5)
// =========================================================================

router.get('/agents/:agentName/status', asyncHandler(async (req: Request, res: Response) => {
  const { agentName } = req.params;
  const workerClient = getWorkerClient();
  const status = await workerClient.get(`/agents/${agentName}/status`);
  res.json(status.data);
}));

router.post('/agents/:agentName/debug', asyncHandler(async (req: Request, res: Response) => {
  const { agentName } = req.params;
  const { input, verbose = true } = req.body;
  const workerClient = getWorkerClient();

  const result = await workerClient.post(`/agents/${agentName}/debug`, {
    input,
    verbose,
    trace: true,
  });

  const typedData = result.data as { trace?: unknown; timing?: unknown } | undefined;
  res.json({
    agentName,
    result: result.data,
    trace: typedData?.trace,
    timing: typedData?.timing,
  });
}));

export default router;
