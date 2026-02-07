/**
 * Statistical Recommendations Routes
 *
 * Proxies to the worker's statistical knowledge graph API:
 * - GET /api/analysis/recommendations - Method recommendations by study/outcome type
 * - POST /api/analysis/explain-method - Natural-language explanation for a method
 * - GET /api/analysis/assumption-tests/:method - Assumption tests for a method
 */

import { Router, Request, Response } from 'express';
import * as z from 'zod';

import { config } from '../config/env';
import { asyncHandler } from '../middleware/asyncHandler';
import { requirePermission } from '../middleware/rbac';

const router = Router();
const WORKER_URL = config.workerUrl;

// ===== VALIDATION SCHEMAS =====

const recommendationsQuerySchema = z.object({
  studyType: z.string().min(1, 'studyType is required'),
  outcomeType: z.string().min(1, 'outcomeType is required'),
  sampleSize: z
    .string()
    .optional()
    .transform((s) => (s != null && s !== '' ? parseInt(s, 10) : undefined)),
  hasConfounders: z
    .enum(['true', 'false', '1', '0'])
    .optional()
    .transform((s) => s === 'true' || s === '1'),
  isClustered: z
    .enum(['true', 'false', '1', '0'])
    .optional()
    .transform((s) => s === 'true' || s === '1'),
});

const explainMethodBodySchema = z.object({
  method: z.string().min(1, 'method is required'),
  context: z.record(z.unknown()).optional(),
});

// ===== ROUTES =====

/**
 * GET /api/analysis/recommendations
 * Query: studyType, outcomeType, sampleSize?, hasConfounders?, isClustered?
 */
router.get(
  '/recommendations',
  requirePermission('ANALYZE'),
  asyncHandler(async (req: Request, res: Response) => {
    const parseResult = recommendationsQuerySchema.safeParse(req.query);
    if (!parseResult.success) {
      return res.status(400).json({
        error: 'INVALID_QUERY',
        message: 'Invalid query parameters',
        details: parseResult.error.issues,
      });
    }

    const { studyType, outcomeType, sampleSize, hasConfounders, isClustered } = parseResult.data;
    const params = new URLSearchParams({
      studyType,
      outcomeType,
    });
    if (sampleSize != null && !Number.isNaN(sampleSize)) {
      params.set('sampleSize', String(sampleSize));
    }
    if (hasConfounders === true) {
      params.set('hasConfounders', 'true');
    }
    if (isClustered === true) {
      params.set('isClustered', 'true');
    }

    const workerResponse = await fetch(
      `${WORKER_URL}/api/analysis/recommendations?${params.toString()}`
    );

    if (!workerResponse.ok) {
      const text = await workerResponse.text();
      return res.status(workerResponse.status).json({
        error: 'WORKER_ERROR',
        message: workerResponse.statusText,
        details: text || undefined,
      });
    }

    const data = await workerResponse.json();
    res.json(data);
  })
);

/**
 * POST /api/analysis/explain-method
 * Body: { method: string, context?: object }
 */
router.post(
  '/explain-method',
  requirePermission('ANALYZE'),
  asyncHandler(async (req: Request, res: Response) => {
    const parseResult = explainMethodBodySchema.safeParse(req.body);
    if (!parseResult.success) {
      return res.status(400).json({
        error: 'INVALID_BODY',
        message: 'Invalid request body',
        details: parseResult.error.issues,
      });
    }

    const { method, context } = parseResult.data;

    const workerResponse = await fetch(`${WORKER_URL}/api/analysis/explain-method`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ method, context }),
    });

    if (!workerResponse.ok) {
      const text = await workerResponse.text();
      return res.status(workerResponse.status).json({
        error: 'WORKER_ERROR',
        message: workerResponse.statusText,
        details: text || undefined,
      });
    }

    const data = await workerResponse.json();
    res.json(data);
  })
);

/**
 * GET /api/analysis/assumption-tests/:method
 */
router.get(
  '/assumption-tests/:method',
  requirePermission('ANALYZE'),
  asyncHandler(async (req: Request, res: Response) => {
    const method = req.params.method;
    if (!method || !method.trim()) {
      return res.status(400).json({
        error: 'INVALID_PARAM',
        message: 'Method parameter is required',
      });
    }

    const encodedMethod = encodeURIComponent(method);
    const workerResponse = await fetch(
      `${WORKER_URL}/api/analysis/assumption-tests/${encodedMethod}`
    );

    if (!workerResponse.ok) {
      const text = await workerResponse.text();
      return res.status(workerResponse.status).json({
        error: 'WORKER_ERROR',
        message: workerResponse.statusText,
        details: text || undefined,
      });
    }

    const data = await workerResponse.json();
    res.json(data);
  })
);

export default router;
