#!/bin/bash
# Production Load Testing Suite
# Phase 3 Enterprise Performance Validation

set -e

echo "🚀 Starting Production Load Testing Suite"
echo "========================================"

# Configuration
BASE_URL=${1:-"http://localhost:3001"}
CONCURRENT_USERS=${2:-50}
TOTAL_REQUESTS=${3:-1000}
TEST_DURATION=${4:-"60s"}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test results directory
RESULTS_DIR="load-test-results-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$RESULTS_DIR"

echo "Configuration:"
echo "- Base URL: $BASE_URL"
echo "- Concurrent Users: $CONCURRENT_USERS"
echo "- Total Requests: $TOTAL_REQUESTS"
echo "- Test Duration: $TEST_DURATION"
echo "- Results Directory: $RESULTS_DIR"
echo ""

# Check if hey (load testing tool) is installed
if ! command -v hey &> /dev/null; then
    echo -e "${RED}❌ 'hey' load testing tool is not installed${NC}"
    echo "Install with: go install github.com/rakyll/hey@latest"
    echo "Or on macOS: brew install hey"
    exit 1
fi

# Function to run test and capture results
run_load_test() {
    local endpoint=$1
    local description=$2
    local method=${3:-GET}
    local payload=${4:-""}
    local test_file="${RESULTS_DIR}/${description// /_}.txt"
    
    echo -e "${YELLOW}Testing: $description${NC}"
    echo "Endpoint: $method $BASE_URL$endpoint"
    
    if [ "$method" = "POST" ] && [ -n "$payload" ]; then
        hey -n $TOTAL_REQUESTS -c $CONCURRENT_USERS -m $method \
            -H "Content-Type: application/json" \
            -d "$payload" \
            "$BASE_URL$endpoint" > "$test_file" 2>&1
    else
        hey -n $TOTAL_REQUESTS -c $CONCURRENT_USERS -m $method \
            "$BASE_URL$endpoint" > "$test_file" 2>&1
    fi
    
    # Extract key metrics
    local avg_time=$(grep "Average:" "$test_file" | awk '{print $2}' || echo "N/A")
    local max_time=$(grep "Slowest:" "$test_file" | awk '{print $2}' || echo "N/A")
    local rps=$(grep "Requests/sec:" "$test_file" | awk '{print $2}' || echo "N/A")
    local success_rate=$(grep "Status code distribution:" -A 5 "$test_file" | grep "200" | awk '{print $2}' || echo "0")
    
    echo "  Average: $avg_time | Max: $max_time | RPS: $rps | Success: $success_rate"
    echo ""
}

# Health check before testing
echo -e "${YELLOW}Pre-flight health check...${NC}"
if curl -f -s "$BASE_URL/health" > /dev/null; then
    echo -e "${GREEN}✅ Health check passed${NC}"
else
    echo -e "${RED}❌ Health check failed - ensure services are running${NC}"
    exit 1
fi

echo ""
echo "🧪 Starting Load Tests..."
echo "========================"

# Test 1: Basic Health Endpoint
run_load_test "/health" "Health Check Endpoint"

# Test 2: API Health with Authentication
run_load_test "/api/health" "API Health Check"

# Test 3: Recovery System Status
run_load_test "/api/recovery/status" "Recovery System Status"

# Test 4: Backup System Status
run_load_test "/api/backup/status" "Backup System Status"

# Test 5: Security System Status
run_load_test "/api/security/status" "Security System Status"

# Test 6: Compliance System Status
run_load_test "/api/compliance/status" "Compliance System Status"

# Test 7: AI Research Brief (POST with payload)
run_load_test "/api/ai/research-brief" "AI Research Brief Generation" "POST" '{"topic":"diabetes telemedicine","max_tokens":1000}'

# Test 8: Workflow Stage Processing
run_load_test "/api/workflow/stages" "Workflow Stages List"

# Test 9: Metrics Endpoint
run_load_test "/api/metrics" "System Metrics"

# Test 10: Concurrent Recovery System Test
echo -e "${YELLOW}Testing: Recovery System Under Load${NC}"
hey -n 500 -c 25 -m POST "$BASE_URL/api/recovery/test-retry" \
    -H "Content-Type: application/json" \
    -d '{"should_fail":true,"max_retries":3}' \
    > "${RESULTS_DIR}/Recovery_System_Load_Test.txt" 2>&1

echo ""
echo "🔒 Security Load Testing..."
echo "=========================="

# Test 11: Rate Limiting Test (should trigger rate limits)
echo -e "${YELLOW}Testing: Rate Limiting Behavior${NC}"
hey -n 2000 -c 100 -z 30s "$BASE_URL/api/security/status" \
    > "${RESULTS_DIR}/Rate_Limiting_Test.txt" 2>&1

# Test 12: DDoS Protection Test
echo -e "${YELLOW}Testing: DDoS Protection${NC}"
hey -n 1500 -c 150 -z 10s "$BASE_URL/health" \
    > "${RESULTS_DIR}/DDoS_Protection_Test.txt" 2>&1

echo ""
echo "💾 Data Processing Load Tests..."
echo "==============================="

