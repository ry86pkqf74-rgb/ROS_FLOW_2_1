# Repository Maintenance Guide

Quick reference for keeping the repository clean and healthy.

## Running Quality Checks

```bash
# Type checking
pnpm run typecheck          # or: pnpm run type-check

# Unit tests
pnpm run test:unit

# Both together
pnpm run typecheck && pnpm run test:unit
```

## Branch Pruning

### Local branches
```bash
# List branches already merged into main
git branch --merged main | grep -v "^\*\|main\|master"

# Delete them (review list first!)
git branch --merged main | grep -v "^\*\|main\|master" | xargs git branch -d
```

### Remote branches
```bash
# Prune references to deleted remote branches
git fetch --prune

# ⚠️ Delete remote branch (DANGEROUS - verify first!)
git push origin --delete branch-name
```

**Safety rules:**
- Never force-delete (`-D`) without understanding why
- Verify branch is merged before deletion
- Check with team before deleting shared remote branches
- Keep release branches (`release-*`, `hotfix-*`)

## Minimal Extraction PRs

**Goal:** Avoid massive conflict-prone PRs. Extract clean, focused changes instead.

### Example: PR #31 approach

1. **Create a fresh branch from latest main**
   ```bash
   git checkout main && git pull
   git checkout -b feat/minimal-extraction
   ```

2. **Cherry-pick or manually extract ONLY the needed changes**
   - Don't merge entire branches with conflicts
   - Copy specific files or functions you need
   - Test the extraction works standalone

3. **Open a small, reviewable PR**
   - Clear title describing the ONE thing it does
   - Link to original work if relevant
   - Keep diff under ~500 lines when possible

4. **Merge and iterate**
   - Get it merged quickly (less time = fewer conflicts)
   - Extract next piece in a new PR
   - Repeat until all useful changes are migrated

## Hetzner Full-Stack Deploy (IP-First)

For deploying the complete ResearchFlow stack on Hetzner VPS servers without domain/TLS configuration:

**Current Production Server:**
- **Server:** ROSflow2
- **IP:** 178.156.139.210

**Quick Deploy:**
```bash
# SSH into server
ssh root@178.156.139.210

# Navigate to deployment directory
cd /opt/researchflow/researchflow-production-main

# Pull latest changes
git pull

# Update environment if needed
nano .env

# Restart services with pinned IMAGE_TAG
export IMAGE_TAG=abc1234  # Use specific commit SHA or release tag
docker compose pull && docker compose up -d

# Verify health
./scripts/health-check.sh
```

### Preflight Checks

Before deploying or after updates, run preflight checks to verify system readiness:

```bash
# Run preflight checks (from researchflow-production-main directory)
./scripts/hetzner-preflight.sh

# Expected output: System info, Docker versions, resource checks, health endpoints
# All checks should show ✓ PASS (warnings are acceptable)
```

**What the preflight script checks:**
- Docker and Docker Compose installation and versions
- Available disk space (20GB+ recommended) and memory (4GB+)
- Running container status
- Service health endpoints: `/health` and API routes
- Container image versions (via `docker compose images`)

**Exit codes:**
- `0`: All checks passed (or passed with warnings)
- `1`: Critical failures detected - fix before deploying

For complete setup instructions, firewall configuration, troubleshooting, and health check details:

📖 **[Hetzner Full-Stack Deployment Guide](../researchflow-production-main/docs/deployment/hetzner-fullstack.md)**

This guide covers:
- Server prerequisites and sizing recommendations
- Firewall configuration (ports 22, 80 public; keep 3001 internal)
- Step-by-step deployment using `docker-compose.yml`
- Environment variable configuration from `.env.example`
- Canonical health checks for all services
- Common failure modes and fixes

## Apply edit_sessions Migration (020)

Migration `020_edit_sessions.sql` creates the `edit_sessions` table used by the
Phase 3 human-in-the-loop workflow (draft → submit → approve/reject → merge).

### Quick apply

```bash
# From the orchestrator directory (services/orchestrator/)
DATABASE_URL=postgres://user:pass@host:5432/db node scripts/run-migration-020.mjs

# Or with .env already configured:
cd services/orchestrator && node scripts/run-migration-020.mjs
```

The runner script will:
1. Verify `DATABASE_URL` is set (fails fast with instructions if missing)
2. Test database connectivity (5 s timeout)
3. Apply the migration (idempotent — safe to re-run)
4. Print the resulting column list for verification

### What it creates

| Object | Purpose |
|--------|---------|
| `edit_sessions` table | Stores HITL edit session state |
| CHECK constraint on `status` | Restricts to `draft`, `submitted`, `approved`, `rejected`, `merged` |
| `idx_edit_sessions_manuscript` | Index on `manuscript_id` |
| `idx_edit_sessions_status` | Index on `status` |
| `idx_edit_sessions_branch` | Index on `branch_id` |
| `update_edit_session_updated_at()` | Trigger function — auto-bumps `updated_at` |

### Running tests

```bash
# From repo root (skips automatically when DB unavailable)
DATABASE_URL=postgres://... pnpm vitest run src/__tests__/migrations/020_edit_sessions.test.ts
```
