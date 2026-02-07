/**
 * Model Monitoring API Routes
 *
 * Endpoints for post-deployment monitoring, drift detection, and safety events.
 * Implements Phase 14 requirements for production model oversight.
 *
 * Priority: P0 - CRITICAL (Phase 14 Post-Deployment Monitoring)
 *
 * @module services/orchestrator/src/routes/monitoring
 * @version 1.0.0
 */

import { desc, eq, and, sql, gte, lte } from 'drizzle-orm';
import { Router, Request, Response, NextFunction } from 'express';
import { z } from 'zod';

import { db } from '../../db.js';
import { requireRole } from '../middleware/rbac';
import { eventBus } from '../services/event-bus';


// Async handler wrapper
function asyncHandler(fn: (req: Request, res: Response, next: NextFunction) => Promise<void>) {
  return (req: Request, res: Response, next: NextFunction) => {
    Promise.resolve(fn(req, res, next)).catch(next);
  };
}

const router = Router();

// ============================================================================
// Constants and Thresholds
// ============================================================================

const DRIFT_SEVERITY_LEVELS = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'] as const;
type DriftSeverity = typeof DRIFT_SEVERITY_LEVELS[number];

const SAFETY_SEVERITY_LEVELS = ['INFO', 'WARNING', 'ERROR', 'CRITICAL'] as const;
type SafetySeverity = typeof SAFETY_SEVERITY_LEVELS[number];

const DEFAULT_DRIFT_THRESHOLDS = {
  psi_low: 0.1,
  psi_medium: 0.2,
  psi_high: 0.25,
  kl_divergence_threshold: 0.1,
  performance_degradation_threshold: 0.05,
};

// ============================================================================
// Validation Schemas
// ============================================================================

const DriftMetricSchema = z.object({
  model_id: z.string().uuid(),
  model_version: z.string(),
  metric_type: z.enum(['INPUT_DRIFT', 'OUTPUT_DRIFT', 'PERFORMANCE_DRIFT', 'CONCEPT_DRIFT']),
  feature_name: z.string().optional(),
  psi_value: z.number().optional(),
  kl_divergence: z.number().optional(),
  js_divergence: z.number().optional(),
  reference_mean: z.number().optional(),
  current_mean: z.number().optional(),
  reference_std: z.number().optional(),
  current_std: z.number().optional(),
  sample_size_reference: z.number().int().optional(),
  sample_size_current: z.number().int().optional(),
  severity: z.enum(DRIFT_SEVERITY_LEVELS).optional(),
  details: z.record(z.any()).optional(),
});

const BiasMetricSchema = z.object({
  model_id: z.string().uuid(),
  model_version: z.string(),
  protected_attribute: z.string(),
  metric_name: z.string(),
  baseline_value: z.number(),
  current_value: z.number(),
  threshold: z.number(),
  violated: z.boolean(),
  subgroup_values: z.record(z.number()).optional(),
});

const SafetyEventSchema = z.object({
  model_id: z.string().uuid(),
  model_version: z.string(),
  event_type: z.string(),
  severity: z.enum(SAFETY_SEVERITY_LEVELS),
  description: z.string(),
  affected_predictions: z.number().int().optional(),
  root_cause: z.string().optional(),
  remediation_status: z.enum(['OPEN', 'INVESTIGATING', 'MITIGATED', 'RESOLVED']).default('OPEN'),
  details: z.record(z.any()).optional(),
});

// ============================================================================
// Drift Monitoring Endpoints
// ============================================================================

/**
 * POST /api/monitoring/drift
 * Record drift metrics for a model
 */
