/**
 * User Favorites API Routes
 *
 * Endpoints for user favorites/bookmarks (starred resources).
 * GET list, POST add, DELETE remove.
 */

import { sql } from 'drizzle-orm';
import { Router, Request, Response, NextFunction } from 'express';
import { z } from 'zod';

import { db } from '../../db.js';
import { requireRole } from '../middleware/rbac';

function asyncHandler(fn: (req: Request, res: Response, next: NextFunction) => Promise<void>) {
  return (req: Request, res: Response, next: NextFunction) => {
    Promise.resolve(fn(req, res, next)).catch(next);
  };
}

const AddFavoriteSchema = z.object({
  resourceType: z.string().min(1).max(64),
  resourceId: z.string().min(1).max(255),
});

const router = Router();

/**
 * GET /api/favorites
 * List favorites for the authenticated user
 */
router.get(
  '/',
  requireRole('VIEWER'),
  asyncHandler(async (req: Request, res: Response) => {
    if (!db) {
      res.status(503).json({ error: 'Database unavailable' });
      return;
    }
    const userId = req.user?.id;
    if (!userId) {
      res.status(401).json({ error: 'Unauthorized', code: 'AUTH_REQUIRED' });
      return;
    }

    const result = await db.execute(sql`
      SELECT id, user_id, resource_type, resource_id, created_at
      FROM user_favorites
      WHERE user_id = ${userId}
      ORDER BY created_at DESC
    `);

    const favorites = (result.rows || []).map((row: any) => ({
      id: row.id,
      userId: row.user_id,
      resourceType: row.resource_type,
      resourceId: row.resource_id,
      createdAt: row.created_at,
    }));

    res.json({ favorites });
  })
);

/**
 * POST /api/favorites
 * Add a favorite (resourceType, resourceId)
 */
router.post(
  '/',
  requireRole('VIEWER'),
  asyncHandler(async (req: Request, res: Response) => {
    if (!db) {
      res.status(503).json({ error: 'Database unavailable' });
      return;
    }
    const userId = req.user?.id;
    if (!userId) {
      res.status(401).json({ error: 'Unauthorized', code: 'AUTH_REQUIRED' });
      return;
    }

    const parsed = AddFavoriteSchema.safeParse(req.body);
    if (!parsed.success) {
      res.status(400).json({ error: 'Invalid body', details: parsed.error.flatten() });
      return;
    }

    const { resourceType, resourceId } = parsed.data;

    const result = await db.execute(sql`
      INSERT INTO user_favorites (user_id, resource_type, resource_id)
      VALUES (${userId}, ${resourceType}, ${resourceId})
      ON CONFLICT (user_id, resource_type, resource_id) DO UPDATE SET created_at = NOW()
      RETURNING id, user_id, resource_type, resource_id, created_at
    `);

    const row = (result.rows || [])[0] as any;
    if (!row) {
      res.status(500).json({ error: 'Failed to create favorite' });
      return;
    }

    res.status(201).json({
      id: row.id,
      userId: row.user_id,
      resourceType: row.resource_type,
      resourceId: row.resource_id,
      createdAt: row.created_at,
    });
  })
);

/**
 * DELETE /api/favorites/:favoriteId
 * Remove a favorite (only if owned by user)
 */
router.delete(
  '/:favoriteId',
  requireRole('VIEWER'),
  asyncHandler(async (req: Request, res: Response) => {
    if (!db) {
      res.status(503).json({ error: 'Database unavailable' });
      return;
    }
    const userId = req.user?.id;
    if (!userId) {
      res.status(401).json({ error: 'Unauthorized', code: 'AUTH_REQUIRED' });
      return;
    }

    const { favoriteId } = req.params;

    const result = await db.execute(sql`
      DELETE FROM user_favorites
      WHERE id = ${favoriteId} AND user_id = ${userId}
      RETURNING id
    `);

    if (!result.rows || result.rows.length === 0) {
      res.status(404).json({ error: 'Favorite not found' });
      return;
    }

    res.status(204).send();
  })
);

export default router;
