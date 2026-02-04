#!/bin/bash

###############################################################################
# Quick Stage 7 API Test
# Simple script to test the statistical analysis endpoint
###############################################################################

set -e

# Configuration
ORCHESTRATOR_URL="${ORCHESTRATOR_URL:-http://localhost:3001}"
RESEARCH_ID="test-$(date +%s)"

echo "Testing Stage 7 Statistical Analysis API"
echo "========================================="
echo ""

# Test 1: Health Check
echo "1. Health Check..."
curl -s "${ORCHESTRATOR_URL}/api/analysis/statistical/health" | jq '.'
echo ""

# Test 2: List Tests
echo "2. Available Tests..."
curl -s "${ORCHESTRATOR_URL}/api/analysis/statistical/tests" | jq '.tests[] | .name'
echo ""

# Test 3: Execute Analysis
echo "3. Running T-Test Analysis..."
curl -s -X POST "${ORCHESTRATOR_URL}/api/research/${RESEARCH_ID}/stage/7/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "study_data": {
      "groups": ["Treatment", "Treatment", "Treatment", "Treatment", "Treatment",
                 "Control", "Control", "Control", "Control", "Control"],
      "outcomes": {
        "blood_pressure": [120, 118, 122, 119, 121, 135, 138, 140, 136, 139]
      },
      "metadata": {
        "study_title": "Blood Pressure Trial"
      }
    },
    "options": {
      "test_type": "t_test_independent",
      "confidence_level": 0.95,
      "calculate_effect_size": true,
      "check_assumptions": true
    }
  }' | jq '{
    status: .status,
    test: .result.inferential.test_name,
    p_value: .result.inferential.p_value,
    cohens_d: .result.effect_sizes.cohens_d,
    assumptions_passed: .result.assumptions.passed
  }'

echo ""
echo "Test complete!"
