import * as Sentry from '@sentry/node';
import { nodeProfilingIntegration } from '@sentry/profiling-node';
import type { Express, RequestHandler } from 'express';

export type SentryInitOptions = {
  dsn?: string;
  environment?: string;
  release?: string;
  tracesSampleRate?: number;
  profilesSampleRate?: number;
  enabled?: boolean;
  serverName?: string;
};

function envNumber(v: string | undefined, fallback: number): number {
  if (!v) return fallback;
  const n = Number(v);
  return Number.isFinite(n) ? n : fallback;
}

function envBool(v: string | undefined, fallback: boolean): boolean {
  if (!v) return fallback;
  const s = v.toLowerCase().trim();
  if (['1', 'true', 'yes', 'y', 'on'].includes(s)) return true;
  if (['0', 'false', 'no', 'n', 'off'].includes(s)) return false;
  return fallback;
}

/**
 * Initializes Sentry for Express.
 *
 * Sentry v8 migration notes:
 * - Sentry.Handlers.requestHandler() / tracingHandler() → automatic via
 *   Sentry.init() integrations (expressIntegration handles both).
 *   NOTE: expressIntegration() is registered in instrument.ts (the early
 *   init path). If using this function as the sole init path, add
 *   Sentry.expressIntegration() to the integrations array below.
 * - Sentry.Handlers.errorHandler() → Sentry.setupExpressErrorHandler(app).
 *
 * IMPORTANT: Call the returned `setupErrorHandler(app)` AFTER all routes
 * but BEFORE other error-handling middleware.
 */
export function initSentry(_app: Express, opts: SentryInitOptions = {}) {
  const dsn = opts.dsn ?? process.env.SENTRY_DSN;
  const enabled = opts.enabled ?? envBool(process.env.SENTRY_ENABLED, Boolean(dsn));

  const noopRequestHandler: RequestHandler = (_req, _res, next) => next();
  const noopSetup = (_a: Express) => { /* noop */ };

  if (!enabled) {
    return {
      enabled: false,
      requestHandler: noopRequestHandler,
      setupErrorHandler: noopSetup,
    };
  }

  Sentry.init({
    dsn,
    environment: opts.environment ?? process.env.SENTRY_ENVIRONMENT ?? process.env.NODE_ENV,
    release: opts.release ?? process.env.SENTRY_RELEASE,
    serverName: opts.serverName ?? process.env.SENTRY_SERVER_NAME,
    integrations: [
      nodeProfilingIntegration(),
    ],
    tracesSampleRate: opts.tracesSampleRate ?? envNumber(process.env.SENTRY_TRACES_SAMPLE_RATE, 0.1),
    profilesSampleRate: opts.profilesSampleRate ?? envNumber(process.env.SENTRY_PROFILES_SAMPLE_RATE, 0.0),
  });

  return {
    enabled: true,
    requestHandler: noopRequestHandler,
    /**
     * Register Sentry's Express error handler on the app.
     * Must be called AFTER all routes but BEFORE other error middleware.
     */
    setupErrorHandler: (appInstance: Express) => {
      Sentry.setupExpressErrorHandler(appInstance);
    },
  };
}
