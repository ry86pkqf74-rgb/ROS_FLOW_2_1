/**
 * HTI-1 Source Attributes API Routes
 *
 * Endpoints for managing Predictive DSI Source Attributes per HTI-1 requirements.
 * Ensures transparency for AI-assisted decision support interventions.
 *
 * Priority: P0 - CRITICAL (Phase 9 HTI-1 Compliance)
 *
 * @module services/orchestrator/src/routes/source-attributes
 * @version 1.0.0
 */

import { Router, Request, Response, NextFunction } from 'express';
import { requireRole } from '../middleware/rbac';
import { db } from '../../db.js';
import { desc, eq, and, sql, gte, lte, isNull } from 'drizzle-orm';
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
// HTI-1 Required Attribute Keys
// ============================================================================

const HTI1_REQUIRED_KEYS = [
  'output_source',
  'output_developer',
  'data_sources',
  'intended_use',
  'limitations',
  'intervention_risk',
  'last_updated',
] as const;

type HTI1AttributeKey = typeof HTI1_REQUIRED_KEYS[number];

// ============================================================================
// Validation Schemas
// ============================================================================

const PredictiveDSICreateSchema = z.object({
  model_id: z.string().uuid(),
  dsi_name: z.string().min(1).max(255),
  dsi_type: z.enum(['DIAGNOSIS', 'PROGNOSIS', 'TREATMENT', 'RISK_ASSESSMENT', 'MONITORING', 'OTHER']),
  clinical_context: z.string().optional(),
  integration_point: z.string().optional(),
  requires_human_review: z.boolean().default(true),
});

const SourceAttributeSchema = z.object({
  attribute_key: z.enum(HTI1_REQUIRED_KEYS),
  display_name: z.string().min(1).max(255),
  value_text: z.string(),
  plain_language_summary: z.string().optional(),
  source_document_url: z.string().url().optional(),
  effective_date: z.string().datetime().optional(),
  expiry_date: z.string().datetime().optional(),
  requires_update_review: z.boolean().default(false),
});

const PlainLanguageResponseSchema = z.object({
  question_text: z.string().min(1),
  answer_text: z.string().min(1),
  reading_level: z.enum(['BASIC', 'INTERMEDIATE', 'TECHNICAL']).optional(),
  language_code: z.string().length(2).default('en'),
});

// ============================================================================
// Predictive DSI Endpoints
// ============================================================================

/**
 * GET /api/source-attributes/dsi
 * List all Predictive DSI registrations
 */
router.get(
  '/dsi',
  requireRole(['VIEWER', 'RESEARCHER', 'STEWARD', 'ADMIN']),
  asyncHandler(async (req: Request, res: Response) => {
    const { model_id, dsi_type, is_active, limit = '50', offset = '0' } = req.query;

    const conditions: any[] = [];
    if (model_id) conditions.push(sql`pd.model_id = ${model_id}`);
    if (dsi_type) conditions.push(sql`pd.dsi_type = ${dsi_type}`);
    if (is_active === 'true') conditions.push(sql`pd.is_active = true`);
    if (is_active === 'false') conditions.push(sql`pd.is_active = false`);

    const whereClause = conditions.length > 0
      ? sql`WHERE ${sql.join(conditions, sql` AND `)}`
      : sql``;

    const dsiList = await db.execute(sql`
      SELECT
        pd.*,
        mr.name as model_name,
        mr.model_type,
        (
          SELECT COUNT(DISTINCT sa.attribute_key)
          FROM source_attributes sa
          WHERE sa.dsi_id = pd.id AND sa.is_current = true
        ) as attributes_count,
        (
          SELECT COUNT(*)
          FROM source_attributes sa
          WHERE sa.dsi_id = pd.id
            AND sa.is_current = true
            AND sa.requires_update_review = true
        ) as pending_reviews
      FROM predictive_dsi pd
      LEFT JOIN model_registry mr ON pd.model_id = mr.id
      ${whereClause}
      ORDER BY pd.created_at DESC
      LIMIT ${parseInt(limit as string)}
      OFFSET ${parseInt(offset as string)}
    `);

    res.json({
      dsi_list: dsiList.rows,
      pagination: {
        limit: parseInt(limit as string),
        offset: parseInt(offset as string),
      },
    });
  })
);

