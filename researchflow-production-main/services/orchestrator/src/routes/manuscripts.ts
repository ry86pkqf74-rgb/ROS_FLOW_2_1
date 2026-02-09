/**
 * Manuscript Studio - Canonical REST API Routes
 *
 * API namespace: /api/manuscripts
 *
 * Endpoints:
 * - GET    /ping                           # Health check
 * - POST   /                               # Create manuscript
 * - GET    /                               # List manuscripts
 * - GET    /:id                            # Get manuscript
 * - PATCH  /:id                            # Update manuscript
 * - DELETE /:id                            # Delete manuscript (soft)
 * - GET    /:id/sections                   # Get sections
 * - GET    /:id/doc                        # Get latest doc state
 * - POST   /:id/doc/save                   # Save doc snapshot
 * - POST   /:id/sections/:sectionId/generate   # Generate section
 * - POST   /:id/sections/:sectionId/refine     # Refine with AI (diff)
 * - POST   /:id/sections/:sectionId/validate   # Validate section
 * - POST   /:id/abstract/generate              # Generate abstract
 * - GET    /:id/events                     # Provenance log
 *
 * @module routes/manuscripts
 */

import { createHash } from 'crypto';

import { sql } from 'drizzle-orm';
import { Router, Request, Response } from 'express';
import { nanoid } from 'nanoid';
import * as z from 'zod';

import { db, pool } from '../../db';
import { requireRole } from '../middleware/rbac';
import { appendEvent, type DbClient } from '../services/audit.service';
import { scanForPhi } from '../services/phi-protection';

const router = Router();

// =============================================================================
// Validation Schemas
// =============================================================================

const createManuscriptSchema = z.object({
  title: z.string().min(1).max(500),
  researchId: z.string().uuid().optional(),
  projectId: z.string().uuid().optional(),
  templateType: z.enum([
    'imrad', 'case_report', 'systematic_review',
    'meta_analysis', 'letter', 'editorial', 'review_article'
  ]).default('imrad'),
  citationStyle: z.enum(['AMA', 'APA', 'Vancouver', 'Harvard', 'Chicago']).default('AMA'),
  targetJournal: z.string().max(200).optional(),
});

const updateManuscriptSchema = z.object({
  title: z.string().min(1).max(500).optional(),
  status: z.enum([
    'draft', 'in_review', 'revision_requested',
    'approved', 'submitted', 'published', 'archived'
  ]).optional(),
  targetJournal: z.string().max(200).optional(),
  metadata: z.record(z.any()).optional(),
});

const sectionSnapshotSchema = z.object({
  content: z.string().optional(),
  wordCount: z.number().int().nonnegative().optional(),
}).catchall(z.any());

const saveDocSchema = z.object({
  sectionId: z.string().uuid().optional(),
  yjsState: z.string().optional(), // Base64 encoded Yjs state
  contentText: z.string().optional(),
  changeDescription: z.string().max(500).optional(),
  sections: z.record(sectionSnapshotSchema).optional(),
}).refine((data) => !!(data.contentText || data.sections), {
  message: 'contentText or sections are required',
  path: ['contentText'],
});

const generateSectionSchema = z.object({
  sectionType: z.enum([
    'title', 'abstract', 'introduction', 'methods',
    'results', 'discussion', 'conclusion', 'references'
  ]),
  options: z.object({
    structured: z.boolean().optional(),
    wordLimit: z.number().positive().optional(),
    journalStyle: z.string().optional(),
    instructions: z.string().max(1000).optional(),
  }).optional(),
});

const refineSectionSchema = z.object({
  selectedText: z.string().min(1),
  instruction: z.string().min(1).max(500),
  selectionStart: z.number().int().nonnegative(),
  selectionEnd: z.number().int().nonnegative(),
});

// =============================================================================
// Helper Functions
// =============================================================================

function isLiveMode(): boolean {
  const mode = process.env.GOVERNANCE_MODE || process.env.ROS_MODE || 'DEMO';
  return mode === 'LIVE';
}

function generateContentHash(content: string): string {
  return createHash('sha256').update(content).digest('hex');
}

function countWords(text: string): number {
  return text.split(/\s+/).filter(Boolean).length;
}

function serializeSectionsToText(
  sections?: Record<string, { content?: string }>
): string {
  if (!sections) {
    return '';
  }

  return Object.entries(sections)
    .map(([sectionId, section]) => {
      const content = section?.content?.trim() || '';
      return `## ${sectionId}\n\n${content}`.trim();
    })
    .filter(Boolean)
    .join('\n\n');
}

const STREAM_TYPE_MANUSCRIPT = 'MANUSCRIPT';
const SERVICE_ORCHESTRATOR = 'orchestrator';

