import * as Sentry from '@sentry/node';

// IMPORTANT: this module must be imported before any other application code.
Sentry.init({
  dsn:
    process.env.SENTRY_DSN ??
    'https://d53d372ecaca9faa05694f8a0351066b@o4510819008446464.ingest.us.sentry.io/4510819115663360',
  sendDefaultPii: (process.env.SENTRY_SEND_DEFAULT_PII ?? 'true').toLowerCase() === 'true',
  environment: process.env.SENTRY_ENVIRONMENT ?? process.env.NODE_ENV,
  release: process.env.SENTRY_RELEASE,
  integrations: [
    Sentry.expressIntegration(), // v8: replaces Handlers.requestHandler + tracingHandler
  ],
});

export { Sentry };