# Test 13: Large Data Processing (if endpoint exists)
if curl -f -s "$BASE_URL/api/data/process" > /dev/null 2>&1; then
    run_load_test "/api/data/process" "Large Data Processing" "POST" '{"data_size":"large","processing_mode":"batch"}'
fi

# Test 14: Database-heavy operations
run_load_test "/api/workflow/history?limit=100" "Database Query Performance"

echo ""
echo "📊 Generating Load Test Summary Report..."
echo "======================================="

# Create comprehensive summary report
SUMMARY_FILE="${RESULTS_DIR}/LOAD_TEST_SUMMARY.md"

cat > "$SUMMARY_FILE" << EOF
# Load Test Summary Report
**Generated:** $(date)
**Base URL:** $BASE_URL
**Configuration:** $CONCURRENT_USERS concurrent users, $TOTAL_REQUESTS requests per test

## Test Results Overview

| Test | Avg Response | Max Response | Requests/sec | Success Rate |
|------|--------------|--------------|--------------|--------------|
EOF

# Process each test result
for test_file in "${RESULTS_DIR}"/*.txt; do
    if [ -f "$test_file" ]; then
        test_name=$(basename "$test_file" .txt | sed 's/_/ /g')
        avg_time=$(grep "Average:" "$test_file" | awk '{print $2}' || echo "N/A")
        max_time=$(grep "Slowest:" "$test_file" | awk '{print $2}' || echo "N/A")
        rps=$(grep "Requests/sec:" "$test_file" | awk '{print $2}' || echo "N/A")
        success_count=$(grep "Status code distribution:" -A 5 "$test_file" | grep "200" | awk '{print $2}' || echo "0")
        
        if [ "$success_count" != "0" ]; then
            success_rate="${success_count}/${TOTAL_REQUESTS}"
        else
            success_rate="N/A"
        fi
        
        echo "| $test_name | $avg_time | $max_time | $rps | $success_rate |" >> "$SUMMARY_FILE"
    fi
done

# Add recommendations to summary
cat >> "$SUMMARY_FILE" << EOF

## Performance Analysis

### Key Metrics Summary
- **Average Response Time**: $(find "${RESULTS_DIR}" -name "*.txt" -exec grep "Average:" {} \; | awk '{sum += $2; count++} END {if(count>0) printf "%.3fs", sum/count; else print "N/A"}')
- **Peak Response Time**: $(find "${RESULTS_DIR}" -name "*.txt" -exec grep "Slowest:" {} \; | awk '{if($2>max) max=$2} END {printf "%.3fs", max}')
- **Average Throughput**: $(find "${RESULTS_DIR}" -name "*.txt" -exec grep "Requests/sec:" {} \; | awk '{sum += $2; count++} END {if(count>0) printf "%.1f req/s", sum/count; else print "N/A"}')

### Recommendations

1. **Response Time Optimization**
   - Target: <200ms for health checks, <2s for complex operations
   - Review any endpoints with >1s average response time

2. **Throughput Optimization**
   - Monitor requests/second under sustained load
   - Consider scaling if throughput drops significantly

3. **Error Rate Monitoring**
   - Investigate any 5xx errors
   - Verify rate limiting is working correctly

4. **Phase 3 System Performance**
   - Recovery system should handle failures gracefully
   - Security systems should not significantly impact performance
   - Compliance logging should be asynchronous

5. **Database Performance**
   - Monitor connection pool utilization
   - Consider read replicas for heavy read operations

## Next Steps

- Review individual test results in this directory
- Monitor system resources during peak load
- Adjust Phase 3 configuration based on performance
- Set up ongoing performance monitoring
- Consider auto-scaling based on load patterns

## Test Files

EOF

# List all test result files
for test_file in "${RESULTS_DIR}"/*.txt; do
    if [ -f "$test_file" ]; then
        echo "- $(basename "$test_file")" >> "$SUMMARY_FILE"
    fi
done

echo ""
echo "📈 Performance Analysis Complete"
echo "==============================="

# Quick analysis
total_tests=$(find "${RESULTS_DIR}" -name "*.txt" | wc -l)
avg_response=$(find "${RESULTS_DIR}" -name "*.txt" -exec grep "Average:" {} \; | awk '{sum += $2; count++} END {if(count>0) printf "%.3f", sum/count; else print "0"}')

echo "Total test scenarios: $total_tests"
echo "Average response time: ${avg_response}s"

# Check for errors
error_files=$(find "${RESULTS_DIR}" -name "*.txt" -exec grep -l "Error distribution" {} \; | wc -l)
if [ "$error_files" -gt 0 ]; then
    echo -e "${RED}⚠️  Some tests encountered errors. Check individual result files.${NC}"
else
    echo -e "${GREEN}✅ All load tests completed successfully!${NC}"
fi

echo ""
echo -e "${GREEN}🎉 Load testing complete!${NC}"
echo "Results directory: $RESULTS_DIR"
echo "Summary report: $SUMMARY_FILE"
echo ""
echo "Next steps:"
echo "- Review the summary report and individual test results"
echo "- Monitor system resources during peak load"
echo "- Adjust Phase 3 configuration based on performance findings"
echo "- Set up ongoing performance monitoring dashboards"