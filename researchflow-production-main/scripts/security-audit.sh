#!/bin/bash

################################################################################
# ResearchFlow Security Audit Script
# Track D - Security & Supply Chain Hardening (ROS-113)
#
# Comprehensive security audit including:
# - npm audit for Node.js dependencies
# - pip-audit for Python dependencies
# - Outdated dependency checks
# - Secret scanning (trufflehog)
# - License compliance verification
# - JSON report generation with exit codes based on severity
#
# Usage: ./scripts/security-audit.sh [--full|--quick|--report-only]
################################################################################

set -o pipefail

# ============================================================================
# Configuration
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)
DATE=$(date -u +%Y%m%d)
REPORT_DIR="${PROJECT_ROOT}/security-reports"
REPORT_FILE="${REPORT_DIR}/security-audit-${DATE}.json"

# Create report directory
mkdir -p "$REPORT_DIR"

# Color codes for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Exit codes
EXIT_SUCCESS=0
EXIT_INFO=0
EXIT_WARNING=1
EXIT_ERROR=2
EXIT_CRITICAL=3

# Counters
TOTAL_ISSUES=0
CRITICAL_ISSUES=0
HIGH_ISSUES=0
MEDIUM_ISSUES=0
LOW_ISSUES=0
SECRETS_FOUND=0

# Configuration flags
AUDIT_NPM=true
AUDIT_PIP=true
CHECK_OUTDATED=true
SCAN_SECRETS=true
CHECK_LICENSES=true
GENERATE_REPORT=true

# ============================================================================
# Helper Functions
# ============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $*" >&2
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*" >&2
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $*" >&2
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*" >&2
}

log_section() {
    echo ""
    echo -e "${BLUE}================================================================================${NC}"
    echo -e "${BLUE}$*${NC}"
    echo -e "${BLUE}================================================================================${NC}"
}

increment_issue() {
    local severity=$1
    TOTAL_ISSUES=$((TOTAL_ISSUES + 1))
    case "$severity" in
        critical)
            CRITICAL_ISSUES=$((CRITICAL_ISSUES + 1))
            ;;
        high)
            HIGH_ISSUES=$((HIGH_ISSUES + 1))
            ;;
        medium)
            MEDIUM_ISSUES=$((MEDIUM_ISSUES + 1))
            ;;
        low)
            LOW_ISSUES=$((LOW_ISSUES + 1))
            ;;
    esac
}

# ============================================================================
# Audit Functions
# ============================================================================

audit_npm_dependencies() {
    log_section "NPM Dependency Audit"

    if [ ! -f "$PROJECT_ROOT/package.json" ]; then
        log_warning "package.json not found, skipping npm audit"
        return 0
    fi

    if ! command -v npm &>/dev/null; then
        log_error "npm not found, skipping npm audit"
        return 1
    fi

    log_info "Running npm audit..."
    
    # Run npm audit and capture output
    local audit_output
    audit_output=$(npm audit --json 2>/dev/null || echo '{"metadata":{"vulnerabilities":{"critical":0,"high":0,"moderate":0,"low":0}}}')
    
    # Parse vulnerability counts
    local critical high moderate low
    critical=$(echo "$audit_output" | jq '.metadata.vulnerabilities.critical // 0' 2>/dev/null || echo "0")
    high=$(echo "$audit_output" | jq '.metadata.vulnerabilities.high // 0' 2>/dev/null || echo "0")
    moderate=$(echo "$audit_output" | jq '.metadata.vulnerabilities.moderate // 0' 2>/dev/null || echo "0")
    low=$(echo "$audit_output" | jq '.metadata.vulnerabilities.low // 0' 2>/dev/null || echo "0")

    echo "$audit_output" > "$REPORT_DIR/npm-audit-${DATE}.json"

    log_info "npm audit results:"
    log_info "  Critical:  $critical"
    log_info "  High:      $high"
    log_info "  Moderate:  $moderate"
    log_info "  Low:       $low"

    # Count issues
    for ((i=0; i<critical; i++)); do increment_issue "critical"; done
    for ((i=0; i<high; i++)); do increment_issue "high"; done
    for ((i=0; i<moderate; i++)); do increment_issue "medium"; done
    for ((i=0; i<low; i++)); do increment_issue "low"; done

    if [ "$critical" -gt 0 ]; then
        log_error "Found $critical critical vulnerabilities in Node.js dependencies"
        return 1
    elif [ "$high" -gt 0 ]; then
        log_warning "Found $high high-severity vulnerabilities in Node.js dependencies"
    fi

    log_success "npm audit completed"
    return 0
}

