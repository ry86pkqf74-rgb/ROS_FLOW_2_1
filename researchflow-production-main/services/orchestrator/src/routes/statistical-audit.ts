/**
 * Statistical Audit Trail API
 *
 * Routes:
 * - GET /api/audit/statistical/:analysisId
 * - GET /api/audit/statistical/:analysisId/diagram
 * - GET /api/audit/statistical/:analysisId/summary
 * - POST /api/audit/statistical/:analysisId/export
 * - GET /api/audit/statistical/:analysisId/methodology
 *
 * These endpoints proxy to the worker service, enriching requests with
 * authentication metadata and returning standardized error responses.
 */

import { Router, type Request, type Response } from 'express';
import { z } from 'zod';

import { config } from '../config/env';
import { asyncHandler } from '../middleware/asyncHandler';
import { requireAuth } from '../middleware/auth';

const router = Router();
const WORKER_URL = config.workerUrl;

// =============================================================================
// Validation Schemas
// =============================================================================

const analysisIdSchema = z.string().min(1, 'analysisId is required').max(200);

const summaryQuerySchema = z.object({
  detail: z.enum(['brief', 'detailed', 'technical']).optional(),
});

const exportBodySchema = z.object({
  format: z.enum(['json', 'jsonl', 'csv', 'markdown', 'text']).default('json'),
  includeSummary: z.boolean().optional(),
  includeMethodology: z.boolean().optional(),
  metadata: z.record(z.unknown()).optional(),
});

const methodologyQuerySchema = z.object({
  analysisType: z.string().optional(),
});

// =============================================================================
// Helper Functions
// =============================================================================

function buildWorkerUrl(path: string): string {
  return `${WORKER_URL}${path}`;
}

