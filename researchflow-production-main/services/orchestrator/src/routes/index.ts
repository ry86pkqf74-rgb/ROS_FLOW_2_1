/**
 * Routes barrel: re-exports internal router for mounting at /internal.
 * Mount in app with: app.use('/internal', internalRoutes) in src/index.ts.
 */
import internalRoutes from './internal';

export default internalRoutes;
