#!/bin/bash

################################################################################
# ResearchFlow AI Feature Rollout Script
# Version: Phase 9 - Production Ready
# Purpose: Gradual feature flag rollout with health checks and automatic rollback
#
# Usage:
#   ./feature-rollout.sh --feature ai_inference --target-percentage 100
#   ./feature-rollout.sh --feature vector_search --dry-run
#   ./feature-rollout.sh --feature semantic_cache --rollback
################################################################################

set -euo pipefail

# Enable error handling
trap 'handle_error $? $LINENO' ERR

################################################################################
# CONFIGURATION
################################################################################

# Default values
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_DIR="${LOG_DIR:-${PROJECT_ROOT}/logs}"
CONFIG_DIR="${CONFIG_DIR:-${SCRIPT_DIR}}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="${LOG_DIR}/feature-rollout-${TIMESTAMP}.log"

# Feature flags configuration
FEATURE_FLAGS_FILE="${CONFIG_DIR}/feature-flags.json"
FEATURE_STATE_FILE="${CONFIG_DIR}/.feature-state-${TIMESTAMP}.json"

# Deployment parameters
TARGET_PERCENTAGE=0
DRY_RUN=false
FORCE=false
ROLLBACK=false
VERBOSE=false

# Health check parameters
HEALTH_CHECK_TIMEOUT=300  # 5 minutes
HEALTH_CHECK_INTERVAL=10  # 10 seconds
ERROR_THRESHOLD=0.05      # 5% error rate
LATENCY_THRESHOLD=5000    # 5 seconds in milliseconds
P99_LATENCY_THRESHOLD=8000

# Rollout stages
declare -a ROLLOUT_STAGES=(10 25 50 75 100)
CURRENT_STAGE=0

# Service endpoints
PROMETHEUS_URL="${PROMETHEUS_URL:-http://localhost:9090}"
FEATURE_FLAG_SERVICE="${FEATURE_FLAG_SERVICE:-http://localhost:8080}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

################################################################################
# UTILITY FUNCTIONS
################################################################################

log() {
    local level="$1"
    shift
    local message="$@"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[${timestamp}] [${level}] ${message}" | tee -a "$LOG_FILE"
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $@" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $@" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[⚠]${NC} $@" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[✗]${NC} $@" | tee -a "$LOG_FILE"
}

handle_error() {
    local exit_code=$1
    local line_number=$2
    log_error "Script failed at line ${line_number} with exit code ${exit_code}"
    cleanup
    exit "$exit_code"
}

cleanup() {
    log_info "Cleaning up temporary files..."
    # Remove temporary state files
    [ -f "$FEATURE_STATE_FILE" ] && rm -f "$FEATURE_STATE_FILE"
}

print_usage() {
    cat <<EOF
Usage: $0 [OPTIONS]

Options:
    --feature FEATURE_NAME          Feature flag name to rollout (required)
    --target-percentage PERCENT     Target rollout percentage (default: 100)
    --dry-run                       Simulate rollout without making changes
    --force                         Skip confirmation prompts
    --rollback                      Rollback to previous version
    --verbose                       Enable verbose logging
    --help                          Display this help message

Examples:
    # Gradual rollout of AI inference feature to 100%
    $0 --feature ai_inference --target-percentage 100

    # Dry-run simulation
    $0 --feature vector_search --dry-run

    # Rollback feature
    $0 --feature semantic_cache --rollback

EOF
}

################################################################################
# ARGUMENT PARSING
################################################################################

FEATURE_NAME=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --feature)
            FEATURE_NAME="$2"
            shift 2
            ;;
        --target-percentage)
            TARGET_PERCENTAGE="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        --rollback)
            ROLLBACK=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --help)
            print_usage
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            print_usage
            exit 1
            ;;
    esac
done

################################################################################
# VALIDATION
################################################################################

