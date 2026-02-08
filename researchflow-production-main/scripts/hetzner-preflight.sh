#!/bin/bash
# ==============================================================================
# ResearchFlow Hetzner Preflight Check Script
# ==============================================================================
# Usage: ./scripts/hetzner-preflight.sh [OPTIONS]
#
# Performs preflight checks for ResearchFlow deployment on Hetzner servers.
# Validates Docker, system resources, and service health.
#
# Options:
#   --orchestrator-url URL     Orchestrator URL (default: http://127.0.0.1:3001)
#   --worker-url URL           Worker URL (default: http://127.0.0.1:8000)
#   --guideline-url URL        Guideline Engine URL (default: http://127.0.0.1:8001)
#   --collab-url URL           Collaboration Server URL (default: http://127.0.0.1:1235)
#   --web-url URL              Web Frontend URL (default: http://127.0.0.1)
#
# Example usage on ROSflow2 (Hetzner):
#   # From local machine to remote server
#   ssh user@rosflow2 'cd /opt/researchflow && ./scripts/hetzner-preflight.sh'
#
#   # On the server itself
#   cd /opt/researchflow
#   ./scripts/hetzner-preflight.sh
#
#   # With custom URLs for reverse proxy setup
#   ./scripts/hetzner-preflight.sh \
#     --orchestrator-url https://api.rosflow2.example.com \
#     --web-url https://rosflow2.example.com
# ==============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Default configuration (server-local endpoints)
ORCHESTRATOR_URL="${ORCHESTRATOR_URL:-http://127.0.0.1:3001}"
WORKER_URL="${WORKER_URL:-http://127.0.0.1:8000}"
GUIDELINE_URL="${GUIDELINE_URL:-http://127.0.0.1:8001}"
COLLAB_URL="${COLLAB_URL:-http://127.0.0.1:1235}"
WEB_URL="${WEB_URL:-http://127.0.0.1}"

# Parse command line arguments
while [ $# -gt 0 ]; do
    case "$1" in
        --orchestrator-url)
            ORCHESTRATOR_URL="$2"
            shift 2
            ;;
        --worker-url)
            WORKER_URL="$2"
            shift 2
            ;;
        --guideline-url)
            GUIDELINE_URL="$2"
            shift 2
            ;;
        --collab-url)
            COLLAB_URL="$2"
            shift 2
            ;;
        --web-url)
            WEB_URL="$2"
            shift 2
            ;;
        --help|-h)
            sed -n '2,31p' "$0" | sed 's/^# //; s/^#//'
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Results tracking
PASSED=0
FAILED=0
WARNINGS=0

# Helper functions
print_header() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
}

check_pass() {
    local name=$1
    printf "  %-30s" "$name"
    echo -e "${GREEN}✓ PASS${NC}"
    PASSED=$((PASSED + 1))
}

check_fail() {
    local name=$1
    local reason=$2
    printf "  %-30s" "$name"
    echo -e "${RED}✗ FAIL${NC} - $reason"
    FAILED=$((FAILED + 1))
}

check_warn() {
    local name=$1
    local reason=$2
    printf "  %-30s" "$name"
    echo -e "${YELLOW}⚠ WARN${NC} - $reason"
    WARNINGS=$((WARNINGS + 1))
}

# Main checks
print_header "ResearchFlow Hetzner Preflight Check"

echo -e "${BLUE}=== System Information ===${NC}"
echo ""
echo "Hostname:       $(hostname)"
echo "OS:             $(uname -s) $(uname -r)"
echo "Architecture:   $(uname -m)"
echo "Date:           $(date)"
echo ""

# Docker checks
print_header "Docker Environment"

# Check Docker
if command -v docker >/dev/null 2>&1; then
    docker_version=$(docker --version | awk '{print $3}' | sed 's/,//')
    echo "Docker version: $docker_version"
    check_pass "Docker installed"
    
    # Check Docker daemon
    if docker ps >/dev/null 2>&1; then
        check_pass "Docker daemon running"
    else
        check_fail "Docker daemon" "not running or no permissions"
    fi
else
    check_fail "Docker" "not installed"
fi

