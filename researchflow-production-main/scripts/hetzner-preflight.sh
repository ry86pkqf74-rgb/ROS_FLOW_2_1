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
write_validation_artifact() {
    local agent_key="$1"
    local timestamp="$2"
    local status="$3"
    local container_running="$4"
    local health_endpoint="$5"
    local health_status="$6"
    local langsmith_status="$7"
    local error_msg="$8"
    local agent_url="$9"
    local service_name="${10:-}"
    
    local artifact_dir="/data/artifacts/validation/${agent_key}/${timestamp}"
    mkdir -p "$artifact_dir" 2>/dev/null || return 1
    
    python3 -c "
import json
import sys
data = {
    'agentKey': sys.argv[1],
    'validation_script': 'hetzner-preflight.sh',
    'timestamp': sys.argv[2],
    'status': sys.argv[3],
    'container_running': sys.argv[4].lower() == 'true',
    'health_endpoint': sys.argv[5],
    'health_response_status': sys.argv[6],
    'langsmith_info_status': sys.argv[7],
    'error': sys.argv[8] if sys.argv[8] else None,
    'agent_url': sys.argv[9]
}
if len(sys.argv) > 10 and sys.argv[10]:
    data['service_name'] = sys.argv[10]
json.dump(data, sys.stdout, indent=2)
" "$agent_key" "$timestamp" "$status" "$container_running" "$health_endpoint" \
  "$health_status" "$langsmith_status" "$error_msg" "$agent_url" "$service_name" \
  > "${artifact_dir}/summary.json" 2>/dev/null || return 1
    
    return 0
}

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
    check_service "Orchestrator Health" "$ORCHESTRATOR_URL" "/health"
    check_service "Worker" "$WORKER_URL" "/health"
    check_service "Guideline Engine" "$GUIDELINE_URL" "/health"
    check_service "Collab Server" "$COLLAB_URL" "/health"
    check_service "Workflows API" "$ORCHESTRATOR_URL" "/api/workflows"
    check_service "Export Manifest" "$ORCHESTRATOR_URL" "/api/export/manifest"
fi

echo ""

# ==============================================================================
# Mandatory Agent Fleet Validation (Dynamic from AGENT_ENDPOINTS_JSON)
# ==============================================================================
print_header "Mandatory Agent Fleet Validation"

# Validate orchestrator is running
if ! docker ps --format "{{.Names}}" | grep -q "orchestrator"; then
    check_fail "Orchestrator" "container not running - cannot validate agents"
    echo ""
    echo -e "${RED}CRITICAL: Orchestrator must be running to validate agent configuration!${NC}"
    echo "Start orchestrator: docker compose up -d orchestrator"
    exit 1
fi

# Fetch AGENT_ENDPOINTS_JSON from orchestrator
echo "Fetching AGENT_ENDPOINTS_JSON from orchestrator..."
ENDPOINTS_JSON=$(docker compose exec -T orchestrator sh -c 'echo $AGENT_ENDPOINTS_JSON' 2>/dev/null || echo "")

if [ -z "$ENDPOINTS_JSON" ]; then
    check_fail "AGENT_ENDPOINTS_JSON" "not set in orchestrator"
    echo ""
    echo -e "${RED}CRITICAL: AGENT_ENDPOINTS_JSON is not configured!${NC}"
    echo ""
    echo "Remediation:"
    echo "  1. Add AGENT_ENDPOINTS_JSON to docker-compose.yml orchestrator environment"
    echo "  2. Restart orchestrator: docker compose up -d --force-recreate orchestrator"
    echo "  3. Verify: docker compose exec orchestrator sh -c 'echo \$AGENT_ENDPOINTS_JSON'"
    echo ""
    exit 1
fi

# Validate JSON is parseable
if ! echo "$ENDPOINTS_JSON" | python3 -m json.tool >/dev/null 2>&1; then
    check_fail "AGENT_ENDPOINTS_JSON" "invalid JSON"
    echo ""
    echo -e "${RED}CRITICAL: AGENT_ENDPOINTS_JSON is not valid JSON!${NC}"
    echo ""
    echo "Current value (first 200 chars):"
    echo "$ENDPOINTS_JSON" | head -c 200
    echo ""
    echo "Remediation:"
    echo "  1. Fix the JSON syntax in docker-compose.yml orchestrator environment"
    echo "  2. Validate JSON: echo '\$AGENT_ENDPOINTS_JSON' | python3 -m json.tool"
    echo "  3. Restart orchestrator: docker compose up -d --force-recreate orchestrator"
    echo ""
    exit 1
