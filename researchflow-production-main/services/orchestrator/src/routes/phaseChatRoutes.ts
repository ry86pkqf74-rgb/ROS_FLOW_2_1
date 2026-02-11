/**
 * Phase Chat Routes
 *
 * API endpoints for phase-specific chat with AI agents.
 * Maps workflow stages (1-20) to specialized agents with RAG + AI router.
 */

import { Router, Request, Response, NextFunction } from 'express';
import * as z from 'zod';

import {
  getAgentById,
  getAgentsForStage,
  listAgents,
  STAGE_DESCRIPTIONS,
  STAGE_TO_AGENTS,
} from '../services/phase-chat/registry';
import { phaseChatService } from '../services/phase-chat/service';
import { asString } from '../utils/asString';

const router = Router();

// Input validation schema
const PhaseChatInputSchema = z.object({
  query: z.string().min(1).max(10000),
  topic: z.string().optional(),
  context: z.record(z.unknown()).optional(),
  conversationId: z.string().optional(),
  userId: z.string().optional(),
  agentId: z.string().optional(),
});

/**
 * GET /api/phase/:stage/agents
 * List available agents for a workflow stage
 */
router.get('/:stage/agents', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const stage = parseInt(asString(req.params.stage), 10);

    if (isNaN(stage) || stage < 1 || stage > 20) {
      return res.status(400).json({
        error: 'Invalid stage',
        message: 'Stage must be a number between 1 and 20',
      });
    }

    const agents = getAgentsForStage(stage);

    res.json({
      stage,
      stageDescription: STAGE_DESCRIPTIONS[stage] || 'Unknown stage',
      agents: agents.map((a) => ({
        id: a.id,
        name: a.name,
        description: a.description,
        modelTier: a.modelTier,
      })),
    });
  } catch (error) {
    next(error);
  }
});

/**
 * POST /api/phase/:stage/chat
 * Phase-specific chat endpoint (auto-select primary agent for the stage)
 */
router.post('/:stage/chat', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const stage = parseInt(asString(req.params.stage), 10);
    const parseResult = PhaseChatInputSchema.safeParse(req.body);

    if (isNaN(stage) || stage < 1 || stage > 20) {
      return res.status(400).json({
        error: 'Invalid stage',
        message: 'Stage must be a number between 1 and 20',
      });
    }

    if (!parseResult.success) {
      return res.status(400).json({
        error: 'Validation error',
        details: parseResult.error.errors,
      });
    }

    const { query, topic, context, conversationId, userId } = parseResult.data;
    const agents = getAgentsForStage(stage);

    if (agents.length === 0) {
      return res.status(400).json({
        error: 'No agents available',
        message: `No agents configured for stage ${stage}`,
      });
    }

    // Select primary agent (first one)
    const primaryAgent = agents[0];

    const result = await phaseChatService.sendMessage({
      stage,
      query,
      topic,
      context,
      conversationId,
      userId,
      agentId: primaryAgent.id,
    });

    res.json({
      stage: result.stage,
      stageDescription: result.stageDescription,
      agentUsed: result.agent.id,
      topic: topic || 'general',
      conversationId: result.sessionId,
      response: {
        content: result.response.content,
        citations: result.ragContext.map((c) => c.id),
        metadata: {
          modelTier: result.response.routing.finalTier,
          phiScanRequired: result.agent.phiScanRequired,
          tokensUsed: result.response.usage.totalTokens,
          processingTimeMs: result.response.metrics.latencyMs,
          qualityGate: result.response.qualityGate,
          routing: result.response.routing,
          ragContext: result.ragContext,
        },
      },
      governance: result.governance,
    });
  } catch (error) {
    next(error);
  }
});

/**
 * POST /api/phase/:stage/chat/:agentId
 * Call a specific agent within a stage
 */
router.post('/:stage/chat/:agentId', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const stage = parseInt(asString(req.params.stage), 10);
    const agentId = asString(req.params.agentId);
    const parseResult = PhaseChatInputSchema.safeParse(req.body);

    if (isNaN(stage) || stage < 1 || stage > 20) {
      return res.status(400).json({ error: 'Invalid stage' });
    }

    const agentConfig = getAgentById(agentId);
    if (!agentConfig) {
      return res.status(404).json({
        error: 'Agent not found',
        message: `No agent with id "${agentId}"`,
        availableAgents: Object.keys(STAGE_TO_AGENTS).flatMap((s) => STAGE_TO_AGENTS[Number(s)]),
      });
    }

    if (!parseResult.success) {
      return res.status(400).json({
        error: 'Validation error',
        details: parseResult.error.errors,
      });
    }

    const { query, topic, context, conversationId, userId } = parseResult.data;

    const result = await phaseChatService.sendMessage({
      stage,
      query,
      topic,
      context,
      conversationId,
      userId,
      agentId: agentConfig.id,
    });

    res.json({
      stage: result.stage,
      stageDescription: result.stageDescription,
      agentUsed: result.agent.id,
      conversationId: result.sessionId,
      response: {
        content: result.response.content,
        citations: result.ragContext.map((c) => c.id),
        metadata: {
          modelTier: result.response.routing.finalTier,
          phiScanRequired: result.agent.phiScanRequired,
          tokensUsed: result.response.usage.totalTokens,
          processingTimeMs: result.response.metrics.latencyMs,
          qualityGate: result.response.qualityGate,
          routing: result.response.routing,
          ragContext: result.ragContext,
        },
      },
    });
  } catch (error) {
    next(error);
  }
});

/**
 * GET /api/phase/registry
 * Get full agent registry
 */
router.get('/registry', async (_req: Request, res: Response) => {
  res.json({
    agents: listAgents().map((a) => ({
      id: a.id,
      name: a.name,
      description: a.description,
      modelTier: a.modelTier,
    })),
    stageMappings: STAGE_TO_AGENTS,
    stageDescriptions: STAGE_DESCRIPTIONS,
  });
});

export default router;