router.post(
  '/drift',
  requireRole(['RESEARCHER', 'STEWARD', 'ADMIN']),
  asyncHandler(async (req: Request, res: Response) => {
    const validated = DriftMetricSchema.parse(req.body);

    // Calculate severity if not provided
    let severity = validated.severity;
    if (!severity && validated.psi_value !== undefined) {
      if (validated.psi_value >= DEFAULT_DRIFT_THRESHOLDS.psi_high) {
        severity = 'CRITICAL';
      } else if (validated.psi_value >= DEFAULT_DRIFT_THRESHOLDS.psi_medium) {
        severity = 'HIGH';
      } else if (validated.psi_value >= DEFAULT_DRIFT_THRESHOLDS.psi_low) {
        severity = 'MEDIUM';
      } else {
        severity = 'LOW';
      }
    }

    const result = await db.execute(sql`
      INSERT INTO drift_metrics (
        model_id, model_version, metric_type, feature_name,
        psi_value, kl_divergence, js_divergence,
        reference_mean, current_mean, reference_std, current_std,
        sample_size_reference, sample_size_current,
        severity, details
      ) VALUES (
        ${validated.model_id},
        ${validated.model_version},
        ${validated.metric_type},
        ${validated.feature_name || null},
        ${validated.psi_value || null},
        ${validated.kl_divergence || null},
        ${validated.js_divergence || null},
        ${validated.reference_mean || null},
        ${validated.current_mean || null},
        ${validated.reference_std || null},
        ${validated.current_std || null},
        ${validated.sample_size_reference || null},
        ${validated.sample_size_current || null},
        ${severity || 'LOW'},
        ${JSON.stringify(validated.details || {})}::jsonb
      )
      RETURNING *
    `);

    // Emit alert if severity is HIGH or CRITICAL
    if (severity === 'HIGH' || severity === 'CRITICAL') {
      eventBus.emit('monitoring:drift_alert', {
        modelId: validated.model_id,
        metricType: validated.metric_type,
        severity,
        psiValue: validated.psi_value,
        featureName: validated.feature_name,
      });
    }

    res.status(201).json(result.rows[0]);
  })
);

/**
 * GET /api/monitoring/drift/:modelId
 * Get drift metrics for a model
 */
router.get(
  '/drift/:modelId',
  requireRole(['VIEWER', 'RESEARCHER', 'STEWARD', 'ADMIN']),
  asyncHandler(async (req: Request, res: Response) => {
    const { modelId } = req.params;
    const {
      metric_type,
      severity,
      since,
      until,
      limit = '100'
    } = req.query;

    const conditions: any[] = [sql`model_id = ${modelId}`];
    if (metric_type) conditions.push(sql`metric_type = ${metric_type}`);
    if (severity) conditions.push(sql`severity = ${severity}`);
    if (since) conditions.push(sql`measured_at >= ${since}::timestamp`);
    if (until) conditions.push(sql`measured_at <= ${until}::timestamp`);

    const metrics = await db.execute(sql`
      SELECT * FROM drift_metrics
      WHERE ${sql.join(conditions, sql` AND `)}
      ORDER BY measured_at DESC
      LIMIT ${parseInt(limit as string)}
    `);

    // Get summary statistics
    const summary = await db.execute(sql`
      SELECT
        metric_type,
        COUNT(*) as count,
        AVG(psi_value) as avg_psi,
        MAX(psi_value) as max_psi,
        COUNT(*) FILTER (WHERE severity IN ('HIGH', 'CRITICAL')) as alert_count
      FROM drift_metrics
      WHERE model_id = ${modelId}
        AND measured_at >= NOW() - INTERVAL '7 days'
      GROUP BY metric_type
    `);

    res.json({
      model_id: modelId,
      metrics: metrics.rows,
      summary: summary.rows,
      thresholds: DEFAULT_DRIFT_THRESHOLDS,
    });
  })
);

/**
 * GET /api/monitoring/drift/:modelId/trend
 * Get drift trend over time
 */
router.get(
  '/drift/:modelId/trend',
  requireRole(['VIEWER', 'RESEARCHER', 'STEWARD', 'ADMIN']),
  asyncHandler(async (req: Request, res: Response) => {
    const { modelId } = req.params;
    const { days = '30', metric_type } = req.query;

    const metricFilter = metric_type
      ? sql`AND metric_type = ${metric_type}`
      : sql``;

    const trend = await db.execute(sql`
      SELECT
        DATE(measured_at) as date,
        metric_type,
        AVG(psi_value) as avg_psi,
        MAX(psi_value) as max_psi,
        COUNT(*) as measurement_count,
        COUNT(*) FILTER (WHERE severity IN ('HIGH', 'CRITICAL')) as alerts
      FROM drift_metrics
      WHERE model_id = ${modelId}
        AND measured_at >= NOW() - INTERVAL '${sql.raw(days as string)} days'
        ${metricFilter}
      GROUP BY DATE(measured_at), metric_type
      ORDER BY date, metric_type
    `);

    res.json({
      model_id: modelId,
      period_days: parseInt(days as string),
      trend: trend.rows,
    });
  })
);

// ============================================================================
// Bias Monitoring Endpoints
// ============================================================================

/**
 * POST /api/monitoring/bias
 * Record bias metrics for a model
 */
