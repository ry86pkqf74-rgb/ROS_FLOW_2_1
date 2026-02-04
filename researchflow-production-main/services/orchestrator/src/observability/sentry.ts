import * as Sentry from '@sentry/node';
import { nodeProfilingIntegration } from '@sentry/profiling-node';
import type { Express } from 'express';

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
 * Initializes Sentry and returns the Express error handler.
 *
 * IMPORTANT: You must register the returned `errorHandler` AFTER all routes.
 */
export function initSentry(app: Express, opts: SentryInitOptions = {}) {
  const dsn = opts.dsn ?? process.env.SENTRY_DSN;
  const enabled = opts.enabled ?? envBool(process.env.SENTRY_ENABLED, Boolean(dsn));

  if (!enabled) {
    return {
      enabled: false,
      requestHandler: (req: any, res: any, next: any) => next(),
      errorHandler: (err: any, req: any, res: any, next: any) => next(err),
    };
  }

  Sentry.init({
    dsn,
    environment: opts.environment ?? process.env.SENTRY_ENVIRONMENT ?? process.env.NODE_ENV,
    release: opts.release ?? process.env.SENTRY_RELEASE,
    serverName: opts.serverName ?? process.env.SENTRY_SERVER_NAME,
    integrations: [nodeProfilingIntegration()],
    tracesSampleRate: opts.tracesSampleRate ?? envNumber(process.env.SENTRY_TRACES_SAMPLE_RATE, 0.1),
    profilesSampleRate: opts.profilesSampleRate ?? envNumber(process.env.SENTRY_PROFILES_SAMPLE_RATE, 0.0),
  });

  const requestHandler = Sentry.Handlers.requestHandler();
  const tracingHandler = Sentry.Handlers.tracingHandler();

  // Ensure Sentry request context is registered early.
  app.use(requestHandler);
  app.use(tracingHandler);

  const errorHandler = Sentry.Handlers.errorHandler();

  return { enabled: true, requestHandler, errorHandler };
}
