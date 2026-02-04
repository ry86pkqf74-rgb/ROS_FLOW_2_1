#!/bin/bash

################################################################################
# ResearchFlow Phase 9 AI - Quick Start Script
# Purpose: Initialize and deploy AI services with minimal configuration
################################################################################

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/.env"
COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.ai.yml"

################################################################################
# FUNCTIONS
################################################################################

print_header() {
    echo -e "${BLUE}═════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  ResearchFlow Phase 9 - AI Services Quick Start${NC}"
    echo -e "${BLUE}═════════════════════════════════════════════════════════════${NC}"
    echo ""
}

print_section() {
    echo -e "${BLUE}→ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

check_prerequisites() {
    print_section "Checking Prerequisites"

    local missing_tools=()

    # Check Docker
    if ! command -v docker &> /dev/null; then
        missing_tools+=("docker")
    else
        print_success "Docker found: $(docker --version)"
    fi

    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        missing_tools+=("docker-compose")
    else
        print_success "Docker Compose found: $(docker-compose --version)"
    fi

    # Check curl
    if ! command -v curl &> /dev/null; then
        missing_tools+=("curl")
    else
        print_success "curl found"
    fi

    # Check jq
    if ! command -v jq &> /dev/null; then
        missing_tools+=("jq")
    else
        print_success "jq found"
    fi

    # Check Docker daemon
    if ! docker ps &> /dev/null; then
        print_error "Docker daemon is not running"
        return 1
    fi
    print_success "Docker daemon is running"

    # Check for GPU (optional)
    if command -v nvidia-smi &> /dev/null; then
        print_success "NVIDIA GPU detected"
        nvidia-smi --query-gpu=name --format=csv,noheader
    else
        print_warning "NVIDIA GPU not detected (optional, using CPU)"
    fi

    # Check available disk space
    local available_space=$(df -BG "$SCRIPT_DIR" | awk 'NR==2 {print $4}' | sed 's/G//')
    if [ "$available_space" -lt 100 ]; then
        print_error "Less than 100GB available disk space (have ${available_space}GB)"
        return 1
    fi
    print_success "Disk space available: ${available_space}GB"

    # Check available memory
    local available_memory=$(free -BG | awk 'NR==2 {print $7}')
    if [ "$available_memory" -lt 16 ]; then
        print_warning "Less than 16GB available memory (have ${available_memory}GB)"
    else
        print_success "Memory available: ${available_memory}GB"
    fi

    # Report missing tools
    if [ ${#missing_tools[@]} -gt 0 ]; then
        print_error "Missing required tools: ${missing_tools[*]}"
        print_error "Please install missing tools and try again"
        return 1
    fi

    echo ""
    return 0
}

setup_environment() {
    print_section "Setting Up Environment"

    if [ -f "$ENV_FILE" ]; then
        print_warning "Environment file already exists at $ENV_FILE"
        read -p "Do you want to use existing configuration? (y/n) " -r
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_success "Using existing .env file"
            return 0
        fi
    fi

    # Copy example environment file
    if [ ! -f "${SCRIPT_DIR}/.env.example" ]; then
        print_error "Environment example file not found"
        return 1
    fi

    cp "${SCRIPT_DIR}/.env.example" "$ENV_FILE"
    print_success "Created .env file from template"

    # Generate secure passwords
    local redis_password=$(openssl rand -base64 32)
    local grafana_password=$(openssl rand -base64 16)

    # Update environment file
    sed -i.bak "s|your-secure-redis-password-here|$redis_password|g" "$ENV_FILE"
    sed -i.bak "s|your-secure-grafana-password-here|$grafana_password|g" "$ENV_FILE"
    rm -f "${ENV_FILE}.bak"

    print_success "Generated secure passwords"
    echo ""
    echo "Environment file created at: $ENV_FILE"
    echo "Redis password: $redis_password"
    echo "Grafana password: $grafana_password"
    echo ""
    echo "IMPORTANT: Save these passwords somewhere secure!"
    echo ""

    return 0
}

validate_configuration() {
    print_section "Validating Configuration"

    if [ ! -f "$COMPOSE_FILE" ]; then
        print_error "docker-compose.ai.yml not found"
        return 1
    fi

    if ! docker-compose -f "$COMPOSE_FILE" config > /dev/null 2>&1; then
        print_error "Invalid docker-compose.ai.yml configuration"
        docker-compose -f "$COMPOSE_FILE" config
        return 1
    fi

    print_success "docker-compose.ai.yml is valid"

    # Validate feature flags
    if [ -f "deploy/feature-flags.json" ]; then
        if ! jq empty deploy/feature-flags.json 2>/dev/null; then
            print_error "Invalid feature-flags.json"
            return 1
        fi
        print_success "feature-flags.json is valid"
    fi

    # Validate Prometheus config
    if [ -f "deploy/prometheus.yml" ]; then
        print_success "prometheus.yml found"
    fi

    # Validate alert rules
    if [ -f "deploy/alert-rules.yml" ]; then
        print_success "alert-rules.yml found"
    fi

    echo ""
    return 0
}

start_services() {
    print_section "Starting AI Services"

    # Load environment
    if [ -f "$ENV_FILE" ]; then
        set -a
        source "$ENV_FILE"
        set +a
    fi

    # Start services
    echo "Starting Docker Compose services..."
    docker-compose -f "$COMPOSE_FILE" up -d

    if [ $? -ne 0 ]; then
        print_error "Failed to start services"
        return 1
    fi

    print_success "Services started"
    echo ""

    return 0
}

wait_for_services() {
    print_section "Waiting for Services to Be Ready"

    local max_attempts=30
    local attempt=1

    echo "Checking service health..."
    echo ""

    while [ $attempt -le $max_attempts ]; do
        local all_healthy=true

        # Check Ollama
        if curl -s -f http://localhost:11434/api/tags > /dev/null 2>&1; then
            print_success "Ollama is healthy"
        else
            all_healthy=false
        fi

        # Check Triton
        if curl -s -f http://localhost:8000/v2/health/ready > /dev/null 2>&1; then
            print_success "Triton is healthy"
        else
            all_healthy=false
        fi

        # Check FAISS
        if curl -s -f http://localhost:5000/health > /dev/null 2>&1; then
            print_success "FAISS is healthy"
        else
            all_healthy=false
        fi

        # Check Redis
        if redis-cli ping > /dev/null 2>&1; then
            print_success "Redis is healthy"
        else
            all_healthy=false
        fi

        # Check Prometheus
        if curl -s -f http://localhost:9090/-/healthy > /dev/null 2>&1; then
            print_success "Prometheus is healthy"
        else
            all_healthy=false
        fi

        # Check Grafana
        if curl -s -f http://localhost:3000/api/health > /dev/null 2>&1; then
            print_success "Grafana is healthy"
        else
            all_healthy=false
        fi

        if [ "$all_healthy" = true ]; then
            print_success "All services are healthy"
            echo ""
            return 0
        fi

        if [ $attempt -lt $max_attempts ]; then
            echo "Waiting for services... (attempt $attempt/$max_attempts)"
            sleep 5
        fi

        attempt=$((attempt + 1))
    done

    print_error "Some services did not become healthy in time"
    print_warning "Services may still be initializing. Check logs with:"
    echo "  docker-compose -f $COMPOSE_FILE logs"
    echo ""

    return 0  # Continue anyway
}

display_summary() {
    print_section "Deployment Summary"

    echo ""
    echo "ResearchFlow Phase 9 AI Services are now running!"
    echo ""
    echo "Service Endpoints:"
    echo "  Ollama:        http://localhost:11434"
    echo "  Triton:        http://localhost:8000"
    echo "  FAISS:         http://localhost:5000"
    echo "  Redis:         redis://localhost:6379"
    echo "  Prometheus:    http://localhost:9090"
    echo "  Grafana:       http://localhost:3000"
    echo ""
    echo "Next Steps:"
    echo "  1. Open Grafana: http://localhost:3000"
    echo "  2. Login with credentials from .env file"
    echo "  3. View AI dashboards to monitor services"
    echo "  4. Run feature rollouts: ./deploy/feature-rollout.sh --help"
    echo ""
    echo "Documentation:"
    echo "  Read DEPLOYMENT.md for detailed information"
    echo ""
    echo "Logs:"
    echo "  View service logs: docker-compose -f $COMPOSE_FILE logs -f"
    echo "  View specific service: docker-compose -f $COMPOSE_FILE logs -f [service]"
    echo ""

    return 0
}

cleanup_on_error() {
    print_error "Quickstart failed. Rolling back changes..."
    docker-compose -f "$COMPOSE_FILE" down 2>/dev/null || true
}

################################################################################
# MAIN EXECUTION
################################################################################

main() {
    print_header

    trap cleanup_on_error ERR

    # Execute steps
    check_prerequisites || exit 1
    setup_environment || exit 1
    validate_configuration || exit 1
    start_services || exit 1
    wait_for_services
    display_summary

    echo -e "${GREEN}✓ Quickstart completed successfully!${NC}"
    echo ""
}

main "$@"
