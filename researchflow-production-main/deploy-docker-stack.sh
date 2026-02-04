#!/bin/bash

################################################################################
# ResearchFlow Docker Stack Deployment Script
# Production-ready deployment with validation, health checks, and logging
# 
# Services:
#   1. orchestrator:3001  - Node.js API (Auth, RBAC, AI Router, Job Queue)
#   2. worker:8000        - Python compute (FastAPI, 20-stage workflow)
#   3. web:5173           - React frontend (Vite, shadcn/ui)
#   4. collab:1234        - Real-time collaboration (Yjs)
#   5. guideline-engine:8001 - Clinical guidelines
#   6. postgres:5432      - PostgreSQL database
#   7. redis:6379         - Cache & job queue
################################################################################

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="${SCRIPT_DIR}/deploy-$(date +%Y%m%d-%H%M%S).log"
HEALTH_CHECK_TIMEOUT=300  # 5 minutes
HEALTH_CHECK_INTERVAL=5   # 5 seconds
MAX_RETRIES=10
STRICT_ENV_CHECK=${STRICT_ENV_CHECK:-false}

# Service definitions with ports and health check endpoints
declare -A SERVICES=(
    [postgres]="5432"
    [redis]="6379"
    [orchestrator]="3001"
    [worker]="8000"
    [guideline-engine]="8001"
    [web]="5173"
    [collab]="1234"
)

declare -A HEALTH_ENDPOINTS=(
    [postgres]="postgres"
    [redis]="redis"
    [orchestrator]="http://localhost:3001/health"
    [worker]="http://localhost:8000/health"
    [guideline-engine]="http://localhost:8001/health"
    [web]="http://localhost:5173"
    [collab]="http://localhost:1234/health"
)

# Service startup dependencies
declare -A DEPENDENCIES=(
    [postgres]=""
    [redis]=""
    [orchestrator]="postgres redis"
    [worker]="postgres redis"
    [guideline-engine]="postgres"
    [web]=""
    [collab]="redis orchestrator"
)

################################################################################
# Utility Functions
################################################################################

log() {
    local level=$1
    shift
    local message="$@"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${timestamp} [${level}] ${message}" | tee -a "${LOG_FILE}"
}

log_info() {
    log "INFO" "${BLUE}$@${NC}"
}

log_success() {
    log "SUCCESS" "${GREEN}$@${NC}"
}

log_warning() {
    log "WARNING" "${YELLOW}$@${NC}"
}

log_error() {
    log "ERROR" "${RED}$@${NC}"
}

print_header() {
    echo -e "\n${BLUE}================================${NC}"
    echo -e "${BLUE}$@${NC}"
    echo -e "${BLUE}================================${NC}\n"
}

print_divider() {
    echo -e "${BLUE}----------------------------------------${NC}"
}

################################################################################
# Validation Functions
################################################################################

load_env_file() {
    local env_file="${SCRIPT_DIR}/.env"

    if [[ -f "$env_file" ]]; then
        set -a
        # shellcheck disable=SC1090
        source "$env_file"
        set +a
        log_info "Loaded environment variables from ${env_file}"
    else
        log_warning "No .env file found in ${SCRIPT_DIR}; using defaults/exports"
    fi
}

validate_environment() {
    print_header "Validating Environment"
    
    local required_vars=(
        "POSTGRES_USER"
        "POSTGRES_PASSWORD"
        "POSTGRES_DB"
        "REDIS_PASSWORD"
        "NODE_ENV"
        "VITE_API_BASE_URL"
        "VITE_API_URL"
    )
    
    local missing_vars=()
    
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            missing_vars+=("$var")
            log_warning "Missing environment variable: $var"
        else
            log_info "✓ $var is set"
        fi
    done
    
    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        if [[ "$STRICT_ENV_CHECK" == "true" ]]; then
            log_error "Missing required environment variables: ${missing_vars[*]}"
            log_info "Please set the following variables:"
            for var in "${missing_vars[@]}"; do
                echo "  export $var=<value>"
            done
            return 1
        fi

        log_warning "Missing environment variables (using defaults where available): ${missing_vars[*]}"
        return 0
    fi

    log_success "All required environment variables are set"
    return 0
}

