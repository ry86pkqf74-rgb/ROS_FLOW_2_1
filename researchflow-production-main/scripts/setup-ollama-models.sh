#!/bin/bash
# ============================================
# ResearchFlow - Ollama Model Setup Script
# ============================================
# Phase 2.2: Model initialization for ResearchFlow
# Linear Issue: ROS-99
#
# This script pulls required Ollama models for ResearchFlow:
# - qwen2.5-coder:7b (code generation)
# - llama3.1:8b (general reasoning)
# - nomic-embed-text (embeddings for RAG)
# ============================================

set -e

# Configuration
OLLAMA_HOST="${OLLAMA_HOST:-http://localhost:11434}"
LOG_FILE="${LOG_FILE:-/var/log/ollama-setup.log}"
REQUIRED_MODELS=(
    "qwen2.5-coder:7b"
    "llama3.1:8b"
    "nomic-embed-text"
)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    local level=$1
    shift
    local message="$@"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${timestamp} [${level}] ${message}" | tee -a "$LOG_FILE"
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

# Check if Ollama service is running
check_ollama_service() {
    log_info "Checking Ollama service at ${OLLAMA_HOST}..."

    local max_retries=30
    local retry_count=0

    while [ $retry_count -lt $max_retries ]; do
        if curl -s "${OLLAMA_HOST}/api/tags" > /dev/null 2>&1; then
            log_success "Ollama service is running"
            return 0
        fi

        retry_count=$((retry_count + 1))
        log_warning "Ollama not ready, waiting... (attempt ${retry_count}/${max_retries})"
        sleep 2
    done

    log_error "Ollama service is not available at ${OLLAMA_HOST}"
    return 1
}

# Check available disk space
check_disk_space() {
    local required_gb=50  # Approximate space needed for all models
    local available_kb=$(df -k /root 2>/dev/null | tail -1 | awk '{print $4}')
    local available_gb=$((available_kb / 1024 / 1024))

    log_info "Checking disk space..."
    log_info "Available: ${available_gb}GB, Required: ~${required_gb}GB"

    if [ "$available_gb" -lt "$required_gb" ]; then
        log_warning "Low disk space! Models may fail to download."
        log_warning "Consider freeing up space or using smaller model variants."
    else
        log_success "Sufficient disk space available"
    fi
}

# Pull a single model
pull_model() {
    local model=$1
    log_info "Pulling model: ${model}..."

    local start_time=$(date +%s)

    if ollama pull "$model" 2>&1 | tee -a "$LOG_FILE"; then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        log_success "Successfully pulled ${model} (took ${duration}s)"
        return 0
    else
        log_error "Failed to pull ${model}"
        return 1
    fi
}

# Verify model is available
verify_model() {
    local model=$1
    log_info "Verifying model: ${model}..."

    if ollama list 2>/dev/null | grep -q "${model%%:*}"; then
        log_success "Model ${model} is available"
        return 0
    else
        log_error "Model ${model} verification failed"
        return 1
    fi
}

# Main setup function
main() {
    log_info "============================================"
    log_info "ResearchFlow Ollama Model Setup"
    log_info "Started at: $(date)"
    log_info "============================================"

    # Pre-flight checks
    check_ollama_service || exit 1
    check_disk_space

    # Track results
    local success_count=0
    local fail_count=0
    local failed_models=()

    # Pull each required model
    for model in "${REQUIRED_MODELS[@]}"; do
        log_info "----------------------------------------"
        if pull_model "$model"; then
            if verify_model "$model"; then
                success_count=$((success_count + 1))
            else
                fail_count=$((fail_count + 1))
                failed_models+=("$model")
            fi
        else
            fail_count=$((fail_count + 1))
            failed_models+=("$model")
        fi
    done

    # Summary
    log_info "============================================"
    log_info "Setup Complete"
    log_info "============================================"
    log_success "Successfully installed: ${success_count} models"

    if [ $fail_count -gt 0 ]; then
        log_error "Failed to install: ${fail_count} models"
        log_error "Failed models: ${failed_models[*]}"
        exit 1
    fi

    # List all installed models
    log_info "Installed models:"
    ollama list

    log_success "All models ready for ResearchFlow!"
}

# Run main function
main "$@"
