# Maintenance and Operations

Short reference for deployment and operational constraints.

## Deployment Readiness Checklist

This repo uses **direct-to-main** workflow (no PRs). Before pushing to `main`, verify all of the following.

### Run DB-backed tests locally

1. **Set DATABASE_URL**  
   Export (or inline) a Postgres connection string:
   ```bash
   export DATABASE_URL=postgres://user:password@localhost:5432/researchflow_dev
   ```
   Or use the ResearchFlow project `.env`:
   ```bash
   set -a && source researchflow-production-main/.env && set +a
   ```

2. **Run migration 020**  
   From the workspace root:
   ```bash
   node researchflow-production-main/services/orchestrator/scripts/run-migration-020.mjs
   ```
   Ensure it reports `✅ Migration 020_edit_sessions applied successfully.`

3. **Run DB-backed test files explicitly**  
   ```bash
   pnpm test src/__tests__/migrations/020_edit_sessions.test.ts
   pnpm test services/orchestrator/src/services/__tests__/edit-session.service.test.ts
   ```
   Both must pass (not skip). If they skip, the DB is unavailable—see below.

### CI expectations

- **CI must include Postgres** (via `docker-compose.yml` or a service container).  
- **CI must run DB-backed tests** without skipping them. If tests skip in CI due to missing `DATABASE_URL`, the build is invalid for release.

See `.github/workflows/ci.yml` for the current setup (Docker Compose with Postgres).

### Direct-to-main policy (this repo)

⚠️ **Warning**: This repository allows (and expects) direct pushes to `main`. There are **no pull requests** and **no branch protection** on `main`.

**Before pushing to `main`, you MUST:**

1. ✅ Set `DATABASE_URL` and confirm Postgres is reachable
2. ✅ Run `node services/orchestrator/scripts/run-migration-020.mjs` (exit 0)
3. ✅ Run DB-backed tests: `pnpm test src/__tests__/migrations/020_edit_sessions.test.ts` and `pnpm test services/orchestrator/src/services/__tests__/edit-session.service.test.ts`
4. ✅ Verify CI is green on your local branch if available
5. ✅ Run any other relevant test suites (`pnpm test:unit`, `pnpm test:integration`)
6. ✅ Ensure Docker images build successfully if touching Dockerfiles
7. ✅ Review deployment workflow changes if modifying `.github/workflows/build-push-deploy-hetzner-fullstack.yml`

**Once pushed to `main`:**
- The Hetzner deployment workflow triggers automatically
- Images are built and pushed to GHCR
- Changes deploy to production immediately

### If DB unavailable

When `DATABASE_URL` is unset or Postgres is unreachable, DB-backed tests **will skip** (not fail).

⚠️ **Skipped tests are NOT acceptable for release validation.**  
If tests skip locally or in CI, the code is not deployment-ready. Fix the database connection before pushing to `main`.

---

## Storage and paths (deployment)

- **ARTIFACTS_PATH** (and aliases `ARTIFACT_PATH`, `RESEARCHFLOW_ARTIFACTS_DIR`) must be **absolute** and under **`/data/*`** (e.g. `/data/artifacts`) in deployment runs. Do not use paths under `/app` or relative paths.
- **Avoid bind-mounting `/app`** on server deployments (e.g. `./services/worker:/app` or `./services/collab:/app`). It overwrites built image contents and can break permissions and artifacts. Use the published GHCR images as-is, with only `/data` (and optionally `/data/projects`) volume-mounted.

See also: [Hetzner Full-Stack Deployment](deployment/hetzner-fullstack.md#persistent-data-storage).

## Collab service (if still misbehaving)

Removing `./services/collab:/app` is the durable fix. If collab still behaves strangely after redeploy, the next step is to remove any volume that can shadow built artifacts—e.g. drop `./packages:/app/packages` and `/app/node_modules` for the collab service in the compose file used on the server so the container runs the image as-is.