check_required_tools() {
    print_header "Checking Required Tools"
    
    local required_tools=("docker" "docker-compose" "curl" "grep")
    local missing_tools=()
    
    for tool in "${required_tools[@]}"; do
        if command -v "$tool" &> /dev/null; then
            local version=$("$tool" --version 2>/dev/null | head -n1)
            log_info "✓ $tool: $version"
        else
            missing_tools+=("$tool")
            log_error "✗ $tool is not installed"
        fi
    done
    
    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        log_error "Missing required tools: ${missing_tools[*]}"
        return 1
    fi
    
    log_success "All required tools are available"
    return 0
}

check_docker_daemon() {
    print_header "Checking Docker Daemon"
    
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        log_info "Start Docker and try again:"
        echo "  sudo systemctl start docker    # Linux"
        echo "  open -a Docker                 # macOS"
        echo "  docker-machine start default   # Legacy Docker"
        return 1
    fi
    
    log_success "Docker daemon is running"
    
    # Check Docker version
    local docker_version=$(docker --version)
    log_info "Docker version: $docker_version"
    
    # Check Docker Compose version
    local compose_version=$(docker-compose --version)
    log_info "Docker Compose version: $compose_version"
    
    return 0
}

check_docker_compose_file() {
    print_header "Checking Docker Compose File"
    
    if [[ ! -f "docker-compose.yml" && ! -f "docker-compose.yaml" ]]; then
        log_error "docker-compose.yml not found in current directory"
        log_info "Please ensure docker-compose.yml is in: $(pwd)"
        return 1
    fi
    
    local compose_file=$(ls docker-compose.y* 2>/dev/null | head -n1)
    log_success "Found docker-compose file: $compose_file"
    
    # Validate compose file syntax
    if ! docker-compose config -q 2>/dev/null; then
        log_error "docker-compose.yml has syntax errors"
        docker-compose config
        return 1
    fi
    
    log_success "docker-compose.yml is valid"
    return 0
}

check_port_availability() {
    print_header "Checking Port Availability"
    
    local ports_in_use=()
    local port_info=""
    
    for service in "${!SERVICES[@]}"; do
        local port=${SERVICES[$service]}
        port_info=$(netstat -tuln 2>/dev/null | grep ":${port} " || echo "")
        
        if [[ -n "$port_info" ]]; then
            ports_in_use+=("$port")
            log_warning "Port $port ($service) is already in use"
        else
            log_info "✓ Port $port ($service) is available"
        fi
    done
    
    if [[ ${#ports_in_use[@]} -gt 0 ]]; then
        log_error "The following ports are already in use: ${ports_in_use[*]}"
        log_info "You can:"
        log_info "  1. Stop the services using those ports"
        log_info "  2. Change the port mappings in docker-compose.yml"
        log_info "  3. Use 'docker-compose down' to stop existing containers"
        return 1
    fi
    
    log_success "All required ports are available"
    return 0
}

################################################################################
# Docker Deployment Functions
################################################################################

pull_images() {
    print_header "Pulling Docker Images"
    
    log_info "Pulling latest images from registry..."
    
    if ! docker-compose pull 2>&1 | tee -a "${LOG_FILE}"; then
        log_error "Failed to pull Docker images"
        return 1
    fi
    
    log_success "Docker images pulled successfully"
    return 0
}

start_services() {
    print_header "Starting Docker Services"
    
    log_info "Starting database services (postgres, redis)..."
    if ! docker-compose up -d postgres redis 2>&1 | tee -a "${LOG_FILE}"; then
        log_error "Failed to start database services"
        return 1
    fi
    
    log_success "Database services started"
    print_divider
    
    # Wait for databases to be ready
    log_info "Waiting for databases to be ready..."
    if ! wait_for_service "postgres" || ! wait_for_service "redis"; then
        log_error "Databases failed to become ready"
        return 1
    fi
    
    log_success "Databases are ready"
    print_divider
    
    # Start application services
    log_info "Starting application services..."
    if ! docker-compose up -d 2>&1 | tee -a "${LOG_FILE}"; then
        log_error "Failed to start application services"
        return 1
    fi
    
    log_success "All services started"
    return 0
}

wait_for_service() {
    local service=$1
    local elapsed=0
    local max_attempts=$((HEALTH_CHECK_TIMEOUT / HEALTH_CHECK_INTERVAL))
    local attempt=0
    
    log_info "Waiting for $service to be ready..."
    
    while [[ $attempt -lt $max_attempts ]]; do
        if is_service_healthy "$service"; then
            log_success "$service is ready"
            return 0
        fi
        
        attempt=$((attempt + 1))
        elapsed=$((attempt * HEALTH_CHECK_INTERVAL))
        
        if [[ $((attempt % 4)) -eq 0 ]]; then
            log_info "Still waiting for $service... (${elapsed}s/${HEALTH_CHECK_TIMEOUT}s)"
        fi
        
        sleep "$HEALTH_CHECK_INTERVAL"
    done
    
    log_error "$service failed to become ready after ${HEALTH_CHECK_TIMEOUT}s"
    return 1
}

is_service_healthy() {
    local service=$1
    local endpoint=${HEALTH_ENDPOINTS[$service]:-""}
    
    case "$service" in
        postgres)
            # Check if postgres is accepting connections
            docker-compose exec -T postgres pg_isready -U "${POSTGRES_USER}" &> /dev/null
            return $?
            ;;
        redis)
            # Check if redis is responding to ping
            docker-compose exec -T redis redis-cli --no-auth-warning -a "${REDIS_PASSWORD:-redis-dev-password}" ping &> /dev/null
            return $?
            ;;
        *)
            # Check HTTP health endpoints
            if [[ -z "$endpoint" ]]; then
                # Service is running if container exists
                docker-compose ps "$service" | grep -q "Up"
                return $?
            fi
            
            if curl -sf "$endpoint" > /dev/null 2>&1; then
                return 0
            else
                return 1
            fi
            ;;
    esac
}

