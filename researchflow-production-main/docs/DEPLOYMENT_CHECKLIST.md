# Deployment Checklist

## Pre-deployment checks
- [ ] `pnpm install` succeeds at repo root
- [ ] Unit/integration tests pass (as applicable)
- [ ] Docker images build successfully:
  - [ ] `services/orchestrator`
  - [ ] `services/web`
  - [ ] `services/worker`
- [ ] Database migrations reviewed and ready (if deploying new schema)

## Required environment variables (high-level)

### Orchestrator / API
- `NODE_ENV` (e.g. `production`)
- Database connection (one of):
  - `DATABASE_URL` (preferred)
  - or individual host/port/user/pass vars if used by the service
- Auth / security:
  - `JWT_SECRET` (or equivalent)

### Web
- `VITE_API_BASE_URL` / `VITE_API_URL` (as used by the Dockerfile/build)
- `VITE_WS_URL` (if websockets are used)

### Worker
- `PYTHONPATH` is set in Dockerfile; additionally ensure:
  - Provider keys (as needed): `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, etc.

## Docker build commands
```bash
# build everything (minimal)
docker compose -f docker-compose.minimal.yml build

# build a single service
docker compose -f docker-compose.minimal.yml build worker
```

## Deploy / run
```bash
# start
docker compose -f docker-compose.minimal.yml up -d

# follow logs
docker compose -f docker-compose.minimal.yml logs -f worker
```

## Health check verification
```bash
curl -f http://localhost:3001/health
curl -f http://localhost/health
curl -f http://localhost:8000/health
```

## Post-deployment verification
- [ ] Confirm containers are healthy (`docker ps` / compose status)
- [ ] Confirm API endpoints respond (smoke tests)
- [ ] Confirm worker can process a minimal job (if applicable)
