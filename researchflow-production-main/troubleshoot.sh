#!/bin/bash

################################################################################
# ResearchFlow Docker Troubleshooting Utility
# Comprehensive diagnostics and recovery procedures
################################################################################

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $@"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $@"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $@"; }
log_error() { echo -e "${RED}[ERROR]${NC} $@"; }

print_header() {
    echo -e "\n${BLUE}=== $@ ===${NC}\n"
}

# Available diagnostic checks
CHECKS=(
    "docker_status"
    "compose_validity"
    "container_health"
    "service_connectivity"
    "resource_usage"
    "error_logs"
    "port_availability"
    "database_connection"
)

check_docker_status() {
    print_header "Docker Status Check"
    
    if ! docker info &>/dev/null; then
        log_error "Docker daemon is not running"
        log_info "Start Docker and try again"
        return 1
    fi
    
    log_success "Docker daemon is running"
    echo "Docker version: $(docker --version)"
    echo "Docker Compose version: $(docker-compose --version)"
    
    local total_containers=$(docker ps -a --format "{{json .}}" | wc -l)
    local running_containers=$(docker ps --format "{{json .}}" | wc -l)
    
    echo "Total containers: $total_containers"
    echo "Running containers: $running_containers"
}

check_compose_validity() {
    print_header "Docker Compose Configuration Check"
    
    if [[ ! -f docker-compose.yml && ! -f docker-compose.yaml ]]; then
        log_error "docker-compose.yml not found"
        return 1
    fi
    
    local compose_file=$(ls docker-compose.y* 2>/dev/null | head -1)
    log_success "Found: $compose_file"
    
    if ! docker-compose config -q 2>/dev/null; then
        log_error "Configuration has errors:"
        docker-compose config
        return 1
    fi
    
    log_success "Configuration is valid"
    
    # Show services
    echo -e "\nServices defined:"
    docker-compose config --services
}

check_container_health() {
    print_header "Container Health Status"
    
    if ! docker-compose ps &>/dev/null; then
        log_warning "No containers are running"
        return 0
    fi
    
    docker-compose ps
    
    echo -e "\nHealth check status:"
    docker-compose ps | while read -r line; do
        if [[ $line == *"Up"* ]]; then
            local container=$(echo "$line" | awk '{print $1}')
            local health=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "N/A")
            printf "  %-30s Health: %s\n" "$container" "$health"
        fi
    done
}

check_service_connectivity() {
    print_header "Service Connectivity Check"
    
    local services=(
        "localhost:3001:orchestrator"
        "localhost:8000:worker"
        "localhost:8001:guideline"
        "localhost:1234:collaboration"
        "localhost:5173:web"
        "localhost:5432:postgres"
        "localhost:6379:redis"
    )
    
    for service_spec in "${services[@]}"; do
        IFS=':' read -r host port name <<< "$service_spec"
        
        if nc -z "$host" "$port" 2>/dev/null; then
            log_success "$name ($host:$port) - RESPONDING"
        else
            log_warning "$name ($host:$port) - NOT RESPONDING"
        fi
    done
}

check_resource_usage() {
    print_header "Container Resource Usage"
    
    if ! docker-compose ps -q &>/dev/null; then
        log_warning "No containers running"
        return 0
    fi
    
    # CPU and Memory
    echo "CPU and Memory Usage:"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" \
        $(docker-compose ps -q) 2>/dev/null || log_warning "Unable to get stats"
    
    # Disk Usage
    echo -e "\nDisk Usage (Data Volumes):"
    for dir in postgres_data redis_data *_logs *_cache *_data; do
        if [[ -d "$dir" ]]; then
            local size=$(du -sh "$dir" 2>/dev/null | cut -f1)
            printf "  %-25s %s\n" "$dir" "$size"
        fi
    done
    
    # System Resources
    echo -e "\nSystem Resources:"
    echo "Memory: $(free -h | grep Mem | awk '{print "Total: " $2 ", Used: " $3 ", Free: " $4}')"
    echo "Disk: $(df -h . | tail -1 | awk '{print "Total: " $2 ", Used: " $3 ", Free: " $4}')"
}

