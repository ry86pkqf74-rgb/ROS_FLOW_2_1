# Docker Compose: Stale Container Detector & Cleanup Guide

Quick reference for diagnosing and recovering from stale images, duplicate **Created** containers, and compose timeouts in the ResearchFlow stack.

**See also:** [Stack Doctor](../../scripts/DOCTOR.md) — run `./scripts/doctor.sh` from the repo root for a read-only stack health check (unhealthy/Created/duplicates, Redis).

---

## Symptoms

| Symptom | What you might see |
|--------|---------------------|
| **Stale image** | Service runs old code after a rebuild; `docker compose up -d` doesn’t pick up new image; logs or behavior don’t match latest code. |
| **Duplicate / Created containers** | `docker compose ps -a` shows more than one container per service (e.g. two `agent-stage2-lit`); or a container stuck in **Created** (never started or left after a failed start). |
| **Compose timeouts** | `docker compose up -d` hangs or times out; containers stay in **Created**; health checks never pass. |

These often appear together after interrupted builds, timeouts, or repeated `up`/`down` cycles.

---

## Safe recovery steps

**Assumption:** You’re in the repo root (or the directory that has your `docker-compose.yml`) and using the correct compose project (see [Identifying the compose project](#identifying-the-compose-project)).

### 1. Diagnose

```bash
# Optional: full stack health (unhealthy, Created, duplicates, Redis)
./scripts/doctor.sh

# Or manually
docker compose ps -a
```

Note which service(s) are unhealthy, in **Created**, or duplicated.

### 2. Remove and recreate a single service (no volume wipe)

For **one** service (e.g. `agent-policy-review`):

```bash
# Stop and remove the service’s container(s); -f = don’t ask, -s = stop first
docker compose rm -sf <service_name>

# Recreate and start (pulls/uses current image)
docker compose up -d <service_name>
```

Example:

```bash
docker compose rm -sf agent-policy-review
docker compose up -d agent-policy-review
```

### 3. Verify the running container uses the expected image

```bash
# Replace <container_name_or_id> with the name from docker compose ps
docker inspect <container_name_or_id> --format '{{.Image}}'
```

Compare with the image ID you expect (e.g. from a recent `docker compose build`). If the ID is old, the stack is still running a stale image; repeat step 2 and ensure no old containers are left.

### 4. Full stack reset (when multiple services are wrong)

Only if single-service recovery isn’t enough:

```bash
docker compose down
docker compose up -d --build
```

Use `docker compose down -t 0` to shorten shutdown timeout. To also remove orphan containers: `docker compose down --remove-orphans`.

---

## Warnings

### Do not prune volumes

- **Do not** run `docker volume prune` or `docker system prune -a --volumes` unless you intend to delete data.
- ResearchFlow uses named volumes for DB, Redis, ChromaDB, etc. Pruning volumes will destroy that data.

### Identifying the compose project

Compose chooses a project name (e.g. `researchflow`) and only manages containers with that project label. If you have multiple stacks or run from different directories, you might be looking at the wrong containers.

- **By directory:** Compose typically uses the directory name as project name when you don’t set `COMPOSE_PROJECT_NAME`. Run `docker compose` from the repo root that contains the `docker-compose.yml` you care about.
- **By label:** Containers from this stack have:
  `com.docker.compose.project=<project_name>` and `com.docker.compose.service=<service_name>`.
- **List “our” containers:**
  ```bash
  docker ps -a --filter "label=com.docker.compose.project=researchflow"
  ```
  (Replace `researchflow` with your project name if different.)

Always run recovery commands from the same directory (and same `-f docker-compose.yml` if you pass one) so you’re acting on the correct project.

---

## Common cases (from our history)

### 1. Policy-review stale image

**What happened:** After rebuilding the policy-review agent image, the running container kept using an old image; code/logic didn’t match the latest build.

**Fix:**

```bash
docker compose rm -sf agent-policy-review
docker compose up -d agent-policy-review
```

Then confirm:

```bash
docker inspect researchflow-agent-policy-review --format '{{.Image}}'
```

(Container name may have a suffix; get it from `docker compose ps -a`.)

### 2. ChromaDB unhealthy

**What happened:** ChromaDB container was **running** but reported **unhealthy**; RAG/lit-review could fail or time out.

**Fix:**

- Check logs: `docker compose logs --tail=200 chromadb`
- Remove and recreate so Compose brings up a fresh container (and re-runs health checks):
  ```bash
  docker compose rm -sf chromadb
  docker compose up -d chromadb
  ```
- Re-run `./scripts/doctor.sh` to confirm Redis and ChromaDB are healthy.

### 3. Stage2-lit stuck in Created

**What happened:** After a timeout or failed `docker compose up`, `agent-stage2-lit` had one or more containers in **Created** state (never fully started). Compose then showed duplicates or “Created” in `ps -a`.

**Fix:**

```bash
docker compose rm -sf agent-stage2-lit
docker compose up -d agent-stage2-lit
```

Then run `./scripts/doctor.sh` or `docker compose ps -a` and confirm a single running container for `agent-stage2-lit`.

---

## Quick reference

| Goal | Command |
|------|--------|
| Diagnose stack | `./scripts/doctor.sh` |
| Remove + recreate one service | `docker compose rm -sf <svc>` then `docker compose up -d <svc>` |
| Check image of running container | `docker inspect <name_or_id> --format '{{.Image}}'` |
| Full reset (no volume prune) | `docker compose down` then `docker compose up -d --build` |
| Ensure correct project | Run from repo root; check `com.docker.compose.project` on containers |

**Do not:** `docker volume prune` / `docker system prune -a --volumes` (unless you intend to lose stack data).