router.post(
  '/bias',
  requireRole(['RESEARCHER', 'STEWARD', 'ADMIN']),
  asyncHandler(async (req: Request, res: Response) => {
    const validated = BiasMetricSchema.parse(req.body);

    const result = await db.execute(sql`
      INSERT INTO bias_metrics (
        model_id, model_version, protected_attribute, metric_name,
        baseline_value, current_value, threshold, violated, subgroup_values
      ) VALUES (
        ${validated.model_id},
        ${validated.model_version},
        ${validated.protected_attribute},
        ${validated.metric_name},
        ${validated.baseline_value},
        ${validated.current_value},
        ${validated.threshold},
        ${validated.violated},
        ${JSON.stringify(validated.subgroup_values || {})}::jsonb
      )
      RETURNING *
    `);

    // Emit alert if bias threshold violated
    if (validated.violated) {
      eventBus.emit('monitoring:bias_alert', {
        modelId: validated.model_id,
        protectedAttribute: validated.protected_attribute,
        metricName: validated.metric_name,
        currentValue: validated.current_value,
        threshold: validated.threshold,
      });
    }

    res.status(201).json(result.rows[0]);
  })
);

/**
 * GET /api/monitoring/bias/:modelId
 * Get bias metrics for a model
 */
router.get(
  '/bias/:modelId',
  requireRole(['VIEWER', 'RESEARCHER', 'STEWARD', 'ADMIN']),
  asyncHandler(async (req: Request, res: Response) => {
    const { modelId } = req.params;
    const { protected_attribute, violated_only, limit = '100' } = req.query;

    const conditions: any[] = [sql`model_id = ${modelId}`];
    if (protected_attribute) conditions.push(sql`protected_attribute = ${protected_attribute}`);
    if (violated_only === 'true') conditions.push(sql`violated = true`);

    const metrics = await db.execute(sql`
      SELECT * FROM bias_metrics
      WHERE ${sql.join(conditions, sql` AND `)}
      ORDER BY measured_at DESC
      LIMIT ${parseInt(limit as string)}
    `);

    // Get violation summary
    const summary = await db.execute(sql`
      SELECT
        protected_attribute,
        metric_name,
        COUNT(*) as total_measurements,
        COUNT(*) FILTER (WHERE violated = true) as violations,
        AVG(current_value) as avg_value,
        MAX(current_value) as max_value
      FROM bias_metrics
      WHERE model_id = ${modelId}
        AND measured_at >= NOW() - INTERVAL '30 days'
      GROUP BY protected_attribute, metric_name
    `);

    res.json({
      model_id: modelId,
      metrics: metrics.rows,
      summary: summary.rows,
    });
  })
);

// ============================================================================
// Safety Events Endpoints
// ============================================================================

/**
 * POST /api/monitoring/safety-events
 * Record a safety event
 */
router.post(
  '/safety-events',
  requireRole(['RESEARCHER', 'STEWARD', 'ADMIN']),
  asyncHandler(async (req: Request, res: Response) => {
    const validated = SafetyEventSchema.parse(req.body);
    const userId = (req as any).user?.id || 'system';

    const result = await db.execute(sql`
      INSERT INTO safety_events (
        model_id, model_version, event_type, severity, description,
        affected_predictions, root_cause, remediation_status, details, reported_by
      ) VALUES (
        ${validated.model_id},
        ${validated.model_version},
        ${validated.event_type},
        ${validated.severity},
        ${validated.description},
        ${validated.affected_predictions || null},
        ${validated.root_cause || null},
        ${validated.remediation_status},
        ${JSON.stringify(validated.details || {})}::jsonb,
        ${userId}
      )
      RETURNING *
    `);

    // Emit safety event
    eventBus.emit('monitoring:safety_event', {
      eventId: result.rows[0].id,
      modelId: validated.model_id,
      eventType: validated.event_type,
      severity: validated.severity,
      description: validated.description,
    });

    // Auto-trigger FAVES re-evaluation for CRITICAL events
    if (validated.severity === 'CRITICAL') {
      eventBus.emit('faves:trigger_evaluation', {
        modelId: validated.model_id,
        trigger: 'SAFETY_EVENT',
        eventId: result.rows[0].id,
      });
    }

    res.status(201).json(result.rows[0]);
  })
);

/**
 * GET /api/monitoring/safety-events
 * List safety events with filtering
 */