check_error_logs() {
    print_header "Recent Errors in Logs"
    
    echo "Errors in services:"
    docker-compose logs | grep -i "error\|failed\|exception" | tail -20 || echo "  No errors found in recent logs"
    
    echo -e "\nFailed containers:"
    docker-compose ps | grep -i "exited\|error" || echo "  No failed containers"
}

check_port_availability() {
    print_header "Port Availability Check"
    
    local ports=(3001 5173 8000 8001 1234 5432 6379)
    
    for port in "${ports[@]}"; do
        if netstat -tuln 2>/dev/null | grep -q ":$port "; then
            local process=$(lsof -i :$port 2>/dev/null | grep LISTEN | awk '{print $1}' || echo "unknown")
            log_warning "Port $port is in use by: $process"
        else
            log_success "Port $port is available"
        fi
    done
}

check_database_connection() {
    print_header "Database Connection Check"
    
    # PostgreSQL
    echo "PostgreSQL Connection:"
    if docker-compose exec -T postgres pg_isready -U "${POSTGRES_USER:-researchflow}" &>/dev/null; then
        log_success "PostgreSQL is accessible"
    else
        log_error "PostgreSQL connection failed"
    fi
    
    # Redis
    echo -e "\nRedis Connection:"
    if docker-compose exec -T redis redis-cli ping &>/dev/null; then
        log_success "Redis is accessible"
    else
        log_error "Redis connection failed"
    fi
}

# Recovery procedures
recover_restart_all() {
    print_header "Restarting All Services"
    
    log_info "Stopping services..."
    docker-compose down 2>/dev/null || true
    
    sleep 2
    
    log_info "Starting services..."
    docker-compose up -d
    
    log_success "Services restarted"
}

recover_clear_logs() {
    print_header "Clearing Container Logs"
    
    local containers=$(docker-compose ps -q 2>/dev/null || echo "")
    
    if [[ -z "$containers" ]]; then
        log_warning "No containers found"
        return 1
    fi
    
    for container in $containers; do
        log_info "Clearing logs for: $container"
        docker logs --tail 0 -f "$container" 2>/dev/null || true
    done
    
    log_success "Logs cleared"
}

recover_reset_volumes() {
    print_header "WARNING: Reset All Data Volumes"
    
    log_warning "This will DELETE all container data!"
    read -p "Are you sure? (yes/no): " -r confirmation
    
    if [[ "$confirmation" != "yes" ]]; then
        log_info "Operation cancelled"
        return 0
    fi
    
    log_info "Stopping services..."
    docker-compose down -v 2>/dev/null || true
    
    log_info "Removing volumes..."
    docker volume prune -f 2>/dev/null || true
    
    log_success "All volumes reset"
}

show_usage() {
    cat << EOF
ResearchFlow Docker Troubleshooting Utility

Usage: $0 [COMMAND]

Diagnostic Commands:
    all                 Run all diagnostics
    docker              Docker daemon status
    compose             Docker Compose validation
    health              Container health status
    connectivity        Service connectivity check
    resources           Resource usage (CPU, memory, disk)
    errors              Recent errors in logs
    ports               Port availability check
    database            Database connectivity check

Recovery Commands:
    restart             Restart all services
    clear-logs          Clear container logs
    reset-volumes       DELETE all data and reset volumes

Other Commands:
    help                Show this help message

Examples:
    $0 all              # Run complete diagnostics
    $0 connectivity     # Check if services are responding
    $0 restart          # Restart all services
    $0 errors           # View recent errors
EOF
}

main() {
    local command="${1:-all}"
    
    case "$command" in
        all)
            for check in "${CHECKS[@]}"; do
                check_${check} || log_warning "Check failed: $check"
                sleep 1
            done
            ;;
        docker)
            check_docker_status
            ;;
        compose)
            check_compose_validity
            ;;
        health)
            check_container_health
            ;;
        connectivity)
            check_service_connectivity
            ;;
        resources)
            check_resource_usage
            ;;
        errors)
            check_error_logs
            ;;
        ports)
            check_port_availability
            ;;
        database)
            check_database_connection
            ;;
        restart)
            recover_restart_all
            ;;
        clear-logs)
            recover_clear_logs
            ;;
        reset-volumes)
            recover_reset_volumes
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

main "$@"