# Check Docker Compose
if command -v docker-compose >/dev/null 2>&1; then
    compose_version=$(docker-compose --version | awk '{print $4}' | sed 's/,//')
    echo "Docker Compose version: $compose_version"
    check_pass "Docker Compose installed"
elif docker compose version >/dev/null 2>&1; then
    compose_version=$(docker compose version --short)
    echo "Docker Compose version: $compose_version"
    check_pass "Docker Compose (plugin)"
else
    check_fail "Docker Compose" "not installed"
fi

echo ""

# System resources
print_header "System Resources"

# Disk space
echo "Disk usage:"
df -h / | tail -n 1
disk_avail=$(df -BG / | tail -n 1 | awk '{print $4}' | sed 's/G//')
if [ "$disk_avail" -ge 20 ]; then
    check_pass "Disk space" "($disk_avail GB available)"
elif [ "$disk_avail" -ge 10 ]; then
    check_warn "Disk space" "only $disk_avail GB available (20GB+ recommended)"
else
    check_fail "Disk space" "only $disk_avail GB available (need 20GB+)"
fi

# Memory
echo ""
echo "Memory usage:"
free -h | grep -E "Mem:|total"
mem_avail_kb=$(free | grep Mem | awk '{print $7}')
mem_avail_gb=$((mem_avail_kb / 1024 / 1024))
if [ "$mem_avail_gb" -ge 4 ]; then
    check_pass "Memory" "($mem_avail_gb GB available)"
elif [ "$mem_avail_gb" -ge 2 ]; then
    check_warn "Memory" "only $mem_avail_gb GB available (4GB+ recommended)"
else
    check_fail "Memory" "only $mem_avail_gb GB available (need 4GB+)"
fi

echo ""

# Docker containers
print_header "Docker Containers"

if docker ps >/dev/null 2>&1; then
    echo "Running containers:"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null | head -20
    echo ""
    
    # Check if compose project is running
    if docker ps --format "{{.Names}}" | grep -q "researchflow"; then
        check_pass "ResearchFlow containers" "running"
        
        # Show image tags for running services
        echo ""
        echo "Container images and tags:"
        if command -v docker-compose >/dev/null 2>&1; then
            docker-compose images 2>/dev/null || true
        elif docker compose version >/dev/null 2>&1; then
            docker compose images 2>/dev/null || true
        fi
    else
        check_warn "ResearchFlow containers" "no containers found (not started yet?)"
    fi
else
    check_fail "Docker status" "cannot list containers"
fi

echo ""

# Environment configuration checks
print_header "Environment Configuration"

