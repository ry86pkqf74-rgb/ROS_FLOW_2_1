import { Router } from 'express';
import { Pool } from 'pg';
import { NotificationService } from '../collaboration/notification-service';
import { pool } from '../../db';

function parseIntParam(v: any, fallback: number) {
  const n = Number.parseInt(String(v ?? ''), 10);
  return Number.isFinite(n) ? n : fallback;
}

function requireUserId(req: any): string {
  // NOTE: This project likely has auth middleware setting req.user.
  // We support a few common shapes and fallback to header for development/testing.
  const fromUser = req.user?.id ?? req.userId;
  const fromHeader = req.header('x-user-id');
  const userId = fromUser ?? fromHeader;

  if (!userId) {
    const err: any = new Error('Unauthorized');
    err.status = 401;
    throw err;
  }

  return String(userId);
}

export function createNotificationsRouter(opts: { pool: Pool }) {
  const router = Router();
  const service = new NotificationService({ pool: opts.pool });

  // GET /api/notifications?limit=20&offset=0
  router.get('/', async (req, res, next) => {
    try {
      const userId = requireUserId(req);
      const limit = parseIntParam(req.query.limit, 20);
      const offset = parseIntParam(req.query.offset, 0);

      const items = await service.listNotifications(userId, { limit, offset });
      res.json({ items, limit: Math.max(1, Math.min(100, limit)), offset });
    } catch (e) {
      next(e);
    }
  });

  // GET /api/notifications/unread-count
  router.get('/unread-count', async (req, res, next) => {
    try {
      const userId = requireUserId(req);
      const count = await service.getUnreadCount(userId);
      res.json({ count });
    } catch (e) {
      next(e);
    }
  });

  // POST /api/notifications/:id/read
  router.post('/:id/read', async (req, res, next) => {
    try {
      const userId = requireUserId(req);
      const id = String(req.params.id);
      const ok = await service.markRead(userId, id);
      res.json({ ok });
    } catch (e) {
      next(e);
    }
  });

  // POST /api/notifications/read-all
  router.post('/read-all', async (req, res, next) => {
    try {
      const userId = requireUserId(req);
      const updated = await service.markAllRead(userId);
      res.json({ updated });
    } catch (e) {
      next(e);
    }
  });

  // GET /api/notifications/preferences
  router.get('/preferences', async (req, res, next) => {
    try {
      const userId = requireUserId(req);
      const prefs = await service.getPreferences(userId);
      res.json({ preferences: prefs });
    } catch (e) {
      next(e);
    }
  });

  // PUT /api/notifications/preferences
  router.put('/preferences', async (req, res, next) => {
    try {
      const userId = requireUserId(req);
      const patch = req.body ?? {};

      const prefs = await service.updatePreferences(userId, {
        email_digest: typeof patch.email_digest === 'boolean' ? patch.email_digest : undefined,
        slack_mentions: typeof patch.slack_mentions === 'boolean' ? patch.slack_mentions : undefined,
        in_app: typeof patch.in_app === 'boolean' ? patch.in_app : undefined,
        digest_frequency: typeof patch.digest_frequency === 'string' ? patch.digest_frequency : undefined,
      });

      res.json({ preferences: prefs });
    } catch (e) {
      next(e);
    }
  });

  return router;
}

// Default export for use in index.ts route registration
// Falls back to a no-op router if pool is not available (test environments)
const notificationsRouter = pool
  ? createNotificationsRouter({ pool })
  : Router();

export default notificationsRouter;
