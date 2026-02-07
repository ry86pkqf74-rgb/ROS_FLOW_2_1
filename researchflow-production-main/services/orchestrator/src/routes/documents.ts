/**
 * Documents API Routes
 *
 * Exposes document-like artifacts (manuscript, conference_abstract, conference_poster,
 * conference_slides) as /api/documents. Uses artifacts table (migration 001 schema).
 *
 * API namespace: /api/documents
 *
 * Endpoints:
 * - GET    /           # List current user's documents
 * - GET    /:id        # Get document by id
 * - POST   /:id/export # DOCX export (body: { format?: "docx" })
 *
 * @module routes/documents
 */

import { sql } from 'drizzle-orm';
import { Router, Request, Response } from 'express';

import { db } from '../../db';
import { config } from '../config/env';

const router = Router();

/** Build content payload { title, sections } from artifact row for DOCX generation. */
function buildExportContent(artifact: {
  name?: string | null;
  description?: string | null;
  metadata?: Record<string, unknown> | null;
}): { title: string; sections: Array<{ heading: string; paragraphs?: string[]; bullets?: string[]; table?: string[][] }> } {
  const meta = (artifact.metadata as Record<string, unknown>) || {};
  const title =
    (typeof meta.title === 'string' ? meta.title : null) ||
    (artifact.name && String(artifact.name).trim()) ||
    'Untitled';
  const sections = meta.sections as Array<{ heading?: string; paragraphs?: string[]; bullets?: string[]; table?: string[][] }> | undefined;
  if (Array.isArray(sections) && sections.length > 0) {
    return {
      title,
      sections: sections.map((sec) => ({
        heading: (sec?.heading && String(sec.heading)) || 'Section',
        paragraphs: Array.isArray(sec.paragraphs) ? sec.paragraphs.map(String) : undefined,
        bullets: Array.isArray(sec.bullets) ? sec.bullets.map(String) : undefined,
        table: Array.isArray(sec.table) ? sec.table.map((r) => (Array.isArray(r) ? r.map(String) : [])) : undefined,
      })),
    };
  }
  const contentMarkdown = typeof meta.contentMarkdown === 'string' ? meta.contentMarkdown : null;
  const content = typeof meta.content === 'string' ? meta.content : null;
  const text = contentMarkdown || content || (artifact.description && String(artifact.description).trim()) || 'No content available.';
  return {
    title,
    sections: [{ heading: 'Content', paragraphs: [text] }],
  };
}

function getUserId(req: Request): string | null {
  return (req as any).user?.id ?? null;
}

/**
 * GET /api/documents
 * List documents (artifacts with document-like type) for the authenticated user.
 */
router.get('/', async (req: Request, res: Response) => {
  try {
    const userId = getUserId(req);
    if (!userId) {
      return res.status(401).json({
        error: 'Unauthorized',
        code: 'AUTH_REQUIRED',
        message: 'Authentication required',
      });
    }

    if (!db) {
      return res.status(503).json({ error: 'Database not available' });
    }

    const result = await db.execute(sql`
      SELECT id, type, name, description, status, metadata, created_at, updated_at
      FROM artifacts
      WHERE owner_user_id = ${userId}
        AND type IN ('manuscript', 'conference_abstract', 'conference_poster', 'conference_slides')
        AND deleted_at IS NULL
      ORDER BY updated_at DESC NULLS LAST, created_at DESC
    `);

    res.json(result.rows);
  } catch (error) {
    console.error('[documents/list] Error:', error);
    res.status(500).json({ error: 'Failed to list documents' });
  }
});

/**
 * POST /api/documents/:id/export
 * Export document as DOCX. Body: { format?: "docx" }. Calls worker to generate, returns file download.
 * Defined before GET /:id so /:id/export is matched correctly.
 */
router.post('/:id/export', async (req: Request, res: Response) => {
  try {
    const userId = getUserId(req);
    if (!userId) {
      return res.status(401).json({
        error: 'Unauthorized',
        code: 'AUTH_REQUIRED',
        message: 'Authentication required',
      });
    }

    const { id } = req.params;
    if (!id) {
      return res.status(400).json({ error: 'Document id is required' });
    }

    const format = (req.body?.format as string) || 'docx';
    if (format !== 'docx') {
      return res.status(400).json({ error: 'Unsupported format', supported: ['docx'] });
    }

    if (!db) {
      return res.status(503).json({ error: 'Database not available' });
    }

    const result = await db.execute(sql`
      SELECT id, name, description, metadata
      FROM artifacts
      WHERE id = ${id}::uuid
        AND owner_user_id = ${userId}
        AND type IN ('manuscript', 'conference_abstract', 'conference_poster', 'conference_slides')
        AND deleted_at IS NULL
    `);

    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Document not found' });
    }

    const artifact = result.rows[0] as { id: string; name?: string | null; description?: string | null; metadata?: Record<string, unknown> | null };
    const content = buildExportContent(artifact);
    const workerUrl = config.workerUrl;
    const workerResponse = await fetch(`${workerUrl}/api/ros/documents/export`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content }),
    });

    if (!workerResponse.ok) {
      const errText = await workerResponse.text();
      console.error('[documents/export] Worker error:', workerResponse.status, errText);
      return res.status(502).json({
        error: 'Export failed',
        message: 'Worker could not generate DOCX',
      });
    }

    const buffer = Buffer.from(await workerResponse.arrayBuffer());
    const safeName = (content.title || 'document').replace(/[^a-zA-Z0-9\s-_]/g, '').replace(/\s+/g, '_').slice(0, 50) || 'document';
    const filename = `${safeName}.docx`;
    res.setHeader('Content-Type', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document');
    res.setHeader('Content-Disposition', `attachment; filename="${filename}"`);
    res.send(buffer);
  } catch (error) {
    console.error('[documents/export] Error:', error);
    res.status(500).json({ error: 'Failed to export document' });
  }
});

/**
 * GET /api/documents/:id
 * Get a single document by id (must be owned by the authenticated user).
 */
router.get('/:id', async (req: Request, res: Response) => {
  try {
    const userId = getUserId(req);
    if (!userId) {
      return res.status(401).json({
        error: 'Unauthorized',
        code: 'AUTH_REQUIRED',
        message: 'Authentication required',
      });
    }

    const { id } = req.params;
    if (!id) {
      return res.status(400).json({ error: 'Document id is required' });
    }

    if (!db) {
      return res.status(503).json({ error: 'Database not available' });
    }

    const result = await db.execute(sql`
      SELECT id, type, name, description, status, metadata, created_at, updated_at
      FROM artifacts
      WHERE id = ${id}::uuid
        AND owner_user_id = ${userId}
        AND type IN ('manuscript', 'conference_abstract', 'conference_poster', 'conference_slides')
        AND deleted_at IS NULL
    `);

    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Document not found' });
    }

    res.json(result.rows[0]);
  } catch (error) {
    console.error('[documents/get] Error:', error);
    res.status(500).json({ error: 'Failed to get document' });
  }
});

export default router;