fi

# Dynamically derive mandatory agent keys from AGENT_ENDPOINTS_JSON
MANDATORY_AGENT_KEYS=$(echo "$ENDPOINTS_JSON" | python3 -c 'import json,sys; print("\n".join(sorted(json.load(sys.stdin).keys())))' 2>/dev/null || echo "")

if [ -z "$MANDATORY_AGENT_KEYS" ]; then
    check_fail "Agent Keys" "failed to parse AGENT_ENDPOINTS_JSON"
    echo ""
    echo -e "${RED}CRITICAL: Could not extract agent keys from AGENT_ENDPOINTS_JSON!${NC}"
    exit 1
fi

# Convert to array
MANDATORY_AGENTS=()
while IFS= read -r agent_key; do
    [ -n "$agent_key" ] && MANDATORY_AGENTS+=("$agent_key")
done <<< "$MANDATORY_AGENT_KEYS"

AGENT_COUNT=${#MANDATORY_AGENTS[@]}
check_pass "AGENT_ENDPOINTS_JSON" "valid JSON with $AGENT_COUNT agent(s)"
echo ""
echo "Dynamically derived $AGENT_COUNT mandatory agents from AGENT_ENDPOINTS_JSON"
echo ""

# Validate required environment variables (names only, no values)
echo "Validating required environment variables..."
REQUIRED_ENV_VARS=(
    "WORKER_SERVICE_TOKEN"
    "LANGSMITH_API_KEY"
    "LANGSMITH_ARTIFACT_AUDITOR_AGENT_ID"
    "LANGSMITH_RESILIENCE_ARCHITECTURE_ADVISOR_AGENT_ID"
    "LANGSMITH_MULTILINGUAL_LITERATURE_PROCESSOR_AGENT_ID"
    "LANGSMITH_HYPOTHESIS_REFINER_AGENT_ID"
)

# Check each required env var
ENV_VAR_MISSING=0
for var_name in "${REQUIRED_ENV_VARS[@]}"; do
    VAR_CHECK=$(docker compose exec -T orchestrator sh -c "echo \${${var_name}:+SET}" 2>/dev/null || echo "")
    if [ "$VAR_CHECK" = "SET" ]; then
        check_pass "  $var_name" "configured"
    else
        check_fail "  $var_name" "not set"
        ENV_VAR_MISSING=1
    fi
done

if [ $ENV_VAR_MISSING -gt 0 ]; then
    echo ""
    echo -e "${YELLOW}Warning: Some required environment variables are missing.${NC}"
    echo "LangSmith-backed agents may fail without LANGSMITH_API_KEY."
    echo ""
fi

echo ""

# Validate each mandatory agent
echo "Validating $AGENT_COUNT mandatory agents..."
echo ""

AGENT_VALIDATION_FAILED=0

for agent_key in "${MANDATORY_AGENTS[@]}"; do
    echo "Checking: $agent_key"
    
    # Initialize artifact variables
    ARTIFACT_STATUS="unknown"
    ARTIFACT_CONTAINER_RUNNING=false
    ARTIFACT_HEALTH_ENDPOINT="none"
    ARTIFACT_HEALTH_STATUS="unknown"
    ARTIFACT_LANGSMITH_INFO_STATUS="N/A"
    ARTIFACT_ERROR=""
    
    # 1. Get agent URL from AGENT_ENDPOINTS_JSON
    AGENT_URL=$(echo "$ENDPOINTS_JSON" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('$agent_key', ''))" 2>/dev/null || echo "")
    
    if [ -z "$AGENT_URL" ]; then
        check_fail "  $agent_key [Registry]" "missing from AGENT_ENDPOINTS_JSON (unexpected)"
        AGENT_VALIDATION_FAILED=1
        ARTIFACT_STATUS="fail"
        ARTIFACT_ERROR="missing from AGENT_ENDPOINTS_JSON"
        
        # Write failure artifact
        TIMESTAMP=$(date -u +%Y%m%dT%H%M%SZ)
        if ! write_validation_artifact "$agent_key" "$TIMESTAMP" "$ARTIFACT_STATUS" \
            "${ARTIFACT_CONTAINER_RUNNING}" "$ARTIFACT_HEALTH_ENDPOINT" "$ARTIFACT_HEALTH_STATUS" \
            "$ARTIFACT_LANGSMITH_INFO_STATUS" "$ARTIFACT_ERROR" "$AGENT_URL"; then
            echo "  Warning: Could not write artifact (permissions or /data not mounted)"
            AGENT_VALIDATION_FAILED=1
        fi
        
        echo ""
        continue
    fi
    
    # 2. Validate URL format
    if ! echo "$AGENT_URL" | grep -qE '^https?://'; then
        check_fail "  $agent_key [URL]" "invalid format: $AGENT_URL"
        AGENT_VALIDATION_FAILED=1
        ARTIFACT_STATUS="fail"
        ARTIFACT_ERROR="invalid URL format: $AGENT_URL"
        
        # Write failure artifact
        TIMESTAMP=$(date -u +%Y%m%dT%H%M%SZ)
        write_validation_artifact "$agent_key" "$TIMESTAMP" "$ARTIFACT_STATUS" \
            "${ARTIFACT_CONTAINER_RUNNING}" "$ARTIFACT_HEALTH_ENDPOINT" "$ARTIFACT_HEALTH_STATUS" \
            "$ARTIFACT_LANGSMITH_INFO_STATUS" "$ARTIFACT_ERROR" "$AGENT_URL" >/dev/null 2>&1
        
        echo ""
        echo -e "${YELLOW}  Remediation:${NC}"
        echo "    URL must start with http:// or https://"
        echo "    Update AGENT_ENDPOINTS_JSON in docker-compose.yml"
        echo ""
        continue
    fi
    
    check_pass "  $agent_key [Registry]" "$AGENT_URL"
    
    # 3. Extract service name and port from URL (format: http://service-name:port)
    SERVICE_NAME=$(echo "$AGENT_URL" | sed -n 's|^https\?://\([^:]*\):.*|\1|p')
    SERVICE_PORT=$(echo "$AGENT_URL" | sed -n 's|^https\?://[^:]*:\([0-9]*\).*|\1|p')
    
    if [ -z "$SERVICE_NAME" ] || [ -z "$SERVICE_PORT" ]; then
        check_fail "  $agent_key [URL Parse]" "invalid URL format: $AGENT_URL"
        AGENT_VALIDATION_FAILED=1
        ARTIFACT_STATUS="fail"
        ARTIFACT_ERROR="URL parse failed: expected format http://service-name:port"
        
        # Write failure artifact
        TIMESTAMP=$(date -u +%Y%m%dT%H%M%SZ)
        write_validation_artifact "$agent_key" "$TIMESTAMP" "$ARTIFACT_STATUS" \
            "${ARTIFACT_CONTAINER_RUNNING}" "$ARTIFACT_HEALTH_ENDPOINT" "$ARTIFACT_HEALTH_STATUS" \
            "$ARTIFACT_LANGSMITH_INFO_STATUS" "$ARTIFACT_ERROR" "$AGENT_URL" "parse_failed" >/dev/null 2>&1
        
        echo "    Expected format: http://service-name:port"
        echo ""
        continue
    fi
    
    # 4. Check if container is running
    if ! docker ps --format "{{.Names}}" | grep -q "^${SERVICE_NAME}$\|^researchflow-${SERVICE_NAME}$"; then
        check_fail "  $agent_key [Container]" "not running"
        AGENT_VALIDATION_FAILED=1
        ARTIFACT_STATUS="fail"
        ARTIFACT_CONTAINER_RUNNING=false
        ARTIFACT_ERROR="Container ${SERVICE_NAME} not running"
        
        # Write failure artifact
        TIMESTAMP=$(date -u +%Y%m%dT%H%M%SZ)
        write_validation_artifact "$agent_key" "$TIMESTAMP" "$ARTIFACT_STATUS" \
            "false" "$ARTIFACT_HEALTH_ENDPOINT" "$ARTIFACT_HEALTH_STATUS" \
            "$ARTIFACT_LANGSMITH_INFO_STATUS" "$ARTIFACT_ERROR" "$AGENT_URL" "$SERVICE_NAME" >/dev/null 2>&1
        
        echo ""
        echo -e "${YELLOW}  Remediation:${NC}"
        echo "    Start container: docker compose up -d $SERVICE_NAME"
        echo "    Check compose definition: grep -A 20 '${SERVICE_NAME}:' docker-compose.yml"
        echo "    Check logs: docker compose logs $SERVICE_NAME"
        echo ""
        continue
    fi
    
    ARTIFACT_CONTAINER_RUNNING=true
    check_pass "  $agent_key [Container]" "running"
    
    # 5. Health check via docker exec (internal network)
    # Try /health/ready first (preferred), then /health, then /api/health, then /routes/health (fallback for legacy agents)
    HEALTH_CHECK=$(docker compose exec -T "$SERVICE_NAME" curl -fsS "http://localhost:${SERVICE_PORT}/health/ready" 2>/dev/null || echo "")
    HEALTH_ENDPOINT="/health/ready"
    
    if [ -z "$HEALTH_CHECK" ]; then
        # Try /health
        HEALTH_CHECK=$(docker compose exec -T "$SERVICE_NAME" curl -fsS "http://localhost:${SERVICE_PORT}/health" 2>/dev/null || echo "")
        HEALTH_ENDPOINT="/health"
    fi
    
    if [ -z "$HEALTH_CHECK" ]; then
        # Try /api/health
        HEALTH_CHECK=$(docker compose exec -T "$SERVICE_NAME" curl -fsS "http://localhost:${SERVICE_PORT}/api/health" 2>/dev/null || echo "")
        if [ -n "$HEALTH_CHECK" ]; then
            HEALTH_ENDPOINT="/api/health"
            check_warn "  $agent_key [Health]" "responds at /api/health (non-standard)"
        fi
    fi
    
    if [ -z "$HEALTH_CHECK" ]; then
        # Try /routes/health
        HEALTH_CHECK=$(docker compose exec -T "$SERVICE_NAME" curl -fsS "http://localhost:${SERVICE_PORT}/routes/health" 2>/dev/null || echo "")
        if [ -n "$HEALTH_CHECK" ]; then
            HEALTH_ENDPOINT="/routes/health"
            check_warn "  $agent_key [Health]" "responds at /routes/health (non-standard)"
        fi
    fi
    
    # Set artifact health endpoint
    ARTIFACT_HEALTH_ENDPOINT="$HEALTH_ENDPOINT"
    if [ -n "$HEALTH_CHECK" ]; then
        ARTIFACT_HEALTH_STATUS="200"
    else
        ARTIFACT_HEALTH_STATUS="unreachable"
    fi
    
    # For proxy agents, validate upstream LangSmith /info is reachable (enforce readiness)
    if [[ "$agent_key" == *"-proxy" ]]; then
        # Check if LangSmith API is reachable (required for proxy readiness)
        LANGSMITH_KEY=$(docker compose exec -T orchestrator sh -c 'echo ${LANGSMITH_API_KEY}' 2>/dev/null || echo "")
        if [ -n "$LANGSMITH_KEY" ]; then
            LANGSMITH_API_URL="${LANGSMITH_API_URL:-https://api.smith.langchain.com/api/v1}"
            LANGSMITH_INFO_STATUS=$(docker compose exec -T "$SERVICE_NAME" sh -c "curl -fsS -o /dev/null -w '%{http_code}' -H 'x-api-key: \$LANGSMITH_API_KEY' ${LANGSMITH_API_URL}/info 2>/dev/null" || echo "000")
            ARTIFACT_LANGSMITH_INFO_STATUS="$LANGSMITH_INFO_STATUS"
            
            if [ "$LANGSMITH_INFO_STATUS" = "200" ]; then
                check_pass "  $agent_key [LangSmith]" "upstream /info returns 2xx"
            elif [ "$LANGSMITH_INFO_STATUS" = "401" ] || [ "$LANGSMITH_INFO_STATUS" = "403" ] || [ "$LANGSMITH_INFO_STATUS" = "404" ]; then
                check_fail "  $agent_key [LangSmith]" "upstream /info returns $LANGSMITH_INFO_STATUS (auth/not found)"
                AGENT_VALIDATION_FAILED=1
                ARTIFACT_STATUS="fail"
                ARTIFACT_ERROR="LangSmith upstream /info returns $LANGSMITH_INFO_STATUS"
                
                # Write failure artifact
                TIMESTAMP=$(date -u +%Y%m%dT%H%M%SZ)
                write_validation_artifact "$agent_key" "$TIMESTAMP" "$ARTIFACT_STATUS" \
                    "true" "$ARTIFACT_HEALTH_ENDPOINT" "$ARTIFACT_HEALTH_STATUS" \
                    "$ARTIFACT_LANGSMITH_INFO_STATUS" "$ARTIFACT_ERROR" "$AGENT_URL" "$SERVICE_NAME" >/dev/null 2>&1
                
                echo ""
                echo -e "${YELLOW}  Remediation:${NC}"
                echo "    Verify LANGSMITH_API_KEY is valid in .env"
                echo "    Check LangSmith account status: https://smith.langchain.com"
                echo "    Restart proxy: docker compose restart $SERVICE_NAME"
                echo ""
                continue
            else
                check_fail "  $agent_key [LangSmith]" "upstream /info returns non-2xx: $LANGSMITH_INFO_STATUS"
                AGENT_VALIDATION_FAILED=1
                ARTIFACT_STATUS="fail"
                ARTIFACT_ERROR="LangSmith upstream /info returns non-2xx: $LANGSMITH_INFO_STATUS"
                
                # Write failure artifact
                TIMESTAMP=$(date -u +%Y%m%dT%H%M%SZ)
                write_validation_artifact "$agent_key" "$TIMESTAMP" "$ARTIFACT_STATUS" \
                    "true" "$ARTIFACT_HEALTH_ENDPOINT" "$ARTIFACT_HEALTH_STATUS" \
                    "$ARTIFACT_LANGSMITH_INFO_STATUS" "$ARTIFACT_ERROR" "$AGENT_URL" "$SERVICE_NAME" >/dev/null 2>&1
                
                echo ""
                echo -e "${YELLOW}  Remediation:${NC}"
                echo "    Check network connectivity to https://api.smith.langchain.com"
                echo "    Verify LANGSMITH_API_KEY is set: docker compose exec orchestrator env | grep LANGSMITH"
                echo ""
                continue
            fi
        else
            check_warn "  $agent_key [LangSmith]" "LANGSMITH_API_KEY not set (readiness check skipped)"
            ARTIFACT_LANGSMITH_INFO_STATUS="key_not_set"
        fi
    fi
    
    if echo "$HEALTH_CHECK" | grep -qiE '"?ok"?|"?healthy"?|"?status"?:\s*"?ok"?'; then
        check_pass "  $agent_key [Health]" "responding"
        ARTIFACT_STATUS="pass"
    else
        check_fail "  $agent_key [Health]" "not responding or unhealthy"
        AGENT_VALIDATION_FAILED=1
        ARTIFACT_STATUS="fail"
        ARTIFACT_ERROR="Health check failed or unhealthy response"
        
        # Write failure artifact
        TIMESTAMP=$(date -u +%Y%m%dT%H%M%SZ)
        write_validation_artifact "$agent_key" "$TIMESTAMP" "$ARTIFACT_STATUS" \
            "true" "$ARTIFACT_HEALTH_ENDPOINT" "$ARTIFACT_HEALTH_STATUS" \
            "$ARTIFACT_LANGSMITH_INFO_STATUS" "$ARTIFACT_ERROR" "$AGENT_URL" "$SERVICE_NAME" >/dev/null 2>&1
        
        echo ""
        echo -e "${YELLOW}  Remediation:${NC}"
        echo "    Check logs: docker compose logs $SERVICE_NAME"
        echo "    Restart: docker compose restart $SERVICE_NAME"
        echo "    Test health: docker compose exec $SERVICE_NAME curl -v http://localhost:${SERVICE_PORT}/health"
        echo "    Check environment: docker compose exec $SERVICE_NAME env | grep -i langsmith"
        echo ""
        continue
    fi
    
    # Write success artifact
    TIMESTAMP=$(date -u +%Y%m%dT%H%M%SZ)
    if ! write_validation_artifact "$agent_key" "$TIMESTAMP" "$ARTIFACT_STATUS" \
        "true" "$ARTIFACT_HEALTH_ENDPOINT" "$ARTIFACT_HEALTH_STATUS" \
        "$ARTIFACT_LANGSMITH_INFO_STATUS" "" "$AGENT_URL" "$SERVICE_NAME"; then
        echo "  Warning: Failed to write artifact summary (permissions or /data not mounted)"
        AGENT_VALIDATION_FAILED=1
    fi
    
    echo ""
done

# Hard-fail if any agent is unhealthy
if [ $AGENT_VALIDATION_FAILED -gt 0 ]; then
    echo ""
    echo -e "${RED}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${RED}✗ PREFLIGHT FAILED: One or more mandatory agents are unhealthy!${NC}"
    echo -e "${RED}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "All agents declared in AGENT_ENDPOINTS_JSON must be running and healthy."
    echo ""
    echo "Quick fixes:"
    echo "  1. Start all agents: docker compose up -d"
    echo "  2. Check failed agents: docker compose ps | grep -E 'unhealthy|exited'"
    echo "  3. View logs: docker compose logs <failed-agent>"
    echo "  4. Rebuild if needed: docker compose build <failed-agent> && docker compose up -d <failed-agent>"
    echo ""
    echo "If an agent is not needed, remove it from AGENT_ENDPOINTS_JSON in docker-compose.yml"
    echo "and restart orchestrator: docker compose up -d --force-recreate orchestrator"
    echo ""
    exit 1
fi

echo -e "${GREEN}✓ All $AGENT_COUNT mandatory agents are running and healthy!${NC}"
echo ""

# ==============================================================================
# Preflight Summary
# ==============================================================================
print_header "Preflight Summary"

echo -e "Results: ${GREEN}$PASSED passed${NC}, ${YELLOW}$WARNINGS warnings${NC}, ${RED}$FAILED failed${NC}"
echo ""

if [ $FAILED -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}════════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}✓ ALL PREFLIGHT CHECKS PASSED!${NC}"
    echo -e "${GREEN}✓ System is ready for ResearchFlow deployment.${NC}"
    echo -e "${GREEN}════════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "Validated:"
    echo "  • $AGENT_COUNT agents running and healthy"
    echo "  • AGENT_ENDPOINTS_JSON configured correctly"
    echo "  • All required environment variables present"
    echo "  • Core services responding"
    echo ""
    echo "Next steps:"
    echo "  1. Deploy: docker compose up -d"
    echo "  2. Run smoke tests: ./scripts/stagewise-smoke.sh"
    echo "  3. Monitor: docker compose logs -f"
    echo ""
    exit 0