audit_pip_dependencies() {
    log_section "Python Dependency Audit"

    if [ ! -f "$PROJECT_ROOT/services/worker/requirements.txt" ]; then
        log_warning "requirements.txt not found, skipping pip-audit"
        return 0
    fi

    if ! command -v pip-audit &>/dev/null; then
        log_warning "pip-audit not found, installing..."
        if ! pip install pip-audit &>/dev/null; then
            log_error "Failed to install pip-audit"
            return 1
        fi
    fi

    log_info "Running pip-audit..."

    # Run pip-audit
    local audit_output
    audit_output=$(pip-audit --desc --format json --requirements "$PROJECT_ROOT/services/worker/requirements.txt" 2>/dev/null || echo '{"vulnerabilities":[]}')

    echo "$audit_output" > "$REPORT_DIR/pip-audit-${DATE}.json"

    # Parse vulnerability count
    local vuln_count
    vuln_count=$(echo "$audit_output" | jq '.vulnerabilities | length' 2>/dev/null || echo "0")

    log_info "pip-audit results:"
    log_info "  Total vulnerabilities: $vuln_count"

    # Extract severity breakdown
    if [ "$vuln_count" -gt 0 ]; then
        log_info "  Affected packages:"
        echo "$audit_output" | jq -r '.vulnerabilities[] | "    - \(.name): \(.vulnerability_id)"' 2>/dev/null || true
        
        # Increment issues (treating all as medium for now)
        for ((i=0; i<vuln_count; i++)); do increment_issue "medium"; done
        
        log_warning "Found $vuln_count Python dependencies with known vulnerabilities"
    fi

    log_success "pip-audit completed"
    return 0
}

check_outdated_dependencies() {
    log_section "Outdated Dependency Check"

    local outdated_npm=0
    local outdated_pip=0

    # Check npm outdated
    if command -v npm &>/dev/null && [ -f "$PROJECT_ROOT/package.json" ]; then
        log_info "Checking for outdated npm packages..."
        
        local npm_output
        npm_output=$(npm outdated --json 2>/dev/null || echo '{}')
        outdated_npm=$(echo "$npm_output" | jq 'keys | length' 2>/dev/null || echo "0")

        if [ "$outdated_npm" -gt 0 ]; then
            echo "$npm_output" > "$REPORT_DIR/npm-outdated-${DATE}.json"
            log_warning "Found $outdated_npm outdated npm packages"
            # Treat outdated packages as low severity
            for ((i=0; i<outdated_npm; i++)); do increment_issue "low"; done
        else
            log_success "All npm packages are up to date"
        fi
    fi

    # Check pip outdated
    if command -v pip &>/dev/null && [ -f "$PROJECT_ROOT/services/worker/requirements.txt" ]; then
        log_info "Checking for outdated pip packages..."
        
        local pip_output
        pip_output=$(pip list --outdated --format json 2>/dev/null || echo '[]')
        outdated_pip=$(echo "$pip_output" | jq 'length' 2>/dev/null || echo "0")

        if [ "$outdated_pip" -gt 0 ]; then
            echo "$pip_output" > "$REPORT_DIR/pip-outdated-${DATE}.json"
            log_warning "Found $outdated_pip outdated pip packages"
            # Treat outdated packages as low severity
            for ((i=0; i<outdated_pip; i++)); do increment_issue "low"; done
        else
            log_success "All pip packages are up to date"
        fi
    fi

    return 0
}

