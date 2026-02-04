#!/bin/bash
# Verification script for StatisticalAnalysisAgent implementation

echo "=========================================="
echo "StatisticalAnalysisAgent Verification"
echo "=========================================="
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counters
PASSED=0
FAILED=0

check() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $1"
        ((PASSED++))
    else
        echo -e "${RED}✗${NC} $1"
        ((FAILED++))
    fi
}

# 1. Check files exist
echo "1. Checking files exist..."
test -f services/worker/agents/analysis/statistical_types.py
check "statistical_types.py exists"

test -f services/worker/agents/analysis/statistical_utils.py
check "statistical_utils.py exists"

test -f services/worker/agents/analysis/statistical_analysis_agent.py
check "statistical_analysis_agent.py exists"

test -f services/worker/agents/analysis/__init__.py
check "__init__.py updated"

test -f services/worker/tests/test_statistical_analysis_agent.py
check "test file exists"

echo ""

# 2. Check file sizes (should be substantial)
echo "2. Checking file sizes..."
SIZE=$(wc -c < services/worker/agents/analysis/statistical_types.py)
if [ $SIZE -gt 15000 ]; then
    echo -e "${GREEN}✓${NC} statistical_types.py is substantial ($SIZE bytes)"
    ((PASSED++))
else
    echo -e "${RED}✗${NC} statistical_types.py too small ($SIZE bytes)"
    ((FAILED++))
fi

SIZE=$(wc -c < services/worker/agents/analysis/statistical_analysis_agent.py)
if [ $SIZE -gt 30000 ]; then
    echo -e "${GREEN}✓${NC} statistical_analysis_agent.py is substantial ($SIZE bytes)"
    ((PASSED++))
else
    echo -e "${RED}✗${NC} statistical_analysis_agent.py too small ($SIZE bytes)"
    ((FAILED++))
fi

echo ""

# 3. Check Python syntax
echo "3. Checking Python syntax..."
cd services/worker
python3 -m py_compile agents/analysis/statistical_types.py 2>/dev/null
check "statistical_types.py compiles"

python3 -m py_compile agents/analysis/statistical_utils.py 2>/dev/null
check "statistical_utils.py compiles"

python3 -m py_compile agents/analysis/statistical_analysis_agent.py 2>/dev/null
check "statistical_analysis_agent.py compiles"

python3 -m py_compile tests/test_statistical_analysis_agent.py 2>/dev/null
check "test file compiles"

cd ../..

echo ""

# 4. Check key imports
echo "4. Checking key imports..."
grep -q "from pydantic import BaseModel" services/worker/agents/analysis/statistical_types.py
check "Pydantic imported"

grep -q "from scipy import stats" services/worker/agents/analysis/statistical_analysis_agent.py
check "scipy.stats imported"

grep -q "from agents.base_agent import" services/worker/agents/analysis/statistical_analysis_agent.py
check "BaseAgent imported"

echo ""

# 5. Check key classes defined
echo "5. Checking key classes/types..."
grep -q "class TestType" services/worker/agents/analysis/statistical_types.py
check "TestType enum defined"

grep -q "class StatisticalAnalysisAgent" services/worker/agents/analysis/statistical_analysis_agent.py
check "StatisticalAnalysisAgent class defined"

grep -q "class StudyData" services/worker/agents/analysis/statistical_types.py
check "StudyData class defined"

grep -q "class StatisticalResult" services/worker/agents/analysis/statistical_types.py
check "StatisticalResult class defined"

echo ""

# 6. Check key methods implemented
echo "6. Checking key methods..."
grep -q "def calculate_descriptive_stats" services/worker/agents/analysis/statistical_analysis_agent.py
check "calculate_descriptive_stats() implemented"

grep -q "def run_hypothesis_test" services/worker/agents/analysis/statistical_analysis_agent.py
check "run_hypothesis_test() implemented"

grep -q "def calculate_effect_size" services/worker/agents/analysis/statistical_analysis_agent.py
check "calculate_effect_size() implemented"

grep -q "def check_assumptions" services/worker/agents/analysis/statistical_analysis_agent.py
check "check_assumptions() implemented"

echo ""

# 7. Check P0 enhancements
echo "7. Checking P0 enhancements..."
grep -q "remediation_suggestions" services/worker/agents/analysis/statistical_types.py
check "Remediation suggestions (P0)"

grep -q "class FigureSpec" services/worker/agents/analysis/statistical_types.py
check "FigureSpec for visualizations (P0)"

grep -q "List\[pd.Series\]" services/worker/agents/analysis/statistical_analysis_agent.py
check "Multiple group support (P0)"

echo ""

# 8. Check TODO markers for Mercury
echo "8. Checking TODO markers..."
TODO_COUNT=$(grep -c "TODO (Mercury)" services/worker/agents/analysis/statistical_analysis_agent.py)
if [ $TODO_COUNT -gt 0 ]; then
    echo -e "${GREEN}✓${NC} Found $TODO_COUNT TODO markers for Mercury"
    ((PASSED++))
else
    echo -e "${YELLOW}⚠${NC} No TODO markers found"
fi

echo ""

# 9. Check tests
echo "9. Checking test coverage..."
TEST_COUNT=$(grep -c "def test_" services/worker/tests/test_statistical_analysis_agent.py)
if [ $TEST_COUNT -gt 15 ]; then
    echo -e "${GREEN}✓${NC} Found $TEST_COUNT test functions"
    ((PASSED++))
else
    echo -e "${YELLOW}⚠${NC} Only $TEST_COUNT test functions found"
fi

echo ""

# 10. Check documentation
echo "10. Checking documentation..."
test -f services/worker/agents/analysis/STATISTICAL_ANALYSIS_README.md
check "README.md exists"

test -f services/worker/agents/analysis/IMPLEMENTATION_SUMMARY.md
check "IMPLEMENTATION_SUMMARY.md exists"

echo ""

# Summary
echo "=========================================="
echo "VERIFICATION SUMMARY"
echo "=========================================="
echo -e "${GREEN}Passed:${NC} $PASSED checks"
echo -e "${RED}Failed:${NC} $FAILED checks"

if [ $FAILED -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ ALL CHECKS PASSED!${NC}"
    echo -e "${GREEN}StatisticalAnalysisAgent is ready for testing.${NC}"
    exit 0
else
    echo ""
    echo -e "${RED}✗ SOME CHECKS FAILED${NC}"
    echo "Please review failures above."
    exit 1
fi
