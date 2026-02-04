# Sentry (Orchestrator)

This service runs in **ESM** mode and uses `tsx` to execute TypeScript.

## 1) Install

```bash
cd services/orchestrator
npm install
```

Dependencies are already included in `package.json`:
- `@sentry/node`
- `@sentry/profiling-node`

## 2) Initialize as early as possible

An instrument module is provided:
- `src/instrument.ts`

It calls `Sentry.init(...)` with the DSN and `sendDefaultPii`.

**You must import it at the very top of your entrypoint** (`src/index.ts`) before any other imports:

- ESM (recommended for this repo):
  - `import './instrument.js';` (preferred if running built JS)
  - or `import './instrument.ts';` (when executing TS directly via `tsx`)

## 3) Error handler ordering (required)

In `src/index.ts`, register Sentry’s error handler:

- after all routes/controllers
- **before** any other error middleware (your current `errorHandler`)

Example:
- `app.use(Sentry.Handlers.errorHandler());`
- then `app.use(errorHandler);`

## 4) Verify

Add a temporary route that throws (e.g. `GET /api/sentry-test`) and confirm the event appears in Sentry.
