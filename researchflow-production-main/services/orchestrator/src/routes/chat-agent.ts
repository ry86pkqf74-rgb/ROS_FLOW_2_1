/**
 * Chat Agent Routes (Phase 5.5 Stream F - ROS-30)
 *
 * Provides REST and SSE endpoints for the frontend chat UI to interact with
 * LangGraph agents. Routes handle:
 * - Sending messages to agents
 * - Streaming responses via SSE
 * - Session management
 * - Improvement loop actions
 * - Human-in-the-loop approvals
 *
 * All agent execution happens in the Python worker. This route acts as the
 * HTTP bridge between frontend and worker.
 */

import type { Queue } from 'bullmq';
import { Router, type Request, type Response } from 'express';
import { z } from 'zod';

import { asyncHandler } from '../middleware/asyncHandler';
import { requirePermission } from '../middleware/rbac';
import { logAction } from '../services/audit-service';

const router = Router();

// =============================================================================
// Type Definitions
// =============================================================================

type AgentType = 'dataprep' | 'analysis' | 'quality' | 'irb' | 'manuscript';
type GovernanceMode = 'DEMO' | 'REVIEW' | 'LIVE';

interface ChatSession {
  sessionId: string;
  agentType: AgentType;
  artifactType: string;
  artifactId: string;
  projectId: string;
  userId: string;
  governanceMode: GovernanceMode;
  createdAt: string;
  updatedAt: string;
  messageCount: number;
  status: 'active' | 'complete' | 'error';
}

interface ChatMessage {
  id: string;
  sessionId: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  metadata?: {
    stage?: number;
    tokenUsage?: { input: number; output: number };
    qualityScore?: number;
    actionRequired?: boolean;
  };
}

// =============================================================================
// Request Schemas
// =============================================================================

const SendMessageSchema = z.object({
  message: z.string().min(1).max(10000),
  governanceMode: z.enum(['DEMO', 'REVIEW', 'LIVE']).default('DEMO'),
  metadata: z.record(z.any()).optional(),
});

const ApproveActionSchema = z.object({
  approved: z.boolean(),
  feedback: z.string().optional(),
});

const ImprovementRequestSchema = z.object({
  feedback: z.string().min(1).max(5000),
  targetSection: z.string().optional(),
});

const RevertRequestSchema = z.object({
  versionId: z.string().min(1),
});

// =============================================================================
// In-Memory State (Replace with Redis in production)
// =============================================================================

const chatSessions = new Map<string, ChatSession>();
const sessionMessages = new Map<string, ChatMessage[]>();
const sseClients = new Map<string, Response[]>();

// =============================================================================
// Helper Functions
// =============================================================================

function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
}

function getStageRange(agentType: AgentType): [number, number] {
  const ranges: Record<AgentType, [number, number]> = {
    dataprep: [1, 5],
    analysis: [6, 9],
    quality: [10, 12],
    irb: [13, 14],
    manuscript: [15, 20],
  };
  return ranges[agentType];
}

function broadcastToSession(sessionId: string, event: string, data: any): void {
  const clients = sseClients.get(sessionId) || [];
  const message = `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`;

  clients.forEach((res) => {
    try {
      res.write(message);
    } catch (e) {
      // Client disconnected
    }
  });
}

// =============================================================================
// Routes
// =============================================================================

/**
 * POST /api/chat/:agentType/:artifactType/:artifactId/message
 *
 * Send a message to a chat agent and start processing.
 * Returns immediately with a job ID for tracking.
 */
