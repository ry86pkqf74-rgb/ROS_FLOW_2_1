#!/usr/bin/env bash
#
# Comprehensive Hetzner Dispatch Sweep - All 31 Task Types
# 
# Tests dispatch routing for all task types defined in ai-router.ts TASK_TYPE_TO_AGENT
# Validates that every task type correctly routes to its designated agent.
#
# Usage:
#   export WORKER_SERVICE_TOKEN=$(grep WORKER_SERVICE_TOKEN .env | cut -d= -f2)
#   ./scripts/hetzner-dispatch-sweep-full.sh
#
# Optional environment variables:
#   ORCHESTRATOR_URL - Override target URL (default: http://127.0.0.1:3001)
#   WORKER_SERVICE_TOKEN - Service authentication token (required)
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Configuration
ORCHESTRATOR_URL="${ORCHESTRATOR_URL:-http://127.0.0.1:3001}"
DISPATCH_ENDPOINT="${ORCHESTRATOR_URL}/api/ai/router/dispatch"

# Check for required token
if [ -z "${WORKER_SERVICE_TOKEN:-}" ]; then
  echo -e "${RED}ERROR: WORKER_SERVICE_TOKEN not set${NC}"
  echo "The dispatch endpoint requires service token authentication."
  echo "Run: export WORKER_SERVICE_TOKEN=\$(grep WORKER_SERVICE_TOKEN .env | cut -d= -f2)"
  exit 1
fi

# Test counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
declare -a FAILED_TASKS=()

# Print header
echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  ${BOLD}Hetzner Dispatch Routing Validation - All 31 Task Types${NC}${BLUE}   ║${NC}"
echo -e "${BLUE}║  ${BOLD}Target: ${ORCHESTRATOR_URL}${NC}${BLUE}                    ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Starting comprehensive dispatch routing tests..."
echo ""

# Task type to agent mapping (synchronized with ai-router.ts at commit 5e6657d)
# Format: "TASK_TYPE|expected-agent-name|description"
declare -a TASK_MAPPINGS=(
  # Native agents (FastAPI services)
  "STAGE_2_LITERATURE_REVIEW|agent-stage2-lit|Stage 2 Literature Review"
  "STAGE2_SCREEN|agent-stage2-screen|Stage 2 Screening"
  "STAGE_2_EXTRACT|agent-stage2-extract|Stage 2 Data Extraction"
  "STAGE2_EXTRACT|agent-stage2-extract|Stage 2 Extract (alias)"
  "STAGE2_SYNTHESIZE|agent-stage2-synthesize|Stage 2 Synthesis"
  "LIT_RETRIEVAL|agent-lit-retrieval|Literature Retrieval"
  "LIT_TRIAGE|agent-lit-triage|Literature Triage"
  "POLICY_REVIEW|agent-policy-review|Policy Review"
  "RAG_INGEST|agent-rag-ingest|RAG Document Ingestion"
  "RAG_RETRIEVE|agent-rag-retrieve|RAG Knowledge Retrieval"
  "SECTION_WRITE_INTRO|agent-intro-writer|Introduction Section Writer"
  "SECTION_WRITE_METHODS|agent-methods-writer|Methods Section Writer"
  "SECTION_WRITE_RESULTS|agent-results-writer|Results Section Writer"
  "SECTION_WRITE_DISCUSSION|agent-discussion-writer|Discussion Section Writer"
  "CLAIM_VERIFY|agent-verify|Claim Verification"
  "EVIDENCE_SYNTHESIS|agent-evidence-synthesis|Evidence Synthesis"
  
  # LangSmith-backed agents (proxy services)
  "CLINICAL_MANUSCRIPT_WRITE|agent-clinical-manuscript-proxy|Clinical Manuscript Writer"
  "CLINICAL_SECTION_DRAFT|agent-section-drafter-proxy|Clinical Section Drafter"
  "RESULTS_INTERPRETATION|agent-results-interpretation-proxy|Results Interpretation"
  "STATISTICAL_ANALYSIS|agent-results-interpretation-proxy|Statistical Analysis (alias)"
  "PEER_REVIEW_SIMULATION|agent-peer-review-simulator-proxy|Peer Review Simulator"
  "CLINICAL_BIAS_DETECTION|agent-bias-detection-proxy|Clinical Bias Detection"
  "DISSEMINATION_FORMATTING|agent-dissemination-formatter-proxy|Dissemination Formatter"
  "PERFORMANCE_OPTIMIZATION|agent-performance-optimizer-proxy|Performance Optimizer"
  "JOURNAL_GUIDELINES_CACHE|agent-journal-guidelines-cache-proxy|Journal Guidelines Cache"
  "COMPLIANCE_AUDIT|agent-compliance-auditor-proxy|Compliance Auditor"
  "ARTIFACT_AUDIT|agent-artifact-auditor-proxy|Artifact Auditor"
  "RESILIENCE_ARCHITECTURE|agent-resilience-architecture-advisor-proxy|Resilience Architecture Advisor"
  "MULTILINGUAL_LITERATURE_PROCESSING|agent-multilingual-literature-processor-proxy|Multilingual Literature Processor"
  "CLINICAL_MODEL_FINE_TUNING|agent-clinical-model-fine-tuner-proxy|Clinical Model Fine-Tuner"
  "HYPOTHESIS_REFINEMENT|agent-hypothesis-refiner-proxy|Hypothesis Refiner"
)

