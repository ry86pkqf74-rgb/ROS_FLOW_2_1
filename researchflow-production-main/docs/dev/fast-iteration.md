# Dev fast path: no full rebuild, targeted restart

Quick reference for iterating on a single service without rebuilding the whole stack. Use this when you’ve changed one service (e.g. an agent or the orchestrator) and want to run the new code without `docker compose up -d --build` across everything.

**See also:**

- [Docker troubleshooting](./docker-troubleshooting.md) — stale images, duplicate **Created** containers, recovery steps
- [ChromaDB offline startup](./chromadb-offline-startup.md) — ChromaDB health timing and DNS
- [Stack Doctor](../../scripts/DOCTOR.md) — `./scripts/doctor.sh` for stack health

---

## When to use `up -d` vs `up -d --build`

| Situation | Command | Why |
|-----------|---------|-----|
| **No code/image changes** — config or env only, or just restarting | `docker compose up -d [service]` | Uses existing images; fastest. |
| **One service’s code changed** — you rebuilt that image | `docker compose build <svc>` then `docker compose up -d --no-deps <svc>` | Rebuild only that service; bring it up without restarting dependencies. |
| **Multiple services or compose file changed** — new service, new deps, or unsure | `docker compose up -d --build` | Full rebuild and up so everything matches. |

Use **targeted rebuild + restart** when you’re only changing one service (e.g. `agent-policy-review`, `agent-stage2-lit`, `orchestrator`) and want to avoid long full rebuilds and unnecessary restarts of DB, Redis, ChromaDB, etc.

---

## Targeted rebuild (dev fast path)

Rebuild a single service and replace only that container, without touching its dependencies.

```bash
# From repo root (where docker-compose.yml lives)
cd /path/to/researchflow-production-main

# 1. Rebuild only the service image
docker compose build agent-policy-review

# 2. Replace the running container with one from the new image (no dependency restart)
docker compose up -d --no-deps agent-policy-review
```

- **`docker compose build <svc>`** — builds only that service’s image; other images are unchanged.
- **`docker compose up -d --no-deps <svc>`** — creates/updates the container for that service only; does **not** start or restart `depends_on` services.

So DB, Redis, ChromaDB, Ollama, etc. keep running; only the one service is restarted with the new image.

### Examples

```bash
# Agent: policy-review
docker compose build agent-policy-review
docker compose up -d --no-deps agent-policy-review

# Agent: literature retrieval
docker compose build agent-lit-retrieval
docker compose up -d --no-deps agent-lit-retrieval

# Agent: Stage 2 literature (depends on chromadb + ollama; see below)
docker compose build agent-stage2-lit
docker compose up -d --no-deps agent-stage2-lit

# Orchestrator
docker compose build orchestrator
docker compose up -d --no-deps orchestrator

# Worker
docker compose build worker
docker compose up -d --no-deps worker
```

---

## Verify running image SHA for a service

After a targeted rebuild, confirm the running container is using the image you just built.

**By container name (from `docker compose ps`):**

```bash
# Full image ID (SHA) of the running container
docker inspect researchflow-agent-policy-review --format '{{.Image}}'

# Same, with image repo:tag
docker inspect researchflow-agent-policy-review --format '{{.Config.Image}}'
```

**By service name (Compose project):**

```bash
# Get container name for the service, then inspect
CONTAINER=$(docker compose ps -q agent-policy-review)
docker inspect $CONTAINER --format '{{.Image}}'
```

**Compare with the image you just built:**

```bash
# Image ID of the image built for this service (after docker compose build <svc>)
docker images --format '{{.ID}} {{.Repository}}:{{.Tag}}' | grep agent-policy-review
```

