#!/bin/bash
# Integration Health Check Script
# Validates all enhanced systems are operational

set -e

echo "🔍 ResearchFlow Integration Health Check"
echo "========================================"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASSED=0
FAILED=0

check_component() {
    local name=$1
    local command=$2
    
    echo -n "Checking $name... "
    
    if eval "$command" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ PASS${NC}"
        ((PASSED++))
    else
        echo -e "${RED}❌ FAIL${NC}"
        ((FAILED++))
    fi
}

echo "🧪 Core System Checks:"
check_component "Python Environment" "python3 -c 'import sys; assert sys.version_info >= (3, 8)'"
check_component "Required Packages" "python3 -c 'import networkx, pandas, numpy, scipy, psutil'"
check_component "Citation Analyzer" "python3 -c 'from services.worker.src.analysis.citation_network_analyzer import CitationNetworkAnalyzer'"
check_component "Enhanced Monitor" "python3 -c 'from services.worker.src.monitoring.enhanced_monitoring import EnhancedMonitor'"
check_component "Analytics Module" "python3 -c 'from services.worker.src.analytics import get_citation_analyzer'"

echo ""
echo "🌐 API Health Checks:"
check_component "FastAPI Import" "python3 -c 'from fastapi import FastAPI'"
check_component "Citation API" "python3 -c 'from services.worker.src.api.citation_analysis_api import app'"

echo ""
echo "📊 Integration Components:"
check_component "Protocol Generator" "python3 -c 'from services.worker.src.enhanced_protocol_generation import create_enhanced_generator'"
check_component "Statistical Agent" "python3 -c 'from services.worker.agents.analysis.statistical_analysis_agent import StatisticalAnalysisAgent'"

echo ""
echo "🐳 Docker Environment:"
check_component "Docker Available" "docker --version"
check_component "Docker Compose" "docker-compose --version"

echo ""
echo "📈 Results Summary:"
echo "=================="
echo -e "✅ Passed: ${GREEN}$PASSED${NC}"
echo -e "❌ Failed: ${RED}$FAILED${NC}"

if [ $FAILED -eq 0 ]; then
    echo -e "\n🎉 ${GREEN}ALL SYSTEMS OPERATIONAL!${NC}"
    echo "Ready for production deployment! 🚀"
    exit 0
else
    echo -e "\n⚠️  ${YELLOW}Some components need attention${NC}"
    echo "Please review failed checks before deployment."
    exit 1
fi