#!/bin/bash
# ==============================================================================
# Generate wiring documentation for all native agents
# ==============================================================================
# This script generates standardized wiring.md files for all native FastAPI
# agents declared in AGENT_ENDPOINTS_JSON.
#
# Usage: ./scripts/generate-agent-wiring-docs.sh
# ==============================================================================

set -euo pipefail

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

DOCS_BASE="researchflow-production-main/docs/agents"

echo "════════════════════════════════════════════════════════════════"
echo "Generating wiring documentation for native agents"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Native agents (not proxy services)
NATIVE_AGENTS=(
  "agent-stage2-lit:STAGE_2_LITERATURE_REVIEW:8000:Literature search via PubMed/SemanticScholar"
  "agent-stage2-screen:STAGE2_SCREEN:8000:Deduplication and inclusion/exclusion criteria"
  "agent-stage2-extract:STAGE_2_EXTRACT,STAGE2_EXTRACT:8000:PICO extraction from papers"
  "agent-stage2-synthesize:STAGE2_SYNTHESIZE:8000:Evidence synthesis (legacy stub)"
  "agent-lit-retrieval:LIT_RETRIEVAL:8000:Deterministic PubMed search"
  "agent-lit-triage:LIT_TRIAGE:8000:AI-powered literature prioritization"
  "agent-policy-review:POLICY_REVIEW:8000:Policy and guideline compliance review"
  "agent-rag-ingest:RAG_INGEST:8000:Document chunking and embedding to ChromaDB"
  "agent-rag-retrieve:RAG_RETRIEVE:8000:Vector similarity search and grounding"
  "agent-verify:CLAIM_VERIFY:8000:Claim verification against evidence"
  "agent-intro-writer:SECTION_WRITE_INTRO:8000:Introduction section generation"
  "agent-methods-writer:SECTION_WRITE_METHODS:8000:Methods section generation"
  "agent-results-writer:SECTION_WRITE_RESULTS:8000:Results section generation"
  "agent-discussion-writer:SECTION_WRITE_DISCUSSION:8000:Discussion section generation"
  "agent-evidence-synthesis:EVIDENCE_SYNTHESIS:8000:GRADE-based evidence synthesis with conflict analysis"
)

