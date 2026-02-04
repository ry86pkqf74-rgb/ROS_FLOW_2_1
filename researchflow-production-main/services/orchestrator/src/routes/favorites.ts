import { Router, type Request, type Response } from 'express';
import { requirePermission } from '../middleware/rbac';
import { asyncHandler } from '../middleware/asyncHandler';
import {
  addFavorite,
  getUserFavorites,
  removeFavorite,
  FavoriteResourceType,
} from '../services/favoritesService';

const router = Router();

router.get(
  '/',
  requirePermission('READ'),
  asyncHandler(async (req: Request, res: Response) => {
    const user = (req as any).user;
    if (!user) {
      return res.status(401).json({ error: 'AUTHENTICATION_REQUIRED', message: 'Authentication required' });
    }

    const favorites = await getUserFavorites(user.id);
    res.json({ favorites });
  })
);

router.post(
  '/',
  requirePermission('READ'),
  asyncHandler(async (req: Request, res: Response) => {
    const user = (req as any).user;
    if (!user) {
      return res.status(401).json({ error: 'AUTHENTICATION_REQUIRED', message: 'Authentication required' });
    }

    const { resourceType, resourceId } = req.body as { resourceType?: FavoriteResourceType; resourceId?: string };

    if (!resourceType || !resourceId) {
      return res.status(400).json({ error: 'VALIDATION_ERROR', message: 'resourceType and resourceId are required' });
    }

    try {
      const favorite = await addFavorite(user.id, resourceType, resourceId);
      res.status(200).json({ favorite });
    } catch (error: any) {
      if (error?.message === 'INVALID_RESOURCE_TYPE' || error?.message === 'INVALID_RESOURCE_ID') {
        return res.status(400).json({ error: 'VALIDATION_ERROR', message: 'Invalid resourceType or resourceId' });
      }
      throw error;
    }
  })
);

router.delete(
  '/:id',
  requirePermission('READ'),
  asyncHandler(async (req: Request, res: Response) => {
    const user = (req as any).user;
    if (!user) {
      return res.status(401).json({ error: 'AUTHENTICATION_REQUIRED', message: 'Authentication required' });
    }

    try {
      await removeFavorite(user.id, req.params.id);
      res.status(204).send();
    } catch (error: any) {
      if (error?.message === 'FAVORITE_NOT_FOUND') {
        return res.status(404).json({ error: 'NOT_FOUND', message: 'Favorite not found' });
      }
      throw error;
    }
  })
);

export default router;