function getHipaaMode(): boolean {
  const mode = process.env.GOVERNANCE_MODE || process.env.ROS_MODE || '';
  const appMode = String(process.env.APP_MODE || '').toLowerCase();
  return (
    mode === 'LIVE' ||
    appMode === 'hipaa' ||
    String(process.env.HIPAA_MODE || '').toLowerCase() === 'true' ||
    String(process.env.HIPAA_MODE || '').toLowerCase() === '1'
  );
}

/** Run a function inside a DB transaction. Commits on success, rolls back on throw. */
async function runWithTransaction<T>(fn: (tx: DbClient) => Promise<T>): Promise<T> {
  if (!pool) throw new Error('Database pool not initialized');
  const client = await pool.connect();
  try {
    await client.query('BEGIN');
    const result = await fn(client as DbClient);
    await client.query('COMMIT');
    return result;
  } catch (err) {
    await client.query('ROLLBACK').catch(() => {});
    throw err;
  } finally {
    client.release();
  }
}

async function logManuscriptEvent(
  manuscriptId: string,
  action: string,
  userId: string,
  details: Record<string, any>,
  previousHash?: string
): Promise<string> {
  const hashInput = JSON.stringify({ manuscriptId, action, details, previousHash, timestamp: Date.now() });
  const currentHash = generateContentHash(hashInput);

  await db.execute(sql`
    INSERT INTO manuscript_audit_log (id, manuscript_id, action, details, user_id, previous_hash, current_hash)
    VALUES (${`audit_${nanoid(12)}`}, ${manuscriptId}, ${action}, ${JSON.stringify(details)}::jsonb, ${userId}, ${previousHash || null}, ${currentHash})
  `);

  return currentHash;
}

/** Log manuscript event inside an existing transaction (for use with canonical audit). */
async function logManuscriptEventTx(
  tx: DbClient,
  manuscriptId: string,
  action: string,
  userId: string,
  details: Record<string, any>,
  previousHash?: string | null
): Promise<string> {
  const hashInput = JSON.stringify({ manuscriptId, action, details, previousHash, timestamp: Date.now() });
  const currentHash = generateContentHash(hashInput);
  await tx.query(
    `INSERT INTO manuscript_audit_log (id, manuscript_id, action, details, user_id, previous_hash, current_hash)
     VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7)`,
    [`audit_${nanoid(12)}`, manuscriptId, action, JSON.stringify(details), userId, previousHash ?? null, currentHash]
  );
  return currentHash;
}

// =============================================================================
// Routes
// =============================================================================

/**
 * GET /api/manuscripts/ping
 * Health check endpoint
 */
router.get('/ping', (req: Request, res: Response) => {
  res.json({
    status: 'ok',
    timestamp: Date.now(),
    service: 'manuscript-studio',
    mode: process.env.GOVERNANCE_MODE || 'DEMO',
  });
});

/**
 * POST /api/manuscripts
 * Create a new manuscript
 */
router.post('/', requireRole('RESEARCHER'), async (req: Request, res: Response) => {
  try {
    const userId = (req as any).user?.id;
    if (!userId) {
      return res.status(401).json({ error: 'Authentication required' });
    }

    const parsed = createManuscriptSchema.safeParse(req.body);
    if (!parsed.success) {
      return res.status(400).json({ error: 'Invalid input', details: parsed.error.flatten() });
    }

    const { title, researchId, projectId, templateType, citationStyle, targetJournal } = parsed.data;
    const manuscriptId = `ms_${nanoid(12)}`;
    const versionId = `ver_${nanoid(12)}`;

    await runWithTransaction(async (tx) => {
      await tx.query(
        `INSERT INTO manuscripts (id, user_id, project_id, title, template_type, citation_style, target_journal)
         VALUES ($1, $2, $3, $4, $5, $6, $7)`,
        [manuscriptId, userId, projectId ?? null, title, templateType, citationStyle, targetJournal ?? null]
      );

      const initialContent = {
        sections: {
          title: { content: title, wordCount: title.split(/\s+/).length },
          abstract: { content: '', wordCount: 0 },
          introduction: { content: '', wordCount: 0 },
          methods: { content: '', wordCount: 0 },
          results: { content: '', wordCount: 0 },
          discussion: { content: '', wordCount: 0 },
          conclusion: { content: '', wordCount: 0 },
          references: { content: '', citations: [] },
        },
      };
      const contentHash = generateContentHash(JSON.stringify(initialContent));

      await tx.query(
        `INSERT INTO manuscript_versions (id, manuscript_id, version_number, content, data_snapshot_hash, word_count, change_description, current_hash, created_by)
         VALUES ($1, $2, 1, $3::jsonb, $4, 0, 'Initial creation', $4, $5)`,
        [versionId, manuscriptId, JSON.stringify(initialContent), contentHash, userId]
      );

      await tx.query(
        `UPDATE manuscripts SET current_version_id = $1 WHERE id = $2`,
        [versionId, manuscriptId]
      );

      await logManuscriptEventTx(tx, manuscriptId, 'MANUSCRIPT_CREATED', userId, {
        templateType,
        citationStyle,
        researchId,
      });

      await appendEvent(
        tx,
        {
          stream_type: STREAM_TYPE_MANUSCRIPT,
          stream_key: manuscriptId,
          actor_type: 'USER',
          actor_id: userId,
          service: SERVICE_ORCHESTRATOR,
          action: 'CREATE',
          resource_type: 'manuscript',
          resource_id: manuscriptId,
          after_hash: contentHash,
          payload: { manuscript_id: manuscriptId, template_type: templateType, citation_style: citationStyle, version_id: versionId },
          dedupe_key: `manuscript:create:${manuscriptId}`,
        },
        { hipaaMode: getHipaaMode() }
      );
    });

    res.status(201).json({
      id: manuscriptId,
      title,
      status: 'draft',
      templateType,
      citationStyle,
      targetJournal,
      currentVersionId: versionId,
      createdAt: new Date().toISOString(),
    });
  } catch (error: any) {
    console.error('[manuscripts] Create error:', error);
    res.status(500).json({ error: 'Failed to create manuscript' });
  }
});

