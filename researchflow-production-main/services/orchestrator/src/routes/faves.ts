/**
 * FAVES Compliance API Routes
 *
 * Endpoints for Fair, Appropriate, Valid, Effective, Safe evaluation framework.
 * Implements deployment gates and compliance tracking per Phase 10.
 *
 * Priority: P0 - CRITICAL (Phase 10 FAVES Compliance)
 *
 * @module services/orchestrator/src/routes/faves
 * @version 1.0.0
 */

import { Router, Request, Response, NextFunction } from 'express';
import { requireRole } from '../middleware/rbac';
import { db } from '../../db.js';
import { desc, eq, and, sql, gte, lte } from 'drizzle-orm';
import { eventBus } from '../services/event-bus';
import { z } from 'zod';

// Async handler wrapper
function asyncHandler(fn: (req: Request, res: Response, next: NextFunction) => Promise<void>) {
  return (req: Request, res: Response, next: NextFunction) => {
    Promise.resolve(fn(req, res, next)).catch(next);
  };
}

const router = Router();

// ============================================================================
// FAVES Dimensions and Statuses
// ============================================================================

const FAVES_DIMENSIONS = ['FAIR', 'APPROPRIATE', 'VALID', 'EFFECTIVE', 'SAFE'] as const;
type FAVESDimension = typeof FAVES_DIMENSIONS[number];

const FAVES_STATUSES = ['PASS', 'FAIL', 'PARTIAL', 'NOT_EVALUATED'] as const;
type FAVESStatus = typeof FAVES_STATUSES[number];

// Default thresholds per the execution plan
const DEFAULT_THRESHOLDS = {
  FAIR: {
    demographic_parity_gap: 0.1,
    min_subgroup_auc: 0.7,
  },
  APPROPRIATE: {
    intended_use_coverage: 0.9,
    workflow_fit: 0.8,
  },
  VALID: {
    calibration_error: 0.1,
    brier_score: 0.25,
    external_validation_auc: 0.7,
  },
  EFFECTIVE: {
    net_benefit_positive: 0,
  },
  SAFE: {
    max_error_rate: 0.05,
    failure_mode_coverage: 0.9,
  },
};

// ============================================================================
// Validation Schemas
// ============================================================================

const FAVESEvaluationCreateSchema = z.object({
  model_id: z.string().uuid(),
  model_version: z.string(),
  evaluation_type: z.enum(['PRE_DEPLOYMENT', 'PERIODIC', 'TRIGGERED', 'MANUAL']),
  trigger_reason: z.string().optional(),
});

const DimensionResultSchema = z.object({
  dimension: z.enum(FAVES_DIMENSIONS),
  status: z.enum(FAVES_STATUSES),
  score: z.number().min(0).max(100),
  metrics: z.array(z.object({
    metric_name: z.string(),
    value: z.number(),
    threshold: z.number().optional(),
    passed: z.boolean(),
    unit: z.string().optional(),
  })),
  missing_requirements: z.array(z.string()).default([]),
  recommendations: z.array(z.string()).default([]),
});

const FAVESArtifactSchema = z.object({
  artifact_name: z.string(),
  artifact_path: z.string(),
  artifact_type: z.enum(['REPORT', 'DOCUMENTATION', 'DATA', 'CODE', 'CONFIGURATION']),
  faves_dimension: z.enum(FAVES_DIMENSIONS),
  is_required: z.boolean().default(true),
  file_hash: z.string().optional(),
  file_size_bytes: z.number().int().optional(),
});

// ============================================================================
// FAVES Evaluation Endpoints
// ============================================================================

/**
 * GET /api/faves/evaluations
 * List all FAVES evaluations
 */
