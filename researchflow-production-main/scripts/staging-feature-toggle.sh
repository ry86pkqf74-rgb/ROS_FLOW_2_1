#!/bin/bash
# ============================================
# ResearchFlow - Feature Flag Toggle Script
# ============================================
# Toggle ENABLE_NEW_STAGE_1 feature flag for A/B testing
# Allows switching between new Protocol Design Agent and legacy Stage 1
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
PROJECT_ROOT="$(dirname "$(dirname "$(realpath "$0")")")"
STAGING_ENV_FILE="$PROJECT_ROOT/.env.staging"

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║               Feature Flag Toggle Utility                   ║${NC}"
echo -e "${BLUE}║           ENABLE_NEW_STAGE_1 A/B Testing                    ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Function to get current flag status
get_flag_status() {
    local api_response=$(curl -s "$API_BASE/api/feature-flags" 2>/dev/null || echo '{}')
    local api_flag=$(echo "$api_response" | jq -r '.["ENABLE_NEW_STAGE_1"] // "unknown"')
    
    local env_flag="unknown"
    if [ -f "$STAGING_ENV_FILE" ]; then
        env_flag=$(grep "^ENABLE_NEW_STAGE_1=" "$STAGING_ENV_FILE" 2>/dev/null | cut -d'=' -f2 || echo "unknown")
    fi
    
    echo "$api_flag,$env_flag"
}

# Function to update feature flag via API
update_flag_api() {
    local new_value=$1
    local update_payload=$(cat << EOF
{
  "enabled": $new_value,
  "description": "Stage 1 Protocol Design Agent feature flag",
  "scope": "stage_1",
  "rolloutPercent": 100,
  "requiredModes": ["DEMO", "LIVE"]
}
EOF
)
    
    curl -s -X PUT "$API_BASE/api/feature-flags/ENABLE_NEW_STAGE_1" \
        -H "Content-Type: application/json" \
        -d "$update_payload" || echo '{"error": "api_update_failed"}'
}

# Function to update environment file
update_env_file() {
    local new_value=$1
    if [ -f "$STAGING_ENV_FILE" ]; then
        sed -i.bak "s/ENABLE_NEW_STAGE_1=.*/ENABLE_NEW_STAGE_1=$new_value/" "$STAGING_ENV_FILE"
        rm -f "$STAGING_ENV_FILE.bak"
    fi
}

# Function to restart services for environment variable changes
restart_services() {
    echo "Restarting services to apply environment changes..."
    cd "$PROJECT_ROOT"
    docker-compose -f docker-compose.staging.yml restart orchestrator worker
    
    # Wait for services to be ready
    echo "Waiting for services to restart..."
    sleep 10
    
    for i in {1..30}; do
        if curl -s "$API_BASE/health" >/dev/null 2>&1; then
            echo -e "${GREEN}✅ Services restarted successfully${NC}"
            return
        fi
        echo -n "."
        sleep 2
    done
    
    echo -e "${YELLOW}⚠️  Services may still be starting up${NC}"
}

# Function to validate stage implementation
validate_stage_implementation() {
    local expected_enabled=$1
    local worker_base="http://localhost:8001"
    
    local stage_info=$(curl -s "$worker_base/api/stages/1/info" 2>/dev/null || echo '{}')
    local stage_class=$(echo "$stage_info" | jq -r '.class_name // "unknown"')
    
    if [ "$expected_enabled" = "true" ]; then
        if [[ "$stage_class" == *"ProtocolDesign"* ]]; then
            echo -e "✅ Validation: ${GREEN}New Protocol Design Agent active${NC}"
            return 0
        else
            echo -e "❌ Validation: ${RED}Expected Protocol Design Agent, got $stage_class${NC}"
            return 1
        fi
    else
        if [[ "$stage_class" == *"Upload"* ]] || [[ "$stage_class" == *"Intake"* ]]; then
            echo -e "✅ Validation: ${GREEN}Legacy Upload Stage active${NC}"
            return 0
        else
            echo -e "❌ Validation: ${RED}Expected legacy stage, got $stage_class${NC}"
            return 1
        fi
    fi
}

# Get current status
echo -e "${CYAN}📊 Current Feature Flag Status:${NC}"
flag_status=$(get_flag_status)
api_flag=$(echo "$flag_status" | cut -d',' -f1)
env_flag=$(echo "$flag_status" | cut -d',' -f2)