/**
 * GET /api/manuscripts
 * List manuscripts for current user
 */
router.get('/', requireRole('VIEWER'), async (req: Request, res: Response) => {
  try {
    const userId = (req as any).user?.id;
    if (!userId) {
      return res.status(401).json({ error: 'Authentication required' });
    }

    const { status, limit = '20', offset = '0' } = req.query;

    let query = sql`
      SELECT m.*,
        (SELECT COUNT(*) FROM manuscript_versions WHERE manuscript_id = m.id) as version_count
      FROM manuscripts m
      WHERE m.user_id = ${userId}
    `;

    if (status) {
      query = sql`${query} AND m.status = ${status as string}`;
    }

    query = sql`${query} ORDER BY m.updated_at DESC LIMIT ${parseInt(limit as string)} OFFSET ${parseInt(offset as string)}`;

    const result = await db.execute(query);

    res.json({
      manuscripts: result.rows || [],
      pagination: {
        limit: parseInt(limit as string),
        offset: parseInt(offset as string),
        hasMore: (result.rows?.length || 0) === parseInt(limit as string),
      },
    });
  } catch (error: any) {
    console.error('[manuscripts] List error:', error);
    res.status(500).json({ error: 'Failed to list manuscripts' });
  }
});

/**
 * GET /api/manuscripts/:id
 * Get manuscript by ID
 */
router.get('/:id', requireRole('VIEWER'), async (req: Request, res: Response) => {
  try {
    const { id } = req.params;
    const userId = (req as any).user?.id;

    const result = await db.execute(sql`
      SELECT m.*, mv.content, mv.version_number, mv.word_count
      FROM manuscripts m
      LEFT JOIN manuscript_versions mv ON m.current_version_id = mv.id
      WHERE m.id = ${id}
    `);

    if (!result.rows || result.rows.length === 0) {
      return res.status(404).json({ error: 'Manuscript not found' });
    }

    const manuscript = result.rows[0];

    // Get authors
    const authorsResult = await db.execute(sql`
      SELECT * FROM manuscript_authors WHERE manuscript_id = ${id} ORDER BY order_index
    `);

    // Get citation count
    const citationsResult = await db.execute(sql`
      SELECT COUNT(*) as count FROM manuscript_citations WHERE manuscript_id = ${id}
    `);

    res.json({
      ...manuscript,
      authors: authorsResult.rows || [],
      citationCount: parseInt(citationsResult.rows?.[0]?.count || '0'),
    });
  } catch (error: any) {
    console.error('[manuscripts] Get error:', error);
    res.status(500).json({ error: 'Failed to get manuscript' });
  }
});

/**
 * PATCH /api/manuscripts/:id
 * Update manuscript
 */