router.get(
  '/evaluations',
  requireRole('VIEWER'),
  asyncHandler(async (req: Request, res: Response) => {
    const {
      model_id,
      evaluation_type,
      overall_status,
      deployment_allowed,
      limit = '50',
      offset = '0'
    } = req.query;

    const conditions: any[] = [];
    if (model_id) conditions.push(sql`fe.model_id = ${model_id}`);
    if (evaluation_type) conditions.push(sql`fe.evaluation_type = ${evaluation_type}`);
    if (overall_status) conditions.push(sql`fe.overall_status = ${overall_status}`);
    if (deployment_allowed === 'true') conditions.push(sql`fe.deployment_allowed = true`);
    if (deployment_allowed === 'false') conditions.push(sql`fe.deployment_allowed = false`);

    const whereClause = conditions.length > 0
      ? sql`WHERE ${sql.join(conditions, sql` AND `)}`
      : sql``;

    const evaluations = await db.execute(sql`
      SELECT
        fe.*,
        mr.name as model_name,
        mr.model_type
      FROM faves_evaluations fe
      LEFT JOIN model_registry mr ON fe.model_id = mr.id
      ${whereClause}
      ORDER BY fe.evaluated_at DESC
      LIMIT ${parseInt(limit as string)}
      OFFSET ${parseInt(offset as string)}
    `);

    const totalResult = await db.execute(sql`
      SELECT COUNT(*) as total FROM faves_evaluations fe ${whereClause}
    `);

    res.json({
      evaluations: evaluations.rows,
      pagination: {
        total: parseInt(totalResult.rows[0]?.total || '0'),
        limit: parseInt(limit as string),
        offset: parseInt(offset as string),
      },
    });
  })
);

/**
 * GET /api/faves/evaluations/:id
 * Get a specific FAVES evaluation with full details
 */
router.get(
  '/evaluations/:id',
  requireRole('VIEWER'),
  asyncHandler(async (req: Request, res: Response) => {
    const { id } = req.params;

    const evalResult = await db.execute(sql`
      SELECT
        fe.*,
        mr.name as model_name,
        mr.model_type,
        mr.framework
      FROM faves_evaluations fe
      LEFT JOIN model_registry mr ON fe.model_id = mr.id
      WHERE fe.id = ${id}
    `);

    if (evalResult.rows.length === 0) {
      res.status(404).json({ error: 'FAVES evaluation not found' });
      return;
    }

    const evaluation = evalResult.rows[0];

    // Get artifacts
    const artifactsResult = await db.execute(sql`
      SELECT * FROM faves_artifacts
      WHERE evaluation_id = ${id}
      ORDER BY faves_dimension, artifact_name
    `);

    res.json({
      evaluation,
      artifacts: artifactsResult.rows,
    });
  })
);

/**
 * POST /api/faves/evaluations
 * Create a new FAVES evaluation
 */
router.post(
  '/evaluations',
  requireRole(['RESEARCHER', 'STEWARD', 'ADMIN']),
  asyncHandler(async (req: Request, res: Response) => {
    const validated = FAVESEvaluationCreateSchema.parse(req.body);
    const userId = (req as any).user?.id || 'system';

    // Verify model exists
    const modelCheck = await db.execute(sql`
      SELECT id, current_version FROM model_registry WHERE id = ${validated.model_id}
    `);

    if (modelCheck.rows.length === 0) {
      res.status(400).json({ error: 'Model not found in registry' });
      return;
    }

    // Create evaluation record
    const result = await db.execute(sql`
      INSERT INTO faves_evaluations (
        model_id, model_version, evaluation_type, trigger_reason,
        overall_status, deployment_allowed, evaluated_by,
        fair_status, fair_score,
        appropriate_status, appropriate_score,
        valid_status, valid_score,
        effective_status, effective_score,
        safe_status, safe_score,
        blocking_issues
      ) VALUES (
        ${validated.model_id},
        ${validated.model_version},
        ${validated.evaluation_type},
        ${validated.trigger_reason || null},
        'NOT_EVALUATED',
        false,
        ${userId},
        'NOT_EVALUATED', 0,
        'NOT_EVALUATED', 0,
        'NOT_EVALUATED', 0,
        'NOT_EVALUATED', 0,
        'NOT_EVALUATED', 0,
        '[]'::jsonb
      )
      RETURNING *
    `);

    eventBus.emit('faves:evaluation_created', {
      evaluationId: result.rows[0].id,
      modelId: validated.model_id,
      evaluationType: validated.evaluation_type,
      createdBy: userId,
    });

    res.status(201).json(result.rows[0]);
  })
);