echo "  - API Flag:         $api_flag"
echo "  - Environment File: $env_flag"

if [ "$api_flag" = "$env_flag" ]; then
    echo -e "  - Status:           ${GREEN}✅ Synchronized${NC}"
else
    echo -e "  - Status:           ${YELLOW}⚠️  Out of sync${NC}"
fi
echo ""

# Determine target state
if [ "${1:-toggle}" = "enable" ]; then
    target_state="true"
    action="Enabling"
elif [ "${1:-toggle}" = "disable" ]; then
    target_state="false"
    action="Disabling"
else
    # Toggle mode
    if [ "$api_flag" = "true" ] || [ "$env_flag" = "true" ]; then
        target_state="false"
        action="Disabling"
    else
        target_state="true"
        action="Enabling"
    fi
fi

echo -e "${BLUE}🔄 $action New Stage 1 Protocol Design Agent...${NC}"
echo "  Target state: $target_state"
echo ""

# Get confirmation
if [ -t 0 ]; then  # Only prompt if running interactively
    read -p "Continue? [y/N] " confirm
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        echo "Operation cancelled."
        exit 0
    fi
fi

# Update via API
echo "1. Updating feature flag via API..."
api_result=$(update_flag_api "$target_state")
api_success=$(echo "$api_result" | jq -r '.success // false' 2>/dev/null || echo "false")

if [ "$api_success" = "true" ]; then
    echo -e "   ${GREEN}✅ API update successful${NC}"
else
    echo -e "   ${YELLOW}⚠️  API update failed or not available${NC}"
fi

# Update environment file
echo "2. Updating environment file..."
update_env_file "$target_state"
echo -e "   ${GREEN}✅ Environment file updated${NC}"

# Restart services
echo "3. Restarting services..."
restart_services

# Wait a moment for changes to take effect
echo "4. Validating changes..."
sleep 5

# Check final status
final_status=$(get_flag_status)
final_api_flag=$(echo "$final_status" | cut -d',' -f1)
final_env_flag=$(echo "$final_status" | cut -d',' -f2)

echo ""
echo -e "${CYAN}📊 Updated Feature Flag Status:${NC}"
echo "  - API Flag:         $final_api_flag"
echo "  - Environment File: $final_env_flag"

# Validate implementation
echo ""
echo -e "${BLUE}🔍 Validating Stage Implementation:${NC}"
if validate_stage_implementation "$target_state"; then
    validation_status="✅ PASSED"
else
    validation_status="❌ FAILED"
fi

# Summary
echo ""
echo -e "${BLUE}📋 Toggle Summary:${NC}"
echo "==================="
echo "  - Target State: $target_state"
echo "  - API Update: $([ "$api_success" = "true" ] && echo "✅ Success" || echo "⚠️  Warning")"
echo "  - Environment: ✅ Updated"
echo "  - Services: ✅ Restarted"
echo "  - Validation: $validation_status"

if [ "$final_api_flag" = "$target_state" ] && [ "$final_env_flag" = "$target_state" ]; then
    echo ""
    echo -e "${GREEN}🎉 Feature flag toggle completed successfully!${NC}"
    
    if [ "$target_state" = "true" ]; then
        echo "New Stage 1 Protocol Design Agent is now ACTIVE"
        echo "  - PICO framework extraction enabled"
        echo "  - AI-powered protocol generation enabled"
        echo "  - Enhanced quality gates active"
    else
        echo "Legacy Stage 1 Upload Agent is now ACTIVE"
        echo "  - File upload workflow enabled"
        echo "  - Traditional pipeline active"
    fi
    
    echo ""
    echo -e "${CYAN}🧪 Testing Recommendations:${NC}"
    echo "  - Run: ./scripts/test-stage-1.sh"
    echo "  - Monitor: http://localhost:3003 (Grafana)"
    echo "  - Check frontend: http://localhost:3000"
    
else
    echo ""
    echo -e "${YELLOW}⚠️  Feature flag toggle completed with warnings${NC}"
    echo "Some components may not have updated properly."
    echo "Check logs: docker-compose -f docker-compose.staging.yml logs"
fi

echo ""