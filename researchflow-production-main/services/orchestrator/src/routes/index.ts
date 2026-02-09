/**
 * Routes barrel: public API router (mount at /api in app if desired).
 * Internal routes are mounted from ./routes/internal in src/index.ts:
 *   import internalRoutes from './routes/internal';
 *   app.use('/internal', internalRoutes);
 */
import { Router } from 'express';

const router = Router();
export default router;
