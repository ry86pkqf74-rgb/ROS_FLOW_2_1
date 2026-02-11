/**
 * Transparency API Routes
 *
 * Endpoints for Evidence Bundle management and transparency artifact operations.
 * Part of HTI-1 compliance and TRIPOD+AI/CONSORT-AI reporting requirements.
 *
 * Priority: P0 - CRITICAL (Phase 8 Transparency Build)
 *
 * @module services/orchestrator/src/routes/transparency
 * @version 1.0.0
 */

import { desc, eq, and, sql, gte, lte } from 'drizzle-orm';
import { Router, Request, Response, NextFunction } from 'express';
import * as z from 'zod';

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
// Validation Schemas
// ============================================================================

const EvidenceBundleCreateSchema = z.object({
  model_id: z.string().uuid(),
  model_version: z.string(),
  bundle_type: z.enum(['TRIPOD_AI', 'CONSORT_AI', 'HTI_1', 'FAVES', 'CUSTOM']),
  title: z.string().min(1).max(500),
  description: z.string().optional(),
});

const EvidenceBundleUpdateSchema = z.object({
  status: z.enum(['DRAFT', 'REVIEW', 'APPROVED', 'PUBLISHED', 'ARCHIVED']).optional(),
  title: z.string().min(1).max(500).optional(),
  description: z.string().optional(),
  approved_by: z.string().optional(),
  published_at: z.string().datetime().optional(),
});

const PerformanceMetricSchema = z.object({
  metric_name: z.string(),
  metric_type: z.enum(['DISCRIMINATION', 'CALIBRATION', 'FAIRNESS', 'UTILITY', 'SAFETY']),
  value: z.number(),
  confidence_lower: z.number().optional(),
  confidence_upper: z.number().optional(),
  threshold: z.number().optional(),
  passed: z.boolean().optional(),
  unit: z.string().optional(),
  methodology: z.string().optional(),
});

const StratifiedMetricSchema = z.object({
  metric_id: z.string().uuid(),
  stratum_variable: z.string(),
  stratum_value: z.string(),
  sample_size: z.number().int().nonnegative(),
  metric_value: z.number(),
  confidence_lower: z.number().optional(),
  confidence_upper: z.number().optional(),
});

// ============================================================================
// Evidence Bundle Endpoints
// ============================================================================

/**
 * GET /api/transparency/bundles
 * List all evidence bundles with optional filtering
 */
router.get(
  '/bundles',
  requireRole(['VIEWER', 'RESEARCHER', 'STEWARD', 'ADMIN']),
  asyncHandler(async (req: Request, res: Response) => {
    const { model_id, bundle_type, status, limit = '50', offset = '0' } = req.query;

    // Build query conditions
    const conditions: any[] = [];
    if (model_id) conditions.push(sql`model_id = ${model_id}`);
    if (bundle_type) conditions.push(sql`bundle_type = ${bundle_type}`);
    if (status) conditions.push(sql`status = ${status}`);

    const whereClause = conditions.length > 0
      ? sql`WHERE ${sql.join(conditions, sql` AND `)}`
      : sql``;

    const bundles = await db.execute(sql`
      SELECT
        eb.*,
        mr.name as model_name,
        mr.model_type,
        (SELECT COUNT(*) FROM performance_metrics pm WHERE pm.bundle_id = eb.id) as metric_count
      FROM evidence_bundles eb
      LEFT JOIN model_registry mr ON eb.model_id = mr.id
      ${whereClause}
      ORDER BY eb.created_at DESC
      LIMIT ${parseInt(limit as string)}
      OFFSET ${parseInt(offset as string)}
    `);

    const totalResult = await db.execute(sql`
      SELECT COUNT(*) as total FROM evidence_bundles eb ${whereClause}
    `);

    res.json({
      bundles: bundles.rows,
      pagination: {
        total: parseInt(totalResult.rows[0]?.total || '0'),
        limit: parseInt(limit as string),
        offset: parseInt(offset as string),
      },
    });
  })
);