If the ID from `inspect` is older than the one from `docker images`, the running container is still on a stale image. Remove and recreate the service (see [Recover from duplicate / Created containers](#recover-from-duplicate--created-containers)).

---

## Recover from duplicate / Created containers

If `docker compose ps -a` shows duplicate containers for a service or a container stuck in **Created**, Compose can keep using an old container or get stuck. Clean up that service and bring it back:

```bash
# Stop and remove the service’s container(s); -f = don’t ask, -s = stop first
docker compose rm -sf agent-policy-review

# Recreate and start (uses current image for that service)
docker compose up -d agent-policy-review
```

For a **targeted** restart with a fresh image (no dependency restart):

```bash
docker compose rm -sf agent-policy-review
docker compose build agent-policy-review
docker compose up -d --no-deps agent-policy-review
```

More cases (stale image, ChromaDB, stage2-lit) are in [Docker troubleshooting](./docker-troubleshooting.md#common-cases-from-our-history).

---

## Real examples from the stack

### 1. Policy-review stale image

**Symptom:** You changed `services/agents/agent-policy-review/` and ran `docker compose build agent-policy-review`, but the running container still shows old behavior or logs.

**Cause:** Compose didn’t replace the container (e.g. existing container left from a previous run, or duplicate/Created state).

**Fix:**

```bash
docker compose rm -sf agent-policy-review
docker compose build agent-policy-review
docker compose up -d --no-deps agent-policy-review
```

Then verify:

```bash
docker inspect researchflow-agent-policy-review --format '{{.Image}}'
# Compare with: docker images | grep agent-policy-review
```

---

### 2. ChromaDB health timing

ChromaDB’s healthcheck has a **long `start_period`** (150s in `docker-compose.yml`) so the server has time to start and run its internal init (e.g. hnsw). During that window the container is “starting”; only after it does the check pass and the container becomes **healthy**.

- **Implication:** After `docker compose up -d chromadb` or a targeted restart, wait on the order of 30–60s (with DNS) or up to ~2–3 minutes (without DNS) before ChromaDB is healthy. See [ChromaDB offline startup](./chromadb-offline-startup.md).
- **If you start `agent-stage2-lit`** (which `depends_on: chromadb: service_healthy`), Compose will wait for ChromaDB to be healthy before starting stage2-lit; no need to guess the delay if you do a full `up`.

For **targeted** restarts, bring ChromaDB up first and wait for healthy before starting services that depend on it:

```bash
docker compose up -d chromadb
docker compose ps chromadb   # wait until (healthy)
# then
docker compose up -d --no-deps agent-stage2-lit
```

---

### 3. agent-stage2-lit and `depends_on`

`agent-stage2-lit` declares:

```yaml
depends_on:
  chromadb:
    condition: service_healthy
  ollama:
    condition: service_healthy
```

So when you run **full** `docker compose up -d`:

- Compose starts ChromaDB and Ollama, waits for both to be **healthy**, then starts `agent-stage2-lit`. ChromaDB has `start_period: 150s` and Ollama `start_period: 60s`, so the first full bring-up can take a couple of minutes before stage2-lit appears.

When you use the **dev fast path**:

- `docker compose up -d --no-deps agent-stage2-lit` does **not** start or restart ChromaDB or Ollama. It only ensures the stage2-lit container is recreated with the current image. So:
  - ChromaDB and Ollama must already be running and healthy (e.g. from an earlier `up -d` or from separate `up -d chromadb ollama`).
  - If they aren’t running, stage2-lit may start but fail at runtime when it tries to reach ChromaDB or Ollama.

**Summary:** For “change stage2-lit code only” use: `docker compose build agent-stage2-lit` then `docker compose up -d --no-deps agent-stage2-lit`. For a clean full start, use `docker compose up -d` and allow time for ChromaDB (and Ollama) to become healthy before stage2-lit runs.

---

## Quick reference

| Goal | Command |
|------|--------|
| Restart one service (no rebuild) | `docker compose up -d --no-deps <svc>` |
| Rebuild one service only | `docker compose build <svc>` |
| Rebuild + restart one service (fast path) | `docker compose build <svc>` then `docker compose up -d --no-deps <svc>` |
| Verify running image SHA | `docker inspect <container_name> --format '{{.Image}}'` |
| Fix duplicate/Created for one service | `docker compose rm -sf <svc>` then `docker compose up -d <svc>` (or add `build` + `--no-deps` as above) |
| Full stack rebuild | `docker compose up -d --build` |

**Do not** run `docker volume prune` or `docker system prune -a --volumes` unless you intend to remove stack data (DB, Redis, ChromaDB, etc.).
