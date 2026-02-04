import { pool } from '../db.js';

export type FavoriteResourceType = 'project' | 'workflow' | 'artifact' | 'paper';

export interface Favorite {
  id: string;
  userId: string;
  resourceType: FavoriteResourceType;
  resourceId: string;
  createdAt: Date;
}

const ALLOWED_TYPES: FavoriteResourceType[] = ['project', 'workflow', 'artifact', 'paper'];

function assertPool() {
  if (!pool) throw new Error('Database pool not initialized');
}

function validateResourceType(resourceType: string): asserts resourceType is FavoriteResourceType {
  if (!ALLOWED_TYPES.includes(resourceType as FavoriteResourceType)) {
    throw new Error('INVALID_RESOURCE_TYPE');
  }
}

export async function getUserFavorites(userId: string): Promise<Favorite[]> {
  assertPool();
  const result = await pool!.query(
    'SELECT id, user_id AS "userId", resource_type AS "resourceType", resource_id AS "resourceId", created_at AS "createdAt" FROM favorites WHERE user_id = $1 ORDER BY created_at DESC',
    [userId]
  );
  return result.rows;
}

export async function addFavorite(userId: string, resourceType: string, resourceId: string): Promise<Favorite> {
  assertPool();
  validateResourceType(resourceType);

  if (!resourceId || !resourceId.trim()) {
    throw new Error('INVALID_RESOURCE_ID');
  }

  const result = await pool!.query(
    `INSERT INTO favorites (user_id, resource_type, resource_id)
     VALUES ($1, $2, $3)
     ON CONFLICT (user_id, resource_type, resource_id)
     DO UPDATE SET user_id = EXCLUDED.user_id
     RETURNING id, user_id AS "userId", resource_type AS "resourceType", resource_id AS "resourceId", created_at AS "createdAt"`,
    [userId, resourceType, resourceId]
  );

  return result.rows[0];
}

export async function removeFavorite(userId: string, favoriteId: string): Promise<void> {
  assertPool();
  const result = await pool!.query('DELETE FROM favorites WHERE id = $1 AND user_id = $2', [favoriteId, userId]);
  if (result.rowCount === 0) {
    const err = new Error('FAVORITE_NOT_FOUND');
    (err as any).statusCode = 404;
    throw err;
  }
}