/**
 * GET /api/transparency/bundles/:id
 * Get a specific evidence bundle with all related data
 */
router.get(
  '/bundles/:id',
  requireRole(['VIEWER', 'RESEARCHER', 'STEWARD', 'ADMIN']),
  asyncHandler(async (req: Request, res: Response) => {
    const { id } = req.params;

    const bundleResult = await db.execute(sql`
      SELECT
        eb.*,
        mr.name as model_name,
        mr.model_type,
        mr.framework,
        mr.intended_use_summary
      FROM evidence_bundles eb
      LEFT JOIN model_registry mr ON eb.model_id = mr.id
      WHERE eb.id = ${id}
    `);

    if (bundleResult.rows.length === 0) {
      res.status(404).json({ error: 'Evidence bundle not found' });
      return;
    }

    const bundle = bundleResult.rows[0];

    // Get performance metrics
    const metricsResult = await db.execute(sql`
      SELECT * FROM performance_metrics
      WHERE bundle_id = ${id}
      ORDER BY metric_type, metric_name
    `);

    // Get stratified metrics
    const stratifiedResult = await db.execute(sql`
      SELECT sm.*, pm.metric_name, pm.metric_type
      FROM stratified_metrics sm
      JOIN performance_metrics pm ON sm.metric_id = pm.id
      WHERE pm.bundle_id = ${id}
      ORDER BY pm.metric_name, sm.stratum_variable, sm.stratum_value
    `);

    res.json({
      bundle,
      metrics: metricsResult.rows,
      stratified_metrics: stratifiedResult.rows,
    });
  })
);

/**
 * POST /api/transparency/bundles
 * Create a new evidence bundle
 */
router.post(
  '/bundles',
  requireRole(['RESEARCHER', 'STEWARD', 'ADMIN']),
  asyncHandler(async (req: Request, res: Response) => {
    const validated = EvidenceBundleCreateSchema.parse(req.body);
    const userId = (req as any).user?.id || 'system';

    // Verify model exists
    const modelCheck = await db.execute(sql`
      SELECT id FROM model_registry WHERE id = ${validated.model_id}
    `);

    if (modelCheck.rows.length === 0) {
      res.status(400).json({ error: 'Model not found in registry' });
      return;
    }

    const result = await db.execute(sql`
      INSERT INTO evidence_bundles (
        model_id, model_version, bundle_type, status, title, description, created_by
      ) VALUES (
        ${validated.model_id},
        ${validated.model_version},
        ${validated.bundle_type},
        'DRAFT',
        ${validated.title},
        ${validated.description || null},
        ${userId}
      )
      RETURNING *
    `);

    // Emit event
    eventBus.publish({
      type: 'transparency:bundle_created',
      topic: 'governance',
      ts: new Date().toISOString(),
      payload: {
        bundleId: result.rows[0].id,
        modelId: validated.model_id,
        bundleType: validated.bundle_type,
        createdBy: userId,
      },
    });

    res.status(201).json(result.rows[0]);
  })
);

/**
 * PATCH /api/transparency/bundles/:id
 * Update an evidence bundle
 */