router.patch('/:id', requireRole('RESEARCHER'), async (req: Request, res: Response) => {
  try {
    const { id } = req.params;
    const userId = (req as any).user?.id;

    const parsed = updateManuscriptSchema.safeParse(req.body);
    if (!parsed.success) {
      return res.status(400).json({ error: 'Invalid input', details: parsed.error.flatten() });
    }

    const updates = parsed.data;
    const updateFields: string[] = [];
    const values: any[] = [];

    if (updates.title) {
      updateFields.push('title = $' + (values.length + 1));
      values.push(updates.title);
    }
    if (updates.status) {
      updateFields.push('status = $' + (values.length + 1));
      values.push(updates.status);
    }
    if (updates.targetJournal !== undefined) {
      updateFields.push('target_journal = $' + (values.length + 1));
      values.push(updates.targetJournal);
    }
    if (updates.metadata) {
      updateFields.push('metadata = $' + (values.length + 1));
      values.push(JSON.stringify(updates.metadata));
    }

    if (updateFields.length === 0) {
      return res.status(400).json({ error: 'No valid fields to update' });
    }

    const updatePayloadForDedupe = JSON.stringify(updates);
    const afterHash = generateContentHash(updatePayloadForDedupe);

    await runWithTransaction(async (tx) => {
      values.push(id);
      const setClause = updateFields.join(', ') + ', updated_at = NOW()';
      await tx.query(
        `UPDATE manuscripts SET ${setClause} WHERE id = $${values.length}`,
        values
      );

      await logManuscriptEventTx(tx, id, 'MANUSCRIPT_UPDATED', userId, {
        status: updates.status,
        target_journal: updates.targetJournal,
      });

      await appendEvent(
        tx,
        {
          stream_type: STREAM_TYPE_MANUSCRIPT,
          stream_key: id,
          actor_type: 'USER',
          actor_id: userId ?? null,
          service: SERVICE_ORCHESTRATOR,
          action: 'UPDATE',
          resource_type: 'manuscript',
          resource_id: id,
          after_hash: afterHash,
          payload: { manuscript_id: id, status: updates.status ?? undefined, target_journal: updates.targetJournal ?? undefined },
          dedupe_key: `manuscript:update:${id}:${generateContentHash(updatePayloadForDedupe).substring(0, 16)}`,
        },
        { hipaaMode: getHipaaMode() }
      );
    });

    const result = await db.execute(sql`SELECT * FROM manuscripts WHERE id = ${id}`);
    res.json(result.rows?.[0] || {});
  } catch (error: any) {
    console.error('[manuscripts] Update error:', error);
    res.status(500).json({ error: 'Failed to update manuscript' });
  }
});

/**
 * GET /api/manuscripts/:id/sections
 * Get manuscript sections
 */
router.get('/:id/sections', requireRole('VIEWER'), async (req: Request, res: Response) => {
  try {
    const { id } = req.params;

    const result = await db.execute(sql`
      SELECT mv.content
      FROM manuscripts m
      JOIN manuscript_versions mv ON m.current_version_id = mv.id
      WHERE m.id = ${id}
    `);

    if (!result.rows || result.rows.length === 0) {
      return res.status(404).json({ error: 'Manuscript not found' });
    }

    const content = result.rows[0].content as any;
    const sections = content?.sections;

    if (!sections && content?.text) {
      return res.json({
        manuscriptId: id,
        sections: [{
          type: content.sectionId || 'body',
          content: content.text || '',
          wordCount: countWords(content.text || ''),
        }],
      });
    }

    res.json({
      manuscriptId: id,
      sections: Object.entries(sections || {}).map(([type, data]: [string, any]) => ({
        type,
        content: data.content || '',
        wordCount: data.wordCount || 0,
      })),
    });
  } catch (error: any) {
    console.error('[manuscripts] Get sections error:', error);
    res.status(500).json({ error: 'Failed to get sections' });
  }
});

/**
 * GET /api/manuscripts/:id/doc
 * Get latest document state
 */
router.get('/:id/doc', requireRole('VIEWER'), async (req: Request, res: Response) => {
  try {
    const { id } = req.params;

    const result = await db.execute(sql`
      SELECT mv.*
      FROM manuscripts m
      JOIN manuscript_versions mv ON m.current_version_id = mv.id
      WHERE m.id = ${id}
    `);

    if (!result.rows || result.rows.length === 0) {
      return res.status(404).json({ error: 'Manuscript not found' });
    }

    res.json(result.rows[0]);
  } catch (error: any) {
    console.error('[manuscripts] Get doc error:', error);
    res.status(500).json({ error: 'Failed to get document' });
  }
});

/**
 * POST /api/manuscripts/:id/doc/save
 * Save document snapshot
 */