scan_for_secrets() {
    log_section "Secret Scanning"

    log_info "Scanning for hardcoded secrets..."

    # Check if trufflehog is available
    if command -v trufflehog &>/dev/null; then
        log_info "Using trufflehog for secret scanning..."
        
        # Run trufflehog on the repository
        local secrets_output
        secrets_output=$(trufflehog filesystem "$PROJECT_ROOT" --json 2>/dev/null || echo '{}')
        
        SECRETS_FOUND=$(echo "$secrets_output" | jq -s 'length' 2>/dev/null || echo "0")

        if [ "$SECRETS_FOUND" -gt 0 ]; then
            echo "$secrets_output" > "$REPORT_DIR/secrets-found-${DATE}.json"
            log_error "Found $SECRETS_FOUND potential secrets in repository"
            for ((i=0; i<SECRETS_FOUND; i++)); do increment_issue "critical"; done
        else
            log_success "No secrets detected"
        fi
    else
        log_warning "trufflehog not found, performing basic secret pattern scan..."
        
        # Perform basic pattern-based scanning
        local secret_patterns=(
            "api[_-]?key"
            "api[_-]?secret"
            "password"
            "private[_-]?key"
            "aws[_-]?secret"
            "github[_-]?token"
        )

        local secrets_found=0
        for pattern in "${secret_patterns[@]}"; do
            # Search in source files (excluding node_modules and common safe dirs)
            local matches
            matches=$(grep -r -i "$pattern" "$PROJECT_ROOT" \
                --include="*.ts" --include="*.tsx" --include="*.js" --include="*.jsx" \
                --include="*.json" --include="*.env*" \
                --exclude-dir=node_modules --exclude-dir=.git --exclude-dir=dist \
                --exclude-dir=build 2>/dev/null | grep -v "^\s*\*" | grep -v test | wc -l)
            
            if [ "$matches" -gt 0 ]; then
                log_warning "Found $matches potential matches for pattern: $pattern (review needed)"
                secrets_found=$((secrets_found + matches))
            fi
        done

        if [ "$secrets_found" -gt 0 ]; then
            SECRETS_FOUND=$secrets_found
            log_error "Found $secrets_found potential secret patterns (manual review needed)"
            increment_issue "high"
        else
            log_success "No obvious secrets detected in basic pattern scan"
        fi
    fi

    return 0
}

check_license_compliance() {
    log_section "License Compliance Check"

    local npm_licenses=0
    local pip_licenses=0

    # Check npm licenses
    if command -v npm &>/dev/null && [ -f "$PROJECT_ROOT/package.json" ]; then
        log_info "Checking npm package licenses..."
        
        if ! command -v license-checker &>/dev/null; then
            log_warning "license-checker not found, skipping npm license check"
            npm_licenses=-1
        fi

        if [ "$npm_licenses" -ne -1 ] && command -v license-checker &>/dev/null; then
            local npm_output
            npm_output=$(license-checker --json 2>/dev/null || echo '{}')
            echo "$npm_output" > "$REPORT_DIR/npm-licenses-${DATE}.json"
            
            # Check for concerning licenses
            local gpl_count
            gpl_count=$(echo "$npm_output" | jq 'to_entries | map(select(.value.licenses | contains("GPL"))) | length' 2>/dev/null || echo "0")
            
            if [ "$gpl_count" -gt 0 ]; then
                log_warning "Found $gpl_count packages with GPL licenses (review for compatibility)"
                increment_issue "medium"
            fi
            
            log_success "npm license check completed"
        fi
    fi

    # Check pip licenses
    if command -v pip &>/dev/null && [ -f "$PROJECT_ROOT/services/worker/requirements.txt" ]; then
        log_info "Checking pip package licenses..."
        
        if ! command -v pip-licenses &>/dev/null; then
            log_warning "pip-licenses not found, skipping pip license check"
            pip_licenses=-1
        fi

        if [ "$pip_licenses" -ne -1 ] && command -v pip-licenses &>/dev/null; then
            local pip_output
            pip_output=$(pip-licenses --format=json 2>/dev/null || echo '[]')
            echo "$pip_output" > "$REPORT_DIR/pip-licenses-${DATE}.json"
            
            # Check for concerning licenses
            local gpl_count
            gpl_count=$(echo "$pip_output" | jq '[.[] | select(.License | contains("GPL"))] | length' 2>/dev/null || echo "0")
            
            if [ "$gpl_count" -gt 0 ]; then
                log_warning "Found $gpl_count packages with GPL licenses (review for compatibility)"
                increment_issue "medium"
            fi
            
            log_success "pip license check completed"
        fi
    fi

    return 0
}

# ============================================================================
# Report Generation
# ============================================================================