router.patch(
  '/bundles/:id',
  requireRole(['RESEARCHER', 'STEWARD', 'ADMIN']),
  asyncHandler(async (req: Request, res: Response) => {
    const { id } = req.params;
    const validated = EvidenceBundleUpdateSchema.parse(req.body);
    const userId = (req as any).user?.id || 'system';

    // Check bundle exists and get current status
    const existingBundle = await db.execute(sql`
      SELECT * FROM evidence_bundles WHERE id = ${id}
    `);

    if (existingBundle.rows.length === 0) {
      res.status(404).json({ error: 'Evidence bundle not found' });
      return;
    }

    const current = existingBundle.rows[0];

    // Build update fields
    const updates: string[] = [];
    const values: any[] = [];

    if (validated.status) {
      updates.push('status = $' + (values.length + 1));
      values.push(validated.status);
    }
    if (validated.title) {
      updates.push('title = $' + (values.length + 1));
      values.push(validated.title);
    }
    if (validated.description !== undefined) {
      updates.push('description = $' + (values.length + 1));
      values.push(validated.description);
    }
    if (validated.approved_by) {
      updates.push('approved_by = $' + (values.length + 1));
      values.push(validated.approved_by);
      updates.push('approved_at = NOW()');
    }
    if (validated.published_at) {
      updates.push('published_at = $' + (values.length + 1));
      values.push(validated.published_at);
    }

    if (updates.length === 0) {
      res.status(400).json({ error: 'No valid fields to update' });
      return;
    }

    const result = await db.execute(sql`
      UPDATE evidence_bundles
      SET ${sql.raw(updates.join(', '))}, updated_at = NOW()
      WHERE id = ${id}
      RETURNING *
    `);

    // Emit status change event if applicable
    if (validated.status && validated.status !== current.status) {
      eventBus.publish({
        type: 'transparency:bundle_status_changed',
        topic: 'governance',
        ts: new Date().toISOString(),
        payload: {
          bundleId: id,
          previousStatus: current.status,
          newStatus: validated.status,
          changedBy: userId,
        },
      });
    }

    res.json(result.rows[0]);
  })
);

/**
 * DELETE /api/transparency/bundles/:id
 * Archive an evidence bundle (soft delete)
 */
router.delete(
  '/bundles/:id',
  requireRole(['STEWARD', 'ADMIN']),
  asyncHandler(async (req: Request, res: Response) => {
    const { id } = req.params;
    const userId = (req as any).user?.id || 'system';

    const result = await db.execute(sql`
      UPDATE evidence_bundles
      SET status = 'ARCHIVED', updated_at = NOW()
      WHERE id = ${id}
      RETURNING *
    `);

    if (result.rows.length === 0) {
      res.status(404).json({ error: 'Evidence bundle not found' });
      return;
    }

    eventBus.publish({
      type: 'transparency:bundle_archived',
      topic: 'governance',
      ts: new Date().toISOString(),
      payload: {
        bundleId: id,
        archivedBy: userId,
      },
    });

    res.json({ message: 'Evidence bundle archived', bundle: result.rows[0] });
  })
);

// ============================================================================
// Performance Metrics Endpoints
// ============================================================================

/**
 * POST /api/transparency/bundles/:id/metrics
 * Add performance metrics to a bundle
 */
router.post(
  '/bundles/:bundleId/metrics',
  requireRole(['RESEARCHER', 'STEWARD', 'ADMIN']),
  asyncHandler(async (req: Request, res: Response) => {
    const { bundleId } = req.params;
    const metrics = z.array(PerformanceMetricSchema).parse(req.body);

    // Verify bundle exists and is editable
    const bundleCheck = await db.execute(sql`
      SELECT status FROM evidence_bundles WHERE id = ${bundleId}
    `);

    if (bundleCheck.rows.length === 0) {
      res.status(404).json({ error: 'Evidence bundle not found' });
      return;
    }

    if (!['DRAFT', 'REVIEW'].includes(bundleCheck.rows[0].status)) {
      res.status(400).json({ error: 'Cannot modify metrics on approved/published bundle' });
      return;
    }

    const insertedMetrics = [];

    for (const metric of metrics) {
      const result = await db.execute(sql`
        INSERT INTO performance_metrics (
          bundle_id, metric_name, metric_type, value,
          confidence_lower, confidence_upper, threshold, passed, unit, methodology
        ) VALUES (
          ${bundleId},
          ${metric.metric_name},
          ${metric.metric_type},
          ${metric.value},
          ${metric.confidence_lower || null},
          ${metric.confidence_upper || null},
          ${metric.threshold || null},
          ${metric.passed || null},
          ${metric.unit || null},
          ${metric.methodology || null}
        )
        RETURNING *
      `);
      insertedMetrics.push(result.rows[0]);
    }

    res.status(201).json({ metrics: insertedMetrics });
  })
);

/**
 * POST /api/transparency/metrics/:metricId/stratified
 * Add stratified results for a metric
 */
