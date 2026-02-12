import * as Sentry from '@sentry/node';
import { nodeProfilingIntegration } from '@sentry/profiling-node';
import type { Express, ErrorRequestHandler, RequestHandler } from 'express';

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
 * Initializes Sentry and registers the Express error handler.
 *
 * Sentry v8 migration notes:
 * - Sentry.Handlers.requestHandler() / tracingHandler() → automatic via
 *   Sentry.init() integrations (expressIntegration handles both).
 * - Sentry.Handlers.errorHandler() → Sentry.setupExpressErrorHandler(app).
 *
 * IMPORTANT: Call `setupExpressErrorHandler` AFTER all routes but BEFORE
 * other error-handling middleware.
 */
export function initSentry(app: Express, opts: SentryInitOptions = {}) {
  const dsn = opts.dsn ?? process.env.SENTRY_DSN;
  const enabled = opts.enabled ?? envBool(process.env.SENTRY_ENABLED, Boolean(dsn));

  const noopRequestHandler: RequestHandler = (_req, _res, next) => next();
  const noopErrorHandler: ErrorRequestHandler = (err, _req, _res, next) => next(err);

  if (!enabled) {
    return {
      enabled: false,
      requestHandler: noopRequestHandler,
      errorHandler: noopErrorHandler,
    };
  }

  Sentry.init({
    dsn,
    environment: opts.environment ?? process.env.SENTRY_ENVIRONMENT ?? process.env.NODE_ENV,
    release: opts.release ?? process.env.SENTRY_RELEASE,
    serverName: opts.serverName ?? process.env.SENTRY_SERVER_NAME,
    integrations: [
      nodeProfilingIntegration(),
      Sentry.expressIntegration(),   // replaces requestHandler + tracingHandler
    ],
    tracesSampleRate: opts.tracesSampleRate ?? envNumber(process.env.SENTRY_TRACES_SAMPLE_RATE, 0.1),
    profilesSampleRate: opts.profilesSampleRate ?? envNumber(process.env.SENTRY_PROFILES_SAMPLE_RATE, 0.0),
  });

  // In v8 the error handler is registered directly on the app.
  // It must be called AFTER all routes are defined.
  // We wrap it so callers can still call errorHandler() at the right time.
  const errorHandler: ErrorRequestHandler = (err, req, res, next) => {
    // setupExpressErrorHandler already registers itself, but we also
    // forward to Sentry.captureException for explicit control.
    Sentry.captureException(err);
    next(err);
  };

  // Register Sentry's Express error handler on the app
  Sentry.setupExpressErrorHandler(app);

  return { enabled: true, requestHandler: noopRequestHandler, errorHandler };
}
