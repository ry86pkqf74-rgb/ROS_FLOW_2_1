# Docker Stack Launch Checklist

**Scope**: Web UI + Orchestrator + Worker + Collab

## Prerequisites
- Docker + Docker Compose installed
- `.env` populated (see `.env.example`)
- Ports available: 5173, 3001, 8000, 1234, 1235

## Launch
```bash
docker compose up -d
```

## Verify Health
```bash
# Quick verification script
./scripts/verify-docker-web-launch.sh
```

Manual checks:
```bash
curl http://localhost:5173/health
curl http://localhost:3001/health
curl http://localhost:3001/api/health
curl http://localhost:8000/health
curl http://localhost:1235/health
```

## Expected URLs
- Web UI: http://localhost:5173
- Orchestrator API: http://localhost:3001
- Worker API: http://localhost:8000
- Collab WebSocket: ws://localhost:1234
- Collab health: http://localhost:1235/health

## Troubleshooting
- If web loads but API calls fail, confirm `VITE_API_BASE_URL` and `VITE_API_URL`
  in `docker-compose.yml` build args.
- If orchestrator is unhealthy, check logs:
  ```bash
  docker compose logs -f orchestrator
  ```
- If worker is unhealthy, check logs:
  ```bash
  docker compose logs -f worker
  ```
- If collab is unhealthy, check logs:
  ```bash
  docker compose logs -f collab
  ```
