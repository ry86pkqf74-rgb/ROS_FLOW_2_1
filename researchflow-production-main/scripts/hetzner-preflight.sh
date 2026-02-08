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

# Agent fleet health checks - MANDATORY (all agents must be healthy)
print_header "Mandatory Agent Fleet Validation"

# Load mandatory agent list
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENT_LIST_FILE="${SCRIPT_DIR}/lib/agent_endpoints_required.txt"

if [ ! -f "$AGENT_LIST_FILE" ]; then
    check_fail "Agent List File" "$AGENT_LIST_FILE not found"
    echo ""
    echo -e "${RED}CRITICAL: Mandatory agent list missing!${NC}"
    echo "Expected: ${AGENT_LIST_FILE}"
    exit 1
fi

# Parse mandatory agents (skip comments and empty lines)
MANDATORY_AGENTS=()
while IFS= read -r line || [ -n "$line" ]; do
    # Skip comments and empty lines
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    [[ -z "${line// }" ]] && continue
    MANDATORY_AGENTS+=("$(echo "$line" | xargs)")  # trim whitespace
done < "$AGENT_LIST_FILE"

echo "Loaded ${#MANDATORY_AGENTS[@]} mandatory agents from $AGENT_LIST_FILE"
echo ""

# Validate AGENT_ENDPOINTS_JSON is present and parseable
if ! docker ps --format "{{.Names}}" | grep -q "orchestrator"; then
    check_fail "Orchestrator" "container not running - cannot validate agents"
    echo ""
    echo -e "${RED}CRITICAL: Orchestrator must be running to validate agent configuration!${NC}"
    echo "Start orchestrator: docker compose up -d orchestrator"
    exit 1
fi

echo "Validating AGENT_ENDPOINTS_JSON configuration..."
ENDPOINTS_JSON=$(docker compose exec -T orchestrator sh -c 'echo $AGENT_ENDPOINTS_JSON' 2>/dev/null || echo "")

if [ -z "$ENDPOINTS_JSON" ]; then
    check_fail "AGENT_ENDPOINTS_JSON" "not set in orchestrator"
    echo ""
    echo -e "${RED}CRITICAL: AGENT_ENDPOINTS_JSON is not configured!${NC}"
    echo "Add to docker-compose.yml orchestrator environment and restart."
    exit 1
fi

# Validate JSON is parseable
if ! echo "$ENDPOINTS_JSON" | python3 -m json.tool >/dev/null 2>&1; then
    check_fail "AGENT_ENDPOINTS_JSON" "invalid JSON"
    echo ""
    echo -e "${RED}CRITICAL: AGENT_ENDPOINTS_JSON is not valid JSON!${NC}"
    echo "Fix the JSON syntax in docker-compose.yml and restart orchestrator."
    exit 1
fi

check_pass "AGENT_ENDPOINTS_JSON" "valid JSON with $(echo "$ENDPOINTS_JSON" | python3 -c 'import json,sys; print(len(json.load(sys.stdin)))' 2>/dev/null || echo '?') entries"
echo ""

# Validate each mandatory agent
echo "Validating ${#MANDATORY_AGENTS[@]} mandatory agents..."
echo ""

AGENT_VALIDATION_FAILED=0

for agent_key in "${MANDATORY_AGENTS[@]}"; do
    echo "Checking: $agent_key"
    
    # 1. Check if agent is in AGENT_ENDPOINTS_JSON
    AGENT_URL=$(echo "$ENDPOINTS_JSON" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('$agent_key', ''))" 2>/dev/null || echo "")
    
    if [ -z "$AGENT_URL" ]; then
        check_fail "  $agent_key [Registry]" "not found in AGENT_ENDPOINTS_JSON"
        AGENT_VALIDATION_FAILED=1
        echo ""
        echo -e "${YELLOW}  Remediation:${NC}"
        echo "    Add to AGENT_ENDPOINTS_JSON: \"$agent_key\":\"http://$agent_key:8000\""
        echo "    Then: docker compose up -d --force-recreate orchestrator"
        echo ""
        continue
    fi
    
    check_pass "  $agent_key [Registry]" "URL: $AGENT_URL"
    
    # 2. Extract service name and port from URL (format: http://service-name:port)
    SERVICE_NAME=$(echo "$AGENT_URL" | sed -n 's|^http://\([^:]*\):.*|\1|p')
    SERVICE_PORT=$(echo "$AGENT_URL" | sed -n 's|^http://[^:]*:\([0-9]*\).*|\1|p')
    
    if [ -z "$SERVICE_NAME" ] || [ -z "$SERVICE_PORT" ]; then
        check_fail "  $agent_key [URL Parse]" "invalid URL format: $AGENT_URL"
        AGENT_VALIDATION_FAILED=1
        echo "    Expected format: http://service-name:port"
        echo ""
        continue
    fi
    
    # 3. Check if container is running
    if ! docker ps --format "{{.Names}}" | grep -q "^${SERVICE_NAME}$\|^researchflow-${SERVICE_NAME}$"; then
        check_fail "  $agent_key [Container]" "not running"
        AGENT_VALIDATION_FAILED=1
        echo ""
        echo -e "${YELLOW}  Remediation:${NC}"
        echo "    Start container: docker compose up -d $SERVICE_NAME"
        echo "    Check logs: docker compose logs $SERVICE_NAME"
        echo ""
        continue
    fi
    
    check_pass "  $agent_key [Container]" "running"
    
    # 4. Health check via docker exec (internal network)
    HEALTH_CHECK=$(docker compose exec -T "$SERVICE_NAME" curl -f "http://localhost:${SERVICE_PORT}/health" 2>/dev/null || echo "FAIL")
    
    if echo "$HEALTH_CHECK" | grep -q "ok\|healthy\|status.*ok"; then
        check_pass "  $agent_key [Health]" "responding"
    else
        check_fail "  $agent_key [Health]" "not responding or unhealthy"
        AGENT_VALIDATION_FAILED=1
        echo ""
        echo -e "${YELLOW}  Remediation:${NC}"
        echo "    Check logs: docker compose logs $SERVICE_NAME"
        echo "    Restart: docker compose restart $SERVICE_NAME"
        echo "    Test health: docker compose exec $SERVICE_NAME curl http://localhost:${SERVICE_PORT}/health"
        echo ""
        continue
    fi
    
    echo ""
done

if [ $AGENT_VALIDATION_FAILED -gt 0 ]; then
    echo ""
    echo -e "${RED}✗ One or more mandatory agents failed validation!${NC}"
    echo -e "${RED}✗ All agents must be running and healthy before deployment.${NC}"
    echo ""
    echo "Quick fixes:"
    echo "  1. Start all agents: docker compose up -d"
    echo "  2. Check failed agents: docker compose ps | grep -v 'Up'"
    echo "  3. View logs: docker compose logs <failed-service>"
    echo ""
    FAILED=$((FAILED + 1))
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
    echo ""
    echo "Note: Warnings do not block deployment but should be addressed."
    exit 0
else
    echo -e "${RED}✗ Preflight checks FAILED!${NC}"
    echo -e "${RED}✗ CRITICAL: Fix all failed checks before deploying.${NC}"
    echo ""
    echo "Failed checks must be resolved. Deployment is blocked."
    echo "Common issues:"
    echo "  - Missing agents: Ensure all services in AGENT_ENDPOINTS_JSON are running"
    echo "  - Unhealthy agents: Check container logs with 'docker compose logs <service>'"
    echo "  - Configuration errors: Verify AGENT_ENDPOINTS_JSON JSON syntax"
    echo ""
    exit 1
fi