################################################################################
# Health Check Functions
################################################################################

run_health_checks() {
    print_header "Running Health Checks on All Services"
    
    local failed_services=()
    
    for service in "${!SERVICES[@]}"; do
        if is_service_healthy "$service"; then
            log_success "✓ $service is healthy"
        else
            log_error "✗ $service is not responding"
            failed_services+=("$service")
        fi
    done
    
    print_divider
    
    if [[ ${#failed_services[@]} -gt 0 ]]; then
        log_error "The following services failed health checks: ${failed_services[*]}"
        return 1
    fi
    
    log_success "All services passed health checks"
    return 0
}

get_service_status() {
    print_header "Service Status Report"
    
    echo -e "\n${BLUE}Docker Compose Status:${NC}"
    docker-compose ps
    
    echo -e "\n${BLUE}Service Details:${NC}"
    for service in "${!SERVICES[@]}"; do
        local port=${SERVICES[$service]}
        local status="UNKNOWN"
        
        if docker-compose ps "$service" | grep -q "Up"; then
            status="RUNNING"
        elif docker-compose ps "$service" | grep -q "Exited"; then
            status="STOPPED"
        fi
        
        printf "  %-20s | Port: %-5s | Status: %s\n" "$service" "$port" "$status"
    done
    
    echo -e "\n${BLUE}Container Resource Usage:${NC}"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" \
        $(docker-compose ps -q) 2>/dev/null || log_warning "Unable to retrieve container stats"
}

show_service_logs() {
    local service=$1
    
    print_header "Logs for $service (Last 20 lines)"
    
    docker-compose logs --tail=20 "$service" 2>&1 || {
        log_error "Failed to retrieve logs for $service"
        return 1
    }
}

################################################################################
# Troubleshooting Functions
################################################################################

diagnose_deployment() {
    print_header "Deployment Diagnostics"
    
    echo -e "\n${BLUE}System Information:${NC}"
    echo "  Hostname: $(hostname)"
    echo "  OS: $(uname -s)"
    echo "  Kernel: $(uname -r)"
    echo "  Available Memory: $(free -h 2>/dev/null | grep Mem | awk '{print $7}' || echo 'N/A')"
    echo "  Available Disk: $(df -h . | tail -1 | awk '{print $4}')"
    
    echo -e "\n${BLUE}Docker Information:${NC}"
    docker system df
    
    echo -e "\n${BLUE}Network Check:${NC}"
    for service in "${!SERVICES[@]}"; do
        local port=${SERVICES[$service]}
        echo "  $service:$port - $(netstat -tuln 2>/dev/null | grep ":${port} " > /dev/null && echo 'LISTENING' || echo 'NOT LISTENING')"
    done
    
    echo -e "\n${BLUE}Failed Container Logs:${NC}"
    local failed_containers=$(docker-compose ps | grep -i "exited\|error" | awk '{print $1}')
    
    if [[ -z "$failed_containers" ]]; then
        echo "  No failed containers found"
    else
        while IFS= read -r container; do
            echo -e "\n  Logs for $container:"
            docker logs --tail=10 "$container" 2>&1 | sed 's/^/    /'
        done <<< "$failed_containers"
    fi
}

################################################################################
# Cleanup Functions
################################################################################

cleanup_deployment() {
    print_header "Cleaning Up Deployment"
    
    log_warning "Stopping all services..."
    docker-compose down -v 2>&1 | tee -a "${LOG_FILE}"
    
    log_success "Deployment cleaned up"
    log_info "To restart, run: $0"
}

################################################################################
# Main Functions
################################################################################

show_usage() {
    cat << EOF
ResearchFlow Docker Stack Deployment

Usage:
    $0 [COMMAND]

Commands:
    deploy          Deploy the full stack (default)
    start           Start existing services
    stop            Stop all services
    status          Show service status
    logs [service]  Show logs for a service
    health          Run health checks only
    diagnose        Run deployment diagnostics
    clean           Stop and remove all containers
    help            Show this help message

Examples:
    $0                          # Full deployment
    $0 status                   # Check service status
    $0 logs orchestrator        # View orchestrator logs
    $0 diagnose                 # Troubleshoot issues
    $0 clean                    # Clean up everything

Environment Variables:
    POSTGRES_USER               PostgreSQL user (required)
    POSTGRES_PASSWORD           PostgreSQL password (required)
    POSTGRES_DB                 PostgreSQL database name (required)
    REDIS_PASSWORD              Redis password (required)
    NODE_ENV                    Node environment (required)
    VITE_API_BASE_URL           Vite API base URL (optional)
    VITE_API_URL                Vite API URL (optional)
    STRICT_ENV_CHECK            Enforce env var validation (true/false)

EOF
}

deploy_stack() {
    print_header "ResearchFlow Docker Stack Deployment"
    echo "Timestamp: $(date)"
    echo "Log file: $LOG_FILE"
    
    load_env_file

    # Run all validations
    validate_environment || return 1
    check_required_tools || return 1
    check_docker_daemon || return 1
    check_docker_compose_file || return 1
    check_port_availability || return 1
    
    # Deploy services
    pull_images || return 1
    start_services || return 1
    
    # Wait for services to stabilize
    sleep 5
    
    # Run health checks
    run_health_checks || {
        log_warning "Some services failed health checks"
        diagnose_deployment
        return 1
    }
    
    # Show final status
    get_service_status
    
    print_header "Deployment Successful"
    echo "ResearchFlow stack is running!"
    echo ""
    echo "Services:"
    echo "  - Orchestrator API:     http://localhost:3001"
    echo "  - Worker:               http://localhost:8000"
    echo "  - Web UI:               http://localhost:5173"
    echo "  - Collaboration:        http://localhost:1234"
    echo "  - Guideline Engine:     http://localhost:8001"
    echo "  - PostgreSQL:           localhost:5432"
    echo "  - Redis:                localhost:6379"
    echo ""
    echo "View logs: docker-compose logs -f [service]"
    echo "Stop services: docker-compose down"
    
    return 0
}

################################################################################
# Main Entry Point
################################################################################

main() {
    local command="${1:-deploy}"
    
    case "$command" in
        deploy)
            deploy_stack
            ;;
        start)
            print_header "Starting Services"
            docker-compose up -d
            log_success "Services started"
            get_service_status
            ;;
        stop)
            print_header "Stopping Services"
            docker-compose down
            log_success "Services stopped"
            ;;
        status)
            get_service_status
            ;;
        logs)
            if [[ -z "${2:-}" ]]; then
                log_error "Please specify a service name"
                echo "Available services: ${!SERVICES[@]}"
                return 1
            fi
            show_service_logs "$2"
            ;;
        health)
            run_health_checks
            ;;
        diagnose)
            diagnose_deployment
            ;;
        clean)
            log_warning "This will remove all containers and volumes"
            read -p "Are you sure? (yes/no): " -r confirmation
            if [[ "$confirmation" == "yes" ]]; then
                cleanup_deployment
            else
                log_info "Cleanup cancelled"
            fi
            ;;
        help|--help|-h)
            show_usage
            ;;
        *)
            log_error "Unknown command: $command"
            show_usage
            return 1
            ;;
    esac
}

# Run main function
main "$@"
exit $?