router.post(
  '/:agentType/:artifactType/:artifactId/message',
  requirePermission('ANALYZE'),
  asyncHandler(async (req: Request, res: Response) => {
    const user = (req as any).user;
    const { agentType, artifactType, artifactId } = req.params;

    // Validate agent type
    const validAgents: AgentType[] = ['dataprep', 'analysis', 'quality', 'irb', 'manuscript'];
    if (!validAgents.includes(agentType as AgentType)) {
      return res.status(400).json({
        error: 'INVALID_AGENT_TYPE',
        message: `Agent type must be one of: ${validAgents.join(', ')}`,
      });
    }

    // Validate request body
    const validation = SendMessageSchema.safeParse(req.body);
    if (!validation.success) {
      return res.status(400).json({
        error: 'VALIDATION_ERROR',
        message: 'Invalid request body',
        details: validation.error.flatten(),
      });
    }

    const { message, governanceMode, metadata } = validation.data;

    // Get or create session
    const sessionKey = `${agentType}:${artifactType}:${artifactId}`;
    let session = chatSessions.get(sessionKey);

    if (!session) {
      session = {
        sessionId: generateId(),
        agentType: agentType as AgentType,
        artifactType,
        artifactId,
        projectId: metadata?.projectId || artifactId,
        userId: user.id,
        governanceMode,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        messageCount: 0,
        status: 'active',
      };
      chatSessions.set(sessionKey, session);
      sessionMessages.set(session.sessionId, []);
    }

    // Create user message
    const userMessage: ChatMessage = {
      id: generateId(),
      sessionId: session.sessionId,
      role: 'user',
      content: message,
      timestamp: new Date().toISOString(),
      metadata: metadata as ChatMessage['metadata'],
    };

    // Store message
    const messages = sessionMessages.get(session.sessionId) || [];
    messages.push(userMessage);
    sessionMessages.set(session.sessionId, messages);
    session.messageCount++;
    session.updatedAt = new Date().toISOString();

    // Create job for worker
    const jobId = generateId();
    const stageRange = getStageRange(agentType as AgentType);

    const jobPayload = {
      jobId,
      sessionId: session.sessionId,
      agentType,
      artifactType,
      artifactId,
      projectId: session.projectId,
      userId: user.id,
      message,
      governanceMode,
      stageRange,
      messageHistory: messages.map((m) => ({
        role: m.role,
        content: m.content,
      })),
      metadata,
    };

    // In production, enqueue to BullMQ
    // await chatQueue.add('process-message', jobPayload);

    // Audit log
    await logAction({
      eventType: 'CHAT_MESSAGE',
      action: 'MESSAGE_SENT',
      userId: user.id,
      resourceType: 'chat_session',
      resourceId: session.sessionId,
      details: {
        agentType,
        artifactId,
        messageLength: message.length,
        governanceMode,
      },
    });

    // Broadcast to SSE clients
    broadcastToSession(session.sessionId, 'message', userMessage);
    broadcastToSession(session.sessionId, 'processing', {
      jobId,
      status: 'queued',
    });

    res.json({
      sessionId: session.sessionId,
      messageId: userMessage.id,
      jobId,
      status: 'processing',
    });
  })
);

/**
 * GET /api/chat/:agentType/:artifactType/:artifactId/sessions
 *
 * Get chat sessions for an artifact.
 */
router.get(
  '/:agentType/:artifactType/:artifactId/sessions',
  requirePermission('READ'),
  asyncHandler(async (req: Request, res: Response) => {
    const { agentType, artifactType, artifactId } = req.params;
    const sessionKey = `${agentType}:${artifactType}:${artifactId}`;
    const session = chatSessions.get(sessionKey);

    if (!session) {
      return res.json({ sessions: [] });
    }

    res.json({
      sessions: [
        {
          ...session,
          messages: sessionMessages.get(session.sessionId)?.length || 0,
        },
      ],
    });
  })
);

/**
 * GET /api/chat/sessions/:sessionId/messages
 *
 * Get messages for a chat session.
 */
router.get(
  '/sessions/:sessionId/messages',
  requirePermission('READ'),
  asyncHandler(async (req: Request, res: Response) => {
    const { sessionId } = req.params;
    const { limit = '50', offset = '0' } = req.query;

    const messages = sessionMessages.get(sessionId) || [];
    const limitNum = parseInt(limit as string, 10);
    const offsetNum = parseInt(offset as string, 10);

    const paginatedMessages = messages.slice(offsetNum, offsetNum + limitNum);

    res.json({
      messages: paginatedMessages,
      total: messages.length,
      limit: limitNum,
      offset: offsetNum,
    });
  })
);

/**
 * POST /api/chat/actions/:actionId/approve
 *
 * Approve or reject a pending human-in-the-loop action.
 */
router.post(
  '/actions/:actionId/approve',
  requirePermission('APPROVE'),
  asyncHandler(async (req: Request, res: Response) => {
    const user = (req as any).user;
    const { actionId } = req.params;

    const validation = ApproveActionSchema.safeParse(req.body);
    if (!validation.success) {
      return res.status(400).json({
        error: 'VALIDATION_ERROR',
        message: 'Invalid request body',
        details: validation.error.flatten(),
      });
    }

    const { approved, feedback } = validation.data;

    // In production, signal the worker to continue
    // await actionQueue.add('action-response', { actionId, approved, feedback });

    await logAction({
      eventType: 'CHAT_ACTION',
      action: approved ? 'ACTION_APPROVED' : 'ACTION_REJECTED',
      userId: user.id,
      resourceType: 'chat_action',
      resourceId: actionId,
      details: { feedback },
    });

    res.json({
      actionId,
      status: approved ? 'approved' : 'rejected',
      timestamp: new Date().toISOString(),
    });
  })
);

/**
 * GET /api/chat/stream/:sessionId
 *
 * SSE endpoint for streaming chat updates.
 */