/**
 * GET /api/source-attributes/dsi/:id
 * Get a specific Predictive DSI with all current attributes
 */
router.get(
  '/dsi/:id',
  requireRole(['VIEWER', 'RESEARCHER', 'STEWARD', 'ADMIN']),
  asyncHandler(async (req: Request, res: Response) => {
    const { id } = req.params;

    const dsiResult = await db.execute(sql`
      SELECT
        pd.*,
        mr.name as model_name,
        mr.model_type,
        mr.framework,
        mr.intended_use_summary
      FROM predictive_dsi pd
      LEFT JOIN model_registry mr ON pd.model_id = mr.id
      WHERE pd.id = ${id}
    `);

    if (dsiResult.rows.length === 0) {
      res.status(404).json({ error: 'Predictive DSI not found' });
      return;
    }

    const dsi = dsiResult.rows[0];

    // Get current source attributes
    const attributesResult = await db.execute(sql`
      SELECT * FROM source_attributes
      WHERE dsi_id = ${id} AND is_current = true
      ORDER BY attribute_key
    `);

    // Get plain language responses
    const plainLanguageResult = await db.execute(sql`
      SELECT * FROM plain_language_responses
      WHERE dsi_id = ${id} AND is_active = true
      ORDER BY question_text
    `);

    // Check HTI-1 compliance
    const currentKeys = new Set(attributesResult.rows.map((a: any) => a.attribute_key));
    const missingKeys = HTI1_REQUIRED_KEYS.filter(k => !currentKeys.has(k));
    const isCompliant = missingKeys.length === 0;

    res.json({
      dsi,
      attributes: attributesResult.rows,
      plain_language: plainLanguageResult.rows,
      compliance: {
        is_hti1_compliant: isCompliant,
        required_keys: HTI1_REQUIRED_KEYS,
        present_keys: Array.from(currentKeys),
        missing_keys: missingKeys,
      },
    });
  })
);

/**
 * POST /api/source-attributes/dsi
 * Register a new Predictive DSI
 */