router.post('/:id/doc/save', requireRole('RESEARCHER'), async (req: Request, res: Response) => {
  try {
    const { id } = req.params;
    const userId = (req as any).user?.id;

    const parsed = saveDocSchema.safeParse(req.body);
    if (!parsed.success) {
      return res.status(400).json({ error: 'Invalid input', details: parsed.error.flatten() });
    }

    const { sectionId, yjsState, contentText, changeDescription, sections } = parsed.data;
    const resolvedContentText = contentText || serializeSectionsToText(sections);

    if (!resolvedContentText) {
      return res.status(400).json({ error: 'contentText or sections required' });
    }

    // PHI scan in LIVE mode
    if (isLiveMode()) {
      const phiResult = scanForPhi(resolvedContentText);
      if (phiResult.detected) {
        return res.status(400).json({
          error: 'PHI_DETECTED',
          message: 'Content contains PHI. Please remove or redact before saving.',
          locations: phiResult.identifiers.map((id) => ({
            start: id.position.start,
            end: id.position.end,
            type: id.type,
            // NO raw value returned
          })),
        });
      }
    }

    // Get current version info
    const currentResult = await db.execute(sql`
      SELECT mv.version_number, mv.current_hash
      FROM manuscripts m
      JOIN manuscript_versions mv ON m.current_version_id = mv.id
      WHERE m.id = ${id}
    `);

    if (!currentResult.rows || currentResult.rows.length === 0) {
      return res.status(404).json({ error: 'Manuscript not found' });
    }

    const currentVersion = currentResult.rows[0];
    const newVersionNumber = (currentVersion.version_number || 0) + 1;
    const newVersionId = `ver_${nanoid(12)}`;

    const contentPayload = sections
      ? { sections, yjsState: yjsState || null, sectionId: sectionId || null }
      : { text: resolvedContentText, yjsState: yjsState || null, sectionId: sectionId || null };
    const contentHash = generateContentHash(JSON.stringify(contentPayload));
    const wordCount = countWords(resolvedContentText);
    const sectionsCount = sections ? Object.keys(sections).length : undefined;

    await runWithTransaction(async (tx) => {
      await tx.query(
        `INSERT INTO manuscript_versions (id, manuscript_id, version_number, content, data_snapshot_hash, word_count, change_description, previous_hash, current_hash, created_by)
         VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7, $8, $9, $10)`,
        [
          newVersionId,
          id,
          newVersionNumber,
          JSON.stringify(contentPayload),
          contentHash,
          wordCount,
          changeDescription || 'Document saved',
          currentVersion.current_hash,
          contentHash,
          userId,
        ]
      );

      await tx.query(
        `UPDATE manuscripts SET current_version_id = $1, updated_at = NOW() WHERE id = $2`,
        [newVersionId, id]
      );

      await logManuscriptEventTx(tx, id, 'DOCUMENT_SAVED', userId, {
        versionNumber: newVersionNumber,
        wordCount,
        sectionId,
        sectionsCount,
      }, currentVersion.current_hash);

      await appendEvent(
        tx,
        {
          stream_type: STREAM_TYPE_MANUSCRIPT,
          stream_key: id,
          actor_type: 'USER',
          actor_id: userId ?? null,
          service: SERVICE_ORCHESTRATOR,
          action: 'DOC_SAVE',
          resource_type: 'manuscript_version',
          resource_id: newVersionId,
          before_hash: currentVersion.current_hash ?? null,
          after_hash: contentHash,
          payload: { manuscript_id: id, version_id: newVersionId, version_number: newVersionNumber, word_count: wordCount, sections_count: sectionsCount },
          dedupe_key: `manuscript:doc_save:${id}:${newVersionId}`,
        },
        { hipaaMode: getHipaaMode() }
      );
    });

    res.json({
      id: newVersionId,
      manuscriptId: id,
      versionNumber: newVersionNumber,
      wordCount,
      savedAt: new Date().toISOString(),
    });
  } catch (error: any) {
    console.error('[manuscripts] Save doc error:', error);
    res.status(500).json({ error: 'Failed to save document' });
  }
});

/**
 * POST /api/manuscripts/:id/sections/:sectionId/refine
 * Refine section with AI - returns diff, NOT overwrite
 */