router.post(
  '/metrics/:metricId/stratified',
  requireRole(['RESEARCHER', 'STEWARD', 'ADMIN']),
  asyncHandler(async (req: Request, res: Response) => {
    const { metricId } = req.params;
    const stratifiedData = z.array(StratifiedMetricSchema.omit({ metric_id: true })).parse(req.body);

    // Verify metric exists
    const metricCheck = await db.execute(sql`
      SELECT pm.id, eb.status
      FROM performance_metrics pm
      JOIN evidence_bundles eb ON pm.bundle_id = eb.id
      WHERE pm.id = ${metricId}
    `);

    if (metricCheck.rows.length === 0) {
      res.status(404).json({ error: 'Metric not found' });
      return;
    }

    if (!['DRAFT', 'REVIEW'].includes(metricCheck.rows[0].status)) {
      res.status(400).json({ error: 'Cannot modify stratified data on approved/published bundle' });
      return;
    }

    const inserted = [];

    for (const data of stratifiedData) {
      const result = await db.execute(sql`
        INSERT INTO stratified_metrics (
          metric_id, stratum_variable, stratum_value, sample_size,
          metric_value, confidence_lower, confidence_upper
        ) VALUES (
          ${metricId},
          ${data.stratum_variable},
          ${data.stratum_value},
          ${data.sample_size},
          ${data.metric_value},
          ${data.confidence_lower || null},
          ${data.confidence_upper || null}
        )
        RETURNING *
      `);
      inserted.push(result.rows[0]);
    }

    res.status(201).json({ stratified_metrics: inserted });
  })
);

// ============================================================================
// Export Endpoints
// ============================================================================

/**
 * GET /api/transparency/bundles/:id/export
 * Export an evidence bundle in various formats
 */
router.get(
  '/bundles/:id/export',
  requireRole(['RESEARCHER', 'STEWARD', 'ADMIN']),
  asyncHandler(async (req: Request, res: Response) => {
    const { id } = req.params;
    const { format = 'json' } = req.query;

    // Get full bundle data
    const bundleResult = await db.execute(sql`
      SELECT
        eb.*,
        mr.name as model_name,
        mr.model_type,
        mr.framework,
        mr.intended_use_summary,
        mr.out_of_scope_uses,
        mr.training_data_description,
        mr.evaluation_data_description
      FROM evidence_bundles eb
      LEFT JOIN model_registry mr ON eb.model_id = mr.id
      WHERE eb.id = ${id}
    `);

    if (bundleResult.rows.length === 0) {
      res.status(404).json({ error: 'Evidence bundle not found' });
      return;
    }

    const bundle = bundleResult.rows[0];

    // Get all metrics
    const metricsResult = await db.execute(sql`
      SELECT * FROM performance_metrics WHERE bundle_id = ${id}
    `);

    // Get stratified metrics
    const stratifiedResult = await db.execute(sql`
      SELECT sm.*, pm.metric_name
      FROM stratified_metrics sm
      JOIN performance_metrics pm ON sm.metric_id = pm.id
      WHERE pm.bundle_id = ${id}
    `);

    const exportData = {
      evidence_bundle: bundle,
      performance_metrics: metricsResult.rows,
      stratified_metrics: stratifiedResult.rows,
      exported_at: new Date().toISOString(),
      schema_version: '1.0.0',
    };

    if (format === 'json') {
      res.setHeader('Content-Type', 'application/json');
      res.setHeader('Content-Disposition', `attachment; filename="evidence-bundle-${id}.json"`);
      res.json(exportData);
    } else if (format === 'markdown') {
      // Generate markdown report
      const md = generateMarkdownReport(exportData);
      res.setHeader('Content-Type', 'text/markdown');
      res.setHeader('Content-Disposition', `attachment; filename="evidence-bundle-${id}.md"`);
      res.send(md);
    } else {
      res.status(400).json({ error: 'Unsupported export format. Use json or markdown.' });
    }
  })
);

// ============================================================================
// Summary Statistics
// ============================================================================

/**
 * GET /api/transparency/stats
 * Get transparency compliance statistics
 */
