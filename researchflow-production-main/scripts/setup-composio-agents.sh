#!/bin/bash
# ResearchFlow Composio Agent Setup Script
# Sets up all required toolkits and agent connections

set -e

echo "🔧 ResearchFlow Composio Agent Setup"
echo "======================================"

# Check if composio is installed
if ! command -v composio &> /dev/null; then
    echo "📦 Installing Composio CLI..."
    pip install composio-core composio-langchain composio-openai
fi

# Check for API key
if [ -z "$COMPOSIO_API_KEY" ]; then
    echo "⚠️  COMPOSIO_API_KEY not set. Please run: export COMPOSIO_API_KEY=your_key"
    echo "   Get your key at: https://app.composio.dev/settings/api-keys"
    exit 1
fi

echo ""
echo "📋 Setting up toolkits for ResearchFlow agents..."
echo ""

# Define the label for all connections
LABEL="researchflow"

# ===== FIGMA TOOLKIT (for DesignOps Agent) =====
echo "1️⃣  Setting up FIGMA toolkit..."
composio add figma -l $LABEL || echo "   Figma already connected or needs OAuth"

# ===== GITHUB TOOLKIT (for all agents) =====
echo "2️⃣  Setting up GITHUB toolkit..."
composio add github -l $LABEL || echo "   GitHub already connected"

# ===== NOTION TOOLKIT (for SpecOps, Compliance, Release Guardian) =====
echo "3️⃣  Setting up NOTION toolkit..."
composio add notion -l $LABEL || echo "   Notion already connected"

# ===== LINEAR TOOLKIT (optional, for issue tracking) =====
echo "4️⃣  Setting up LINEAR toolkit..."
composio add linear -l $LABEL || echo "   Linear already connected"

# ===== SLACK TOOLKIT (for notifications) =====
echo "5️⃣  Setting up SLACK toolkit..."
composio add slack -l $LABEL || echo "   Slack already connected"

echo ""
echo "📊 Verifying connections..."
composio connections

echo ""
echo "🔍 Listing available actions per toolkit..."
echo ""
echo "=== FIGMA Actions ==="
composio actions --app figma 2>/dev/null | head -20 || echo "   Run 'composio add figma' to see actions"

echo ""
echo "=== GITHUB Actions ==="
composio actions --app github 2>/dev/null | head -20

echo ""
echo "=== NOTION Actions ==="
composio actions --app notion 2>/dev/null | head -20

echo ""
echo "✅ Composio setup complete!"
echo ""
echo "📝 Next steps:"
echo "   1. Set environment variables in .env:"
echo "      COMPOSIO_API_KEY=your_key"
echo "      FIGMA_FILE_KEY=your_figma_file_key"
echo "      NOTION_PROBLEM_REGISTRY_DB=your_db_id"
echo "      NOTION_DATASET_REGISTRY_DB=your_db_id"
echo "      NOTION_MODEL_REGISTRY_DB=your_db_id"
echo "      NOTION_RISK_REGISTER_DB=your_db_id"
echo "      NOTION_DEPLOYMENTS_DB=your_db_id"
echo "      NOTION_INCIDENTS_DB=your_db_id"
echo ""
echo "   2. Run the agents:"
echo "      python -m agents.design_ops.agent"
echo "      python -m agents.spec_ops.agent"
echo "      python -m agents.compliance.agent"
echo "      python -m agents.release_guardian.agent"
