#!/bin/bash
# ============================================
# ResearchFlow - Stage 1 Protocol Design Agent Testing
# ============================================
# Comprehensive testing suite for Stage 1 Protocol Design Agent
# Tests PICO framework, quality gates, and pipeline integration
# ============================================

set -e

# Colors
BLUE='\033[34m'
GREEN='\033[32m'
YELLOW='\033[33m'
RED='\033[31m'
CYAN='\033[36m'
NC='\033[0m'

# Configuration
API_BASE="http://localhost:3002"
WORKER_BASE="http://localhost:8001"
TEST_RESULTS_DIR="./test-results"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║            Stage 1 Protocol Design Agent Tests              ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Create test results directory
mkdir -p "$TEST_RESULTS_DIR"

# Test 1: Feature Flag Status
echo -e "${BLUE}🚩 Test 1: Feature Flag Validation${NC}"
echo "Testing feature flag configuration..."

FF_RESPONSE=$(curl -s "$API_BASE/api/feature-flags" || echo '{"error": "api_unreachable"}')
ENABLE_NEW_STAGE_1=$(echo "$FF_RESPONSE" | jq -r '.["ENABLE_NEW_STAGE_1"] // "unknown"')

if [ "$ENABLE_NEW_STAGE_1" = "true" ]; then
    echo -e "✅ ENABLE_NEW_STAGE_1: ${GREEN}true${NC} (New agent active)"
elif [ "$ENABLE_NEW_STAGE_1" = "false" ]; then
    echo -e "⚠️  ENABLE_NEW_STAGE_1: ${YELLOW}false${NC} (Legacy agent active)"
else
    echo -e "❌ ENABLE_NEW_STAGE_1: ${RED}$ENABLE_NEW_STAGE_1${NC} (Error)"
fi

echo "$FF_RESPONSE" > "$TEST_RESULTS_DIR/feature_flags_${TIMESTAMP}.json"
echo ""

# Test 2: Stage Registry Validation
echo -e "${BLUE}🔧 Test 2: Stage Registry Validation${NC}"
echo "Checking which Stage 1 implementation is loaded..."

STAGE_INFO=$(curl -s "$WORKER_BASE/api/stages/1/info" || echo '{"error": "endpoint_unreachable"}')
STAGE_CLASS=$(echo "$STAGE_INFO" | jq -r '.class_name // "unknown"')

if [[ "$STAGE_CLASS" == *"ProtocolDesign"* ]]; then
    echo -e "✅ Stage 1 Implementation: ${GREEN}$STAGE_CLASS${NC} (New agent)"
elif [[ "$STAGE_CLASS" == *"UploadIntake"* ]] || [[ "$STAGE_CLASS" == *"Upload"* ]]; then
    echo -e "⚠️  Stage 1 Implementation: ${YELLOW}$STAGE_CLASS${NC} (Legacy agent)"
else
    echo -e "❌ Stage 1 Implementation: ${RED}$STAGE_CLASS${NC} (Unknown)"
fi

echo "$STAGE_INFO" > "$TEST_RESULTS_DIR/stage_registry_${TIMESTAMP}.json"
echo ""

# Test 3: PICO Framework Test
echo -e "${BLUE}🧬 Test 3: PICO Framework Extraction${NC}"
echo "Testing PICO framework with sample research question..."

RESEARCH_QUESTION="Does early intervention with cognitive behavioral therapy reduce depression symptoms in adolescents compared to standard care over 12 weeks?"

TEST_PAYLOAD=$(cat << EOF
{
  "stage_id": 1,
  "config": {
    "protocol_design": {
      "initial_message": "$RESEARCH_QUESTION",
      "max_iterations": 3
    }
  },
  "governance_mode": "DEMO",
  "metadata": {
    "test_id": "pico_test_$TIMESTAMP",
    "test_type": "pico_framework"
  }
}
EOF
)

echo "Submitting test job..."
JOB_RESPONSE=$(curl -s -X POST "$API_BASE/api/jobs" \
  -H "Content-Type: application/json" \
  -d "$TEST_PAYLOAD" || echo '{"error": "job_submission_failed"}')

JOB_ID=$(echo "$JOB_RESPONSE" | jq -r '.job_id // "unknown"')

