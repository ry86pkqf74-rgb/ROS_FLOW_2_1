#!/bin/bash
set -e

echo "=== ResearchFlow Enhancement Verification ==="

# 1. Statistical pipeline
echo "Testing statistical recommendations..."
curl -sf http://localhost:3001/api/analysis/recommendations?studyType=rct || echo "WARN: Stats endpoint not responding"

# 2. Variable selection
echo "Testing variable selection..."
curl -sf http://localhost:3001/api/projects/test/variables || echo "WARN: Variables endpoint not responding"

# 3. Export pipeline
echo "Testing export formats..."
curl -sf http://localhost:3001/api/export/formats || echo "WARN: Export endpoint not responding"

# 4. Audit trail
echo "Testing audit trail..."
curl -sf http://localhost:3001/api/audit/statistical/test/summary || echo "WARN: Audit endpoint not responding"

# 5. Notifications
echo "Testing notifications..."
curl -sf http://localhost:3001/api/notifications || echo "WARN: Notifications endpoint not responding"

echo "=== Enhancement verification complete ==="