/**
 * POST /api/faves/evaluations/:id/dimensions
 * Submit results for FAVES dimensions
 */
router.post(
  '/evaluations/:id/dimensions',
  requireRole(['RESEARCHER', 'STEWARD', 'ADMIN']),
  asyncHandler(async (req: Request, res: Response) => {
    const { id } = req.params;
    const dimensions = z.array(DimensionResultSchema).parse(req.body);

    // Verify evaluation exists
    const evalCheck = await db.execute(sql`
      SELECT * FROM faves_evaluations WHERE id = ${id}
    `);

    if (evalCheck.rows.length === 0) {
      res.status(404).json({ error: 'FAVES evaluation not found' });
      return;
    }

    // Update each dimension
    const updates: any = {};
    const blockingIssues: string[] = [];

    for (const dim of dimensions) {
      const dimLower = dim.dimension.toLowerCase();
      updates[`${dimLower}_status`] = dim.status;
      updates[`${dimLower}_score`] = dim.score;
      updates[`${dimLower}_metrics`] = JSON.stringify(dim.metrics);

      if (dim.status === 'FAIL') {
        blockingIssues.push(`${dim.dimension}: ${dim.missing_requirements.join(', ') || 'Failed metrics'}`);
      }
    }

    // Calculate overall status
    const allPassed = dimensions.every(d => d.status === 'PASS');
    const anyFailed = dimensions.some(d => d.status === 'FAIL');
    const overallStatus = allPassed ? 'PASS' : anyFailed ? 'FAIL' : 'PARTIAL';
    const overallScore = Math.round(dimensions.reduce((sum, d) => sum + d.score, 0) / dimensions.length);
    const deploymentAllowed = allPassed;

    // Build dynamic update query
    const setClauses = Object.entries(updates).map(([key, value]) => {
      if (key.endsWith('_metrics')) {
        return `${key} = '${value}'::jsonb`;
      }
      return typeof value === 'string' ? `${key} = '${value}'` : `${key} = ${value}`;
    });

    setClauses.push(`overall_status = '${overallStatus}'`);
    setClauses.push(`overall_score = ${overallScore}`);
    setClauses.push(`deployment_allowed = ${deploymentAllowed}`);
    setClauses.push(`blocking_issues = '${JSON.stringify(blockingIssues)}'::jsonb`);
    setClauses.push(`evaluated_at = NOW()`);

    const result = await db.execute(sql`
      UPDATE faves_evaluations
      SET ${sql.raw(setClauses.join(', '))}
      WHERE id = ${id}
      RETURNING *
    `);

    // Emit appropriate event
    if (deploymentAllowed) {
      eventBus.emit('faves:evaluation_passed', {
        evaluationId: id,
        modelId: result.rows[0].model_id,
        overallScore,
      });
    } else {
      eventBus.emit('faves:evaluation_failed', {
        evaluationId: id,
        modelId: result.rows[0].model_id,
        blockingIssues,
      });
    }

    res.json(result.rows[0]);
  })
);

/**
 * POST /api/faves/evaluations/:id/artifacts
 * Add artifacts to a FAVES evaluation
 */
