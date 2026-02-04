# ResearchFlow Deployment Fix Summary

**Date**: January 30, 2026
**Status**: Ready for Deployment Testing

## Critical Issues Fixed

### 1. Environment Configuration Port Mismatches (FIXED)

**Problem**: The `.env` file had port configurations that didn't match `docker-compose.yml`.

**Original (Broken)**:
```env
ORCHESTRATOR_PORT=3000
WORKER_PORT=3001
VITE_API_URL=http://localhost:3000/api
VITE_COLLAB_URL=http://localhost:3002
```

**Fixed**:
```env
ORCHESTRATOR_PORT=3001
WORKER_PORT=8000
COLLAB_PORT=1234
VITE_API_BASE_URL=http://localhost:3001
VITE_API_URL=http://localhost:3001
VITE_WS_URL=ws://localhost:1234
VITE_COLLAB_URL=ws://localhost:1234
```

### 2. Orchestrator Build Script Inconsistency (FIXED)

**Problem**: `package.json` `start` script referenced `dist/index.js` but production uses tsx runtime.

**Original**:
```json
"start": "node dist/index.js"
```

**Fixed**:
```json
"start": "npx tsx index.ts"
```

### 3. TypeScript AI Agents Not Wired to AI Providers (FIXED)

**Problem**: All 4 TypeScript agents returned placeholder data instead of making real AI calls.

**Files Updated**:
- `packages/ai-agents/src/agents/ConferenceScoutAgent.ts`
- `packages/ai-agents/src/agents/DataExtractionAgent.ts`
- `packages/ai-agents/src/agents/StatisticalAnalysisAgent.ts`
- `packages/ai-agents/src/agents/ManuscriptDraftingAgent.ts`

**Solution**: Integrated with Claude provider from `@researchflow/ai-router`:
```typescript
import { getClaudeProvider, type ClaudeRequestOptions } from '@researchflow/ai-router';

// Now makes real AI calls with error handling and cost tracking
const result = await claudeProvider.complete(prompt, {
  taskType: 'agent-type',
  maxTokens: 2048,
  temperature: 0.3,
});
```

### 4. Missing ai-router Dependency in ai-agents Package (FIXED)

**Problem**: `packages/ai-agents/package.json` didn't include `@researchflow/ai-router` dependency.

**Fixed**:
```json
"dependencies": {
  "@researchflow/ai-router": "workspace:*",
  // ... other deps
}
```

## Service Architecture Summary

| Service | Port | Health Check |
|---------|------|--------------|
| Web (Nginx) | 5173:80 | `/health` |
| Orchestrator (Node.js) | 3001 | `/health`, `/api/health` |
| Worker (Python FastAPI) | 8000 | `/health` |
| Collab (WebSocket) | 1234, 1235 | `:1235/health` |
| PostgreSQL | 5432 | `pg_isready` |
| Redis | 6379 | `redis-cli ping` |
| Guideline Engine | 8001 | `/health` |

## Deployment Commands

### Development
```bash
docker-compose up -d
```

### Production
```bash
docker-compose -f docker-compose.prod.yml up -d
```

### With AI Services
```bash
docker-compose -f docker-compose.yml -f docker-compose.ai.yml up -d
```

### Health Check Verification
```bash
# Check all services
curl http://localhost:5173/health      # Web
curl http://localhost:3001/health      # Orchestrator
curl http://localhost:8000/health      # Worker
curl http://localhost:1235/health      # Collab
curl http://localhost:8001/health      # Guideline Engine
```

### Full Readiness Check
```bash
curl http://localhost:3001/health/ready
```

## Required Environment Variables

Ensure these are set before deployment:

```env
# Database
POSTGRES_USER=ros
POSTGRES_PASSWORD=your_password
POSTGRES_DB=ros

# Redis
REDIS_PASSWORD=your_redis_password

# AI Providers (at least one required for AI features)
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key

# LangSmith (optional but recommended for tracing)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=researchflow-production
LANGCHAIN_API_KEY=your_langsmith_key

# Composio (optional for agent integrations)
COMPOSIO_API_KEY=your_composio_key
```

## Verification Checklist

