# ResearchFlow k6 Load Test Suite

Scenarios, lib, and config for k6 load testing. Requires [k6](https://k6.io/docs/getting-started/installation/) installed.

## Scripts (from repo root)

- `npm run test:load:normal` — 10 VUs, 5 min (workflow)
- `npm run test:load:peak` — 50 VUs, 10 min (workflow)
- `npm run test:load:stress` — 100 VUs, 15 min (workflow)
- `npm run test:load:ai` — 5 VUs, AI endpoints only
- `npm run test:load:spike` — spike: 10 → 100 VUs → ramp down

## Environment

- `BASE_URL` — Orchestrator URL (default `http://localhost:3001`)
- `WORKER_URL` — Worker URL (default `http://localhost:8000`)
- `AUTH_TOKEN` — Optional Bearer token; if unset, lib uses login.
- `LOAD_TEST_EMAIL` / `LOAD_TEST_PASSWORD` — Credentials for login when `AUTH_TOKEN` is not set (default `k6-load@test.local` / `k6-load-password`). In DEMO mode some endpoints may allow unauthenticated access.

## Thresholds

See `thresholds.json`. Custom metrics: `ai_response_time`, `stage_transition_time`, `manuscript_generation_time`. Reports: `reports/report-template.html` and `reports/INFLUX_GRAFANA.md`.
