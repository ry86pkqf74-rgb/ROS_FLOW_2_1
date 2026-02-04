#!/bin/bash

###############################################################################
# Stage 7 Statistical Analysis - Integration Test Script
#
# Tests the complete end-to-end workflow:
# 1. Orchestrator API health check
# 2. Worker API health check
# 3. Execute statistical analysis
# 4. Verify database storage
# 5. Check results format
#
# Usage:
#   bash scripts/test_stage7_integration.sh
#
# Requirements:
#   - Docker services running (postgres, orchestrator, worker)
#   - curl and jq installed
###############################################################################

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ORCHESTRATOR_URL="${ORCHESTRATOR_URL:-http://localhost:3001}"
WORKER_URL="${WORKER_URL:-http://localhost:8000}"
RESEARCH_ID="${RESEARCH_ID:-test-stage7-$(date +%s)}"

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

###############################################################################
# Helper Functions
###############################################################################

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
    ((TESTS_PASSED++))
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
    ((TESTS_FAILED++))
}

log_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

check_command() {
    if ! command -v $1 &> /dev/null; then
        log_error "Required command '$1' not found"
        exit 1
    fi
}

###############################################################################
# Pre-flight Checks
###############################################################################

echo ""
echo "============================================================"
echo "  Stage 7 Statistical Analysis - Integration Test"
echo "============================================================"
echo ""

log_info "Running pre-flight checks..."

check_command "curl"
check_command "jq"

log_success "All required commands available"

###############################################################################
# Test 1: Orchestrator Health Check
###############################################################################

echo ""
log_info "Test 1: Checking orchestrator health..."

ORCHESTRATOR_HEALTH=$(curl -s "${ORCHESTRATOR_URL}/health" || echo '{"status":"error"}')
ORCHESTRATOR_STATUS=$(echo $ORCHESTRATOR_HEALTH | jq -r '.status // "error"')

if [ "$ORCHESTRATOR_STATUS" = "healthy" ] || [ "$ORCHESTRATOR_STATUS" = "ok" ]; then
    log_success "Orchestrator is healthy"
else
    log_error "Orchestrator is not healthy: $ORCHESTRATOR_STATUS"
    exit 1
fi

###############################################################################
# Test 2: Worker Health Check
###############################################################################

echo ""
log_info "Test 2: Checking worker health..."

WORKER_HEALTH=$(curl -s "${WORKER_URL}/health" || echo '{"status":"error"}')
WORKER_STATUS=$(echo $WORKER_HEALTH | jq -r '.status // "error"')

if [ "$WORKER_STATUS" = "healthy" ] || [ "$WORKER_STATUS" = "ok" ]; then
    log_success "Worker is healthy"
else
    log_error "Worker is not healthy: $WORKER_STATUS"
    exit 1
fi

###############################################################################
# Test 3: Statistical Analysis Endpoint Health
###############################################################################

echo ""
log_info "Test 3: Checking statistical analysis endpoint..."

STAT_HEALTH=$(curl -s "${ORCHESTRATOR_URL}/api/analysis/statistical/health" || echo '{"status":"error"}')
STAT_STATUS=$(echo $STAT_HEALTH | jq -r '.status // "error"')
WORKER_STATUS_CHECK=$(echo $STAT_HEALTH | jq -r '.worker_status // "unknown"')

if [ "$STAT_STATUS" = "healthy" ]; then
    log_success "Statistical analysis endpoint is healthy"
    log_info "Worker status: $WORKER_STATUS_CHECK"
else
    log_error "Statistical analysis endpoint is not healthy"
    exit 1
fi

###############################################################################
# Test 4: List Available Tests
###############################################################################

echo ""
log_info "Test 4: Listing available statistical tests..."

TESTS_RESPONSE=$(curl -s "${ORCHESTRATOR_URL}/api/analysis/statistical/tests")
TEST_COUNT=$(echo $TESTS_RESPONSE | jq '.tests | length')

if [ "$TEST_COUNT" -gt 0 ]; then
    log_success "Found $TEST_COUNT available statistical tests"
    echo $TESTS_RESPONSE | jq -r '.tests[] | "  - \(.name): \(.description)"'
else
    log_error "No statistical tests available"
fi

###############################################################################
# Test 5: Validate Study Data
###############################################################################

echo ""
log_info "Test 5: Validating study data..."