router.get(
  '/safety-events',
  requireRole(['VIEWER', 'RESEARCHER', 'STEWARD', 'ADMIN']),
  asyncHandler(async (req: Request, res: Response) => {
    const {
      model_id,
      severity,
      remediation_status,
      since,
      limit = '50',
      offset = '0'
    } = req.query;

    const conditions: any[] = [];
    if (model_id) conditions.push(sql`model_id = ${model_id}`);
    if (severity) conditions.push(sql`severity = ${severity}`);
    if (remediation_status) conditions.push(sql`remediation_status = ${remediation_status}`);
    if (since) conditions.push(sql`occurred_at >= ${since}::timestamp`);

    const whereClause = conditions.length > 0
      ? sql`WHERE ${sql.join(conditions, sql` AND `)}`
      : sql``;

    const events = await db.execute(sql`
      SELECT
        se.*,
        mr.name as model_name
      FROM safety_events se
      LEFT JOIN model_registry mr ON se.model_id = mr.id
      ${whereClause}
      ORDER BY se.occurred_at DESC
      LIMIT ${parseInt(limit as string)}
      OFFSET ${parseInt(offset as string)}
    `);

    const totalResult = await db.execute(sql`
      SELECT COUNT(*) as total FROM safety_events se ${whereClause}
    `);

    res.json({
      events: events.rows,
      pagination: {
        total: parseInt(totalResult.rows[0]?.total || '0'),
        limit: parseInt(limit as string),
        offset: parseInt(offset as string),
      },
    });
  })
);

/**
 * PATCH /api/monitoring/safety-events/:id
 * Update safety event remediation status
 */
router.patch(
  '/safety-events/:id',
  requireRole(['STEWARD', 'ADMIN']),
  asyncHandler(async (req: Request, res: Response) => {
    const { id } = req.params;
    const { remediation_status, root_cause, resolution_notes } = req.body;
    const userId = (req as any).user?.id || 'system';

    const updates: string[] = [];
    if (remediation_status) updates.push(`remediation_status = '${remediation_status}'`);
    if (root_cause) updates.push(`root_cause = '${root_cause}'`);
    if (resolution_notes) updates.push(`resolution_notes = '${resolution_notes}'`);
    if (remediation_status === 'RESOLVED') updates.push(`resolved_at = NOW()`);

    if (updates.length === 0) {
      res.status(400).json({ error: 'No valid fields to update' });
      return;
    }

    const result = await db.execute(sql`
      UPDATE safety_events
      SET ${sql.raw(updates.join(', '))}
      WHERE id = ${id}
      RETURNING *
    `);

    if (result.rows.length === 0) {
      res.status(404).json({ error: 'Safety event not found' });
      return;
    }

    eventBus.emit('monitoring:safety_event_updated', {
      eventId: id,
      newStatus: remediation_status,
      updatedBy: userId,
    });

    res.json(result.rows[0]);
  })
);

// ============================================================================
// Dashboard and Summary Endpoints
// ============================================================================

/**
 * GET /api/monitoring/dashboard
 * Get monitoring dashboard overview
 */
router.get(
  '/dashboard',
  requireRole(['VIEWER', 'RESEARCHER', 'STEWARD', 'ADMIN']),
  asyncHandler(async (req: Request, res: Response) => {
    const { model_id } = req.query;

    const modelFilter = model_id ? sql`WHERE model_id = ${model_id}` : sql``;

    // Get drift summary
    const driftSummary = await db.execute(sql`
      SELECT
        COUNT(*) as total_metrics,
        COUNT(*) FILTER (WHERE severity = 'LOW') as low_count,
        COUNT(*) FILTER (WHERE severity = 'MEDIUM') as medium_count,
        COUNT(*) FILTER (WHERE severity = 'HIGH') as high_count,
        COUNT(*) FILTER (WHERE severity = 'CRITICAL') as critical_count,
        AVG(psi_value) FILTER (WHERE metric_type = 'INPUT_DRIFT') as avg_input_psi,
        AVG(psi_value) FILTER (WHERE metric_type = 'OUTPUT_DRIFT') as avg_output_psi
      FROM drift_metrics
      ${modelFilter}
      ${model_id ? sql`` : sql`WHERE`} measured_at >= NOW() - INTERVAL '24 hours'
    `);

    // Get bias summary
    const biasSummary = await db.execute(sql`
      SELECT
        COUNT(DISTINCT protected_attribute) as attributes_monitored,
        COUNT(*) as total_measurements,
        COUNT(*) FILTER (WHERE violated = true) as violations
      FROM bias_metrics
      ${modelFilter}
      ${model_id ? sql`` : sql`WHERE`} measured_at >= NOW() - INTERVAL '24 hours'
    `);

    // Get safety events summary
    const safetySummary = await db.execute(sql`
      SELECT
        COUNT(*) as total_events,
        COUNT(*) FILTER (WHERE severity = 'CRITICAL') as critical_events,
        COUNT(*) FILTER (WHERE severity = 'ERROR') as error_events,
        COUNT(*) FILTER (WHERE remediation_status = 'OPEN') as open_events,
        COUNT(*) FILTER (WHERE remediation_status = 'INVESTIGATING') as investigating_events
      FROM safety_events
      ${modelFilter}
      ${model_id ? sql`` : sql`WHERE`} occurred_at >= NOW() - INTERVAL '7 days'
    `);

    // Get models with active alerts
    const activeAlerts = await db.execute(sql`
      SELECT DISTINCT
        dm.model_id,
        mr.name as model_name,
        MAX(dm.severity) as max_severity,
        COUNT(*) as alert_count
      FROM drift_metrics dm
      LEFT JOIN model_registry mr ON dm.model_id = mr.id
      WHERE dm.severity IN ('HIGH', 'CRITICAL')
        AND dm.measured_at >= NOW() - INTERVAL '24 hours'
      GROUP BY dm.model_id, mr.name
      ORDER BY max_severity DESC, alert_count DESC
      LIMIT 10
    `);

    res.json({
      period: '24h',
      drift: driftSummary.rows[0],
      bias: biasSummary.rows[0],
      safety: safetySummary.rows[0],
      active_alerts: activeAlerts.rows,
      thresholds: DEFAULT_DRIFT_THRESHOLDS,
    });
  })
);