- [ ] Docker daemon is running
- [ ] All required environment variables are set
- [ ] PostgreSQL container starts and migrations complete
- [ ] Redis container is healthy
- [ ] Orchestrator health check passes
- [ ] Worker health check passes
- [ ] Web container serves frontend
- [ ] API requests from web reach orchestrator (`/api/*` proxy works)
- [ ] WebSocket connections work for collaboration
- [ ] AI agent endpoints respond with real AI-generated content

## Next Steps

1. **Run Local Deployment Test**:
   ```bash
   cd /path/to/researchflow-production
   docker-compose up -d
   docker-compose ps
   docker-compose logs -f
   ```

2. **Verify Services**:
   - Open http://localhost:5173 in browser
   - Check network tab for API calls to `/api/*`
   - Test login/authentication flow
   - Test project creation
   - Test AI agent functionality

3. **Monitor Logs**:
   ```bash
   docker-compose logs -f orchestrator
   docker-compose logs -f worker
   ```

## Files Changed

1. `.env` - Port configurations fixed, NODE_ENV set to development
2. `services/orchestrator/package.json` - Start script aligned
3. `packages/ai-agents/package.json` - Added ai-router dependency
4. `packages/ai-agents/src/agents/ConferenceScoutAgent.ts` - AI integration
5. `packages/ai-agents/src/agents/DataExtractionAgent.ts` - AI integration
6. `packages/ai-agents/src/agents/StatisticalAnalysisAgent.ts` - AI integration
7. `packages/ai-agents/src/agents/ManuscriptDraftingAgent.ts` - AI integration
8. `services/orchestrator/src/routes/projects.ts` - Fixed database table name (research_projects), pool import
9. `services/web/src/stores/project-store.ts` - Added api client with auth headers for all API calls

## Additional Fixes (January 30, 2026 - Session 2)

### 5. Frontend Auth Timing Issue (FIXED)

**Problem**: The `project-store.ts` was using raw `fetch()` calls without authentication headers, causing 401 errors on the Projects page.

**Solution**: Updated all fetch calls to use the `api` client from `@/api/client.ts` which automatically includes the Bearer token from localStorage.

**Changes**:
```typescript
// Before (broken):
const response = await fetch('/api/projects');

// After (fixed):
import { api } from '@/api/client';
const result = await api.get<{ projects: Project[] }>('/api/projects');
```

### 6. Database Table Name Mismatch in Stats Endpoint (FIXED)

**Problem**: The `/api/projects/stats` endpoint used wrong table name `projects` instead of `research_projects`.

**Solution**: Updated SQL query to use correct table name:
```sql
-- Before:
FROM projects p
LEFT JOIN project_members pm ON p.id = pm.project_id

-- After:
FROM research_projects p
WHERE p.owner_id = $1
```

## Quick Test Commands (Run on Your Machine)

After pulling these changes, run:

```bash
# Navigate to project directory
cd /path/to/researchflow-production

# Rebuild all containers to pick up code changes
docker-compose down
docker-compose build --no-cache orchestrator web
docker-compose up -d

# Check all services are running
docker-compose ps

# Test health endpoints
curl http://localhost:3001/health   # Orchestrator
curl http://localhost:8000/health   # Worker (if built)
curl http://localhost:5173/health   # Web

# Test login and projects API
# First, register/login to get a token:
curl -X POST http://localhost:3001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test-deployment@researchflow.dev","password":"TestPass123!"}'

# Then test projects endpoint with the returned token:
curl -H "Authorization: Bearer <your-token>" \
  http://localhost:3001/api/projects
```

## Updated Files List (Complete)

| File | Change |
|------|--------|
| `.env` | Port configurations, NODE_ENV=development |
| `services/orchestrator/package.json` | Start script → `npx tsx index.ts` |
| `services/orchestrator/src/routes/projects.ts` | Fixed table name, pool import, stats query |
| `services/web/src/stores/project-store.ts` | Added api client with auth headers |
| `packages/ai-agents/package.json` | Added ai-router dependency |
| `packages/ai-agents/src/agents/*.ts` | Integrated real Claude AI provider |
