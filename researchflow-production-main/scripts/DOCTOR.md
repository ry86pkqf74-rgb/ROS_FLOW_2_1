# Stack Doctor (scripts/doctor.sh)

Quick stack health diagnosis for the ResearchFlow Docker Compose stack. Use it to see service status, unhealthy/duplicate containers, and Redis connectivity.

## Usage

```bash
# From repo root (uses docker-compose.yml in current dir)
./scripts/doctor.sh

# From anywhere, passing compose file
./scripts/doctor.sh /path/to/docker-compose.yml

# Custom Redis password (if not using default)
REDIS_PASSWORD=mysecret ./scripts/doctor.sh

# Tail more log lines for unhealthy services (default 100)
LOG_TAIL=200 ./scripts/doctor.sh
```

**Requirements:** Docker and Docker Compose (v2) or docker-compose (v1). Run from the project that contains your `docker-compose.yml`, or pass the path as the first argument.

**Safe:** Read-only. No destructive actions.

## What it does

1. **Docker Compose PS summary** – Prints `docker compose ps -a` so you see all services and their status.
2. **Unhealthy / Created / Exited** – Lists any container that is unhealthy, in `Created` state, or exited, and prints the last 100 log lines for each (configurable via `LOG_TAIL`).
3. **Duplicate or Created (key services)** – For `chromadb`, `agent-policy-review`, and `agent-stage2-lit`, reports each container and warns on duplicates or `Created` (stale) state.
4. **Redis reachability** – Runs `docker compose exec -T redis redis-cli -a <password> ping` and expects `PONG`.
5. **Exit code** – Exits **0** if everything is healthy, **non-zero** if any required service is unhealthy, Redis is unreachable, or duplicates/Created are found.

## Example output (all healthy)

```
=== Docker Compose PS summary ===
NAME                      IMAGE                    COMMAND                  SERVICE             CREATED             STATUS
researchflow-chromadb      chromadb/chroma:0.4.22   "python -m chromadb..."   chromadb            2 days ago          Up 2 days (healthy)
researchflow-redis-1       redis:7-alpine           "docker-entrypoint.s…"   redis               2 days ago          Up 2 days (healthy)
researchflow-agent-stage2-lit   ...                 ...                      agent-stage2-lit   2 days ago          Up 2 days (healthy)
researchflow-agent-policy-review ...                ...                      agent-policy-review 2 days ago          Up 2 days (healthy)
...

=== Unhealthy / Created / Exited services ===
(no output when all healthy)

=== Duplicate or Created containers (chromadb, agent-policy-review, agent-stage2-lit) ===
  chromadb: researchflow-chromadb (status=running)
  agent-policy-review: researchflow-agent-policy-review (status=running)
  agent-stage2-lit: researchflow-agent-stage2-lit (status=running)

=== Redis reachability (from inside compose) ===
  Redis: PONG (reachable)

=== Summary ===
Stack health: OK (no required service unhealthy).
```

## Example output (issues found)

```
=== Docker Compose PS summary ===
...

=== Unhealthy / Created / Exited services ===
  Service: chromadb  Container: researchflow-chromadb  Status: running  Health: unhealthy

=== Last 100 log lines: chromadb (researchflow-chromadb) ===
chromadb  | ERROR ...
chromadb  | ...

=== Duplicate or Created containers (chromadb, agent-policy-review, agent-stage2-lit) ===
  chromadb: researchflow-chromadb (status=created)
WARN: Container in 'Created' state (never started or stale): researchflow-chromadb
  agent-policy-review: researchflow-agent-policy-review (status=running)
  agent-stage2-lit: researchflow-agent-stage2-lit (status=running)

=== Redis reachability (from inside compose) ===
ERROR: Redis not reachable (exec redis-cli ping failed). Set REDIS_PASSWORD if not using default.

=== Summary ===
Stack health: ISSUES (see above). Fix unhealthy/duplicate/Created services or Redis.
```

Exit code in this case: **1**.

## Instructions

- **Run after `docker compose up -d`** to confirm the stack is healthy.
- **Use in CI** – `./scripts/doctor.sh && echo "Stack OK"` (fail the job on non-zero exit).
- **If Redis fails** – Ensure the `redis` service is up and the password matches. Default: `redis-dev-password`; set `REDIS_PASSWORD` in the environment or in `.env` when starting compose.
- **If you see duplicate or "Created" containers** – Run `docker compose down` (or `docker compose down -t 0`) then `docker compose up -d` to clean up and recreate. Optionally remove orphan containers with `docker compose down --remove-orphans`.
- **POSIX** – Script is written for `/bin/sh`; no Bash or extra tools required (only Docker and grep/sed/printf).