function buildRequestId(prefix: string): string {
  return `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
}

function buildAuditHeaders(req: Request, requestId: string): Record<string, string> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'X-Request-ID': requestId,
  };

  if (req.user?.id) {
    headers['X-User-ID'] = req.user.id;
  }

  return headers;
}

async function proxyWorker(
  req: Request,
  res: Response,
  workerPath: string,
  options: RequestInit
): Promise<void> {
  const workerUrl = buildWorkerUrl(workerPath);
  const workerResponse = await fetch(workerUrl, options);

  if (!workerResponse.ok) {
    const text = await workerResponse.text();
    res.status(workerResponse.status).json({
      error: 'WORKER_ERROR',
      message: workerResponse.statusText,
      details: text || undefined,
    });
    return;
  }

  const contentType = workerResponse.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    const data = await workerResponse.json();
    res.json(data);
    return;
  }

  const text = await workerResponse.text();
  res.type(contentType || 'text/plain').send(text);
}

// =============================================================================
// Routes
// =============================================================================

/**
 * GET /api/audit/statistical/:analysisId
 * Returns the full statistical decision trail.
 */
router.get(
  '/:analysisId',
  requireAuth,
  asyncHandler(async (req: Request, res: Response) => {
    const parseResult = analysisIdSchema.safeParse(req.params.analysisId);
    if (!parseResult.success) {
      return res.status(400).json({
        error: 'INVALID_PARAM',
        message: 'Invalid analysisId parameter',
        details: parseResult.error.issues,
      });
    }

    const analysisId = parseResult.data;
    const requestId = buildRequestId('stat_audit');

    return proxyWorker(req, res, `/api/audit/statistical/${analysisId}`, {
      method: 'GET',
      headers: buildAuditHeaders(req, requestId),
    });
  })
);

/**
 * GET /api/audit/statistical/:analysisId/diagram
 * Returns Mermaid decision tree diagram.
 */
router.get(
  '/:analysisId/diagram',
  requireAuth,
  asyncHandler(async (req: Request, res: Response) => {
    const parseResult = analysisIdSchema.safeParse(req.params.analysisId);
    if (!parseResult.success) {
      return res.status(400).json({
        error: 'INVALID_PARAM',
        message: 'Invalid analysisId parameter',
        details: parseResult.error.issues,
      });
    }

    const analysisId = parseResult.data;
    const requestId = buildRequestId('stat_diagram');

    return proxyWorker(req, res, `/api/audit/statistical/${analysisId}/diagram`, {
      method: 'GET',
      headers: buildAuditHeaders(req, requestId),
    });
  })
);

/**
 * GET /api/audit/statistical/:analysisId/summary
 * Query: detail=brief|detailed|technical
 */
router.get(
  '/:analysisId/summary',
  requireAuth,
  asyncHandler(async (req: Request, res: Response) => {
    const idParse = analysisIdSchema.safeParse(req.params.analysisId);
    if (!idParse.success) {
      return res.status(400).json({
        error: 'INVALID_PARAM',
        message: 'Invalid analysisId parameter',
        details: idParse.error.issues,
      });
    }

    const queryParse = summaryQuerySchema.safeParse(req.query);
    if (!queryParse.success) {
      return res.status(400).json({
        error: 'INVALID_QUERY',
        message: 'Invalid query parameters',
        details: queryParse.error.issues,
      });
    }

    const analysisId = idParse.data;
    const detail = queryParse.data.detail;
    const requestId = buildRequestId('stat_summary');
    const params = new URLSearchParams();
    if (detail) {
      params.set('detail', detail);
    }

    const path = params.toString()
      ? `/api/audit/statistical/${analysisId}/summary?${params.toString()}`
      : `/api/audit/statistical/${analysisId}/summary`;

    return proxyWorker(req, res, path, {
      method: 'GET',
      headers: buildAuditHeaders(req, requestId),
    });
  })
);

/**
 * POST /api/audit/statistical/:analysisId/export
 * Body: { format?: 'json'|'jsonl'|'csv'|'markdown'|'text', includeSummary?, includeMethodology?, metadata? }
 */
router.post(
  '/:analysisId/export',
  requireAuth,
  asyncHandler(async (req: Request, res: Response) => {
    const idParse = analysisIdSchema.safeParse(req.params.analysisId);
    if (!idParse.success) {
      return res.status(400).json({
        error: 'INVALID_PARAM',
        message: 'Invalid analysisId parameter',
        details: idParse.error.issues,
      });
    }

    const bodyParse = exportBodySchema.safeParse(req.body);
    if (!bodyParse.success) {
      return res.status(400).json({
        error: 'INVALID_BODY',
        message: 'Invalid request body',
        details: bodyParse.error.issues,
      });
    }

    const analysisId = idParse.data;
    const requestId = buildRequestId('stat_export');

    return proxyWorker(req, res, `/api/audit/statistical/${analysisId}/export`, {
      method: 'POST',
      headers: buildAuditHeaders(req, requestId),
      body: JSON.stringify(bodyParse.data),
    });
  })
);

/**
 * GET /api/audit/statistical/:analysisId/methodology
 * Query: analysisType? (optional override)
 */
router.get(
  '/:analysisId/methodology',
  requireAuth,
  asyncHandler(async (req: Request, res: Response) => {
    const idParse = analysisIdSchema.safeParse(req.params.analysisId);
    if (!idParse.success) {
      return res.status(400).json({
        error: 'INVALID_PARAM',
        message: 'Invalid analysisId parameter',
        details: idParse.error.issues,
      });
    }

    const queryParse = methodologyQuerySchema.safeParse(req.query);
    if (!queryParse.success) {
      return res.status(400).json({
        error: 'INVALID_QUERY',
        message: 'Invalid query parameters',
        details: queryParse.error.issues,
      });
    }

    const analysisId = idParse.data;
    const requestId = buildRequestId('stat_methodology');
    const params = new URLSearchParams();

    if (queryParse.data.analysisType) {
      params.set('analysisType', queryParse.data.analysisType);
    }

    const path = params.toString()
      ? `/api/audit/statistical/${analysisId}/methodology?${params.toString()}`
      : `/api/audit/statistical/${analysisId}/methodology`;

    return proxyWorker(req, res, path, {
      method: 'GET',
      headers: buildAuditHeaders(req, requestId),
    });
  })
);

export default router;