validate_inputs() {
    log_info "Validating inputs..."

    # Check feature name
    if [ -z "$FEATURE_NAME" ]; then
        log_error "Feature name is required"
        print_usage
        exit 1
    fi

    # Check target percentage range
    if [ "$TARGET_PERCENTAGE" -lt 0 ] || [ "$TARGET_PERCENTAGE" -gt 100 ]; then
        log_error "Target percentage must be between 0 and 100"
        exit 1
    fi

    # Check feature flags file exists
    if [ ! -f "$FEATURE_FLAGS_FILE" ]; then
        log_error "Feature flags file not found: $FEATURE_FLAGS_FILE"
        exit 1
    fi

    # Verify feature exists in configuration
    if ! grep -q "\"name\": \"$FEATURE_NAME\"" "$FEATURE_FLAGS_FILE"; then
        log_error "Feature '$FEATURE_NAME' not found in feature flags configuration"
        exit 1
    fi

    log_success "Input validation completed"
}

################################################################################
# FEATURE FLAG OPERATIONS
################################################################################

get_current_rollout_percentage() {
    local feature="$1"
    
    jq -r ".flags[] | select(.name == \"$feature\") | .rollout" "$FEATURE_FLAGS_FILE"
}

get_previous_rollout_percentage() {
    local feature="$1"
    
    if [ -f "${CONFIG_DIR}/.feature-previous-${feature}.json" ]; then
        jq -r '.rollout' "${CONFIG_DIR}/.feature-previous-${feature}.json"
    else
        echo "0"
    fi
}

save_feature_state() {
    local feature="$1"
    local percentage="$2"
    
    log_info "Saving feature state: $feature at $percentage%"
    
    # Backup previous state
    cp "$FEATURE_FLAGS_FILE" "${CONFIG_DIR}/.feature-previous-${feature}.json"
    
    # Update feature flag percentage
    jq ".flags[] |= if .name == \"$feature\" then .rollout = $percentage else . end" \
        "$FEATURE_FLAGS_FILE" > "${FEATURE_STATE_FILE}"
    
    if [ "$DRY_RUN" = false ]; then
        mv "$FEATURE_STATE_FILE" "$FEATURE_FLAGS_FILE"
        log_success "Feature state saved"
    else
        log_info "[DRY-RUN] Would update feature state"
    fi
}

################################################################################
# HEALTH CHECK FUNCTIONS
################################################################################

check_service_health() {
    local service="$1"
    local max_attempts=3
    local attempt=1

    log_info "Checking health of $service..."

    while [ $attempt -le $max_attempts ]; do
        case "$service" in
            ollama)
                if curl -s -f "http://localhost:11434/api/tags" > /dev/null 2>&1; then
                    log_success "$service is healthy"
                    return 0
                fi
                ;;
            triton)
                if curl -s -f "http://localhost:8000/v2/health/ready" > /dev/null 2>&1; then
                    log_success "$service is healthy"
                    return 0
                fi
                ;;
            faiss)
                if curl -s -f "http://localhost:5000/health" > /dev/null 2>&1; then
                    log_success "$service is healthy"
                    return 0
                fi
                ;;
            redis)
                if redis-cli -a "${REDIS_PASSWORD}" ping > /dev/null 2>&1; then
                    log_success "$service is healthy"
                    return 0
                fi
                ;;
            *)
                log_warning "Unknown service: $service"
                return 1
                ;;
        esac

        if [ $attempt -lt $max_attempts ]; then
            log_warning "$service health check failed, retrying... (attempt $attempt/$max_attempts)"
            sleep 5
        fi
        attempt=$((attempt + 1))
    done

    log_error "$service failed health checks"
    return 1
}