router.post(
  '/evaluations/:id/artifacts',
  requireRole(['RESEARCHER', 'STEWARD', 'ADMIN']),
  asyncHandler(async (req: Request, res: Response) => {
    const { id } = req.params;
    const artifacts = z.array(FAVESArtifactSchema).parse(req.body);

    // Verify evaluation exists
    const evalCheck = await db.execute(sql`
      SELECT id FROM faves_evaluations WHERE id = ${id}
    `);

    if (evalCheck.rows.length === 0) {
      res.status(404).json({ error: 'FAVES evaluation not found' });
      return;
    }

    const inserted = [];

    for (const artifact of artifacts) {
      const result = await db.execute(sql`
        INSERT INTO faves_artifacts (
          evaluation_id, artifact_name, artifact_path, artifact_type,
          faves_dimension, is_required, exists_flag, file_hash, file_size_bytes
        ) VALUES (
          ${id},
          ${artifact.artifact_name},
          ${artifact.artifact_path},
          ${artifact.artifact_type},
          ${artifact.faves_dimension},
          ${artifact.is_required},
          true,
          ${artifact.file_hash || null},
          ${artifact.file_size_bytes || null}
        )
        RETURNING *
      `);
      inserted.push(result.rows[0]);
    }

    res.status(201).json({ artifacts: inserted });
  })
);

// ============================================================================
// Deployment Gate Endpoints
// ============================================================================

/**
 * GET /api/faves/gate/:modelId
 * Check if a model passes the FAVES deployment gate
 */
router.get(
  '/gate/:modelId',
  requireRole('VIEWER'),
  asyncHandler(async (req: Request, res: Response) => {
    const { modelId } = req.params;
    const { version } = req.query;

    // Get latest evaluation for this model (optionally filtered by version)
    const versionFilter = version ? sql`AND model_version = ${version}` : sql``;

    const latestEval = await db.execute(sql`
      SELECT *
      FROM faves_evaluations
      WHERE model_id = ${modelId}
        ${versionFilter}
      ORDER BY evaluated_at DESC
      LIMIT 1
    `);

    if (latestEval.rows.length === 0) {
      res.json({
        model_id: modelId,
        gate_status: 'NO_EVALUATION',
        deployment_allowed: false,
        message: 'No FAVES evaluation found for this model',
        recommendation: 'Run FAVES evaluation before deployment',
      });
      return;
    }

    const evaluation = latestEval.rows[0];
    const daysSinceEval = Math.floor(
      (Date.now() - new Date(evaluation.evaluated_at).getTime()) / (1000 * 60 * 60 * 24)
    );

    // Check if evaluation is stale (>90 days)
    const isStale = daysSinceEval > 90;

    res.json({
      model_id: modelId,
      model_version: evaluation.model_version,
      evaluation_id: evaluation.id,
      gate_status: evaluation.deployment_allowed ? 'PASS' : 'FAIL',
      deployment_allowed: evaluation.deployment_allowed && !isStale,
      overall_status: evaluation.overall_status,
      overall_score: evaluation.overall_score,
      dimension_scores: {
        fair: evaluation.fair_score,
        appropriate: evaluation.appropriate_score,
        valid: evaluation.valid_score,
        effective: evaluation.effective_score,
        safe: evaluation.safe_score,
      },
      blocking_issues: evaluation.blocking_issues || [],
      evaluated_at: evaluation.evaluated_at,
      days_since_evaluation: daysSinceEval,
      is_stale: isStale,
      stale_warning: isStale ? 'Evaluation is older than 90 days. Re-evaluation recommended.' : null,
    });
  })
);

/**
 * POST /api/faves/gate/:modelId/override
 * Request deployment gate override (requires approval)
 */
