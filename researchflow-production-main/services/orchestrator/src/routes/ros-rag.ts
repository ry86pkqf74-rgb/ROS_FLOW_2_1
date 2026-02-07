/**
 * RAG E2E proxy routes: forward ingest / retrieve / verify to agent services.
 * Used by smoke-rag.sh and other E2E tests. No auth required (internal/dev).
 *
 * - POST /api/ros/rag/ingest   -> agent-rag-ingest /agents/run/sync
 * - POST /api/ros/rag/retrieve -> agent-rag-retrieve /agents/run/sync
 * - POST /api/ros/rag/verify   -> agent-verify /agents/run/sync
 * - POST /api/ros/rag/demo     -> ingest -> retrieve -> verify (combined response + timings)
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

type AgentCallResult = {
  ok: boolean;
  status: number;
  ms: number;
  data: unknown;
  error?: { code: string; message: string };
};

async function callAgent(agentName: string, payload: unknown): Promise<AgentCallResult> {
  const startedAt = Date.now();
  const baseUrl = getAgentUrl(agentName);
  if (!baseUrl) {
    return {
      ok: false,
      status: 503,
      ms: Date.now() - startedAt,
      data: null,
      error: {
        code: 'AGENT_UNAVAILABLE',
        message: AGENT_ENDPOINTS_STATE.error || `Agent "${agentName}" not configured in AGENT_ENDPOINTS_JSON`,
      },
    };
  }

  const url = `${baseUrl}/agents/run/sync`;
  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await response.json().catch(() => ({}));
    return {
      ok: response.ok,
      status: response.status,
      ms: Date.now() - startedAt,
      data,
    };
  } catch (err) {
    return {
      ok: false,
      status: 503,
      ms: Date.now() - startedAt,
      data: null,
      error: {
        code: 'PROXY_ERROR',
        message: err instanceof Error ? err.message : 'Failed to reach agent',
      },
    };
  }
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

/**
 * POST /api/ros/rag/demo
 * Body: { documents, query, claims, knowledgeBase?, topK?, request_id?, mode?, governanceMode? }
 *
 * Runs ingest -> retrieve -> verify, returns combined response with timings.
 */
router.post(
  '/demo',
  asyncHandler(async (req: Request, res: Response) => {
    const startedAt = Date.now();
    const body = req.body ?? {};

    const requestId: string = body.request_id ?? body.requestId ?? `rag-demo-${Date.now()}`;
    const mode: string = body.mode ?? 'DEMO';
    const governanceMode: string = body.governanceMode ?? 'DEMO';

    const documents = body.documents ?? body.docs ?? body.inputs?.documents;
    const query = body.query ?? body.inputs?.query;
    const claims = body.claims ?? body.inputs?.claims;
    const topKRaw = body.topK ?? body.inputs?.topK;
    const topK =
      typeof topKRaw === 'number'
        ? topKRaw
        : typeof topKRaw === 'string'
          ? Number(topKRaw)
          : 3;
    const knowledgeBase: string =
      body.knowledgeBase ?? body.inputs?.knowledgeBase ?? `rag-demo-${Date.now()}-${Math.random().toString(16).slice(2)}`;

    if (!Array.isArray(documents) || documents.length === 0) {
      res.status(400).json({ error: 'INVALID_REQUEST', message: 'documents must be a non-empty array' });
      return;
    }
    if (typeof query !== 'string' || query.trim().length === 0) {
      res.status(400).json({ error: 'INVALID_REQUEST', message: 'query must be a non-empty string' });
      return;
    }
    if (!Array.isArray(claims) || claims.length === 0) {
      res.status(400).json({ error: 'INVALID_REQUEST', message: 'claims must be a non-empty array of strings' });
      return;
    }
    if (!Number.isFinite(topK) || topK < 1) {
      res.status(400).json({ error: 'INVALID_REQUEST', message: 'topK must be a positive number' });
      return;
    }

    const ingestPayload = {
      request_id: `${requestId}-ingest`,
      task_type: 'RAG_INGEST',
      inputs: {
        knowledgeBase,
        documents,
      },
      mode,
    };
    const ingest = await callAgent('agent-rag-ingest', ingestPayload);
    if (!ingest.ok) {
      res.status(ingest.status).json({
        status: 'error',
        step: 'ingest',
        request_id: requestId,
        knowledgeBase,
        timings: { total_ms: Date.now() - startedAt, ingest_ms: ingest.ms },
        ingest,
      });
      return;
    }

    const retrievePayload = {
      request_id: `${requestId}-retrieve`,
      task_type: 'RAG_RETRIEVE',
      inputs: {
        knowledgeBase,
        query,
        topK,
      },
      mode,
    };
    const retrieve = await callAgent('agent-rag-retrieve', retrievePayload);
    if (!retrieve.ok) {
      res.status(retrieve.status).json({
        status: 'error',
        step: 'retrieve',
        request_id: requestId,
        knowledgeBase,
        timings: { total_ms: Date.now() - startedAt, ingest_ms: ingest.ms, retrieve_ms: retrieve.ms },
        ingest,
        retrieve,
      });
      return;
    }

    const retrieveData: any = retrieve.data ?? {};
    const groundingPack =
      retrieveData.outputs?.groundingPack ??
      retrieveData.outputs?.grounding_pack ??
      retrieveData.outputs?.grounding ??
      retrieveData.grounding ??
      null;

    const verifyPayload = {
      request_id: `${requestId}-verify`,
      task_type: 'CLAIM_VERIFY',
      inputs: {
        claims,
        groundingPack,
        governanceMode,
      },
      mode,
    };
    const verify = await callAgent('agent-verify', verifyPayload);
    if (!verify.ok) {
      res.status(verify.status).json({
        status: 'error',
        step: 'verify',
        request_id: requestId,
        knowledgeBase,
        timings: {
          total_ms: Date.now() - startedAt,
          ingest_ms: ingest.ms,
          retrieve_ms: retrieve.ms,
          verify_ms: verify.ms,
        },
        ingest,
        retrieve,
        verify,
      });
      return;
    }

    res.status(200).json({
      status: 'ok',
      request_id: requestId,
      knowledgeBase,
      timings: {
        total_ms: Date.now() - startedAt,
        ingest_ms: ingest.ms,
        retrieve_ms: retrieve.ms,
        verify_ms: verify.ms,
      },
      ingest,
      retrieve,
      verify,
    });
  })
);

export default router;