# Check for .env file
if [ -f ".env" ]; then
    check_pass ".env file" "exists"
    
    # Check for WORKER_SERVICE_TOKEN
    if grep -q "^WORKER_SERVICE_TOKEN=" .env 2>/dev/null; then
        TOKEN_VALUE=$(grep "^WORKER_SERVICE_TOKEN=" .env | cut -d= -f2 | tr -d '"' | tr -d "'")
        TOKEN_LEN=${#TOKEN_VALUE}
        
        if [ -n "$TOKEN_VALUE" ] && [ "$TOKEN_LEN" -ge 32 ]; then
            check_pass "WORKER_SERVICE_TOKEN" "set ($TOKEN_LEN chars)"
        elif [ -n "$TOKEN_VALUE" ]; then
            check_warn "WORKER_SERVICE_TOKEN" "too short ($TOKEN_LEN chars, need 32+)"
        else
            check_fail "WORKER_SERVICE_TOKEN" "empty value"
        fi
    else
        check_fail "WORKER_SERVICE_TOKEN" "not found in .env - internal auth will fail!"
        echo ""
        echo -e "${YELLOW}Remediation:${NC}"
        echo "  1. Generate token: openssl rand -hex 32"
        echo "  2. Add to .env: WORKER_SERVICE_TOKEN=<generated-token>"
        echo "  3. Recreate services: docker compose up -d --force-recreate orchestrator worker"
        echo ""
    fi
    
    # Verify token is available in running orchestrator (if containers are up)
    if docker ps --format "{{.Names}}" | grep -q "orchestrator"; then
        TOKEN_IN_CONTAINER=$(docker compose exec -T orchestrator sh -c 'echo ${WORKER_SERVICE_TOKEN:+SET}' 2>/dev/null || echo "")
        if [ "$TOKEN_IN_CONTAINER" = "SET" ]; then
            check_pass "WORKER_SERVICE_TOKEN (runtime)" "loaded in orchestrator"
        else
            check_fail "WORKER_SERVICE_TOKEN (runtime)" "not loaded in orchestrator - recreate container!"
        fi
    fi
else
    check_warn ".env file" "not found (using defaults only)"
    check_fail "WORKER_SERVICE_TOKEN" ".env missing - internal auth will fail!"
fi

echo ""

# Worker service token (required for internal dispatch auth; 403 on POST /api/ai/router/dispatch if missing)
print_header "Worker Service Token (WORKER_SERVICE_TOKEN)"

WORKER_TOKEN_SET=false
if [ -f .env ] && grep -qE '^WORKER_SERVICE_TOKEN=.+' .env 2>/dev/null; then
    WORKER_TOKEN_SET=true
fi
if [ "$WORKER_TOKEN_SET" = false ] && docker ps --format "{{.Names}}" 2>/dev/null | grep -q orchestrator; then
    TOKEN_CHECK=$(docker compose exec -T orchestrator sh -c 'echo ${WORKER_SERVICE_TOKEN:+SET}' 2>/dev/null || true)
    if [ "$TOKEN_CHECK" = "SET" ]; then
        WORKER_TOKEN_SET=true
    fi
fi
if [ "$WORKER_TOKEN_SET" = true ]; then
    check_pass "WORKER_SERVICE_TOKEN" "set (internal dispatch auth)"
else
    echo ""
    echo -e "${RED}Remediation:${NC}"
    echo "  1. Generate a token:  openssl rand -hex 32"
    echo "  2. Add to .env:      WORKER_SERVICE_TOKEN=<that-hex-token>"
    echo "  3. Recreate orchestrator:  docker compose up -d --force-recreate orchestrator"
    echo ""
    check_fail "WORKER_SERVICE_TOKEN" "not set (required for stage 2 dispatch; add to .env and recreate orchestrator)"
fi

echo ""

# Service health checks
print_header "Service Health Checks"

check_service() {
    local name=$1
    local url=$2
    local endpoint=$3
    
    response=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 --max-time 10 "$url$endpoint" 2>/dev/null || echo "000")
    
    if [ "$response" = "200" ]; then
        check_pass "$name" "HTTP 200"
    elif [ "$response" = "000" ]; then
        check_fail "$name" "unreachable"
    else
        check_warn "$name" "HTTP $response"
    fi
}

# Check if curl is available
if ! command -v curl >/dev/null 2>&1; then
    check_fail "curl" "not installed (needed for health checks)"
else
    echo "Testing service endpoints..."
    echo ""
    check_service "Web Frontend" "$WEB_URL" "/health"
    check_service "Orchestrator Health" "$ORCHESTRATOR_URL" "/api/health"
    check_service "Worker" "$WORKER_URL" "/health"
    check_service "Guideline Engine" "$GUIDELINE_URL" "/health"
    check_service "Collab Server" "$COLLAB_URL" "/health"
    check_service "Workflows API" "$ORCHESTRATOR_URL" "/api/workflows"
    check_service "Export Manifest" "$ORCHESTRATOR_URL" "/api/export/manifest"
fi

echo ""

# Agent fleet health checks (Step 5 agents)
print_header "Agent Fleet Health Checks"