router.post('/:id/sections/:sectionId/refine', requireRole('RESEARCHER'), async (req: Request, res: Response) => {
  try {
    const { id, sectionId } = req.params;
    const userId = (req as any).user?.id;

    const parsed = refineSectionSchema.safeParse(req.body);
    if (!parsed.success) {
      return res.status(400).json({ error: 'Invalid input', details: parsed.error.flatten() });
    }

    const { selectedText, instruction, selectionStart, selectionEnd } = parsed.data;

    // PHI gate in LIVE mode
    if (isLiveMode()) {
      const phiResult = scanForPhi(selectedText);
      if (phiResult.detected) {
        const locationsCount = phiResult.identifiers.length;
        await runWithTransaction(async (tx) => {
          await logManuscriptEventTx(tx, id, 'PHI_BLOCKED', userId, {
            action: 'refine',
            sectionId,
            locationsCount,
          });
          await appendEvent(
            tx,
            {
              stream_type: STREAM_TYPE_MANUSCRIPT,
              stream_key: id,
              actor_type: 'USER',
              actor_id: userId ?? null,
              service: SERVICE_ORCHESTRATOR,
              action: 'PHI_BLOCKED',
              resource_type: 'manuscript',
              resource_id: id,
              payload: { manuscript_id: id, section_id: sectionId, action: 'refine', locations_count: locationsCount },
              dedupe_key: `manuscript:refine:phi:${id}:${sectionId}:${generateContentHash(selectedText).substring(0, 16)}`,
            },
            { hipaaMode: getHipaaMode() }
          );
        });

        return res.status(400).json({
          error: 'PHI_DETECTED',
          message: 'Selected text contains PHI. Please remove or redact before AI refinement.',
          locations: phiResult.identifiers.map((id) => ({
            start: id.position.start,
            end: id.position.end,
            type: id.type,
          })),
        });
      }
    }

    // TODO: Integrate with actual AI service
    // For now, return a mock diff structure
    const proposedText = `[AI Refined] ${selectedText}`;
    const inputHash = generateContentHash(selectedText);
    const outputHash = generateContentHash(proposedText);
    const provenanceId = `prov_${nanoid(8)}`;

    await runWithTransaction(async (tx) => {
      await logManuscriptEventTx(tx, id, 'AI_REFINE_REQUESTED', userId, {
        sectionId,
        inputHash,
        outputHash,
        model: 'claude-3-sonnet',
      });
      await appendEvent(
        tx,
        {
          stream_type: STREAM_TYPE_MANUSCRIPT,
          stream_key: id,
          actor_type: 'USER',
          actor_id: userId ?? null,
          service: SERVICE_ORCHESTRATOR,
          action: 'AI_REFINE_REQUESTED',
          resource_type: 'manuscript',
          resource_id: id,
          before_hash: inputHash,
          after_hash: outputHash,
          payload: { manuscript_id: id, section_id: sectionId, input_hash: inputHash, output_hash: outputHash },
          dedupe_key: `manuscript:refine:${id}:${sectionId}:${inputHash.substring(0, 16)}`,
        },
        { hipaaMode: getHipaaMode() }
      );
    });

    // Return diff structure - NOT overwrite
    res.json({
      original: selectedText,
      proposed: proposedText,
      diff: {
        type: 'replacement',
        changes: [
          { operation: 'delete', text: selectedText },
          { operation: 'insert', text: proposedText },
        ],
      },
      selectionStart,
      selectionEnd,
      instruction,
      confidence: 0.85,
      provenanceId,
    });
  } catch (error: any) {
    console.error('[manuscripts] Refine error:', error);
    res.status(500).json({ error: 'Failed to refine section' });
  }
});

/**
 * POST /api/manuscripts/:id/abstract/generate
 * Generate abstract
 */
router.post('/:id/abstract/generate', requireRole('RESEARCHER'), async (req: Request, res: Response) => {
  try {
    const { id } = req.params;
    const userId = (req as any).user?.id;

    const { structured = false, wordLimit = 250 } = req.body;

    // Get manuscript content for context
    const result = await db.execute(sql`
      SELECT mv.content
      FROM manuscripts m
      JOIN manuscript_versions mv ON m.current_version_id = mv.id
      WHERE m.id = ${id}
    `);

    if (!result.rows || result.rows.length === 0) {
      return res.status(404).json({ error: 'Manuscript not found' });
    }

    // TODO: Integrate with abstractGeneratorService
    // For now, return placeholder
    const abstractContent = structured
      ? `**Background**: [Generated background]\n\n**Methods**: [Generated methods]\n\n**Results**: [Generated results]\n\n**Conclusion**: [Generated conclusion]`
      : `[Generated abstract - ${wordLimit} word limit]`;

    const provenanceId = `prov_${nanoid(8)}`;
    await runWithTransaction(async (tx) => {
      await logManuscriptEventTx(tx, id, 'ABSTRACT_GENERATED', userId, {
        structured,
        wordLimit,
        model: 'claude-3-sonnet',
      });
      await appendEvent(
        tx,
        {
          stream_type: STREAM_TYPE_MANUSCRIPT,
          stream_key: id,
          actor_type: 'USER',
          actor_id: userId ?? null,
          service: SERVICE_ORCHESTRATOR,
          action: 'ABSTRACT_GENERATED',
          resource_type: 'manuscript',
          resource_id: id,
          payload: { manuscript_id: id, structured, word_limit: wordLimit },
          dedupe_key: `manuscript:abstract:${id}:${generateContentHash(JSON.stringify({ structured, wordLimit })).substring(0, 16)}`,
        },
        { hipaaMode: getHipaaMode() }
      );
    });

    res.json({
      content: abstractContent,
      wordCount: abstractContent.split(/\s+/).length,
      structured,
      provenanceId,
    });
  } catch (error: any) {
    console.error('[manuscripts] Generate abstract error:', error);
    res.status(500).json({ error: 'Failed to generate abstract' });
  }
});