/**
 * GET /api/monitoring/models/:modelId/health
 * Get comprehensive health status for a model
 */
router.get(
  '/models/:modelId/health',
  requireRole(['VIEWER', 'RESEARCHER', 'STEWARD', 'ADMIN']),
  asyncHandler(async (req: Request, res: Response) => {
    const { modelId } = req.params;

    // Get latest drift metrics
    const latestDrift = await db.execute(sql`
      SELECT metric_type, severity, psi_value, measured_at
      FROM drift_metrics
      WHERE model_id = ${modelId}
        AND measured_at >= NOW() - INTERVAL '24 hours'
      ORDER BY measured_at DESC
      LIMIT 10
    `);

    // Get recent bias violations
    const biasViolations = await db.execute(sql`
      SELECT protected_attribute, metric_name, current_value, threshold
      FROM bias_metrics
      WHERE model_id = ${modelId}
        AND violated = true
        AND measured_at >= NOW() - INTERVAL '7 days'
      ORDER BY measured_at DESC
      LIMIT 5
    `);

    // Get open safety events
    const openSafetyEvents = await db.execute(sql`
      SELECT id, event_type, severity, description, occurred_at
      FROM safety_events
      WHERE model_id = ${modelId}
        AND remediation_status IN ('OPEN', 'INVESTIGATING')
      ORDER BY severity DESC, occurred_at DESC
    `);

    // Get latest FAVES evaluation
    const latestFaves = await db.execute(sql`
      SELECT
        id, overall_status, overall_score, deployment_allowed,
        fair_score, appropriate_score, valid_score, effective_score, safe_score,
        evaluated_at
      FROM faves_evaluations
      WHERE model_id = ${modelId}
      ORDER BY evaluated_at DESC
      LIMIT 1
    `);

    // Calculate health score
    const hasCriticalDrift = latestDrift.rows.some((d: any) => d.severity === 'CRITICAL');
    const hasHighDrift = latestDrift.rows.some((d: any) => d.severity === 'HIGH');
    const hasBiasViolations = biasViolations.rows.length > 0;
    const hasCriticalSafetyEvents = openSafetyEvents.rows.some((e: any) => e.severity === 'CRITICAL');
    const favesOk = latestFaves.rows[0]?.deployment_allowed ?? false;

    let healthStatus = 'HEALTHY';
    let healthScore = 100;

    if (hasCriticalDrift || hasCriticalSafetyEvents) {
      healthStatus = 'CRITICAL';
      healthScore = 20;
    } else if (hasHighDrift || hasBiasViolations) {
      healthStatus = 'DEGRADED';
      healthScore = 60;
    } else if (!favesOk) {
      healthStatus = 'WARNING';
      healthScore = 75;
    }

    res.json({
      model_id: modelId,
      health_status: healthStatus,
      health_score: healthScore,
      drift: {
        latest: latestDrift.rows,
        has_critical: hasCriticalDrift,
        has_high: hasHighDrift,
      },
      bias: {
        recent_violations: biasViolations.rows,
        has_violations: hasBiasViolations,
      },
      safety: {
        open_events: openSafetyEvents.rows,
        has_critical: hasCriticalSafetyEvents,
      },
      faves: latestFaves.rows[0] || null,
      checked_at: new Date().toISOString(),
    });
  })
);

export default router;