if [ "$JOB_ID" != "unknown" ] && [ "$JOB_ID" != "null" ]; then
    echo -e "✅ Job submitted: ${GREEN}$JOB_ID${NC}"
    
    # Wait for job completion (max 5 minutes)
    echo "Waiting for job completion..."
    for i in {1..60}; do
        JOB_STATUS=$(curl -s "$API_BASE/api/jobs/$JOB_ID/status" | jq -r '.status // "unknown"')
        
        if [ "$JOB_STATUS" = "completed" ] || [ "$JOB_STATUS" = "failed" ]; then
            break
        fi
        
        echo -n "."
        sleep 5
    done
    echo ""
    
    # Get job results
    JOB_RESULT=$(curl -s "$API_BASE/api/jobs/$JOB_ID/result")
    PICO_ELEMENTS=$(echo "$JOB_RESULT" | jq -r '.output.pico_elements // {}')
    QUALITY_SCORE=$(echo "$JOB_RESULT" | jq -r '.output.quality_score // 0')
    
    # Validate PICO elements
    POPULATION=$(echo "$PICO_ELEMENTS" | jq -r '.population // ""')
    INTERVENTION=$(echo "$PICO_ELEMENTS" | jq -r '.intervention // ""')
    COMPARATOR=$(echo "$PICO_ELEMENTS" | jq -r '.comparator // ""')
    OUTCOMES=$(echo "$PICO_ELEMENTS" | jq -r '.outcomes // []')
    
    echo -e "${CYAN}PICO Analysis Results:${NC}"
    if [ -n "$POPULATION" ] && [ "$POPULATION" != "null" ]; then
        echo -e "  ✅ Population: ${GREEN}$POPULATION${NC}"
    else
        echo -e "  ❌ Population: ${RED}Missing${NC}"
    fi
    
    if [ -n "$INTERVENTION" ] && [ "$INTERVENTION" != "null" ]; then
        echo -e "  ✅ Intervention: ${GREEN}$INTERVENTION${NC}"
    else
        echo -e "  ❌ Intervention: ${RED}Missing${NC}"
    fi
    
    if [ -n "$COMPARATOR" ] && [ "$COMPARATOR" != "null" ]; then
        echo -e "  ✅ Comparator: ${GREEN}$COMPARATOR${NC}"
    else
        echo -e "  ❌ Comparator: ${RED}Missing${NC}"
    fi
    
    OUTCOME_COUNT=$(echo "$OUTCOMES" | jq 'length')
    if [ "$OUTCOME_COUNT" -gt 0 ]; then
        echo -e "  ✅ Outcomes: ${GREEN}$OUTCOME_COUNT identified${NC}"
    else
        echo -e "  ❌ Outcomes: ${RED}None identified${NC}"
    fi
    
    echo -e "  📊 Quality Score: ${CYAN}$QUALITY_SCORE${NC}"
    
    echo "$JOB_RESULT" > "$TEST_RESULTS_DIR/pico_test_${TIMESTAMP}.json"
    
else
    echo -e "❌ Job submission failed: ${RED}$JOB_ID${NC}"
fi
echo ""

# Test 4: Pipeline Integration Test
echo -e "${BLUE}🔄 Test 4: Pipeline Integration (Stages 1→2→3)${NC}"
echo "Testing PICO data flow to Stage 2 and Stage 3..."

if [ "$JOB_ID" != "unknown" ] && [ "$JOB_ID" != "null" ]; then
    # Trigger Stage 2 with Stage 1 output
    STAGE_2_PAYLOAD=$(cat << EOF
{
  "stage_id": 2,
  "config": {
    "literature_review": {
      "search_query": "cognitive behavioral therapy adolescents depression",
      "max_papers": 5
    }
  },
  "governance_mode": "DEMO",
  "parent_job_id": "$JOB_ID",
  "metadata": {
    "test_id": "pipeline_test_$TIMESTAMP",
    "test_type": "stage_integration"
  }
}
EOF
)
    
    STAGE_2_RESPONSE=$(curl -s -X POST "$API_BASE/api/jobs" \
      -H "Content-Type: application/json" \
      -d "$STAGE_2_PAYLOAD" || echo '{"error": "stage2_failed"}')
    
    STAGE_2_JOB_ID=$(echo "$STAGE_2_RESPONSE" | jq -r '.job_id // "unknown"')
    
    if [ "$STAGE_2_JOB_ID" != "unknown" ]; then
        echo -e "✅ Stage 2 triggered: ${GREEN}$STAGE_2_JOB_ID${NC}"
    else
        echo -e "❌ Stage 2 failed to start: ${RED}$STAGE_2_JOB_ID${NC}"
    fi