/**
 * GET /api/manuscripts/:id/events
 * Get provenance/audit log
 */
router.get('/:id/events', requireRole('VIEWER'), async (req: Request, res: Response) => {
  try {
    const { id } = req.params;
    const { limit = '50', offset = '0' } = req.query;

    const result = await db.execute(sql`
      SELECT mal.*, u.email as user_email
      FROM manuscript_audit_log mal
      LEFT JOIN users u ON mal.user_id = u.id
      WHERE mal.manuscript_id = ${id}
      ORDER BY mal.timestamp DESC
      LIMIT ${parseInt(limit as string)} OFFSET ${parseInt(offset as string)}
    `);

    res.json({
      manuscriptId: id,
      events: result.rows || [],
      pagination: {
        limit: parseInt(limit as string),
        offset: parseInt(offset as string),
      },
    });
  } catch (error: any) {
    console.error('[manuscripts] Get events error:', error);
    res.status(500).json({ error: 'Failed to get events' });
  }
});

// =============================================================================
// Phase M3: Comments System
// =============================================================================

const createCommentSchema = z.object({
  sectionId: z.string().uuid().optional(),
  anchorStart: z.number().int().nonnegative().optional(),
  anchorEnd: z.number().int().nonnegative().optional(),
  anchorText: z.string().max(500).optional(),
  body: z.string().min(1).max(5000),
  tag: z.string().max(50).optional(),
  parentId: z.string().uuid().optional(),
});

/**
 * GET /api/manuscripts/:id/comments
 * Get comments for manuscript
 */
router.get('/:id/comments', requireRole('VIEWER'), async (req: Request, res: Response) => {
  try {
    const { id } = req.params;
    const { status, sectionId } = req.query;

    let query = sql`
      SELECT mc.*, u.email as author_email, u.name as author_name
      FROM manuscript_comments mc
      LEFT JOIN users u ON mc.created_by = u.id
      WHERE mc.manuscript_id = ${id}
    `;

    if (status) {
      query = sql`${query} AND mc.status = ${status as string}`;
    }
    if (sectionId) {
      query = sql`${query} AND mc.section_id = ${sectionId as string}`;
    }

    query = sql`${query} ORDER BY mc.created_at ASC`;

    const result = await db.execute(query);

    // Build threaded structure
    const comments = result.rows || [];
    const rootComments = comments.filter((c: any) => !c.parent_id);
    const replies = comments.filter((c: any) => c.parent_id);

    const threaded = rootComments.map((root: any) => ({
      ...root,
      replies: replies.filter((r: any) => r.parent_id === root.id),
    }));

    res.json({
      manuscriptId: id,
      comments: threaded,
      totalCount: comments.length,
    });
  } catch (error: any) {
    console.error('[manuscripts] Get comments error:', error);
    res.status(500).json({ error: 'Failed to get comments' });
  }
});

/**
 * POST /api/manuscripts/:id/comments
 * Add comment to manuscript
 */
router.post('/:id/comments', requireRole('RESEARCHER'), async (req: Request, res: Response) => {
  try {
    const { id } = req.params;
    const userId = (req as any).user?.id;

    if (!userId) {
      return res.status(401).json({ error: 'Authentication required' });
    }

    const parsed = createCommentSchema.safeParse(req.body);
    if (!parsed.success) {
      return res.status(400).json({ error: 'Invalid input', details: parsed.error.flatten() });
    }

    const { sectionId, anchorStart, anchorEnd, anchorText, body, tag, parentId } = parsed.data;
    const commentId = `cmt_${nanoid(12)}`;
    const hasAnchor = !!(anchorStart != null && anchorEnd != null);
    const isReply = !!parentId;

    await runWithTransaction(async (tx) => {
      await tx.query(
        `INSERT INTO manuscript_comments (id, manuscript_id, section_id, anchor_start, anchor_end, anchor_text, body, tag, parent_id, created_by)
         VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)`,
        [commentId, id, sectionId ?? null, anchorStart ?? null, anchorEnd ?? null, anchorText ?? null, body, tag ?? null, parentId ?? null, userId]
      );

      await logManuscriptEventTx(tx, id, 'COMMENT_ADDED', userId, {
        commentId,
        sectionId,
        hasAnchor,
        tag,
        isReply,
      });

      await appendEvent(
        tx,
        {
          stream_type: STREAM_TYPE_MANUSCRIPT,
          stream_key: id,
          actor_type: 'USER',
          actor_id: userId ?? null,
          service: SERVICE_ORCHESTRATOR,
          action: 'COMMENT_ADDED',
          resource_type: 'manuscript_comment',
          resource_id: commentId,
          payload: { manuscript_id: id, comment_id: commentId, section_id: sectionId ?? undefined, has_anchor: hasAnchor, is_reply: isReply },
          dedupe_key: `manuscript:comment:${id}:${commentId}`,
        },
        { hipaaMode: getHipaaMode() }
      );
    });

    const result = await db.execute(sql`
      SELECT mc.*, u.email as author_email, u.name as author_name
      FROM manuscript_comments mc
      LEFT JOIN users u ON mc.created_by = u.id
      WHERE mc.id = ${commentId}
    `);

    res.status(201).json(result.rows?.[0] || { id: commentId });
  } catch (error: any) {
    console.error('[manuscripts] Add comment error:', error);
    res.status(500).json({ error: 'Failed to add comment' });
  }
});

