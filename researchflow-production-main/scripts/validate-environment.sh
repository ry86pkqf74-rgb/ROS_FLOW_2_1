#!/bin/bash

################################################################################
# ResearchFlow Environment Variables Validation Script
# 
# Purpose: Validates required environment variables, checks security 
#          requirements, and generates secure values for optional configs
#
# Usage: ./validate-environment.sh [--fix] [--generate-example] [--verbose]
################################################################################

# Don't use -e for early exit since we need to capture all validation errors
set -uo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Script variables
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${1:-.env}"
FIX_MODE=false
GENERATE_EXAMPLE=false
VERBOSE=false
VALIDATION_ERRORS=0
VALIDATION_WARNINGS=0
VALIDATION_INFO=0

################################################################################
# Helper Functions
################################################################################

print_header() {
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

print_error() {
    echo -e "${RED}✗ ERROR: $1${NC}"
    ((VALIDATION_ERRORS++))
}

print_warning() {
    echo -e "${YELLOW}⚠ WARNING: $1${NC}"
    ((VALIDATION_WARNINGS++))
}

print_info() {
    echo -e "${BLUE}ℹ INFO: $1${NC}"
    ((VALIDATION_INFO++))
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_verbose() {
    if [[ "$VERBOSE" == true ]]; then
        echo -e "${BLUE}→ $1${NC}"
    fi
}

# Generate a secure random string
generate_random_string() {
    local length=${1:-32}
    head -c "$length" /dev/urandom | base64 | tr -d '=+/' | cut -c1-"$length"
}

# Generate a secure JWT secret (minimum 64 characters)
generate_jwt_secret() {
    generate_random_string 64
}

# Validate variable exists and is not empty
check_required_var() {
    local var_name=$1
    local var_value="${!var_name:-}"
    
    if [[ -z "$var_value" ]]; then
        print_error "Required variable '$var_name' is not set"
        return 1
    fi
    
    print_success "Required variable '$var_name' is set"
    return 0
}

# Validate variable if it exists
check_optional_var() {
    local var_name=$1
    local var_value="${!var_name:-}"
    
    if [[ -z "$var_value" ]]; then
        print_verbose "Optional variable '$var_name' is not set"
        return 0
    fi
    
    print_success "Optional variable '$var_name' is configured"
    return 0
}

# Validate numeric port
validate_port() {
    local port_name=$1
    local port_value="${!port_name:-}"
    
    if [[ -z "$port_value" ]]; then
        print_error "$port_name is not set"
        return 1
    fi
    
    if ! [[ "$port_value" =~ ^[0-9]+$ ]] || [ "$port_value" -lt 1 ] || [ "$port_value" -gt 65535 ]; then
        print_error "$port_name value '$port_value' is not a valid port (1-65535)"
        return 1
    fi
    
    print_success "$port_name is valid: $port_value"
    return 0
}

# Validate JWT_SECRET length
validate_jwt_secret() {
    local secret="${JWT_SECRET:-}"
    
    if [[ -z "$secret" ]]; then
        print_error "JWT_SECRET is not set"
        return 1
    fi
    
    local length=${#secret}
    if [[ $length -lt 64 ]]; then
        print_error "JWT_SECRET is too short (${length} chars). Minimum required: 64 characters"
        return 1
    fi
    
    print_success "JWT_SECRET meets security requirements (${length} characters)"
    return 0
}

# Validate password strength
validate_password_strength() {
    local password=$1
    local password_name=$2
    
    if [[ -z "$password" ]]; then
        print_error "$password_name is not set"
        return 1
    fi
    
    local length=${#password}
    
    # Check minimum length
    if [[ $length -lt 12 ]]; then
        print_error "$password_name is too weak (${length} chars). Minimum: 12 characters"
        return 1
    fi
    
    # Check for character variety
    local has_upper=0
    local has_lower=0
    local has_digit=0
    local has_special=0
    
    [[ "$password" =~ [A-Z] ]] && has_upper=1 || true
    [[ "$password" =~ [a-z] ]] && has_lower=1 || true
    [[ "$password" =~ [0-9] ]] && has_digit=1 || true
    [[ "$password" =~ [^A-Za-z0-9] ]] && has_special=1 || true
    
    local complexity=$((has_upper + has_lower + has_digit + has_special))
    
    if [[ $complexity -lt 3 ]]; then
        print_warning "$password_name has low complexity. Consider using: uppercase, lowercase, digits, and special characters"
    else
        print_success "$password_name meets security requirements"
    fi
    
    return 0
}

# Validate PostgreSQL configuration
validate_postgres() {
    print_header "PostgreSQL Configuration"
    
    local errors=0
    
    check_required_var POSTGRES_HOST || ((errors++))
    check_required_var POSTGRES_PORT || ((errors++))
    check_required_var POSTGRES_DB || ((errors++))
    check_required_var POSTGRES_USER || ((errors++))
    check_required_var POSTGRES_PASSWORD || ((errors++))
    
    validate_port POSTGRES_PORT || ((errors++))
    validate_password_strength "${POSTGRES_PASSWORD:-}" "POSTGRES_PASSWORD" || ((errors++))
    
    return $errors
}

# Validate Redis configuration
validate_redis() {
    print_header "Redis Configuration (Optional)"
    
    local redis_host="${REDIS_HOST:-}"
    local redis_port="${REDIS_PORT:-}"
    local redis_password="${REDIS_PASSWORD:-}"
    
    if [[ -z "$redis_host" && -z "$redis_port" && -z "$redis_password" ]]; then
        print_info "Redis configuration is not set (optional)"
        return 0
    fi
    
    local errors=0
    
    check_required_var REDIS_HOST || ((errors++))
    check_required_var REDIS_PORT || ((errors++))
    validate_port REDIS_PORT || ((errors++))
    
    # REDIS_PASSWORD is optional for Redis
    if [[ -n "$redis_password" ]]; then
        validate_password_strength "$redis_password" "REDIS_PASSWORD" || ((errors++))
    else
        print_info "REDIS_PASSWORD is not set (optional for local Redis)"
    fi
    
    return $errors
}

# Validate secrets and encryption
validate_secrets() {
    print_header "Secrets and Encryption Configuration"
    
    local errors=0
    
    validate_jwt_secret || ((errors++))
    check_required_var SESSION_SECRET || ((errors++))
    check_required_var ENCRYPTION_KEY || ((errors++))
    
    return $errors
}

# Validate port configuration
validate_ports() {
    print_header "Service Port Configuration"
    
    local errors=0
    
    validate_port ORCHESTRATOR_PORT || ((errors++))
    validate_port WORKER_PORT || ((errors++))
    validate_port COLLAB_PORT || ((errors++))
    
    # Check for port conflicts
    if [[ "${ORCHESTRATOR_PORT:-}" == "${WORKER_PORT:-}" ]]; then
        print_error "ORCHESTRATOR_PORT and WORKER_PORT cannot be the same"
        ((errors++))
    fi
    
    if [[ "${ORCHESTRATOR_PORT:-}" == "${COLLAB_PORT:-}" ]]; then
        print_error "ORCHESTRATOR_PORT and COLLAB_PORT cannot be the same"
        ((errors++))
    fi
    
    if [[ "${WORKER_PORT:-}" == "${COLLAB_PORT:-}" ]]; then
        print_error "WORKER_PORT and COLLAB_PORT cannot be the same"
        ((errors++))
    fi
    
    return $errors
}

# Validate environment and logging
validate_environment() {
    print_header "Environment and Logging Configuration"
    
    local errors=0
    
    check_required_var NODE_ENV || ((errors++))
    
    local valid_envs=("development" "production" "test" "staging")
    local env_value="${NODE_ENV:-}"
    
    if [[ -n "$env_value" ]]; then
        local valid=0
        for valid_env in "${valid_envs[@]}"; do
            if [[ "$env_value" == "$valid_env" ]]; then
                valid=1
                break
            fi
        done
        
        if [[ $valid -eq 0 ]]; then
            print_error "NODE_ENV value '$env_value' is invalid. Valid values: ${valid_envs[*]}"
            ((errors++))
        else
            print_success "NODE_ENV is valid: $env_value"
        fi
    fi
    
    # Optional logging configuration
    check_optional_var LOG_LEVEL
    
    if [[ -n "${LOG_LEVEL:-}" ]]; then
        local valid_levels=("debug" "info" "warn" "error")
        local level_valid=0
        for valid_level in "${valid_levels[@]}"; do
            if [[ "${LOG_LEVEL}" == "$valid_level" ]]; then
                level_valid=1
                break
            fi
        done
        
        if [[ $level_valid -eq 0 ]]; then
            print_warning "LOG_LEVEL value '${LOG_LEVEL}' is not standard. Recommended: ${valid_levels[*]}"
        fi
    fi
    
    check_optional_var SENTRY_DSN
    
    return $errors
}

# Validate API keys (optional)
validate_api_keys() {
    print_header "External API Configuration (Optional)"
    
    check_optional_var OPENAI_API_KEY || true
    check_optional_var ANTHROPIC_API_KEY || true
    
    if [[ -z "${OPENAI_API_KEY:-}" && -z "${ANTHROPIC_API_KEY:-}" ]]; then
        print_warning "Neither OPENAI_API_KEY nor ANTHROPIC_API_KEY is configured. AI features will be disabled"
    fi
    
    return 0
}

# Validate frontend configuration (optional)
validate_frontend() {
    print_header "Frontend Configuration (Optional)"
    
    check_optional_var VITE_API_URL || true
    check_optional_var VITE_COLLAB_URL || true
    
    return 0
}

# Generate example .env file
generate_env_example() {
    print_header "Generating .env.example Template"
    
    local example_file="${SCRIPT_DIR}/../.env.example"
    
    cat > "$example_file" << 'ENVEOF'
################################################################################
# ResearchFlow Configuration Template
# 
# Copy this file to .env and fill in your actual values
# IMPORTANT: Never commit .env with real secrets to version control
################################################################################

# ============================================================================
# PostgreSQL Configuration (REQUIRED)
# ============================================================================

# PostgreSQL server hostname or IP address
POSTGRES_HOST=localhost

# PostgreSQL server port (default: 5432)
POSTGRES_PORT=5432

# PostgreSQL database name
POSTGRES_DB=researchflow

# PostgreSQL user account
POSTGRES_USER=researchflow_user

# PostgreSQL password (minimum 12 characters, mixed case recommended)
POSTGRES_PASSWORD=your_secure_password_here

# ============================================================================
# Redis Configuration (OPTIONAL)
# ============================================================================
# Omit these variables to use in-memory caching instead of Redis

# Redis server hostname or IP address
# REDIS_HOST=localhost

# Redis server port (default: 6379)
# REDIS_PORT=6379

# Redis password (if authentication is enabled)
# REDIS_PASSWORD=your_redis_password

# ============================================================================
# Security & Secrets Configuration (REQUIRED)
# ============================================================================

# JWT signing secret (minimum 64 characters, used for token generation)
# Generate with: openssl rand -base64 64
JWT_SECRET=your_64_char_minimum_jwt_secret_generated_randomly

# Session secret (for session management)
SESSION_SECRET=your_session_secret_generated_randomly

# Encryption key (for data encryption at rest)
ENCRYPTION_KEY=your_encryption_key_generated_randomly

# ============================================================================
# Service Port Configuration (REQUIRED)
# ============================================================================

# Main orchestrator service port
ORCHESTRATOR_PORT=3000

# Worker service port
WORKER_PORT=3001

# Collaboration service port
COLLAB_PORT=3002

# ============================================================================
# Environment & Logging (REQUIRED)
# ============================================================================

# Node.js environment: development, production, test, staging
NODE_ENV=development

# Logging level: debug, info, warn, error
LOG_LEVEL=info

# Sentry error tracking DSN (optional)
# SENTRY_DSN=https://your_sentry_dsn@sentry.io/project_id

# ============================================================================
# External AI APIs (OPTIONAL)
# ============================================================================
# At least one AI provider is recommended for full functionality

# OpenAI API key for GPT integration
# OPENAI_API_KEY=sk-your_openai_api_key

# Anthropic API key for Claude integration
# ANTHROPIC_API_KEY=your_anthropic_api_key

# ============================================================================
# Frontend Configuration (OPTIONAL)
# ============================================================================

# API server URL for frontend
# VITE_API_URL=http://localhost:3000/api

# Collaboration server URL for frontend
# VITE_COLLAB_URL=http://localhost:3002
ENVEOF
    
    print_success "Generated .env.example template: $example_file"
}

# Generate secure values for missing optional configs
generate_secure_values() {
    print_header "Generating Secure Values for Optional Configurations"
    
    local generated_file="${SCRIPT_DIR}/../.env.generated"
    local has_generated=false
    
    > "$generated_file"
    
    # Check for missing JWT_SECRET
    if [[ -z "${JWT_SECRET:-}" ]]; then
        local jwt_secret=$(generate_jwt_secret)
        echo "JWT_SECRET=$jwt_secret" >> "$generated_file"
        print_success "Generated JWT_SECRET: ${jwt_secret:0:20}... (64 chars)"
        has_generated=true
    fi
    
    # Check for missing SESSION_SECRET
    if [[ -z "${SESSION_SECRET:-}" ]]; then
        local session_secret=$(generate_random_string 32)
        echo "SESSION_SECRET=$session_secret" >> "$generated_file"
        print_success "Generated SESSION_SECRET: ${session_secret:0:20}... (32 chars)"
        has_generated=true
    fi
    
    # Check for missing ENCRYPTION_KEY
    if [[ -z "${ENCRYPTION_KEY:-}" ]]; then
        local encryption_key=$(generate_random_string 32)
        echo "ENCRYPTION_KEY=$encryption_key" >> "$generated_file"
        print_success "Generated ENCRYPTION_KEY: ${encryption_key:0:20}... (32 chars)"
        has_generated=true
    fi
    
    if [[ "$has_generated" == true ]]; then
        print_info "Generated values saved to: $generated_file"
        print_info "You can append these values to your .env file:"
        echo ""
        cat "$generated_file"
        echo ""
    else
        print_info "All security secrets are already configured"
    fi
}

# Run all validations
run_validations() {
    print_header "ResearchFlow Environment Validation"
    echo "Configuration file: $ENV_FILE"
    echo ""
    
    # Load environment variables from .env file if it exists
    if [[ -f "$ENV_FILE" ]]; then
        print_info "Loading configuration from: $ENV_FILE"
        # Use set -a to export all variables
        set -a
        source "$ENV_FILE"
        set +a
    else
        print_warning "Configuration file '$ENV_FILE' not found. Using system environment variables only."
    fi
    
    echo ""
    
    # Run all validation functions - ignore their return codes
    validate_postgres || true
    validate_redis || true
    validate_secrets || true
    validate_ports || true
    validate_environment || true
    validate_api_keys || true
    validate_frontend || true
}

# Generate summary report
generate_summary() {
    print_header "Validation Summary"
    
    echo "Errors:     ${RED}$VALIDATION_ERRORS${NC}"
    echo "Warnings:   ${YELLOW}$VALIDATION_WARNINGS${NC}"
    echo "Info:       ${BLUE}$VALIDATION_INFO${NC}"
    echo ""
    
    if [[ $VALIDATION_ERRORS -eq 0 ]]; then
        print_success "All critical validations passed!"
        return 0
    else
        print_error "$VALIDATION_ERRORS critical validation(s) failed"
        return 1
    fi
}

# Display usage information
show_usage() {
    cat << 'USAGEEOF'
ResearchFlow Environment Variables Validation Script

USAGE:
    ./validate-environment.sh [options]

OPTIONS:
    --fix                Generate missing security secrets
    --generate-example   Create a .env.example template
    --verbose            Show detailed validation messages
    --help               Display this help message

EXAMPLES:
    # Basic validation
    ./validate-environment.sh
    
    # Validate and generate missing secrets
    ./validate-environment.sh --fix
    
    # Generate template and show detailed output
    ./validate-environment.sh --generate-example --verbose
    
    # Validate custom env file
    ./validate-environment.sh /path/to/.env --verbose

REQUIREMENTS:
    - Bash 4.0+
    - Common Unix utilities (head, base64, cut, tr)

CONFIGURATION:
    The script reads from .env file in the current directory by default.
    You can specify a different file as the first argument.

EXIT CODES:
    0 - All validations passed
    1 - One or more validations failed

For more information, see the .env.example template generated by:
    ./validate-environment.sh --generate-example
USAGEEOF
}

################################################################################
# Main Script Execution
################################################################################

main() {
    # Parse command-line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --fix)
                FIX_MODE=true
                shift
                ;;
            --generate-example)
                GENERATE_EXAMPLE=true
                shift
                ;;
            --verbose)
                VERBOSE=true
                shift
                ;;
            --help|-h)
                show_usage
                exit 0
                ;;
            -*)
                print_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
            *)
                ENV_FILE="$1"
                shift
                ;;
        esac
    done
    
    # Run validations
    run_validations
    
    echo ""
    
    # Generate example if requested
    if [[ "$GENERATE_EXAMPLE" == true ]]; then
        generate_env_example
        echo ""
    fi
    
    # Generate secure values if requested
    if [[ "$FIX_MODE" == true ]]; then
        generate_secure_values
        echo ""
    fi
    
    # Show summary
    generate_summary
    local exit_code=$?
    
    # Additional recommendations
    if [[ $VALIDATION_ERRORS -gt 0 ]]; then
        echo ""
        print_header "Recommendations"
        echo ""
        echo "1. Check that all REQUIRED variables are set in your .env file"
        echo "2. Verify security requirements (JWT_SECRET >= 64 chars, passwords >= 12 chars)"
        echo "3. Ensure service ports (3000-3002) are not in use and are unique"
        echo "4. For PostgreSQL/Redis passwords, use strong random values"
        echo ""
        echo "To generate secure values, run:"
        echo "    ./validate-environment.sh --fix"
        echo ""
        echo "To see example configuration, run:"
        echo "    ./validate-environment.sh --generate-example"
    fi
    
    exit $exit_code
}

# Execute main function
main "$@"