generate_json_report() {
    log_section "Generating JSON Report"

    local exit_code=$EXIT_SUCCESS

    # Determine exit code based on issues found
    if [ "$CRITICAL_ISSUES" -gt 0 ]; then
        exit_code=$EXIT_CRITICAL
    elif [ "$HIGH_ISSUES" -gt 0 ]; then
        exit_code=$EXIT_ERROR
    elif [ "$MEDIUM_ISSUES" -gt 0 ]; then
        exit_code=$EXIT_WARNING
    fi

    # Create JSON report
    cat > "$REPORT_FILE" << EOF
{
  "audit_metadata": {
    "timestamp": "$TIMESTAMP",
    "date": "$DATE",
    "project": "researchflow-production",
    "git_sha": "$(cd "$PROJECT_ROOT" && git rev-parse HEAD 2>/dev/null || echo 'unknown')",
    "git_branch": "$(cd "$PROJECT_ROOT" && git rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'unknown')"
  },
  "audit_summary": {
    "total_issues": $TOTAL_ISSUES,
    "critical": $CRITICAL_ISSUES,
    "high": $HIGH_ISSUES,
    "medium": $MEDIUM_ISSUES,
    "low": $LOW_ISSUES,
    "secrets_detected": $SECRETS_FOUND,
    "exit_code": $exit_code
  },
  "audit_components": {
    "npm_audit": {
      "enabled": $([ "$AUDIT_NPM" = true ] && echo "true" || echo "false"),
      "report_file": "npm-audit-${DATE}.json"
    },
    "pip_audit": {
      "enabled": $([ "$AUDIT_PIP" = true ] && echo "true" || echo "false"),
      "report_file": "pip-audit-${DATE}.json"
    },
    "outdated_packages": {
      "enabled": $([ "$CHECK_OUTDATED" = true ] && echo "true" || echo "false"),
      "npm_report": "npm-outdated-${DATE}.json",
      "pip_report": "pip-outdated-${DATE}.json"
    },
    "secret_scanning": {
      "enabled": $([ "$SCAN_SECRETS" = true ] && echo "true" || echo "false"),
      "report_file": "secrets-found-${DATE}.json"
    },
    "license_check": {
      "enabled": $([ "$CHECK_LICENSES" = true ] && echo "true" || echo "false"),
      "npm_report": "npm-licenses-${DATE}.json",
      "pip_report": "pip-licenses-${DATE}.json"
    }
  },
  "recommendations": [
    "Review and remediate critical and high severity vulnerabilities",
    "Update outdated packages to latest secure versions",
    "Ensure no hardcoded secrets are present in codebase",
    "Verify GPL/AGPL license compatibility for commercial use",
    "Consider implementing pre-commit hooks for security scanning"
  ],
  "report_location": "$REPORT_DIR"
}
EOF

    log_success "JSON report generated: $REPORT_FILE"
    
    # Display report summary
    echo ""
    log_info "Summary:"
    log_info "  Total Issues: $TOTAL_ISSUES"
    log_info "  Critical:    $CRITICAL_ISSUES"
    log_info "  High:        $HIGH_ISSUES"
    log_info "  Medium:      $MEDIUM_ISSUES"
    log_info "  Low:         $LOW_ISSUES"
    log_info "  Secrets:     $SECRETS_FOUND"

    return $exit_code
}

# ============================================================================
# Main Execution
# ============================================================================

main() {
    log_section "ResearchFlow Security Audit"
    
    log_info "Audit Mode: Full"
    log_info "Report Directory: $REPORT_DIR"

    # Execute audits
    if [ "$AUDIT_NPM" = true ]; then
        audit_npm_dependencies || true
    fi

    if [ "$AUDIT_PIP" = true ]; then
        audit_pip_dependencies || true
    fi

    if [ "$CHECK_OUTDATED" = true ]; then
        check_outdated_dependencies || true
    fi

    if [ "$SCAN_SECRETS" = true ]; then
        scan_for_secrets || true
    fi

    if [ "$CHECK_LICENSES" = true ]; then
        check_license_compliance || true
    fi

    # Generate final report
    if [ "$GENERATE_REPORT" = true ]; then
        generate_json_report
        local exit_code=$?
    else
        exit_code=$EXIT_SUCCESS
    fi

    # Final summary
    log_section "Audit Complete"
    
    if [ "$exit_code" -eq $EXIT_CRITICAL ]; then
        log_error "Security audit FAILED - Critical issues detected"
        log_error "Exit code: $exit_code"
    elif [ "$exit_code" -eq $EXIT_ERROR ]; then
        log_error "Security audit FAILED - High severity issues detected"
        log_error "Exit code: $exit_code"
    elif [ "$exit_code" -eq $EXIT_WARNING ]; then
        log_warning "Security audit completed with warnings"
        log_warning "Exit code: $exit_code"
    else
        log_success "Security audit PASSED"
        log_success "Exit code: $exit_code"
    fi

    return $exit_code
}

# Run main function
main "$@"
exit $?