router.get(
  '/stats',
  requireRole(['VIEWER', 'RESEARCHER', 'STEWARD', 'ADMIN']),
  asyncHandler(async (req: Request, res: Response) => {
    const { model_id } = req.query;

    const whereClause = model_id ? sql`WHERE model_id = ${model_id}` : sql``;

    const stats = await db.execute(sql`
      SELECT
        COUNT(*) as total_bundles,
        COUNT(*) FILTER (WHERE status = 'DRAFT') as draft_count,
        COUNT(*) FILTER (WHERE status = 'REVIEW') as review_count,
        COUNT(*) FILTER (WHERE status = 'APPROVED') as approved_count,
        COUNT(*) FILTER (WHERE status = 'PUBLISHED') as published_count,
        COUNT(DISTINCT model_id) as models_with_bundles,
        COUNT(*) FILTER (WHERE bundle_type = 'TRIPOD_AI') as tripod_bundles,
        COUNT(*) FILTER (WHERE bundle_type = 'HTI_1') as hti1_bundles,
        COUNT(*) FILTER (WHERE bundle_type = 'FAVES') as faves_bundles
      FROM evidence_bundles
      ${whereClause}
    `);

    res.json(stats.rows[0] || {});
  })
);

// ============================================================================
// Helper Functions
// ============================================================================

function generateMarkdownReport(data: any): string {
  const { evidence_bundle: bundle, performance_metrics: metrics, stratified_metrics: stratified } = data;

  let md = `# Evidence Bundle Report\n\n`;
  md += `**Bundle ID:** ${bundle.id}\n`;
  md += `**Model:** ${bundle.model_name || bundle.model_id}\n`;
  md += `**Version:** ${bundle.model_version}\n`;
  md += `**Type:** ${bundle.bundle_type}\n`;
  md += `**Status:** ${bundle.status}\n`;
  md += `**Created:** ${bundle.created_at}\n\n`;

  if (bundle.description) {
    md += `## Description\n\n${bundle.description}\n\n`;
  }

  if (bundle.intended_use_summary) {
    md += `## Intended Use\n\n${bundle.intended_use_summary}\n\n`;
  }

  md += `## Performance Metrics\n\n`;
  md += `| Metric | Type | Value | CI (95%) | Threshold | Pass |\n`;
  md += `|--------|------|-------|----------|-----------|------|\n`;

  for (const m of metrics) {
    const ci = m.confidence_lower && m.confidence_upper
      ? `[${m.confidence_lower.toFixed(3)}, ${m.confidence_upper.toFixed(3)}]`
      : '-';
    const threshold = m.threshold ? m.threshold.toFixed(3) : '-';
    const pass = m.passed === true ? '✓' : m.passed === false ? '✗' : '-';
    md += `| ${m.metric_name} | ${m.metric_type} | ${m.value.toFixed(3)} | ${ci} | ${threshold} | ${pass} |\n`;
  }

  if (stratified.length > 0) {
    md += `\n## Stratified Results\n\n`;

    // Group by stratum variable
    const grouped: Record<string, any[]> = {};
    for (const s of stratified) {
      const key = s.stratum_variable;
      if (!grouped[key]) grouped[key] = [];
      grouped[key].push(s);
    }

    for (const [variable, items] of Object.entries(grouped)) {
      md += `### ${variable}\n\n`;
      md += `| Stratum | Metric | N | Value | CI (95%) |\n`;
      md += `|---------|--------|---|-------|----------|\n`;

      for (const item of items) {
        const ci = item.confidence_lower && item.confidence_upper
          ? `[${item.confidence_lower.toFixed(3)}, ${item.confidence_upper.toFixed(3)}]`
          : '-';
        md += `| ${item.stratum_value} | ${item.metric_name} | ${item.sample_size} | ${item.metric_value.toFixed(3)} | ${ci} |\n`;
      }
      md += '\n';
    }
  }

  md += `\n---\n*Generated: ${data.exported_at}*\n`;

  return md;
}

export default router;
