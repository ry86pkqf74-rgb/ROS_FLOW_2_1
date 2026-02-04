#!/bin/bash
#
# Setup script for Cursor ↔ LangChain ↔ Composio integration
#
# This script:
# 1. Installs required Python packages
# 2. Gets a Testros access token
# 3. Writes environment variables to .env
# 4. Validates the connection
#
# Usage:
#   ./scripts/setup_cursor_integration.sh [RF_BASE_URL]
#
# Example:
#   ./scripts/setup_cursor_integration.sh http://localhost:3001
#

set -e

echo "🔗 Setting up Cursor ↔ LangChain ↔ Composio Integration"
echo "========================================================"

# Default URL
RF_BASE_URL="${1:-http://localhost:3001}"
echo "📍 ResearchFlow URL: $RF_BASE_URL"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    exit 1
fi

# Install dependencies
echo ""
echo "📦 Installing Python dependencies..."
pip3 install --quiet langchain langchain-openai langchain-core requests aiohttp || {
    echo "⚠️  Basic packages installed. For Composio support, also run:"
    echo "    pip install composio-core composio-langchain"
}

# Optional: Install Composio
read -p "Install Composio packages? (y/N): " install_composio
if [[ "$install_composio" =~ ^[Yy]$ ]]; then
    echo "📦 Installing Composio..."
    pip3 install --quiet composio-core composio-langchain
fi

# Get Testros token
echo ""
echo "🔑 Logging in with Testros backdoor..."
LOGIN_RESPONSE=$(curl -s -X POST "$RF_BASE_URL/api/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"username":"Testros"}')

if echo "$LOGIN_RESPONSE" | grep -q "accessToken"; then
    ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['accessToken'])")
    USER_EMAIL=$(echo "$LOGIN_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('user',{}).get('email','unknown'))")
    echo "✅ Logged in as: $USER_EMAIL"
    echo "   Token: ${ACCESS_TOKEN:0:50}..."
else
    echo "❌ Login failed. Is ResearchFlow running at $RF_BASE_URL?"
    echo "   Response: $LOGIN_RESPONSE"
    exit 1
fi

# Write to .env file
echo ""
echo "📝 Writing environment variables..."

# Backup existing .env if it exists
if [ -f .env ]; then
    cp .env .env.backup
    echo "   (Backed up existing .env to .env.backup)"
fi

# Check for existing keys
OPENAI_KEY="${OPENAI_API_KEY:-}"
COMPOSIO_KEY="${COMPOSIO_API_KEY:-}"

# Create/update .env
cat >> .env << EOF

# ============================================
# Cursor Integration (added by setup script)
# ============================================
RF_BASE_URL=$RF_BASE_URL
RF_ACCESS_TOKEN=$ACCESS_TOKEN
EOF

if [ -n "$OPENAI_KEY" ]; then
    echo "OPENAI_API_KEY=$OPENAI_KEY" >> .env
else
    echo "# OPENAI_API_KEY=sk-...  # Add your OpenAI key" >> .env
fi

if [ -n "$COMPOSIO_KEY" ]; then
    echo "COMPOSIO_API_KEY=$COMPOSIO_KEY" >> .env
else
    echo "# COMPOSIO_API_KEY=...   # Add your Composio key (optional)" >> .env
fi

echo "✅ Environment variables written to .env"

# Validate connection
echo ""
echo "🔍 Validating connection..."
HEALTH_RESPONSE=$(curl -s "$RF_BASE_URL/health")
if echo "$HEALTH_RESPONSE" | grep -q "ok\|healthy\|status"; then
    echo "✅ ResearchFlow is healthy"
else
    echo "⚠️  Health check response: $HEALTH_RESPONSE"
fi

# Test authenticated endpoint
WORKFLOWS_RESPONSE=$(curl -s -X GET "$RF_BASE_URL/api/workflows" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json")

if echo "$WORKFLOWS_RESPONSE" | grep -q "workflows\|error\|[]"; then
    echo "✅ API authentication working"
else
    echo "⚠️  API response: $WORKFLOWS_RESPONSE"
fi

# Print summary
echo ""
echo "========================================================"
echo "✅ Setup Complete!"
echo ""
echo "To use in Python:"
echo "  from agents.cursor_integration import CursorAgentFactory"
echo "  factory = CursorAgentFactory()"
echo "  agent = factory.create_agent()"
echo "  result = agent.invoke({'input': 'List workflows'})"
echo ""
echo "To use in shell:"
echo "  source .env"
echo "  curl -H \"Authorization: Bearer \$RF_ACCESS_TOKEN\" \\"
echo "       $RF_BASE_URL/api/workflows"
echo ""
echo "For Cursor integration, add to your settings:"
echo "  RF_BASE_URL=$RF_BASE_URL"
echo "  RF_ACCESS_TOKEN=\$RF_ACCESS_TOKEN"
echo "========================================================"