router.post(
  '/dsi',
  requireRole(['RESEARCHER', 'STEWARD', 'ADMIN']),
  asyncHandler(async (req: Request, res: Response) => {
    const validated = PredictiveDSICreateSchema.parse(req.body);
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
      INSERT INTO predictive_dsi (
        model_id, dsi_name, dsi_type, clinical_context,
        integration_point, requires_human_review, created_by
      ) VALUES (
        ${validated.model_id},
        ${validated.dsi_name},
        ${validated.dsi_type},
        ${validated.clinical_context || null},
        ${validated.integration_point || null},
        ${validated.requires_human_review},
        ${userId}
      )
      RETURNING *
    `);

    eventBus.emit('source-attributes:dsi_created', {
      dsiId: result.rows[0].id,
      modelId: validated.model_id,
      dsiType: validated.dsi_type,
      createdBy: userId,
    });

    res.status(201).json(result.rows[0]);
  })
);

/**
 * PATCH /api/source-attributes/dsi/:id
 * Update a Predictive DSI
 */
router.patch(
  '/dsi/:id',
  requireRole(['STEWARD', 'ADMIN']),
  asyncHandler(async (req: Request, res: Response) => {
    const { id } = req.params;
    const { is_active, clinical_context, integration_point, requires_human_review } = req.body;

    const updates: string[] = [];
    if (is_active !== undefined) updates.push(`is_active = ${is_active}`);
    if (clinical_context !== undefined) updates.push(`clinical_context = '${clinical_context}'`);
    if (integration_point !== undefined) updates.push(`integration_point = '${integration_point}'`);
    if (requires_human_review !== undefined) updates.push(`requires_human_review = ${requires_human_review}`);

    if (updates.length === 0) {
      res.status(400).json({ error: 'No valid fields to update' });
      return;
    }

    const result = await db.execute(sql`
      UPDATE predictive_dsi
      SET ${sql.raw(updates.join(', '))}, updated_at = NOW()
      WHERE id = ${id}
      RETURNING *
    `);

    if (result.rows.length === 0) {
      res.status(404).json({ error: 'Predictive DSI not found' });
      return;
    }

    res.json(result.rows[0]);
  })
);

// ============================================================================
// Source Attributes Endpoints
// ============================================================================

/**
 * POST /api/source-attributes/dsi/:dsiId/attributes
 * Add or update a source attribute (creates new version)
 */
router.post(
  '/dsi/:dsiId/attributes',
  requireRole(['RESEARCHER', 'STEWARD', 'ADMIN']),
  asyncHandler(async (req: Request, res: Response) => {
    const { dsiId } = req.params;
    const validated = SourceAttributeSchema.parse(req.body);
    const userId = (req as any).user?.id || 'system';

    // Verify DSI exists
    const dsiCheck = await db.execute(sql`
      SELECT id FROM predictive_dsi WHERE id = ${dsiId}
    `);

    if (dsiCheck.rows.length === 0) {
      res.status(404).json({ error: 'Predictive DSI not found' });
      return;
    }

    // Get current version number for this attribute key
    const versionResult = await db.execute(sql`
      SELECT COALESCE(MAX(version), 0) as max_version
      FROM source_attributes
      WHERE dsi_id = ${dsiId} AND attribute_key = ${validated.attribute_key}
    `);
    const newVersion = (versionResult.rows[0]?.max_version || 0) + 1;

    // Mark previous version as not current
    await db.execute(sql`
      UPDATE source_attributes
      SET is_current = false
      WHERE dsi_id = ${dsiId}
        AND attribute_key = ${validated.attribute_key}
        AND is_current = true
    `);

    // Insert new version
    const result = await db.execute(sql`
      INSERT INTO source_attributes (
        dsi_id, attribute_key, display_name, value_text,
        plain_language_summary, source_document_url,
        effective_date, expiry_date, version, is_current,
        requires_update_review, created_by
      ) VALUES (
        ${dsiId},
        ${validated.attribute_key},
        ${validated.display_name},
        ${validated.value_text},
        ${validated.plain_language_summary || null},
        ${validated.source_document_url || null},
        ${validated.effective_date || null},
        ${validated.expiry_date || null},
        ${newVersion},
        true,
        ${validated.requires_update_review},
        ${userId}
      )
      RETURNING *
    `);

    // Log to audit table
    await db.execute(sql`
      INSERT INTO source_attributes_audit (
        attribute_id, dsi_id, attribute_key, action, old_value,
        new_value, changed_by, change_reason
      ) VALUES (
        ${result.rows[0].id},
        ${dsiId},
        ${validated.attribute_key},
        ${newVersion === 1 ? 'CREATE' : 'UPDATE'},
        NULL,
        ${validated.value_text},
        ${userId},
        'Attribute ${newVersion === 1 ? 'created' : 'updated'} via API'
      )
    `);

    eventBus.emit('source-attributes:attribute_updated', {
      dsiId,
      attributeKey: validated.attribute_key,
      version: newVersion,
      updatedBy: userId,
    });

    res.status(201).json(result.rows[0]);
  })
);

/**
 * GET /api/source-attributes/dsi/:dsiId/attributes/:key/history
 * Get version history for a specific attribute
 */
router.get(
  '/dsi/:dsiId/attributes/:key/history',
  requireRole(['STEWARD', 'ADMIN']),
  asyncHandler(async (req: Request, res: Response) => {
    const { dsiId, key } = req.params;

    const history = await db.execute(sql`
      SELECT
        sa.*,
        saa.action,
        saa.old_value,
        saa.changed_by as audit_changed_by,
        saa.change_reason,
        saa.changed_at
      FROM source_attributes sa
      LEFT JOIN source_attributes_audit saa ON saa.attribute_id = sa.id
      WHERE sa.dsi_id = ${dsiId} AND sa.attribute_key = ${key}
      ORDER BY sa.version DESC
    `);

    res.json({ history: history.rows });
  })
);

// ============================================================================
// Plain Language Responses
// ============================================================================

/**
 * POST /api/source-attributes/dsi/:dsiId/plain-language
 * Add a plain language Q&A response
 */
router.post(
  '/dsi/:dsiId/plain-language',
  requireRole(['RESEARCHER', 'STEWARD', 'ADMIN']),
  asyncHandler(async (req: Request, res: Response) => {
    const { dsiId } = req.params;
    const validated = PlainLanguageResponseSchema.parse(req.body);
    const userId = (req as any).user?.id || 'system';

    const result = await db.execute(sql`
      INSERT INTO plain_language_responses (
        dsi_id, question_text, answer_text,
        reading_level, language_code, created_by
      ) VALUES (
        ${dsiId},
        ${validated.question_text},
        ${validated.answer_text},
        ${validated.reading_level || 'INTERMEDIATE'},
        ${validated.language_code},
        ${userId}
      )
      RETURNING *
    `);

    res.status(201).json(result.rows[0]);
  })
);

/**
 * GET /api/source-attributes/dsi/:dsiId/plain-language
 * Get all plain language responses for a DSI
 */
router.get(
  '/dsi/:dsiId/plain-language',
  requireRole(['VIEWER', 'RESEARCHER', 'STEWARD', 'ADMIN']),
  asyncHandler(async (req: Request, res: Response) => {
    const { dsiId } = req.params;
    const { language = 'en' } = req.query;

    const responses = await db.execute(sql`
      SELECT * FROM plain_language_responses
      WHERE dsi_id = ${dsiId}
        AND is_active = true
        AND language_code = ${language}
      ORDER BY question_text
    `);

    res.json({ responses: responses.rows });
  })
);

// ============================================================================
// Compliance Checking
// ============================================================================

/**
 * GET /api/source-attributes/dsi/:dsiId/compliance
 * Check HTI-1 compliance status for a DSI
 */
router.get(
  '/dsi/:dsiId/compliance',
  requireRole(['VIEWER', 'RESEARCHER', 'STEWARD', 'ADMIN']),
  asyncHandler(async (req: Request, res: Response) => {
    const { dsiId } = req.params;

    // Get DSI info
    const dsiResult = await db.execute(sql`
      SELECT * FROM predictive_dsi WHERE id = ${dsiId}
    `);

    if (dsiResult.rows.length === 0) {
      res.status(404).json({ error: 'Predictive DSI not found' });
      return;
    }

    // Get current attributes
    const attributesResult = await db.execute(sql`
      SELECT attribute_key, display_name, value_text, effective_date, expiry_date
      FROM source_attributes
      WHERE dsi_id = ${dsiId} AND is_current = true
    `);

    const currentAttributes = new Map(
      attributesResult.rows.map((a: any) => [a.attribute_key, a])
    );

    // Check each required key
    const checks = HTI1_REQUIRED_KEYS.map(key => {
      const attr = currentAttributes.get(key);
      const present = !!attr;
      const hasValue = present && attr.value_text && attr.value_text.trim().length > 0;
      const isExpired = attr?.expiry_date && new Date(attr.expiry_date) < new Date();

      return {
        key,
        display_name: attr?.display_name || key.replace(/_/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase()),
        status: !present ? 'MISSING' : !hasValue ? 'EMPTY' : isExpired ? 'EXPIRED' : 'VALID',
        effective_date: attr?.effective_date || null,
        expiry_date: attr?.expiry_date || null,
      };
    });

    const validCount = checks.filter(c => c.status === 'VALID').length;
    const isCompliant = validCount === HTI1_REQUIRED_KEYS.length;

    res.json({
      dsi_id: dsiId,
      is_hti1_compliant: isCompliant,
      compliance_score: Math.round((validCount / HTI1_REQUIRED_KEYS.length) * 100),
      total_required: HTI1_REQUIRED_KEYS.length,
      valid_count: validCount,
      checks,
      checked_at: new Date().toISOString(),
    });
  })
);

/**
 * GET /api/source-attributes/compliance/summary
 * Get overall HTI-1 compliance summary across all DSIs
 */
router.get(
  '/compliance/summary',
  requireRole(['STEWARD', 'ADMIN']),
  asyncHandler(async (req: Request, res: Response) => {
    const summary = await db.execute(sql`
      WITH attribute_counts AS (
        SELECT
          dsi_id,
          COUNT(DISTINCT attribute_key) FILTER (WHERE is_current = true) as present_count
        FROM source_attributes
        GROUP BY dsi_id
      )
      SELECT
        COUNT(DISTINCT pd.id) as total_dsi,
        COUNT(DISTINCT pd.id) FILTER (WHERE pd.is_active = true) as active_dsi,
        COUNT(DISTINCT pd.id) FILTER (
          WHERE ac.present_count >= ${HTI1_REQUIRED_KEYS.length}
        ) as compliant_dsi,
        COUNT(DISTINCT pd.id) FILTER (
          WHERE ac.present_count < ${HTI1_REQUIRED_KEYS.length} OR ac.present_count IS NULL
        ) as non_compliant_dsi,
        AVG(COALESCE(ac.present_count, 0)::float / ${HTI1_REQUIRED_KEYS.length} * 100) as avg_compliance_score
      FROM predictive_dsi pd
      LEFT JOIN attribute_counts ac ON pd.id = ac.dsi_id
    `);

    res.json({
      summary: summary.rows[0],
      required_attributes: HTI1_REQUIRED_KEYS,
      checked_at: new Date().toISOString(),
    });
  })
);

// ============================================================================
// Batch Operations (Track B Enhancement)
// ============================================================================

/**
 * POST /api/source-attributes/batch/attributes
 * Batch update source attributes for multiple DSIs (Track B - ROS-109)
 * Supports bulk operations with transaction safety and audit logging
 */
const BatchAttributeUpdateSchema = z.object({
  updates: z.array(
    z.object({
      dsi_id: z.string().uuid(),
      attribute_key: z.enum(HTI1_REQUIRED_KEYS),
      value_text: z.string(),
      display_name: z.string().optional(),
      plain_language_summary: z.string().optional(),
      source_document_url: z.string().url().optional(),
    })
  ),
  batch_reason: z.string().optional(),
  dry_run: z.boolean().default(false),
});

router.post(
  '/batch/attributes',
  requireRole(['STEWARD', 'ADMIN']),
  asyncHandler(async (req: Request, res: Response) => {
    const validated = BatchAttributeUpdateSchema.parse(req.body);
    const userId = (req as any).user?.id || 'system';
    const batchId = `batch_${Date.now()}`;

    const results = {
      batch_id: batchId,
      total: validated.updates.length,
      successful: 0,
      failed: 0,
      skipped: 0,
      details: [] as any[],
      audit_entries: [] as any[],
    };

    // Validate all DSIs exist first
    const dsiIds = [...new Set(validated.updates.map(u => u.dsi_id))];
    const dsiCheck = await db.execute(sql`
      SELECT id FROM predictive_dsi WHERE id = ANY(${dsiIds})
    `);
    const existingDsiIds = new Set(dsiCheck.rows.map((r: any) => r.id));

    for (const update of validated.updates) {
      try {
        if (!existingDsiIds.has(update.dsi_id)) {
          results.details.push({
            dsi_id: update.dsi_id,
            attribute_key: update.attribute_key,
            status: 'SKIPPED',
            reason: 'DSI not found',
          });
          results.skipped++;
          continue;
        }

        if (validated.dry_run) {
          results.details.push({
            dsi_id: update.dsi_id,
            attribute_key: update.attribute_key,
            status: 'DRY_RUN',
            reason: 'Dry run mode - no changes applied',
          });
          results.successful++;
          continue;
        }

        // Get current version
        const versionResult = await db.execute(sql`
          SELECT COALESCE(MAX(version), 0) as max_version
          FROM source_attributes
          WHERE dsi_id = ${update.dsi_id} AND attribute_key = ${update.attribute_key}
        `);
        const newVersion = (versionResult.rows[0]?.max_version || 0) + 1;

        // Mark previous as not current
        await db.execute(sql`
          UPDATE source_attributes
          SET is_current = false
          WHERE dsi_id = ${update.dsi_id}
            AND attribute_key = ${update.attribute_key}
            AND is_current = true
        `);

        // Insert new version
        const result = await db.execute(sql`
          INSERT INTO source_attributes (
            dsi_id, attribute_key, display_name, value_text,
            plain_language_summary, source_document_url, version, is_current,
            requires_update_review, created_by
          ) VALUES (
            ${update.dsi_id},
            ${update.attribute_key},
            ${update.display_name || update.attribute_key},
            ${update.value_text},
            ${update.plain_language_summary || null},
            ${update.source_document_url || null},
            ${newVersion},
            true,
            false,
            ${userId}
          )
          RETURNING *
        `);

        // Log audit entry
        await db.execute(sql`
          INSERT INTO source_attributes_audit (
            attribute_id, dsi_id, attribute_key, action, old_value,
            new_value, changed_by, change_reason
          ) VALUES (
            ${result.rows[0].id},
            ${update.dsi_id},
            ${update.attribute_key},
            'BATCH_UPDATE',
            NULL,
            ${update.value_text},
            ${userId},
            ${validated.batch_reason || `Batch update ${batchId}`}
          )
        `);

        results.details.push({
          dsi_id: update.dsi_id,
          attribute_key: update.attribute_key,
          status: 'SUCCESS',
          version: newVersion,
        });
        results.successful++;

        eventBus.emit('source-attributes:batch_update', {
          batchId,
          dsiId: update.dsi_id,
          attributeKey: update.attribute_key,
          version: newVersion,
          updatedBy: userId,
        });

      } catch (error) {
        logger.error(`Batch update failed for DSI ${update.dsi_id}:`, error);
        results.details.push({
          dsi_id: update.dsi_id,
          attribute_key: update.attribute_key,
          status: 'FAILED',
          reason: (error as Error).message,
        });
        results.failed++;
      }
    }

    res.status(validated.dry_run ? 200 : 201).json(results);
  })
);

// ============================================================================
// Source Integrity Validation (Track B Enhancement - ROS-110)
// ============================================================================

/**
 * POST /api/source-attributes/validate/integrity
 * Validate source integrity and detect anomalies
 * Checks for data consistency, completeness, and provenance
 */
const IntegrityValidationSchema = z.object({
  dsi_ids: z.array(z.string().uuid()).optional(),
  check_expiry: z.boolean().default(true),
  check_completeness: z.boolean().default(true),
  check_consistency: z.boolean().default(true),
});

router.post(
  '/validate/integrity',
  requireRole(['STEWARD', 'ADMIN']),
  asyncHandler(async (req: Request, res: Response) => {
    const validated = IntegrityValidationSchema.parse(req.body);

    const validationResult = {
      validated_at: new Date().toISOString(),
      total_checked: 0,
      issues_found: 0,
      critical: 0,
      warnings: 0,
      findings: [] as any[],
    };

    // Get DSIs to check
    let dsiQuery = sql`SELECT id FROM predictive_dsi WHERE is_active = true`;
    if (validated.dsi_ids && validated.dsi_ids.length > 0) {
      dsiQuery = sql`SELECT id FROM predictive_dsi WHERE id = ANY(${validated.dsi_ids})`;
    }

    const dsiResult = await db.execute(dsiQuery);
    validationResult.total_checked = dsiResult.rows.length;

    for (const { id: dsiId } of dsiResult.rows) {
      // Get current attributes
      const attrResult = await db.execute(sql`
        SELECT * FROM source_attributes
        WHERE dsi_id = ${dsiId} AND is_current = true
      `);

      // Check expiry
      if (validated.check_expiry) {
        for (const attr of attrResult.rows) {
          if (attr.expiry_date) {
            const expiryDate = new Date(attr.expiry_date);
            if (expiryDate < new Date()) {
              validationResult.findings.push({
                dsi_id: dsiId,
                attribute_key: attr.attribute_key,
                severity: 'CRITICAL',
                issue: 'EXPIRED',
                description: `Attribute expired on ${attr.expiry_date}`,
                expiry_date: attr.expiry_date,
              });
              validationResult.critical++;
              validationResult.issues_found++;
            } else if (
              expiryDate.getTime() - new Date().getTime() <
              30 * 24 * 60 * 60 * 1000
            ) {
              validationResult.findings.push({
                dsi_id: dsiId,
                attribute_key: attr.attribute_key,
                severity: 'WARNING',
                issue: 'EXPIRING_SOON',
                description: `Attribute expires within 30 days`,
                expiry_date: attr.expiry_date,
              });
              validationResult.warnings++;
              validationResult.issues_found++;
            }
          }
        }
      }

      // Check completeness
      if (validated.check_completeness) {
        const currentKeys = new Set(attrResult.rows.map((a: any) => a.attribute_key));
        const missingKeys = HTI1_REQUIRED_KEYS.filter(k => !currentKeys.has(k));

        if (missingKeys.length > 0) {
          validationResult.findings.push({
            dsi_id: dsiId,
            severity: 'WARNING',
            issue: 'INCOMPLETE',
            description: `Missing ${missingKeys.length} required attributes`,
            missing_keys: missingKeys,
          });
          validationResult.warnings++;
          validationResult.issues_found++;
        }
      }

      // Check consistency
      if (validated.check_consistency) {
        // Check for empty required fields
        const emptyAttrs = attrResult.rows.filter(
          (a: any) =>
            HTI1_REQUIRED_KEYS.includes(a.attribute_key) &&
            (!a.value_text || a.value_text.trim().length === 0)
        );

        if (emptyAttrs.length > 0) {
          validationResult.findings.push({
            dsi_id: dsiId,
            severity: 'CRITICAL',
            issue: 'EMPTY_REQUIRED_FIELD',
            description: `${emptyAttrs.length} required attributes have empty values`,
            affected_attributes: emptyAttrs.map((a: any) => a.attribute_key),
          });
          validationResult.critical++;
          validationResult.issues_found++;
        }
      }
    }

    res.status(200).json(validationResult);
  })
);

/**
 * GET /api/source-attributes/validate/sources
 * Get source integrity validation report for data provenance tracking
 */
router.get(
  '/validate/sources',
  requireRole(['VIEWER', 'STEWARD', 'ADMIN']),
  asyncHandler(async (req: Request, res: Response) => {
    const { dsi_id, include_history = 'false' } = req.query;

    const queryStr = dsi_id
      ? `WHERE dsi_id = '${dsi_id}'`
      : '';

    const sourcesResult = await db.execute(sql`
      SELECT DISTINCT
        dsi_id,
        attribute_key,
        source_document_url,
        created_at,
        is_current,
        version
      FROM source_attributes
      ${dsi_id ? sql`WHERE dsi_id = ${dsi_id}` : sql``}
      ORDER BY created_at DESC
    `);

    const report = {
      validation_timestamp: new Date().toISOString(),
      total_sources: sourcesResult.rows.length,
      sources: sourcesResult.rows.map((row: any) => ({
        dsi_id: row.dsi_id,
        attribute_key: row.attribute_key,
        source_document_url: row.source_document_url,
        created_at: row.created_at,
        is_current: row.is_current,
        version: row.version,
      })),
    };

    res.json(report);
  })
);

export default router;
