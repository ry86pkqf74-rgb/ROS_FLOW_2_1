#!/bin/bash
# ============================================
# ResearchFlow - Stage 1 Load Testing
# ============================================
# Performance and load testing for Stage 1 Protocol Design Agent
# Tests concurrent executions, response times, and resource usage
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
CONCURRENT_JOBS=${1:-3}
TEST_DURATION=${2:-300}  # 5 minutes default
RESULTS_DIR="./load-test-results"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║           Stage 1 Protocol Design Agent Load Test           ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Configuration:"
echo "  - Concurrent Jobs: $CONCURRENT_JOBS"
echo "  - Test Duration: ${TEST_DURATION}s"
echo "  - Results Dir: $RESULTS_DIR"
echo ""

# Create results directory
mkdir -p "$RESULTS_DIR"

# Test scenarios for Stage 1
declare -a TEST_SCENARIOS=(
    "Does early intervention with physical therapy reduce recovery time in ACL injuries compared to delayed treatment over 6 months?"
    "Can mindfulness-based stress reduction therapy improve quality of life in cancer patients compared to standard supportive care?"
    "Does telehealth monitoring reduce hospital readmissions in heart failure patients compared to traditional follow-up care?"
    "Is cognitive behavioral therapy more effective than medication for treating anxiety disorders in elderly patients?"
    "Does nutritional counseling improve glycemic control in type 2 diabetes patients compared to standard diabetes education?"
)

# Function to submit a test job
submit_test_job() {
    local scenario=$1
    local job_id=$2
    local start_time=$3
    
    local payload=$(cat << EOF
{
  "stage_id": 1,
  "config": {
    "protocol_design": {
      "initial_message": "$scenario",
      "max_iterations": 3
    }
  },
  "governance_mode": "DEMO",
  "metadata": {
    "load_test_id": "load_test_${TIMESTAMP}",
    "job_sequence": $job_id,
    "scenario_type": "performance_test",
    "start_time": $start_time
  }
}
EOF
)
    
    local response=$(curl -s -X POST "$API_BASE/api/jobs" \
        -H "Content-Type: application/json" \
        -d "$payload" 2>/dev/null || echo '{"error": "submission_failed"}')
    
    echo "$response" | jq -r '.job_id // "failed"'
}

# Function to monitor job status
monitor_job() {
    local job_id=$1
    local max_wait=$2
    local start_time=$(date +%s)
    
    for ((i=0; i<max_wait; i+=5)); do
        local status=$(curl -s "$API_BASE/api/jobs/$job_id/status" 2>/dev/null | jq -r '.status // "unknown"')
        
        if [ "$status" = "completed" ]; then
            local end_time=$(date +%s)
            local duration=$((end_time - start_time))
            echo "completed,$duration"
            return
        elif [ "$status" = "failed" ]; then
            local end_time=$(date +%s)
            local duration=$((end_time - start_time))
            echo "failed,$duration"
            return
        fi
        
        sleep 5
    done
    
    echo "timeout,$max_wait"
}

# Function to get system metrics
get_system_metrics() {
    local timestamp=$(date +%s)
    local cpu_usage=$(docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}" | grep -E "(orchestrator|worker)" | awk '{print $2}' | sed 's/%//' | paste -sd+ | bc 2>/dev/null || echo "0")
    local memory_usage=$(docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}" | grep -E "(orchestrator|worker)" | awk '{print $2}' | cut -d'/' -f1 | sed 's/[^0-9.]//g' | paste -sd+ | bc 2>/dev/null || echo "0")
    
    echo "$timestamp,$cpu_usage,$memory_usage"
}

# Initialize metrics file
METRICS_FILE="$RESULTS_DIR/system_metrics_${TIMESTAMP}.csv"
echo "timestamp,cpu_percent,memory_mb" > "$METRICS_FILE"

# Initialize results file  
RESULTS_FILE="$RESULTS_DIR/load_test_results_${TIMESTAMP}.csv"
echo "job_id,scenario,submit_time,completion_time,status,duration_seconds,pico_elements,quality_score" > "$RESULTS_FILE"