if docker ps >/dev/null 2>&1; then
    # Check if agent containers are running
    AGENT_COUNT=$(docker ps --format "{{.Names}}" 2>/dev/null | grep -c "agent-" || echo "0")
    
    if [ "$AGENT_COUNT" -gt 0 ]; then
        echo "Found $AGENT_COUNT agent containers running"
        echo ""
        
        # Evidence Synthesis Agent (commit 197bfcd)
        if docker ps --format "{{.Names}}" | grep -q "agent-evidence-synthesis"; then
            check_pass "Evidence Synthesis Agent" "container running"
            
            # Health check (port 8015 for testing, 8000 internal)
            if curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 --max-time 10 "http://127.0.0.1:8015/health" 2>/dev/null | grep -q "200"; then
                check_pass "Evidence Synthesis Health" "HTTP 200"
            else
                check_warn "Evidence Synthesis Health" "not reachable on port 8015 (may be internal-only)"
            fi
            
            # Check router registration
            if docker ps --format "{{.Names}}" | grep -q "orchestrator"; then
                AGENT_REGISTERED=$(docker compose exec -T orchestrator sh -c 'echo $AGENT_ENDPOINTS_JSON' 2>/dev/null | grep -c "agent-evidence-synthesis" || echo "0")
                if [ "$AGENT_REGISTERED" -gt 0 ]; then
                    check_pass "Evidence Synthesis Router" "registered in AGENT_ENDPOINTS_JSON"
                else
                    check_fail "Evidence Synthesis Router" "not found in AGENT_ENDPOINTS_JSON"
                fi
            fi
        else
            check_warn "Evidence Synthesis Agent" "container not running (new agent, may not be started yet)"
        fi
        
        # Literature Triage Agent (commit c1a42c1)
        if docker ps --format "{{.Names}}" | grep -q "agent-lit-triage"; then
            check_pass "Literature Triage Agent" "container running"
            
            # Health check via docker exec (internal network)
            LIT_TRIAGE_HEALTH=$(docker compose exec -T agent-lit-triage curl -f http://localhost:8000/health 2>/dev/null || echo "FAIL")
            if echo "$LIT_TRIAGE_HEALTH" | grep -q "ok"; then
                check_pass "Literature Triage Health" "HTTP 200"
            else
                check_warn "Literature Triage Health" "health endpoint not responding"
            fi
            
            # Check router registration
            if docker ps --format "{{.Names}}" | grep -q "orchestrator"; then
                AGENT_REGISTERED=$(docker compose exec -T orchestrator sh -c 'echo $AGENT_ENDPOINTS_JSON' 2>/dev/null | grep -c "agent-lit-triage" || echo "0")
                if [ "$AGENT_REGISTERED" -gt 0 ]; then
                    check_pass "Literature Triage Router" "registered in AGENT_ENDPOINTS_JSON"
                else
                    check_fail "Literature Triage Router" "not found in AGENT_ENDPOINTS_JSON"
                fi
            fi
        else
            check_warn "Literature Triage Agent" "container not running (new agent, may not be started yet)"
        fi
        
        # Clinical Manuscript Writer Agent (commit 040b13f - LangSmith-based, not containerized)
        if docker ps --format "{{.Names}}" | grep -q "orchestrator"; then
            # Check if LANGSMITH_API_KEY is configured (LangSmith cloud integration)
            LANGSMITH_KEY_SET=$(docker compose exec -T orchestrator sh -c 'echo ${LANGSMITH_API_KEY:+SET}' 2>/dev/null || echo "")
            if [ "$LANGSMITH_KEY_SET" = "SET" ]; then
                check_pass "Clinical Manuscript Writer" "LANGSMITH_API_KEY configured"
                
                # Check if task type is registered in ai-router
                ROUTER_CHECK=$(docker compose exec -T orchestrator grep -c "CLINICAL_MANUSCRIPT_WRITE" /app/src/routes/ai-router.ts 2>/dev/null || echo "0")
                if [ "$ROUTER_CHECK" -gt 0 ]; then
                    check_pass "Manuscript Writer Router" "task type registered"
                else
                    check_fail "Manuscript Writer Router" "CLINICAL_MANUSCRIPT_WRITE not found in ai-router.ts"
                fi
            else
                check_warn "Clinical Manuscript Writer" "LANGSMITH_API_KEY not set (optional: add to .env for manuscript generation)"
            fi
        fi
        
        # Clinical Study Section Drafter Agent (commit 6a5c93e - LangSmith-based, not containerized)
        if docker ps --format "{{.Names}}" | grep -q "orchestrator"; then
            # Check if LANGSMITH_API_KEY is configured (same key as Manuscript Writer)
            LANGSMITH_KEY_SET=$(docker compose exec -T orchestrator sh -c 'echo ${LANGSMITH_API_KEY:+SET}' 2>/dev/null || echo "")
            if [ "$LANGSMITH_KEY_SET" = "SET" ]; then
                check_pass "Clinical Section Drafter" "LANGSMITH_API_KEY configured"
                
                # Check if task type is registered in ai-router
                ROUTER_CHECK=$(docker compose exec -T orchestrator grep -c "CLINICAL_SECTION_DRAFT" /app/src/routes/ai-router.ts 2>/dev/null || echo "0")
                if [ "$ROUTER_CHECK" -gt 0 ]; then
                    check_pass "Section Drafter Router" "task type registered"
                else
                    check_fail "Section Drafter Router" "CLINICAL_SECTION_DRAFT not found in ai-router.ts"
                fi
            else
                check_warn "Clinical Section Drafter" "LANGSMITH_API_KEY not set (optional: add to .env for specialized section drafting)"
            fi
        fi
        
        # Results Interpretation Agent (LangSmith-based, not containerized)
        if docker ps --format "{{.Names}}" | grep -q "orchestrator"; then
            # Check if LANGSMITH_API_KEY is configured (same key as Manuscript Writer / Section Drafter)
            LANGSMITH_KEY_SET=$(docker compose exec -T orchestrator sh -c 'echo ${LANGSMITH_API_KEY:+SET}' 2>/dev/null || echo "")
            if [ "$LANGSMITH_KEY_SET" = "SET" ]; then
                check_pass "Results Interpretation Agent" "LANGSMITH_API_KEY configured"
                
                # Check if task type is registered in ai-router
                ROUTER_CHECK=$(docker compose exec -T orchestrator grep -c "RESULTS_INTERPRETATION" /app/src/routes/ai-router.ts 2>/dev/null || echo "0")
                if [ "$ROUTER_CHECK" -gt 0 ]; then
                    check_pass "Results Interpretation Router" "task type registered"
                else
                    check_fail "Results Interpretation Router" "RESULTS_INTERPRETATION not found in ai-router.ts"
                fi
                
                # Check if agent is in AGENT_ENDPOINTS_JSON (expected: not yet)
                RI_IN_ENDPOINTS=$(docker compose exec -T orchestrator sh -c 'echo $AGENT_ENDPOINTS_JSON' 2>/dev/null | grep -c "agent-results-interpretation" || echo "0")
                if [ "$RI_IN_ENDPOINTS" -gt 0 ]; then
                    check_pass "Results Interpretation Endpoints" "registered in AGENT_ENDPOINTS_JSON"
                else
                    check_warn "Results Interpretation Endpoints" "not in AGENT_ENDPOINTS_JSON (dispatch will fail until LangSmith proxy is configured)"
                fi
            else
                check_warn "Results Interpretation Agent" "LANGSMITH_API_KEY not set (optional: add to .env for results interpretation)"
            fi
        fi
        
        # Peer Review Simulator Agent (LangSmith-based proxy for Stage 13)
        if docker ps --format "{{.Names}}" | grep -q "orchestrator"; then
            # Check if LANGSMITH_API_KEY is configured
            LANGSMITH_KEY_SET=$(docker compose exec -T orchestrator sh -c 'echo ${LANGSMITH_API_KEY:+SET}' 2>/dev/null || echo "")
            if [ "$LANGSMITH_KEY_SET" = "SET" ]; then
                check_pass "Peer Review Simulator" "LANGSMITH_API_KEY configured"
                
                # Check if task type is registered in ai-router
                ROUTER_CHECK=$(docker compose exec -T orchestrator grep -c "PEER_REVIEW_SIMULATION" /app/src/routes/ai-router.ts 2>/dev/null || echo "0")
                if [ "$ROUTER_CHECK" -gt 0 ]; then
                    check_pass "Peer Review Router" "task type registered"
                else
                    check_fail "Peer Review Router" "PEER_REVIEW_SIMULATION not found in ai-router.ts"
                fi
            else
                check_warn "Peer Review Simulator" "LANGSMITH_API_KEY not set (optional: add to .env for Stage 13 comprehensive review)"
            fi
        fi
        
        # Clinical Bias Detection Agent (LangSmith-based proxy for Stage 4b/7/9/14)
        if docker ps --format "{{.Names}}" | grep -q "orchestrator"; then
            # Check if LANGSMITH_API_KEY is configured
            LANGSMITH_KEY_SET=$(docker compose exec -T orchestrator sh -c 'echo ${LANGSMITH_API_KEY:+SET}' 2>/dev/null || echo "")
            if [ "$LANGSMITH_KEY_SET" = "SET" ]; then
                check_pass "Clinical Bias Detection" "LANGSMITH_API_KEY configured"
                
                # Check if LANGSMITH_BIAS_DETECTION_AGENT_ID is set
                BIAS_AGENT_ID_SET=$(docker compose exec -T orchestrator sh -c 'echo ${LANGSMITH_BIAS_DETECTION_AGENT_ID:+SET}' 2>/dev/null || echo "")
                if [ "$BIAS_AGENT_ID_SET" = "SET" ]; then
                    check_pass "Bias Detection Agent ID" "configured"
                else
                    check_fail "Bias Detection Agent ID" "LANGSMITH_BIAS_DETECTION_AGENT_ID not set (required for bias detection)"
                    echo ""
                    echo -e "${YELLOW}Remediation:${NC}"
                    echo "  1. Get Agent ID from LangSmith: https://smith.langchain.com/"
                    echo "  2. Add to .env: LANGSMITH_BIAS_DETECTION_AGENT_ID=<uuid>"
                    echo "  3. Recreate proxy: docker compose up -d --force-recreate agent-bias-detection-proxy"
                    echo ""
                fi
                
                # Check if task type is registered in ai-router
                ROUTER_CHECK=$(docker compose exec -T orchestrator grep -c "CLINICAL_BIAS_DETECTION" /app/src/routes/ai-router.ts 2>/dev/null || echo "0")
                if [ "$ROUTER_CHECK" -gt 0 ]; then
                    check_pass "Bias Detection Router" "task type registered"
                else
                    check_fail "Bias Detection Router" "CLINICAL_BIAS_DETECTION not found in ai-router.ts"
                fi
                
                # Check if proxy container is running
                if docker ps --format "{{.Names}}" | grep -q "agent-bias-detection-proxy"; then
                    check_pass "Bias Detection Proxy" "container running"
                    
                    # Check proxy health
                    PROXY_HEALTH=$(docker compose exec -T agent-bias-detection-proxy curl -f http://localhost:8000/health 2>/dev/null || echo "FAIL")
                    if echo "$PROXY_HEALTH" | grep -q "ok"; then
                        check_pass "Bias Detection Health" "proxy responding"
                    else
                        check_warn "Bias Detection Health" "health endpoint not responding"
                    fi
                else
                    check_warn "Bias Detection Proxy" "container not running (may not be started yet)"
                fi
            else
                check_warn "Clinical Bias Detection" "LANGSMITH_API_KEY not set (optional: add to .env for bias detection)"
            fi
        fi
        
        # Other Stage 2 agents
        for agent in "agent-stage2-lit" "agent-stage2-screen" "agent-stage2-extract"; do
            if docker ps --format "{{.Names}}" | grep -q "$agent"; then
                check_pass "$agent" "running"
            else
                check_warn "$agent" "not running"
            fi
        done
    else
        check_warn "Agent containers" "no agent containers found (may not be deployed yet)"
    fi
else
    check_fail "Docker status" "cannot check agent containers"
fi

echo ""

# Summary
print_header "Summary"

echo -e "Results: ${GREEN}$PASSED passed${NC}, ${YELLOW}$WARNINGS warnings${NC}, ${RED}$FAILED failed${NC}"
echo ""

if [ $FAILED -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✓ All preflight checks passed!${NC}"
    echo -e "${GREEN}✓ System is ready for ResearchFlow deployment.${NC}"
    exit 0
elif [ $FAILED -eq 0 ]; then
    echo -e "${YELLOW}⚠ Preflight checks passed with warnings.${NC}"
    echo -e "${YELLOW}⚠ Review warnings above before proceeding.${NC}"
    exit 0
else
    echo -e "${RED}✗ Preflight checks failed!${NC}"
    echo -e "${RED}✗ Fix the issues above before deploying.${NC}"
    exit 1
fi
