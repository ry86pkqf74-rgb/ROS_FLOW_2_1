/**
 * RAG E2E proxy routes: forward ingest / retrieve / verify to agent services.
 * Used by smoke-rag.sh and other E2E tests. No auth required (internal/dev).
 *
 * - POST /api/ros/rag/ingest   -> agent-rag-ingest /agents/run/sync
 * - POST /api/ros/rag/retrieve -> agent-rag-retrieve /agents/run/sync
 * - POST /api/ros/rag/verify   -> agent-verify /agents/run/sync
 */

import { Router, type Request, type Response } from 'express';
import { asyncHandler } from '../middleware/asyncHandler';

const router = Router();

const AGENT_ENDPOINTS_STATE: { endpoints: Record<string, string>; error?: string } = (() => {
  const envVar = process.env.AGENT_ENDPOINTS_JSON;
  if (!envVar) {
    return { endpoints: {}, error: 'AGENT_ENDPOINTS_JSON is not set' };
  }
  try {
    const parsed = JSON.parse(envVar);
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
      return { endpoints: {}, error: 'AGENT_ENDPOINTS_JSON must be a JSON object mapping agent names to URLs' };
    }
    return { endpoints: parsed as Record<string, string> };
  } catch {
    return { endpoints: {}, error: 'AGENT_ENDPOINTS_JSON is not valid JSON' };
  }
})();

function getAgentUrl(agentName: string): string | null {
  if (AGENT_ENDPOINTS_STATE.error) return null;
  const base = AGENT_ENDPOINTS_STATE.endpoints[agentName];
  if (!base || typeof base !== 'string') return null;
  return base.replace(/\/$/, '');
}

async function proxyToAgent(agentName: string, body: unknown, res: Response): Promise<void> {
  const baseUrl = getAgentUrl(agentName);
  if (!baseUrl) {
    res.status(503).json({
      error: 'AGENT_UNAVAILABLE',
      message: AGENT_ENDPOINTS_STATE.error || `Agent "${agentName}" not configured in AGENT_ENDPOINTS_JSON`,
      agent: agentName,
    });
    return;
  }
  const url = `${baseUrl}/agents/run/sync`;
  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const data = await response.json().catch(() => ({}));
    res.status(response.status).json(data);
  } catch (err) {
    res.status(503).json({
      error: 'PROXY_ERROR',
      message: err instanceof Error ? err.message : 'Failed to reach agent',
      agent: agentName,
    });
  }
}

/**
 * POST /api/ros/rag/ingest
 * Body: agent run request (request_id, task_type: "RAG_INGEST", inputs: { documents, knowledgeBase, ... }).
 */
router.post(
  '/ingest',
  asyncHandler(async (req: Request, res: Response) => {
    const body = req.body ?? {};
    const payload = {
      request_id: body.request_id ?? `smoke-ingest-${Date.now()}`,
      task_type: 'RAG_INGEST',
      inputs: body.inputs ?? body,
      mode: body.mode ?? 'DEMO',
    };
    await proxyToAgent('agent-rag-ingest', payload, res);
  })
);

/**
 * POST /api/ros/rag/retrieve
 * Body: agent run request (request_id, task_type: "RAG_RETRIEVE", inputs: { query, knowledgeBase, ... }).
 */
router.post(
  '/retrieve',
  asyncHandler(async (req: Request, res: Response) => {
    const body = req.body ?? {};
    const payload = {
      request_id: body.request_id ?? `smoke-retrieve-${Date.now()}`,
      task_type: 'RAG_RETRIEVE',
      inputs: body.inputs ?? body,
      mode: body.mode ?? 'DEMO',
    };
    await proxyToAgent('agent-rag-retrieve', payload, res);
  })
);

/**
 * POST /api/ros/rag/verify
 * Body: agent run request (request_id, task_type: "CLAIM_VERIFY", inputs: { claims, groundingPack, ... }).
 */
router.post(
  '/verify',
  asyncHandler(async (req: Request, res: Response) => {
    const body = req.body ?? {};
    const payload = {
      request_id: body.request_id ?? `smoke-verify-${Date.now()}`,
      task_type: 'CLAIM_VERIFY',
      inputs: body.inputs ?? body,
      mode: body.mode ?? 'DEMO',
    };
    await proxyToAgent('agent-verify', payload, res);
  })
);

export default router;