# Function to test dispatch routing
test_dispatch() {
  local task_type="$1"
  local expected_agent="$2"
  local description="$3"
  local test_num="$4"
  local total="$5"
  
  TOTAL_TESTS=$((TOTAL_TESTS + 1))
  
  echo -e "${BOLD}[Test ${test_num}/${total}]${NC} Testing task_type: ${YELLOW}${task_type}${NC}"
  echo "  Description: ${description}"
  echo "  Expected agent: ${expected_agent}"
  
  # Build request payload
  local payload=$(cat <<EOF
{
  "task_type": "${task_type}",
  "request_id": "sweep-test-${test_num}-$(date +%s)",
  "mode": "DEMO"
}
EOF
)
  
  # Make request
  local response=$(curl -s -X POST "$DISPATCH_ENDPOINT" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer ${WORKER_SERVICE_TOKEN}" \
    -d "$payload")
  
  # Parse response
  local agent_name=$(echo "$response" | grep -o '"agent_name":"[^"]*"' | cut -d'"' -f4 || echo "")
  local agent_url=$(echo "$response" | grep -o '"agent_url":"[^"]*"' | cut -d'"' -f4 || echo "")
  local error=$(echo "$response" | grep -o '"error":"[^"]*"' | cut -d'"' -f4 || echo "")
  
  # Check result
  if [ "$agent_name" = "$expected_agent" ]; then
    echo -e "  ${GREEN}✓ PASS${NC} - Routed to: ${agent_name}"
    echo "  Agent URL: ${agent_url}"
    PASSED_TESTS=$((PASSED_TESTS + 1))
  else
    echo -e "  ${RED}✗ FAIL${NC} - Expected: ${expected_agent}, Got: ${agent_name:-NONE}"
    if [ -n "$error" ]; then
      echo "  Error: ${error}"
    fi
    echo "  Full response: ${response}"
    FAILED_TESTS=$((FAILED_TESTS + 1))
    FAILED_TASKS+=("${task_type} (expected: ${expected_agent}, got: ${agent_name:-ERROR})")
  fi
  
  echo ""
}

# Run all tests
test_counter=1
total_mappings=${#TASK_MAPPINGS[@]}

for mapping in "${TASK_MAPPINGS[@]}"; do
  IFS='|' read -r task_type expected_agent description <<< "$mapping"
  test_dispatch "$task_type" "$expected_agent" "$description" "$test_counter" "$total_mappings"
  test_counter=$((test_counter + 1))
done

# Print summary
echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                     ${BOLD}Test Summary${NC}${BLUE}                              ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo -e "${BOLD}Total Tests:${NC}  ${TOTAL_TESTS}"
echo -e "${GREEN}${BOLD}Passed:${NC}       ${PASSED_TESTS}${NC}"
echo -e "${RED}${BOLD}Failed:${NC}       ${FAILED_TESTS}${NC}"
echo ""

# Print failed tests if any
if [ ${FAILED_TESTS} -gt 0 ]; then
  echo -e "${RED}${BOLD}Failed Tests:${NC}"
  for failed_task in "${FAILED_TASKS[@]}"; do
    echo -e "  ${RED}✗${NC} ${failed_task}"
  done
  echo ""
  echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════╗${NC}"
  echo -e "${BLUE}║  ${RED}✗ TESTS FAILED${NC}${BLUE}                                              ║${NC}"
  echo -e "${BLUE}║  Some task types are not routing correctly                   ║${NC}"
  echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════╝${NC}"
  exit 1
else
  echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════╗${NC}"
  echo -e "${BLUE}║  ${GREEN}✓ ALL DISPATCH TESTS PASSED${NC}${BLUE}                                ║${NC}"
  echo -e "${BLUE}║  Router is correctly routing to all ${TOTAL_TESTS} task types         ║${NC}"
  echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════╝${NC}"
  exit 0
fi