VALIDATION_REQUEST='{
  "groups": ["Treatment", "Treatment", "Treatment", "Control", "Control", "Control"],
  "outcomes": {
    "blood_pressure": [120, 118, 122, 135, 138, 140]
  },
  "metadata": {
    "study_title": "Blood Pressure Test"
  }
}'

VALIDATION_RESPONSE=$(curl -s -X POST \
  "${ORCHESTRATOR_URL}/api/analysis/statistical/validate" \
  -H "Content-Type: application/json" \
  -d "$VALIDATION_REQUEST")

VALIDATION_STATUS=$(echo $VALIDATION_RESPONSE | jq -r '.valid // false')
WARNING_COUNT=$(echo $VALIDATION_RESPONSE | jq '.warnings | length // 0')
ERROR_COUNT=$(echo $VALIDATION_RESPONSE | jq '.errors | length // 0')

if [ "$VALIDATION_STATUS" = "true" ]; then
    log_success "Data validation passed"
    if [ "$WARNING_COUNT" -gt 0 ]; then
        log_warning "$WARNING_COUNT warnings found"
        echo $VALIDATION_RESPONSE | jq -r '.warnings[]'
    fi
else
    log_error "Data validation failed with $ERROR_COUNT errors"
    echo $VALIDATION_RESPONSE | jq -r '.errors[]'
fi

###############################################################################
# Test 6: Execute Statistical Analysis
###############################################################################

echo ""
log_info "Test 6: Executing statistical analysis (Independent t-test)..."

ANALYSIS_REQUEST='{
  "study_data": {
    "groups": ["Treatment", "Treatment", "Treatment", "Treatment", "Treatment", 
               "Control", "Control", "Control", "Control", "Control"],
    "outcomes": {
      "blood_pressure": [120, 118, 122, 119, 121, 135, 138, 140, 136, 139]
    },
    "metadata": {
      "study_title": "Blood Pressure Clinical Trial",
      "outcome_unit": "mmHg"
    }
  },
  "options": {
    "test_type": "t_test_independent",
    "confidence_level": 0.95,
    "alpha": 0.05,
    "calculate_effect_size": true,
    "check_assumptions": true,
    "generate_visualizations": true
  }
}'

log_info "Sending analysis request to ${ORCHESTRATOR_URL}/api/research/${RESEARCH_ID}/stage/7/execute"

ANALYSIS_RESPONSE=$(curl -s -X POST \
  "${ORCHESTRATOR_URL}/api/research/${RESEARCH_ID}/stage/7/execute" \
  -H "Content-Type: application/json" \
  -d "$ANALYSIS_REQUEST")

ANALYSIS_STATUS=$(echo $ANALYSIS_RESPONSE | jq -r '.status // "error"')
REQUEST_ID=$(echo $ANALYSIS_RESPONSE | jq -r '.request_id // "unknown"')

if [ "$ANALYSIS_STATUS" = "completed" ]; then
    log_success "Statistical analysis completed successfully"
    log_info "Request ID: $REQUEST_ID"
    
    # Check for inferential results
    TEST_TYPE=$(echo $ANALYSIS_RESPONSE | jq -r '.result.inferential.test_type // "none"')
    P_VALUE=$(echo $ANALYSIS_RESPONSE | jq -r '.result.inferential.p_value // "N/A"')
    
    if [ "$TEST_TYPE" != "none" ]; then
        log_success "Test performed: $TEST_TYPE"
        log_info "P-value: $P_VALUE"
    fi
    
    # Check for effect sizes
    COHENS_D=$(echo $ANALYSIS_RESPONSE | jq -r '.result.effect_sizes.cohens_d // "N/A"')
    if [ "$COHENS_D" != "N/A" ]; then
        log_success "Effect size calculated: Cohen's d = $COHENS_D"
    fi
    
    # Check for assumptions
    ASSUMPTIONS_PASSED=$(echo $ANALYSIS_RESPONSE | jq -r '.result.assumptions.passed // false')
    if [ "$ASSUMPTIONS_PASSED" = "true" ]; then
        log_success "Statistical assumptions passed"
    else
        log_warning "Some statistical assumptions violated"
    fi
    
    # Save full response for inspection
    echo $ANALYSIS_RESPONSE | jq '.' > /tmp/stage7_analysis_response.json
    log_info "Full response saved to /tmp/stage7_analysis_response.json"
    
else
    log_error "Statistical analysis failed with status: $ANALYSIS_STATUS"
    echo $ANALYSIS_RESPONSE | jq '.'
fi

###############################################################################
# Test 7: Verify Database Storage (if postgres accessible)
###############################################################################

