# ResearchFlow Deployment Checklist (Summary)

Short checklist for production deployment. Full detail: [docs/DEPLOYMENT_CHECKLIST.md](docs/DEPLOYMENT_CHECKLIST.md).

## Pre-deployment

- [ ] Environment variables set (`.env.production` from `.env.production.template`); see [docs/deployment/env-contract.md](docs/deployment/env-contract.md)
- [ ] PostgreSQL and Redis accessible; SSL certs in place (`infrastructure/docker/nginx/ssl/`, `certs/postgres`, `certs/redis` as needed)
- [ ] Run `docker-compose -f docker-compose.prod.yml config` to validate

## Deployment steps

1. **Pull latest code:** `git pull origin main`
2. **Build and start:** `docker-compose -f docker-compose.prod.yml build` then `docker-compose -f docker-compose.prod.yml up -d`
3. **Verify migrations:** `docker-compose -f docker-compose.prod.yml logs migrate` (expect "Migrations complete")
4. **Run verification:** `./scripts/verify-deployment.sh prod`

## Post-deployment verification

- Run `./scripts/verify-deployment.sh prod`
- Hit health endpoints (orchestrator, web, collab); optional smoke test (login, create project)
- API tests: [scripts/test-api-endpoints.sh](scripts/test-api-endpoints.sh) (e.g. `./scripts/test-api-endpoints.sh https localhost 443`)

## Rollback procedure

```bash
docker-compose -f docker-compose.prod.yml down
# Revert to previous image/tag, then:
docker-compose -f docker-compose.prod.yml up -d
```

For database rollback, see [docs/DEPLOYMENT_CHECKLIST.md](docs/DEPLOYMENT_CHECKLIST.md) and [migrations/README.md](migrations/README.md).