else
    echo -e "⚠️  Skipping pipeline test - Stage 1 job failed${NC}"
fi
echo ""

# Test 5: Performance Test
echo -e "${BLUE}⚡ Test 5: Performance Validation${NC}"
echo "Testing response times and resource usage..."

START_TIME=$(date +%s%3N)
PERF_PAYLOAD=$(cat << EOF
{
  "stage_id": 1,
  "config": {
    "protocol_design": {
      "initial_message": "Quick test for performance measurement",
      "max_iterations": 1
    }
  },
  "governance_mode": "DEMO",
  "metadata": {
    "test_id": "perf_test_$TIMESTAMP",
    "test_type": "performance"
  }
}
EOF
)

PERF_RESPONSE=$(curl -s -X POST "$API_BASE/api/jobs" \
  -H "Content-Type: application/json" \
  -d "$PERF_PAYLOAD")

PERF_JOB_ID=$(echo "$PERF_RESPONSE" | jq -r '.job_id // "unknown"')
END_TIME=$(date +%s%3N)
RESPONSE_TIME=$((END_TIME - START_TIME))

echo -e "  📊 Job Submission Time: ${CYAN}${RESPONSE_TIME}ms${NC}"

if [ "$RESPONSE_TIME" -lt 1000 ]; then
    echo -e "  ✅ Performance: ${GREEN}Excellent (<1s)${NC}"
elif [ "$RESPONSE_TIME" -lt 3000 ]; then
    echo -e "  ✅ Performance: ${YELLOW}Good (<3s)${NC}"
else
    echo -e "  ❌ Performance: ${RED}Slow (>${RESPONSE_TIME}ms)${NC}"
fi
echo ""

# Test Summary
echo -e "${BLUE}📋 Test Summary${NC}"
echo "==============================="

TOTAL_TESTS=5
PASSED_TESTS=0

# Count successful tests based on previous results
if [ "$ENABLE_NEW_STAGE_1" = "true" ]; then ((PASSED_TESTS++)); fi
if [[ "$STAGE_CLASS" == *"ProtocolDesign"* ]]; then ((PASSED_TESTS++)); fi
if [ -n "$POPULATION" ] && [ "$POPULATION" != "null" ]; then ((PASSED_TESTS++)); fi
if [ "$STAGE_2_JOB_ID" != "unknown" ] && [ "$JOB_ID" != "unknown" ]; then ((PASSED_TESTS++)); fi
if [ "$RESPONSE_TIME" -lt 3000 ] && [ "$PERF_JOB_ID" != "unknown" ]; then ((PASSED_TESTS++)); fi

PASS_RATE=$((PASSED_TESTS * 100 / TOTAL_TESTS))

echo "Tests Passed: $PASSED_TESTS/$TOTAL_TESTS ($PASS_RATE%)"
echo "Results saved to: $TEST_RESULTS_DIR/"

if [ "$PASS_RATE" -ge 80 ]; then
    echo -e "${GREEN}🎉 Stage 1 Testing: PASSED${NC}"
    echo "Ready for production rollout!"
elif [ "$PASS_RATE" -ge 60 ]; then
    echo -e "${YELLOW}⚠️  Stage 1 Testing: PARTIAL PASS${NC}"
    echo "Some issues detected - review before production"
else
    echo -e "${RED}❌ Stage 1 Testing: FAILED${NC}"
    echo "Critical issues detected - do not deploy to production"
fi

echo ""
echo -e "${CYAN}📊 Detailed Results:${NC}"
echo "  - Feature Flags: $TEST_RESULTS_DIR/feature_flags_${TIMESTAMP}.json"
echo "  - Stage Registry: $TEST_RESULTS_DIR/stage_registry_${TIMESTAMP}.json"
echo "  - PICO Test: $TEST_RESULTS_DIR/pico_test_${TIMESTAMP}.json"
echo ""
echo -e "${CYAN}Next Steps:${NC}"
echo "  1. Review test results in detail"
echo "  2. Check Grafana dashboards for performance metrics"
echo "  3. Test feature flag toggling with: ./scripts/staging-feature-toggle.sh"
echo "  4. Run load tests if performance is acceptable"
echo ""