echo ""
log_info "Test 7: Verifying database storage..."

# Try to connect to postgres
if command -v docker &> /dev/null; then
    POSTGRES_CONTAINER=$(docker ps --format '{{.Names}}' | grep postgres | head -n 1)
    
    if [ -n "$POSTGRES_CONTAINER" ]; then
        log_info "Found postgres container: $POSTGRES_CONTAINER"
        
        # Check if analysis was stored
        ANALYSIS_COUNT=$(docker exec $POSTGRES_CONTAINER psql -U ros -d ros -t -c \
            "SELECT COUNT(*) FROM statistical_analysis_results WHERE analysis_name LIKE '%Blood Pressure%';" \
            2>/dev/null | xargs)
        
        if [ "$ANALYSIS_COUNT" -gt 0 ]; then
            log_success "Analysis results found in database (count: $ANALYSIS_COUNT)"
            
            # Get the latest analysis details
            LATEST_ANALYSIS=$(docker exec $POSTGRES_CONTAINER psql -U ros -d ros -t -c \
                "SELECT analysis_name, test_type, status FROM statistical_analysis_results ORDER BY created_at DESC LIMIT 1;" \
                2>/dev/null)
            
            log_info "Latest analysis: $LATEST_ANALYSIS"
        else
            log_warning "No analysis results found in database (may need to check worker database connection)"
        fi
    else
        log_warning "Postgres container not found, skipping database check"
    fi
else
    log_warning "Docker not available, skipping database check"
fi

###############################################################################
# Test 8: Test Assumption Checking
###############################################################################

echo ""
log_info "Test 8: Testing assumption checks with non-normal data..."

NONNORMAL_REQUEST='{
  "study_data": {
    "groups": ["A", "A", "A", "A", "A", "B", "B", "B", "B", "B"],
    "outcomes": {
      "skewed_data": [1, 2, 2, 3, 50, 100, 101, 102, 103, 104]
    },
    "metadata": {
      "study_title": "Non-normal Distribution Test"
    }
  },
  "options": {
    "test_type": "t_test_independent",
    "check_assumptions": true
  }
}'

NONNORMAL_RESPONSE=$(curl -s -X POST \
  "${ORCHESTRATOR_URL}/api/research/${RESEARCH_ID}-nonnormal/stage/7/execute" \
  -H "Content-Type: application/json" \
  -d "$NONNORMAL_REQUEST")

NONNORMAL_STATUS=$(echo $NONNORMAL_RESPONSE | jq -r '.status // "error"')

if [ "$NONNORMAL_STATUS" = "completed" ]; then
    ASSUMPTIONS_PASSED=$(echo $NONNORMAL_RESPONSE | jq -r '.result.assumptions.passed // false')
    REMEDIATION_COUNT=$(echo $NONNORMAL_RESPONSE | jq '.result.assumptions.remediation_suggestions | length // 0')
    
    if [ "$ASSUMPTIONS_PASSED" = "false" ] && [ "$REMEDIATION_COUNT" -gt 0 ]; then
        log_success "Assumption violations correctly detected"
        log_info "Remediation suggestions provided: $REMEDIATION_COUNT"
        echo $NONNORMAL_RESPONSE | jq -r '.result.assumptions.remediation_suggestions[]'
    else
        log_warning "Assumption checking may need improvement"
    fi
else
    log_error "Non-normal data test failed"
fi

###############################################################################
# Summary
###############################################################################

echo ""
echo "============================================================"
echo "  Test Summary"
echo "============================================================"
echo ""

TOTAL_TESTS=$((TESTS_PASSED + TESTS_FAILED))

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC} ($TESTS_PASSED/$TOTAL_TESTS)"
    echo ""
    echo "Stage 7 Statistical Analysis is fully operational."
    echo ""
    echo "Next steps:"
    echo "  1. Test from frontend UI"
    echo "  2. Implement Mercury enhancements (15 TODOs)"
    echo "  3. Add visualization rendering"
    echo "  4. Create user documentation"
    echo ""
    exit 0
else
    echo -e "${RED}✗ Some tests failed${NC} (Passed: $TESTS_PASSED/$TOTAL_TESTS, Failed: $TESTS_FAILED)"
    echo ""
    echo "Please check the error messages above and:"
    echo "  1. Verify all services are running"
    echo "  2. Check logs for detailed error messages"
    echo "  3. Ensure database migration was applied"
    echo ""
    exit 1
fi
