# Development Tools

This directory contains scripts and utilities for development, testing, and validation.

## Post-Merge Truth Check

**File:** `postmerge-check.sh`

Fast validation script that confirms contract + smoke + key agents are coherent after merges. This catches 80% of integration issues quickly.

### What It Checks

1. **Contract Checker** - Validates all agents conform to the unified agent contract (health, ready, sync, stream endpoints)
2. **Stage 2 Smoke Test** - E2E literature review workflow (execute → BullMQ → worker → router → agent)
3. **RAG Smoke Test** - E2E RAG pipeline (ingest → retrieve → verify)
4. **AI Bridge Smoke** - Confirms AI bridge is configured correctly (optional live invoke with `AI_BRIDGE_INVOKE=1`)

### Usage

```bash
# Local development (default)
./tools/dev/postmerge-check.sh

# Staging environment
BASE_URL=https://staging.researchflow.example.com ./tools/dev/postmerge-check.sh

# With live AI bridge invoke (requires OPENAI_API_KEY or ANTHROPIC_API_KEY)
AI_BRIDGE_INVOKE=1 ./tools/dev/postmerge-check.sh

# Custom timeout for stage 2 smoke test
SMOKE_STAGE2_TIMEOUT=180 ./tools/dev/postmerge-check.sh

# CI mode (GitHub Actions)
GITHUB_ACTIONS=true ./tools/dev/postmerge-check.sh
```

### Exit Codes

- `0` - All checks passed
- `1` - One or more checks failed

### Output

The script provides:
- Real-time progress for each check
- Clear PASS/FAIL summary
- Docker compose logs for failed services (local mode)
- Debugging commands for troubleshooting

Example output:
```
=== Post-Merge Truth Check ===

[INFO] Target: http://localhost:3001
[INFO] Timestamp: 2026-02-06T10:30:00Z
[INFO] Detected local environment

=== Contract Checker ===
[INFO] Running contract checker against all agents...
Agent contract check summary
...
[INFO] ✓ Contract Checker PASSED

=== Stage 2 Smoke Test ===
[INFO] Running Stage 2 smoke test (literature review E2E)...
...
[INFO] ✓ Stage 2 Smoke Test PASSED

=== RAG Smoke Test ===
[INFO] Running RAG smoke test (ingest → retrieve → verify)...
...
[INFO] ✓ RAG Smoke Test PASSED

=== AI Bridge Smoke ===
[INFO] Running AI bridge smoke check...
[INFO] AI bridge smoke: realProvider=true
...
[INFO] ✓ AI Bridge Smoke PASSED

=== Post-Merge Check Summary ===

✓ ALL CHECKS PASSED

  Total tests:  4
  Passed:       4
  Failed:       0

[INFO] Post-merge verification complete. System is coherent.
```

### When to Run

- **After merging branches** - Ensures integration is clean
- **Before pushing to staging** - Validates local changes
- **In CI pipeline** - Automated gate for PR merges
- **After environment updates** - Confirms configuration changes

### Dependencies

- `bash` (with `set -euo pipefail`)
- `curl` (for API requests)
- `jq` (for JSON parsing)
- `python3` (for contract checker)
- `docker` and `docker compose` (local mode only)

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BASE_URL` | `http://localhost:3001` | Target orchestrator URL |
| `AI_BRIDGE_INVOKE` | `0` | Set to `1` to perform live AI invoke |
| `SMOKE_STAGE2_TIMEOUT` | `120` | Stage 2 smoke test timeout (seconds) |
| `GITHUB_ACTIONS` | (unset) | Set to enable CI error annotations |

### Troubleshooting

**Services not running:**
```bash
docker compose up -d
docker compose ps
```

**Check logs manually:**
```bash
docker compose logs -f orchestrator worker agent-stage2-lit
```

**Contract checker fails:**
- Ensure all agent services are healthy: `docker compose ps`
- Check agent health endpoints: `curl http://localhost:8000/health` (adjust port)
- Review agent logs: `docker compose logs agent-stage2-lit`

**Stage 2 smoke test timeout:**
- Increase timeout: `SMOKE_STAGE2_TIMEOUT=300 ./tools/dev/postmerge-check.sh`
- Check worker queue: `docker compose logs worker | grep "Job queued"`
- Verify BullMQ/Redis: `docker compose logs redis`

**RAG smoke test fails:**
- Check ChromaDB: `docker compose logs chromadb`
- Verify embedding provider: Check `OPENAI_API_KEY` in `.env`
- Test ingest agent: `curl http://localhost:8000/health` (rag-ingest port)

## Other Tools

### smoke-stage2.sh

Stage 2 literature review E2E smoke test. Called by `postmerge-check.sh` but can be run standalone.

```bash
./tools/dev/smoke-stage2.sh
BASE_URL=https://staging.example.com ./tools/dev/smoke-stage2.sh
```

### smoke-rag.sh

RAG pipeline E2E smoke test (ingest → retrieve → verify). Called by `postmerge-check.sh` but can be run standalone.

```bash
./tools/dev/smoke-rag.sh
BASE_URL=https://staging.example.com ./tools/dev/smoke-rag.sh
```

### tail-logs.sh

Utility for tailing docker compose logs with filtering.

```bash
./tools/dev/tail-logs.sh [service...]
```

### generate-worker-service-token.ts

Generates JWT service tokens for worker authentication.

```bash
npx ts-node ./tools/dev/generate-worker-service-token.ts
```

## Contributing

When adding new development tools:
1. Follow the naming convention: `[action]-[target].sh` or `[action]-[target].ts`
2. Include `--help` flag with usage documentation
3. Use consistent color coding (GREEN=info, YELLOW=warn, RED=error)
4. Support both local and staging environments via `BASE_URL`
5. Add comprehensive error handling and logging
6. Update this README with usage examples

## See Also

- [Contract Documentation](../../docs/AGENT_CONTRACT.md)
- [RAG Loop Acceptance Criteria](../../docs/RAG_LOOP_ACCEPTANCE_CRITERIA.md)
- [Agent Response Schema](../../docs/agent_response_schema.json)
- [CI/CD Pipeline](.github/workflows/)