router.get(
  '/stream/:sessionId',
  requirePermission('READ'),
  asyncHandler(async (req: Request, res: Response) => {
    const { sessionId } = req.params;

    // Set up SSE headers
    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');
    res.setHeader('X-Accel-Buffering', 'no');

    // Send initial connection event
    res.write(`event: connected\ndata: ${JSON.stringify({ sessionId })}\n\n`);

    // Register client
    const clients = sseClients.get(sessionId) || [];
    clients.push(res);
    sseClients.set(sessionId, clients);

    // Keep connection alive
    const keepAlive = setInterval(() => {
      res.write(': keepalive\n\n');
    }, 30000);

    // Clean up on close
    req.on('close', () => {
      clearInterval(keepAlive);
      const remaining = (sseClients.get(sessionId) || []).filter((r) => r !== res);
      if (remaining.length > 0) {
        sseClients.set(sessionId, remaining);
      } else {
        sseClients.delete(sessionId);
      }
    });
  })
);

/**
 * POST /api/chat/runs/:runId/improve
 *
 * Request improvement on an agent run output.
 */
router.post(
  '/runs/:runId/improve',
  requirePermission('ANALYZE'),
  asyncHandler(async (req: Request, res: Response) => {
    const user = (req as any).user;
    const { runId } = req.params;

    const validation = ImprovementRequestSchema.safeParse(req.body);
    if (!validation.success) {
      return res.status(400).json({
        error: 'VALIDATION_ERROR',
        message: 'Invalid request body',
        details: validation.error.flatten(),
      });
    }

    const { feedback, targetSection } = validation.data;
    const jobId = generateId();

    // In production, enqueue improvement job
    // await improvementQueue.add('improve', { runId, feedback, targetSection, userId: user.id });

    await logAction({
      eventType: 'CHAT_IMPROVEMENT',
      action: 'IMPROVEMENT_REQUESTED',
      userId: user.id,
      resourceType: 'agent_run',
      resourceId: runId,
      details: {
        feedbackLength: feedback.length,
        targetSection,
      },
    });

    res.json({
      jobId,
      runId,
      status: 'improvement_queued',
      timestamp: new Date().toISOString(),
    });
  })
);

/**
 * POST /api/chat/runs/:runId/revert
 *
 * Revert an agent run to a previous version.
 */
router.post(
  '/runs/:runId/revert',
  requirePermission('ANALYZE'),
  asyncHandler(async (req: Request, res: Response) => {
    const user = (req as any).user;
    const { runId } = req.params;

    const validation = RevertRequestSchema.safeParse(req.body);
    if (!validation.success) {
      return res.status(400).json({
        error: 'VALIDATION_ERROR',
        message: 'Invalid request body',
        details: validation.error.flatten(),
      });
    }

    const { versionId } = validation.data;

    // In production, call improvement service
    // await improvementService.revertTo(runId, versionId);

    await logAction({
      eventType: 'CHAT_REVERT',
      action: 'VERSION_REVERTED',
      userId: user.id,
      resourceType: 'agent_run',
      resourceId: runId,
      details: { versionId },
    });

    res.json({
      runId,
      versionId,
      status: 'reverted',
      timestamp: new Date().toISOString(),
    });
  })
);

/**
 * GET /api/chat/runs/:runId/versions
 *
 * Get version history for an agent run.
 */
router.get(
  '/runs/:runId/versions',
  requirePermission('READ'),
  asyncHandler(async (req: Request, res: Response) => {
    const { runId } = req.params;
    const { limit = '10' } = req.query;

    // In production, call improvement service
    // const versions = await improvementService.getVersionHistory(runId, parseInt(limit));

    // Placeholder response
    res.json({
      runId,
      versions: [],
      total: 0,
    });
  })
);

/**
 * GET /api/chat/runs/:runId/diff
 *
 * Get diff between two versions.
 */
router.get(
  '/runs/:runId/diff',
  requirePermission('READ'),
  asyncHandler(async (req: Request, res: Response) => {
    const { runId } = req.params;
    const { from, to } = req.query;

    if (!from || !to) {
      return res.status(400).json({
        error: 'MISSING_PARAMS',
        message: 'Both "from" and "to" version IDs are required',
      });
    }

    // In production, call improvement service
    // const diff = await improvementService.getDiff(runId, from, to);

    res.json({
      runId,
      from,
      to,
      diff: '',
    });
  })
);

/**
 * GET /api/chat/health
 *
 * Health check for chat service.
 */
router.get(
  '/health',
  asyncHandler(async (_req: Request, res: Response) => {
    res.json({
      status: 'healthy',
      timestamp: new Date().toISOString(),
      activeSessions: chatSessions.size,
      sseConnections: Array.from(sseClients.values()).reduce((sum, clients) => sum + clients.length, 0),
    });
  })
);

export default router;