check_metrics_health() {
    local feature="$1"
    local duration=$HEALTH_CHECK_TIMEOUT
    local start_time=$(date +%s)

    log_info "Monitoring metrics for $feature (${duration}s timeout)..."

    while true; do
        local current_time=$(date +%s)
        local elapsed=$((current_time - start_time))

        if [ $elapsed -gt $duration ]; then
            log_success "Health check monitoring period completed"
            return 0
        fi

        # Query error rate from Prometheus
        local error_rate=$(query_prometheus "rate(ai_inference_errors_total[5m])" | head -1)
        
        # Query P95 latency
        local p95_latency=$(query_prometheus \
            "histogram_quantile(0.95, rate(ai_inference_duration_ms_bucket[5m]))" | head -1)

        # Query P99 latency
        local p99_latency=$(query_prometheus \
            "histogram_quantile(0.99, rate(ai_inference_duration_ms_bucket[5m]))" | head -1)

        log_info "Metrics snapshot - Error Rate: ${error_rate}% | P95: ${p95_latency}ms | P99: ${p99_latency}ms"

        # Check error threshold
        if (( $(echo "$error_rate > $ERROR_THRESHOLD" | bc -l 2>/dev/null || echo "0") )); then
            log_error "Error rate exceeded threshold: $error_rate > $ERROR_THRESHOLD"
            return 1
        fi

        # Check P95 latency threshold
        if (( $(echo "$p95_latency > $LATENCY_THRESHOLD" | bc -l 2>/dev/null || echo "0") )); then
            log_warning "P95 latency exceeded threshold: $p95_latency > $LATENCY_THRESHOLD"
        fi

        # Check P99 latency threshold
        if (( $(echo "$p99_latency > $P99_LATENCY_THRESHOLD" | bc -l 2>/dev/null || echo "0") )); then
            log_error "P99 latency exceeded critical threshold: $p99_latency > $P99_LATENCY_THRESHOLD"
            return 1
        fi

        sleep $HEALTH_CHECK_INTERVAL
    done
}

query_prometheus() {
    local query="$1"
    
    if [ -z "$PROMETHEUS_URL" ]; then
        log_warning "Prometheus URL not configured, skipping query: $query"
        echo "0"
        return
    fi

    local result=$(curl -s "$PROMETHEUS_URL/api/v1/query" \
        --data-urlencode "query=$query" \
        2>/dev/null | jq -r '.data.result[0].value[1] // 0' 2>/dev/null || echo "0")

    echo "$result"
}

################################################################################
# ROLLOUT EXECUTION
################################################################################

perform_rollout_stage() {
    local feature="$1"
    local target_percentage="$2"
    local stage_index="$3"

    log_info "Executing rollout stage $((stage_index + 1))/${#ROLLOUT_STAGES[@]}: $target_percentage%"

    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY-RUN] Would update $feature to $target_percentage%"
        return 0
    fi

    # Update feature flag
    save_feature_state "$feature" "$target_percentage"

    # Wait for configuration to propagate
    log_info "Waiting for configuration propagation..."
    sleep 10

    # Check all critical services are healthy
    log_info "Performing health checks..."
    check_service_health "ollama" || return 1
    check_service_health "faiss" || return 1

    # Monitor metrics
    check_metrics_health "$feature" || return 1

    log_success "Rollout stage completed successfully: $feature at $target_percentage%"
}

execute_gradual_rollout() {
    local feature="$1"
    local target="$2"

    log_info "Starting gradual rollout for feature: $feature (target: $target%)"

    local current_percentage=0

    for stage_percentage in "${ROLLOUT_STAGES[@]}"; do
        # Stop if we've reached or exceeded target
        if [ "$stage_percentage" -gt "$target" ]; then
            log_info "Reached target percentage ($target%), stopping rollout"
            break
        fi

        # Skip if already at this percentage
        if [ "$stage_percentage" -eq "$current_percentage" ]; then
            continue
        fi

        log_info "Rolling out to $stage_percentage%..."

        if ! perform_rollout_stage "$feature" "$stage_percentage" "$CURRENT_STAGE"; then
            log_error "Rollout stage failed at $stage_percentage%"
            log_warning "Initiating automatic rollback..."
            rollback_feature "$feature"
            return 1
        fi

        # Wait between stages for stability
        if [ "$stage_percentage" -lt "$target" ]; then
            log_info "Stage completed. Waiting 60 seconds before next stage..."
            sleep 60
        fi

        current_percentage="$stage_percentage"
        CURRENT_STAGE=$((CURRENT_STAGE + 1))
    done

    # Handle final percentage if it doesn't match a stage
    if [ "$current_percentage" -ne "$target" ] && [ "$target" -gt "$current_percentage" ]; then
        log_info "Rolling out to final target: $target%..."
        if perform_rollout_stage "$feature" "$target" "$CURRENT_STAGE"; then
            current_percentage="$target"
        else
            log_error "Final rollout stage failed"
            rollback_feature "$feature"
            return 1
        fi
    fi

    log_success "Feature rollout completed: $feature at $current_percentage%"
    return 0
}

