#!/usr/bin/env bash
# Fix Docker build contexts for 5 failing agent services
# This script updates docker-compose.yml to fix build context paths

set -euo pipefail

cd /opt/researchflow/ROS_FLOW_2_1/researchflow-production-main

echo "🔧 Fixing Docker build contexts for 5 agent services..."

# Backup original docker-compose.yml
cp docker-compose.yml docker-compose.yml.backup-$(date +%Y%m%d-%H%M%S)

# Fix agent-evidence-synthesis
echo "Fixing agent-evidence-synthesis..."
sed -i '/^  agent-evidence-synthesis:/,/^    build:/{
/^    build:/,/^      dockerfile:/{
s|context: \.|context: services/agents/agent-evidence-synthesis|
}
}' docker-compose.yml

# Fix agent-lit-triage
echo "Fixing agent-lit-triage..."
sed -i '/^  agent-lit-triage:/,/^    build:/{
/^    build:/,/^      dockerfile:/{
s|context: \.|context: services/agents/agent-lit-triage|
}
}' docker-compose.yml

# Fix agent-discussion-writer
echo "Fixing agent-discussion-writer..."
sed -i '/^  agent-discussion-writer:/,/^    build:/{
/^    build:/,/^      dockerfile:/{
s|context: \.|context: services/agents/agent-discussion-writer|
}
}' docker-compose.yml

# Fix agent-results-writer
echo "Fixing agent-results-writer..."
sed -i '/^  agent-results-writer:/,/^    build:/{
/^    build:/,/^      dockerfile:/{
s|context: \.|context: services/agents/agent-results-writer|
}
}' docker-compose.yml

# Fix agent-stage2-synthesize
echo "Fixing agent-stage2-synthesize..."
sed -i '/^  agent-stage2-synthesize:/,/^    build:/{
/^    build:/,/^      dockerfile:/{
s|context: \.|context: services/agents/agent-stage2-synthesize|
}
}' docker-compose.yml

echo "✅ Build contexts fixed!"
echo ""
echo "Verifying changes..."
grep -A3 "agent-evidence-synthesis:" docker-compose.yml | grep -A2 "build:"
grep -A3 "agent-lit-triage:" docker-compose.yml | grep -A2 "build:"
grep -A3 "agent-discussion-writer:" docker-compose.yml | grep -A2 "build:"
grep -A3 "agent-results-writer:" docker-compose.yml | grep -A2 "build:"
grep -A3 "agent-stage2-synthesize:" docker-compose.yml | grep -A2 "build:"