/**
 * POST /api/manuscripts/:id/comments/:commentId/resolve
 * Resolve a comment
 */
router.post('/:id/comments/:commentId/resolve', requireRole('RESEARCHER'), async (req: Request, res: Response) => {
  try {
    const { id, commentId } = req.params;
    const userId = (req as any).user?.id;

    if (!userId) {
      return res.status(401).json({ error: 'Authentication required' });
    }

    let row: any;
    await runWithTransaction(async (tx) => {
      const result = await tx.query(
        `UPDATE manuscript_comments
         SET status = 'resolved', resolved_by = $1, resolved_at = NOW(), updated_at = NOW()
         WHERE id = $2 AND manuscript_id = $3
         RETURNING *`,
        [userId, commentId, id]
      );

      if (!result.rows || result.rows.length === 0) {
        throw new Error('COMMENT_NOT_FOUND');
      }
      row = result.rows[0];

      await logManuscriptEventTx(tx, id, 'COMMENT_RESOLVED', userId, { commentId });

      await appendEvent(
        tx,
        {
          stream_type: STREAM_TYPE_MANUSCRIPT,
          stream_key: id,
          actor_type: 'USER',
          actor_id: userId ?? null,
          service: SERVICE_ORCHESTRATOR,
          action: 'COMMENT_RESOLVED',
          resource_type: 'manuscript_comment',
          resource_id: commentId,
          payload: { manuscript_id: id, comment_id: commentId, status: 'resolved' },
          dedupe_key: `manuscript:comment:resolve:${id}:${commentId}`,
        },
        { hipaaMode: getHipaaMode() }
      );
    });

    res.json(row);
  } catch (error: any) {
    if (error?.message === 'COMMENT_NOT_FOUND') {
      return res.status(404).json({ error: 'Comment not found' });
    }
    console.error('[manuscripts] Resolve comment error:', error);
    res.status(500).json({ error: 'Failed to resolve comment' });
  }
});

/**
 * DELETE /api/manuscripts/:id/comments/:commentId
 * Delete a comment (soft delete - archive)
 */
router.delete('/:id/comments/:commentId', requireRole('RESEARCHER'), async (req: Request, res: Response) => {
  try {
    const { id, commentId } = req.params;
    const userId = (req as any).user?.id;

    await runWithTransaction(async (tx) => {
      const result = await tx.query(
        `UPDATE manuscript_comments
         SET status = 'archived', updated_at = NOW()
         WHERE id = $1 AND manuscript_id = $2 AND created_by = $3
         RETURNING *`,
        [commentId, id, userId]
      );

      if (!result.rows || result.rows.length === 0) {
        throw new Error('COMMENT_NOT_FOUND');
      }

      await logManuscriptEventTx(tx, id, 'COMMENT_DELETED', userId, { commentId });

      await appendEvent(
        tx,
        {
          stream_type: STREAM_TYPE_MANUSCRIPT,
          stream_key: id,
          actor_type: 'USER',
          actor_id: userId ?? null,
          service: SERVICE_ORCHESTRATOR,
          action: 'COMMENT_DELETED',
          resource_type: 'manuscript_comment',
          resource_id: commentId,
          payload: { manuscript_id: id, comment_id: commentId, status: 'archived' },
          dedupe_key: `manuscript:comment:delete:${id}:${commentId}`,
        },
        { hipaaMode: getHipaaMode() }
      );
    });

    res.json({ success: true, id: commentId });
  } catch (error: any) {
    if (error?.message === 'COMMENT_NOT_FOUND') {
      return res.status(404).json({ error: 'Comment not found or not authorized' });
    }
    console.error('[manuscripts] Delete comment error:', error);
    res.status(500).json({ error: 'Failed to delete comment' });
  }
});

export default router;
