# Docker Status

## Current status
- Workspace (pnpm) install: **PASS**
- Docker builds: **EXPECTED PASS** (per recent fixes; verify locally/CI)

## Recent fixes affecting Docker builds
- Workspace dependency resolution inside Docker fixed in commit `d69e343`.
- LangChain dependency versions pinned for faster/more reliable `pip` resolution in commit `125d16b`.

## Worker image (services/worker/Dockerfile)
- Uses `requirements-base.txt` + `requirements-langchain.txt` (pinned) and installs in two steps.
- Expected behavior:
  - `pip install -r requirements-base.txt`
  - `pip install -r requirements-langchain.txt`
- Notes:
  - Pinned LangChain ecosystem reduces resolver backtracking and build-time flakiness.

## Minimal compose
- `docker-compose.minimal.yml` builds service images from the repo root context and references service Dockerfiles.

## Local build/run
```bash
# from repo root
docker compose -f docker-compose.minimal.yml build
docker compose -f docker-compose.minimal.yml up
```

## Health checks
- Orchestrator: `http://localhost:3001/health`
- Web: `http://localhost/health` (nginx)
- Worker: `http://localhost:8000/health`
