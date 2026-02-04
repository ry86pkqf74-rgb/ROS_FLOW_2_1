# Security Audit: ResearchFlow (researchflow-production)

Scope: static review of repository configuration and API surface using GitHub contents + GitHub code scanning alerts.

## Summary of Key Findings

- GitHub Code Scanning currently reports a large number of open findings across code and IaC (CodeQL + Checkov).
- API surface is large (many mounted `/api/*` routers). Authentication exists for `/api/auth/*`, but per-route auth enforcement must be verified across all routers.
- Orchestrator Dockerfile uses a non-root user (good) but does not pin base image digest; build stage installs build tooling in base stage (can be tightened).
- `.env.example` appears to be a template (no high-confidence secrets detected), but it includes many sensitive-looking variables that require careful rotation/handling.

## 1) Dependency Scan

### Node.js

Root `package.json` direct dependencies (count: 6): `@anthropic-ai/sdk`, `@notionhq/client`, `concurrently`, `date-fns`, `openai`, `serve`

Root `devDependencies` (count: 13): `@playwright/test`, `@types/node`, `@typescript-eslint/eslint-plugin`, `@typescript-eslint/parser`, `@vitest/coverage-v8`, `drizzle-kit`, `eslint`, `eslint-config-prettier`, `eslint-plugin-import`, `prettier`, `tsx`, `typescript`, `vitest`

A `package-lock.json` is present (lockfileVersion 3).

**Recommendation:** run `npm audit --production` (and `npm audit` in CI), triage findings, and use Dependabot / Renovate for continuous updates.

### Python

`requirements.txt` not found at repository root in this snapshot. Python dependency scanning should be run per-service (e.g., `services/*/requirements.txt` or `pyproject.toml`).

**Recommendation:** ensure each Python service has pinned dependencies and integrate `pip-audit` (or `uv pip audit`) in CI.

## 2) Secrets Detection

Heuristic regex scan of `package.json`, `.env.example`, and `docker-compose.yml` did not detect high-confidence secrets (e.g., AWS keys, GitHub tokens, private key blocks).

**Recommendations:**
- Add automated secret scanning (GitHub Advanced Security secret scanning or gitleaks) and enforce on PRs.
- Block committing `.env` files via `.gitignore` and pre-commit hooks.
- Rotate any credentials that have ever been committed historically.

## 3) Docker Security

Reviewed: `services/orchestrator/Dockerfile`. Highlights:

- Uses `node:20-alpine` base image (small footprint).
- Contains a `USER` directive (non-root runtime) (good).
- Base image is not pinned to an immutable digest (recommend pinning).
- Build tooling is installed in the base stage; consider isolating build deps to builder stages and keeping runtime image minimal.

**Recommendations:**
- Pin base images by digest (e.g., `FROM node:20-alpine@sha256:...`).
- Use multi-stage builds to keep production runtime image free of compilers/package managers.
- Add `HEALTHCHECK` where appropriate and set strict file permissions.
- Consider `npm ci --omit=dev` for production stage and remove caches.

## 4) Environment Variables

Reviewed: `.env.example`. No clear real secrets detected; appears to be documentation/template.

**Recommendations:**
- Ensure example values are placeholders (e.g., `CHANGEME`, `example.com`) and do not resemble live endpoints/keys.
- Document which variables are secrets and where they should be stored (e.g., AWS Secrets Manager, Doppler, 1Password, Kubernetes secrets).

## 5) API Security (AuthZ/AuthN, Rate Limiting, Input Validation)

### Endpoint surface
The orchestrator mounts many routers under `/api/*` (dozens). Example mounts include: `/api/auth`, `/api/profile/api-keys`, `/api/projects`, `/api/webhooks`, `/api/ai/*`, etc.

### Authentication implementation signals
- `services/orchestrator/src/routes/auth.ts` defines auth endpoints: `POST /register`, `POST /login`, `POST /refresh`, `POST /logout`, `GET /user`, `GET /status`, etc.
- `services/orchestrator/src/middleware/auth.ts` is explicitly **development-only**: it sets a mock user for `NODE_ENV=development|test`, and returns `401` in production with message “Production authentication not yet implemented”.

**Risk:** If any deployment accidentally runs with `NODE_ENV=development` (or similar misconfig), endpoints may be accessible with a privileged mock user. Additionally, relying on per-router `requireAuth` can lead to accidental unauthenticated endpoints.

**Recommendations:**
- Enforce production auth globally: mount an authentication middleware at `/api` by default and explicitly allow-list public routes (e.g., `/api/auth/login`, health checks).
- Add rate limiting (CodeQL flags `js/missing-rate-limiting`) at least on auth endpoints and expensive AI/analysis endpoints.
- Add request size limits, input validation (zod/joi), and consistent error handling without stack traces in production.
- Ensure CSRF protections if cookies are used; for bearer tokens, ensure CORS is strict and tokens are stored safely.

## GitHub Code Scanning (Snapshot)

The repository currently has **hundreds of code scanning alerts**. Sample top recurring rules include:

- `js/log-injection`
- `js/missing-rate-limiting`
- `js/path-injection`
- `js/request-forgery`
- Checkov Kubernetes rules (e.g., `CKV_K8S_*`) indicating Kubernetes hardening gaps

**Recommendations:** prioritize fixes by exploitability and exposure; start with public-facing endpoints, auth flows, webhooks, and any file/URL handling paths.

## Recommended Next Steps (Prioritized)

1. **P0:** Ensure production auth cannot be bypassed via `NODE_ENV` misconfiguration; remove/guard mock auth middleware for production builds.
2. **P0:** Implement global rate limiting and request validation; address CodeQL findings for request forgery/path injection.
3. **P1:** Run and act on `npm audit` + enable Dependabot alerts; add Python dependency audit in CI where applicable.
4. **P1:** Harden Docker images (digest pinning, minimal runtime, drop capabilities where possible).
5. **P2:** Add continuous secret scanning and enforce pre-commit/CI policies.

---
Generated on 2026-02-02.