router.post(
  '/gate/:modelId/override',
  requireRole(['STEWARD', 'ADMIN']),
  asyncHandler(async (req: Request, res: Response) => {
    const { modelId } = req.params;
    const { reason, risk_acknowledgment, approval_expires_at } = req.body;
    const userId = (req as any).user?.id || 'system';

    if (!reason || reason.length < 50) {
      res.status(400).json({ error: 'Override reason must be at least 50 characters' });
      return;
    }

    if (!risk_acknowledgment) {
      res.status(400).json({ error: 'Risk acknowledgment is required' });
      return;
    }

    // Log override request
    await db.execute(sql`
      INSERT INTO audit_events_v2 (
        event_type, severity, actor_type, actor_id,
        resource_type, resource_id, action, details, timestamp
      ) VALUES (
        'FAVES_OVERRIDE_REQUESTED',
        'HIGH',
        'USER',
        ${userId},
        'MODEL',
        ${modelId},
        'OVERRIDE_REQUEST',
        ${JSON.stringify({ reason, risk_acknowledgment, approval_expires_at })}::jsonb,
        NOW()
      )
    `);

    eventBus.emit('faves:override_requested', {
      modelId,
      requestedBy: userId,
      reason,
    });

    res.json({
      message: 'Override request submitted for approval',
      model_id: modelId,
      requested_by: userId,
      status: 'PENDING_APPROVAL',
      note: 'An administrator must approve this override request',
    });
  })
);

// ============================================================================
// Statistics and History
// ============================================================================

/**
 * GET /api/faves/stats
 * Get FAVES compliance statistics
 */
router.get(
  '/stats',
  requireRole(['STEWARD', 'ADMIN']),
  asyncHandler(async (req: Request, res: Response) => {
    const stats = await db.execute(sql`
      SELECT
        COUNT(*) as total_evaluations,
        COUNT(*) FILTER (WHERE deployment_allowed = true) as passed_count,
        COUNT(*) FILTER (WHERE deployment_allowed = false) as failed_count,
        COUNT(DISTINCT model_id) as models_evaluated,
        AVG(overall_score) as avg_overall_score,
        AVG(fair_score) as avg_fair_score,
        AVG(appropriate_score) as avg_appropriate_score,
        AVG(valid_score) as avg_valid_score,
        AVG(effective_score) as avg_effective_score,
        AVG(safe_score) as avg_safe_score,
        COUNT(*) FILTER (WHERE evaluation_type = 'PRE_DEPLOYMENT') as pre_deployment_count,
        COUNT(*) FILTER (WHERE evaluation_type = 'PERIODIC') as periodic_count,
        COUNT(*) FILTER (WHERE evaluation_type = 'TRIGGERED') as triggered_count
      FROM faves_evaluations
    `);

    // Get trend data (last 30 days)
    const trend = await db.execute(sql`
      SELECT
        DATE(evaluated_at) as date,
        COUNT(*) as evaluations,
        AVG(overall_score) as avg_score,
        COUNT(*) FILTER (WHERE deployment_allowed = true) as passed
      FROM faves_evaluations
      WHERE evaluated_at >= NOW() - INTERVAL '30 days'
      GROUP BY DATE(evaluated_at)
      ORDER BY date
    `);

    res.json({
      summary: stats.rows[0],
      trend: trend.rows,
      thresholds: DEFAULT_THRESHOLDS,
    });
  })
);

/**
 * GET /api/faves/models/:modelId/history
 * Get FAVES evaluation history for a model
 */
router.get(
  '/models/:modelId/history',
  requireRole('VIEWER'),
  asyncHandler(async (req: Request, res: Response) => {
    const { modelId } = req.params;
    const { limit = '20' } = req.query;

    const history = await db.execute(sql`
      SELECT
        id,
        model_version,
        evaluation_type,
        overall_status,
        overall_score,
        deployment_allowed,
        fair_score,
        appropriate_score,
        valid_score,
        effective_score,
        safe_score,
        evaluated_at,
        evaluated_by
      FROM faves_evaluations
      WHERE model_id = ${modelId}
      ORDER BY evaluated_at DESC
      LIMIT ${parseInt(limit as string)}
    `);

    res.json({ model_id: modelId, history: history.rows });
  })
);

export default router;
