#!/bin/bash

# ResearchFlow Multi-Application Integration Installation Script
# This script sets up all integrations for Notion, Figma, Linear, Slack, Docker, and Cursor

set -e

echo "🚀 ResearchFlow Multi-Application Integration Setup"
echo "=================================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    print_error "Node.js is not installed. Please install Node.js 18+ and try again."
    exit 1
fi
print_success "Node.js is installed: $(node --version)"

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    print_error "npm is not installed. Please install npm and try again."
    exit 1
fi
print_success "npm is installed: $(npm --version)"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker and try again."
    exit 1
fi
print_success "Docker is installed: $(docker --version)"

echo ""
print_info "Step 1: Installing dependencies..."

# Install root dependencies
npm install --silent

# Install Cursor integration package
print_info "Installing Cursor integration package..."
cd packages/cursor-integration
npm install --silent
npm run build
cd ../..
print_success "Cursor integration package installed"

# Install Notion SDK if not already installed
print_info "Checking for Notion SDK..."
if ! npm list @notionhq/client &> /dev/null; then
    npm install @notionhq/client --silent
    print_success "Notion SDK installed"
else
    print_success "Notion SDK already installed"
fi

echo ""
print_info "Step 2: Setting up environment configuration..."

# Create .env.integrations file if it doesn't exist
if [ ! -f .env.integrations ]; then
    cp .env.integrations.example .env.integrations
    print_success "Created .env.integrations file"
    print_info "Please edit .env.integrations with your API keys and secrets"
else
    print_info ".env.integrations already exists (skipping)"
fi

echo ""
print_info "Step 3: Checking service structure..."

# Verify service files exist
SERVICES=(
    "services/orchestrator/src/services/linearService.ts"
    "services/orchestrator/src/services/figmaService.ts"
    "services/orchestrator/src/services/dockerRegistryService.ts"
    "services/orchestrator/src/services/slackService.ts"
    "services/orchestrator/src/services/notionService.ts"
    "services/orchestrator/src/services/multiToolOrchestrator.ts"
)

for service in "${SERVICES[@]}"; do
    if [ -f "$service" ]; then
        print_success "$(basename $service)"
    else
        print_error "$(basename $service) not found"
    fi
done

echo ""
print_info "Step 4: Checking N8N workflows..."

# Check N8N workflows
WORKFLOWS=(
    "infrastructure/n8n/workflows/figma-design-sync.json"
    "infrastructure/n8n/workflows/linear-task-automation.json"
    "infrastructure/n8n/workflows/docker-deployment-pipeline.json"
    "infrastructure/n8n/workflows/multi-agent-orchestrator.json"
)

for workflow in "${WORKFLOWS[@]}"; do
    if [ -f "$workflow" ]; then
        print_success "$(basename $workflow)"
    else
        print_error "$(basename $workflow) not found"
    fi
done

echo ""
print_info "Step 5: Building TypeScript projects..."

# Build services if TypeScript
if [ -f "services/orchestrator/tsconfig.json" ]; then
    cd services/orchestrator
    if npm run build &> /dev/null; then
        print_success "Orchestrator built successfully"
    else
        print_info "Build skipped or not configured"
    fi
    cd ../..
fi

echo ""
print_info "Step 6: Generating Cursor API key..."

# Generate a secure API key for Cursor if not set
if ! grep -q "CURSOR_API_KEY=.\+" .env.integrations 2>/dev/null; then
    CURSOR_KEY=$(openssl rand -hex 32)
    echo "" >> .env.integrations
    echo "# Auto-generated Cursor API Key" >> .env.integrations
    echo "CURSOR_API_KEY=$CURSOR_KEY" >> .env.integrations
    print_success "Generated Cursor API key"
    print_info "Cursor API Key: $CURSOR_KEY"
else
    print_info "Cursor API key already configured"
fi

echo ""
print_info "Step 7: Checking Docker setup..."

# Check if docker-compose is available
if command -v docker-compose &> /dev/null; then
    print_success "docker-compose is available"
elif docker compose version &> /dev/null 2>&1; then
    print_success "docker compose (plugin) is available"
else
    print_error "docker-compose is not installed"
fi

echo ""
print_info "Step 8: Creating necessary directories..."

# Create directories if they don't exist
mkdir -p logs
mkdir -p data
print_success "Directories created"

echo ""
echo "=================================================="
print_success "Installation Complete!"
echo "=================================================="
echo ""
echo "📝 Next Steps:"
echo ""
echo "1. Configure your API keys and secrets:"
echo "   nano .env.integrations"
echo ""
echo "2. Set up webhook URLs in each service:"
echo "   • Linear: https://your-domain.com/api/integrations/linear/webhook"
echo "   • Figma: https://your-domain.com/api/integrations/figma/webhook"
echo "   • Slack: https://your-domain.com/api/integrations/slack/commands"
echo "   • Docker: https://your-domain.com/api/integrations/docker/webhook"
echo ""
echo "3. Create Notion databases and add IDs to .env.integrations:"
echo "   • AI Agent Tasks Database"
echo "   • Projects Database"
echo "   • Deployments Database"
echo ""
echo "4. Import N8N workflows:"
echo "   n8n import:workflow --input=infrastructure/n8n/workflows/*.json"
echo ""
echo "5. Start the services:"
echo "   docker-compose up -d"
echo ""
echo "6. Test the integrations:"
echo "   # In Slack:"
echo "   /ros agent code-review Test file"
echo ""
echo "   # In Linear:"
echo "   Create issue with label: ai-agent:test-generation"
echo ""
echo "   # In Cursor:"
echo "   // @agent fix-this"
echo ""
echo "📚 Documentation:"
echo "   • Setup Guide: INTEGRATION_SETUP_GUIDE.md"
echo "   • Architecture: INTEGRATION_ARCHITECTURE.md"
echo "   • Summary: INTEGRATION_SUMMARY.md"
echo ""
echo "🔗 Useful Links:"
echo "   • Orchestrator: http://localhost:3001"
echo "   • Grafana: http://localhost:3000"
echo "   • Prometheus: http://localhost:9090"
echo "   • N8N: http://localhost:5678"
echo ""
print_success "Happy integrating! 🎉"