################################################################################
# ROLLBACK FUNCTIONS
################################################################################

rollback_feature() {
    local feature="$1"

    log_warning "Rolling back feature: $feature"

    local previous_percentage=$(get_previous_rollout_percentage "$feature")

    if [ -z "$previous_percentage" ] || [ "$previous_percentage" = "null" ]; then
        log_error "Cannot determine previous rollout percentage"
        return 1
    fi

    log_info "Rolling back to previous percentage: $previous_percentage%"

    save_feature_state "$feature" "$previous_percentage"

    # Check health after rollback
    sleep 10
    if check_service_health "ollama" && check_service_health "faiss"; then
        log_success "Rollback completed successfully"
        return 0
    else
        log_error "Health checks failed after rollback"
        return 1
    fi
}

################################################################################
# CONFIRMATION AND EXECUTION
################################################################################

confirm_rollout() {
    local feature="$1"
    local target="$2"
    local current=$(get_current_rollout_percentage "$feature")

    cat <<EOF

================================================================================
Feature Rollout Confirmation
================================================================================
Feature:              $feature
Current Percentage:   ${current}%
Target Percentage:    ${target}%
Dry Run:              $DRY_RUN

Stage Plan:
EOF

    local prev=0
    for stage in "${ROLLOUT_STAGES[@]}"; do
        if [ "$stage" -gt "$target" ]; then
            break
        fi
        echo "  Stage $((prev + 1)): $prev% → $stage%"
        prev="$stage"
    done

    if [ "$prev" -lt "$target" ]; then
        echo "  Final Stage: $prev% → $target%"
    fi

    echo "================================================================================
"

    if [ "$FORCE" = true ]; then
        log_info "Force mode enabled, skipping confirmation"
        return 0
    fi

    read -p "Continue with rollout? (yes/no): " -r
    if [[ $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        return 0
    else
        log_warning "Rollout cancelled by user"
        return 1
    fi
}

################################################################################
# MAIN EXECUTION
################################################################################

main() {
    # Create log directory
    mkdir -p "$LOG_DIR"

    log_info "ResearchFlow AI Feature Rollout - Starting"
    log_info "Log file: $LOG_FILE"

    # Validate inputs
    validate_inputs

    # Show current state
    local current_percentage=$(get_current_rollout_percentage "$FEATURE_NAME")
    log_info "Current rollout percentage: $current_percentage%"

    # Handle rollback
    if [ "$ROLLBACK" = true ]; then
        log_info "Rollback mode enabled"
        if confirm_rollout "$FEATURE_NAME" "0"; then
            if rollback_feature "$FEATURE_NAME"; then
                log_success "Rollback completed successfully"
                exit 0
            else
                log_error "Rollback failed"
                exit 1
            fi
        else
            exit 1
        fi
    fi

    # Confirm rollout plan
    if ! confirm_rollout "$FEATURE_NAME" "$TARGET_PERCENTAGE"; then
        exit 1
    fi

    # Execute gradual rollout
    if execute_gradual_rollout "$FEATURE_NAME" "$TARGET_PERCENTAGE"; then
        log_success "Feature rollout completed successfully"
        cleanup
        exit 0
    else
        log_error "Feature rollout failed"
        cleanup
        exit 1
    fi
}

# Execute main function
main "$@"
