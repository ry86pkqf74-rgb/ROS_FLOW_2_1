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
#   --orchestrator-url URL     Orchestrator URL (default: http://localhost:3001)
#   --worker-url URL           Worker URL (default: http://localhost:8000)
#   --guideline-url URL        Guideline Engine URL (default: http://localhost:8001)
#   --collab-url URL           Collaboration Server URL (default: http://localhost:1235)
#   --web-url URL              Web Frontend URL (default: http://localhost:5173)
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

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Default configuration
ORCHESTRATOR_URL="${ORCHESTRATOR_URL:-http://localhost:3001}"
WORKER_URL="${WORKER_URL:-http://localhost:8000}"
GUIDELINE_URL="${GUIDELINE_URL:-http://localhost:8001}"
COLLAB_URL="${COLLAB_URL:-http://localhost:1235}"
WEB_URL="${WEB_URL:-http://localhost:5173}"

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
    else
        check_warn "ResearchFlow containers" "no containers found (not started yet?)"
    fi
else
    check_fail "Docker status" "cannot list containers"
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
    check_service "Orchestrator" "$ORCHESTRATOR_URL" "/api/health"
    check_service "Web Frontend" "$WEB_URL" "/health"
    check_service "Worker" "$WORKER_URL" "/health"
    check_service "Guideline Engine" "$GUIDELINE_URL" "/health"
    check_service "Collab Server" "$COLLAB_URL" "/health"
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