elif [ $FAILED -eq 0 ]; then
    echo -e "${YELLOW}════════════════════════════════════════════════════════════════${NC}"
    echo -e "${YELLOW}⚠ PREFLIGHT PASSED WITH WARNINGS${NC}"
    echo -e "${YELLOW}════════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "Review warnings above before proceeding."
    echo "Warnings do not block deployment but should be addressed."
    echo ""
    exit 0
else
    echo -e "${RED}════════════════════════════════════════════════════════════════${NC}"
    echo -e "${RED}✗ PREFLIGHT FAILED!${NC}"
    echo -e "${RED}════════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "CRITICAL: Fix all failed checks before deploying."
    echo ""
    echo "Common failure causes:"
    echo "  • Missing agents: Ensure all services in AGENT_ENDPOINTS_JSON exist in docker-compose.yml"
    echo "  • Unhealthy agents: Check container logs with 'docker compose logs <service>'"
    echo "  • Configuration errors: Verify AGENT_ENDPOINTS_JSON JSON syntax"
    echo "  • Missing env vars: Check WORKER_SERVICE_TOKEN, LANGSMITH_API_KEY in .env"
    echo ""
    echo "Quick diagnostics:"
    echo "  • List all containers: docker compose ps"
    echo "  • Check orchestrator env: docker compose exec orchestrator env | grep AGENT_ENDPOINTS_JSON"
    echo "  • View failed service logs: docker compose logs --tail=50 <service>"
    echo ""
    exit 1
fi