echo -e "${BLUE}🚀 Starting Load Test...${NC}"
echo "Monitoring system metrics and job performance"
echo ""

# Start background system monitoring
(
    while [ -f "$RESULTS_DIR/.monitoring" ]; do
        get_system_metrics >> "$METRICS_FILE"
        sleep 10
    done
) &

MONITORING_PID=$!
touch "$RESULTS_DIR/.monitoring"

# Track jobs
declare -a ACTIVE_JOBS=()
declare -a JOB_START_TIMES=()
JOB_COUNTER=1
START_TIME=$(date +%s)

echo -e "${CYAN}Submitting initial batch of $CONCURRENT_JOBS jobs...${NC}"

# Submit initial batch
for ((i=0; i<CONCURRENT_JOBS; i++)); do
    scenario_index=$((i % ${#TEST_SCENARIOS[@]}))
    scenario="${TEST_SCENARIOS[$scenario_index]}"
    
    submit_time=$(date +%s)
    job_id=$(submit_test_job "$scenario" $JOB_COUNTER $submit_time)
    
    if [ "$job_id" != "failed" ]; then
        ACTIVE_JOBS+=("$job_id")
        JOB_START_TIMES+=("$submit_time")
        echo "  ✅ Job $JOB_COUNTER submitted: $job_id"
    else
        echo "  ❌ Job $JOB_COUNTER failed to submit"
    fi
    
    ((JOB_COUNTER++))
done

echo ""
echo -e "${BLUE}⏳ Running load test for ${TEST_DURATION} seconds...${NC}"
echo "Active jobs: ${#ACTIVE_JOBS[@]}"

# Main testing loop
COMPLETED_JOBS=0
FAILED_JOBS=0
TOTAL_RESPONSE_TIME=0

while [ $(($(date +%s) - START_TIME)) -lt $TEST_DURATION ]; do
    # Check status of active jobs
    for i in "${!ACTIVE_JOBS[@]}"; do
        job_id="${ACTIVE_JOBS[$i]}"
        start_time="${JOB_START_TIMES[$i]}"
        
        if [ -n "$job_id" ]; then
            result=$(monitor_job "$job_id" 1)  # Quick check
            status=$(echo "$result" | cut -d',' -f1)
            duration=$(echo "$result" | cut -d',' -f2)
            
            if [ "$status" = "completed" ] || [ "$status" = "failed" ]; then
                # Get job details
                job_result=$(curl -s "$API_BASE/api/jobs/$job_id/result" 2>/dev/null)
                pico_count=$(echo "$job_result" | jq -r '.output.pico_elements | keys | length' 2>/dev/null || echo "0")
                quality_score=$(echo "$job_result" | jq -r '.output.quality_score // 0' 2>/dev/null)
                
                scenario_index=$(((JOB_COUNTER - ${#ACTIVE_JOBS[@]} + i) % ${#TEST_SCENARIOS[@]}))
                scenario="${TEST_SCENARIOS[$scenario_index]}"
                
                # Log result
                echo "$job_id,\"$scenario\",$start_time,$(date +%s),$status,$duration,$pico_count,$quality_score" >> "$RESULTS_FILE"
                
                if [ "$status" = "completed" ]; then
                    ((COMPLETED_JOBS++))
                    TOTAL_RESPONSE_TIME=$((TOTAL_RESPONSE_TIME + duration))
                    echo "  ✅ Job $job_id completed in ${duration}s"
                else
                    ((FAILED_JOBS++))
                    echo "  ❌ Job $job_id failed after ${duration}s"
                fi
                
                # Submit new job to maintain load
                if [ $(($(date +%s) - START_TIME)) -lt $((TEST_DURATION - 60)) ]; then
                    new_scenario_index=$((JOB_COUNTER % ${#TEST_SCENARIOS[@]}))
                    new_scenario="${TEST_SCENARIOS[$new_scenario_index]}"
                    new_submit_time=$(date +%s)
                    new_job_id=$(submit_test_job "$new_scenario" $JOB_COUNTER $new_submit_time)
                    
                    if [ "$new_job_id" != "failed" ]; then
                        ACTIVE_JOBS[$i]="$new_job_id"
                        JOB_START_TIMES[$i]="$new_submit_time"
                        ((JOB_COUNTER++))
                    else
                        ACTIVE_JOBS[$i]=""
                    fi
                else
                    ACTIVE_JOBS[$i]=""
                fi
            fi
        fi
    done
    
    # Show progress
    elapsed=$(($(date +%s) - START_TIME))
    remaining=$((TEST_DURATION - elapsed))
    echo -e "\r${CYAN}Progress: ${elapsed}s/${TEST_DURATION}s | Completed: $COMPLETED_JOBS | Failed: $FAILED_JOBS | Remaining: ${remaining}s${NC}" 
    
    sleep 5
done

echo ""
echo -e "${BLUE}⏹️  Stopping load test and waiting for remaining jobs...${NC}"

# Wait for remaining jobs to complete (max 2 minutes)
for ((i=0; i<24; i++)); do
    remaining_jobs=0
    for job_id in "${ACTIVE_JOBS[@]}"; do
        if [ -n "$job_id" ]; then
            status=$(curl -s "$API_BASE/api/jobs/$job_id/status" 2>/dev/null | jq -r '.status // "unknown"')
            if [ "$status" != "completed" ] && [ "$status" != "failed" ]; then
                ((remaining_jobs++))
            fi
        fi
    done
    
    if [ $remaining_jobs -eq 0 ]; then
        break
    fi
    
    echo "  Waiting for $remaining_jobs remaining jobs..."
    sleep 5
done

# Stop monitoring
rm -f "$RESULTS_DIR/.monitoring"
kill $MONITORING_PID 2>/dev/null || true

# Generate report
echo ""
echo -e "${BLUE}📊 Load Test Report${NC}"
echo "================================================="

TOTAL_JOBS=$((COMPLETED_JOBS + FAILED_JOBS))
SUCCESS_RATE=$((COMPLETED_JOBS * 100 / (TOTAL_JOBS == 0 ? 1 : TOTAL_JOBS)))
AVG_RESPONSE_TIME=$((COMPLETED_JOBS > 0 ? TOTAL_RESPONSE_TIME / COMPLETED_JOBS : 0))

echo "Test Duration: ${TEST_DURATION}s"
echo "Total Jobs: $TOTAL_JOBS"
echo "Completed Jobs: $COMPLETED_JOBS"
echo "Failed Jobs: $FAILED_JOBS"
echo "Success Rate: $SUCCESS_RATE%"
echo "Average Response Time: ${AVG_RESPONSE_TIME}s"

# Performance assessment
if [ $SUCCESS_RATE -ge 95 ] && [ $AVG_RESPONSE_TIME -le 60 ]; then
    echo -e "Overall Performance: ${GREEN}EXCELLENT${NC}"
elif [ $SUCCESS_RATE -ge 90 ] && [ $AVG_RESPONSE_TIME -le 90 ]; then
    echo -e "Overall Performance: ${GREEN}GOOD${NC}"  
elif [ $SUCCESS_RATE -ge 80 ] && [ $AVG_RESPONSE_TIME -le 120 ]; then
    echo -e "Overall Performance: ${YELLOW}ACCEPTABLE${NC}"
else
    echo -e "Overall Performance: ${RED}POOR${NC}"
fi

echo ""
echo -e "${CYAN}📁 Results Files:${NC}"
echo "  - Job Results: $RESULTS_FILE"
echo "  - System Metrics: $METRICS_FILE"
echo ""
echo -e "${CYAN}🔍 Analysis Commands:${NC}"
echo "  - View detailed results: cat $RESULTS_FILE"
echo "  - Plot metrics: python3 scripts/analyze-load-test.py $RESULTS_DIR"
echo "  - Check Grafana: http://localhost:3003"
echo ""