# Function to generate wiring doc
generate_wiring_doc() {
  local agent_key="$1"
  local task_types="$2"
  local port="$3"
  local description="$4"
  
  local doc_dir="${DOCS_BASE}/${agent_key}"
  local doc_file="${doc_dir}/wiring.md"
  
  # Create directory
  mkdir -p "$doc_dir"
  
  # Generate doc
  cat > "$doc_file" <<DOC_EOF
# ${agent_key} - Wiring Documentation

**Agent Key:** \`${agent_key}\`  
**Type:** Native FastAPI Agent  
**Status:** ✅ Production

---

## Overview

${description}

## Deployment Configuration

### Docker Compose Service

**Service Name:** \`${agent_key}\`  
**Container Name:** \`researchflow-${agent_key}\`  
**Internal Port:** ${port}  
**Networks:** \`backend\` (internal only)

### Task Types

This agent handles the following task types in the orchestrator router:

$(echo "$task_types" | tr ',' '\n' | while read -r task_type; do
  [ -n "$task_type" ] && echo "- \`${task_type}\`"
done)

**Router Mapping:** \`TASK_TYPE_TO_AGENT\` in \`services/orchestrator/src/routes/ai-router.ts\`

### Agent Endpoints Registry

**AGENT_ENDPOINTS_JSON Entry:**

Agent must be present in \`AGENT_ENDPOINTS_JSON\` environment variable in \`docker-compose.yml\`.

To verify current registration:
\`\`\`bash
docker compose exec orchestrator sh -c 'echo \$AGENT_ENDPOINTS_JSON' | python3 -m json.tool | grep "${agent_key}"
\`\`\`

**Location:** \`docker-compose.yml\` orchestrator environment

## Health Endpoints

| Endpoint | Method | Response |
|----------|--------|----------|
| \`/health\` | GET | \`{"ok": true, "status": "healthy"}\` |
| \`/health/ready\` | GET | \`{"ready": true, "dependencies": {...}}\` |

**Health Check Command:**
\`\`\`bash
docker compose exec ${agent_key} curl -f http://localhost:${port}/health
\`\`\`

## Required Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| \`AI_BRIDGE_URL\` | Yes | Orchestrator URL for LLM inference |
| \`WORKER_SERVICE_TOKEN\` | Yes | Internal service authentication |
| \`GOVERNANCE_MODE\` | No | Execution mode (DEMO/LIVE) |
| \`ORCHESTRATOR_INTERNAL_URL\` | No | Orchestrator callback URL |

**Note:** Actual environment variables may vary by agent. Check \`docker-compose.yml\` service definition for complete list.

## Validation Commands

### Preflight Validation (Mandatory)

\`\`\`bash
# Runs automatically as part of dynamic agent validation
./scripts/hetzner-preflight.sh
\`\`\`

Preflight validates:
- Agent is present in AGENT_ENDPOINTS_JSON
- Container is running
- Health endpoint responds
- URL format is valid

### Smoke Test (Optional)

\`\`\`bash
# Test all agents including ${agent_key}
CHECK_ALL_AGENTS=1 ./scripts/stagewise-smoke.sh
\`\`\`

Smoke test:
- Dispatches test request through orchestrator
- Validates routing works correctly
- Writes artifact to \`/data/artifacts/validation/${agent_key}/<timestamp>/summary.json\`
- Non-blocking (informational only)

## Deployment Steps

### On ROSflow2 (Hetzner)

\`\`\`bash
# 1. Ensure service is defined in docker-compose.yml
grep -A 20 "${agent_key}:" docker-compose.yml

# 2. Verify AGENT_ENDPOINTS_JSON includes this agent
docker compose config | grep AGENT_ENDPOINTS_JSON | grep "${agent_key}"

# 3. Build and start
docker compose build ${agent_key}
docker compose up -d ${agent_key}

# 4. Wait for healthy
sleep 10

# 5. Verify health
docker compose exec ${agent_key} curl -f http://localhost:${port}/health

# 6. Restart orchestrator to load routing
docker compose up -d --force-recreate orchestrator

# 7. Run preflight
./scripts/hetzner-preflight.sh

# 8. Optional: Run smoke test
CHECK_ALL_AGENTS=1 ./scripts/stagewise-smoke.sh
\`\`\`

## Troubleshooting

### Container won't start
\`\`\`bash
# Check logs
docker compose logs --tail=50 ${agent_key}

# Check for build errors
docker compose build ${agent_key}

# Verify dependencies
docker compose ps postgres redis orchestrator
\`\`\`

### Health check fails
\`\`\`bash
# Check health directly
docker compose exec ${agent_key} curl -v http://localhost:${port}/health

# Check environment
docker compose exec ${agent_key} env | grep -E 'AI_BRIDGE|ORCHESTRATOR'

# Restart service
docker compose restart ${agent_key}
\`\`\`

### Routing failures
\`\`\`bash
# Verify orchestrator has agent in registry
docker compose exec orchestrator sh -c 'echo \$AGENT_ENDPOINTS_JSON' | python3 -m json.tool | grep "${agent_key}"

# Check router registration
grep "${agent_key}" services/orchestrator/src/routes/ai-router.ts

# Test dispatch
curl -X POST http://127.0.0.1:3001/api/ai/router/dispatch \\
  -H "Authorization: Bearer \$TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
    "task_type": "$(echo "$task_types" | cut -d',' -f1)",
    "request_id": "test-001",
    "mode": "DEMO",
    "inputs": {}
  }'
\`\`\`

## Integration

### Upstream Dependencies
- Orchestrator (routing and LLM inference)
- Redis (caching)
- PostgreSQL (persistence)

### Downstream Consumers
- Worker service (workflow engine)
- Frontend UI (direct API calls)
- Other agents (agent-to-agent calls)

## Artifacts

**Path:** \`/data/artifacts/${agent_key}/\`

Artifacts are written when:
- Smoke tests run with \`CHECK_ALL_AGENTS=1\`
- Validation requests executed
- (Agent-specific artifact writes if implemented)

## References

- **Service Definition:** \`docker-compose.yml\` (search for \`${agent_key}:\`)
- **Router Registration:** \`services/orchestrator/src/routes/ai-router.ts\`
- **Agent Implementation:** \`services/agents/${agent_key}/\`
- **Agent Inventory:** \`AGENT_INVENTORY.md\`
- **Health Check Script:** \`scripts/hetzner-preflight.sh\`
- **Smoke Test Script:** \`scripts/stagewise-smoke.sh\`

---

**Last Updated:** $(date -u +%Y-%m-%d)  
**Status:** ✅ Wired for Production
DOC_EOF
  
  echo -e "  ${GREEN}✓${NC} Generated: ${doc_file}"
}

# Generate docs for all native agents
for agent_spec in "${NATIVE_AGENTS[@]}"; do
  IFS=':' read -r agent_key task_types port description <<< "$agent_spec"
  generate_wiring_doc "$agent_key" "$task_types" "$port" "$description"
done

echo ""
echo -e "${GREEN}✓ Generated ${#NATIVE_AGENTS[@]} wiring documents${NC}"
echo ""
echo "Location: ${DOCS_BASE}/<agent-key>/wiring.md"
echo ""
echo "Usage:"
echo "  - Reference in AGENT_INVENTORY.md"
echo "  - Share with operators for deployment"
echo "  - Link in PR descriptions"
