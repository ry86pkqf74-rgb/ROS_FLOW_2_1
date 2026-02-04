// IMPORTANT: initialize Sentry before any other imports
import './instrument.ts';

import * as Sentry from '@sentry/node';

// Re-export the existing entrypoint after instrumentation.
// NOTE: Because the current index.ts is large and generated, we keep wiring minimal here.
import './index.ts';

// If the main index.ts already created an Express app and started listening,
// we cannot safely inject middleware from here.
//
// This file exists to support a clean migration path:
// - Update the service start command to run `src/index.sentry.ts`
// - Then move app creation here so we can register:
//     app.get('/api/sentry-test', ...)
//     app.use(Sentry.Handlers.errorHandler())
//
// For now we provide a direct capture test when the process starts (optional).
if ((process.env.SENTRY_STARTUP_SMOKE_TEST ?? 'false').toLowerCase() === 'true') {
  try {
    // eslint-disable-next-line @typescript-eslint/no-unsafe-call
    (globalThis as any).___sentry_smoke_test___();
  } catch (e) {
    Sentry.captureException(e);
  }
}
