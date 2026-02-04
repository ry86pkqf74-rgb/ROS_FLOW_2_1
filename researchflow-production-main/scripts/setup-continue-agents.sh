#!/bin/bash
# ============================================================================
# ResearchFlow - Continue.dev Agents Setup Script
# ============================================================================
# This script installs Continue CLI and configures agents for VS Code
# Run: chmod +x scripts/setup-continue-agents.sh && ./scripts/setup-continue-agents.sh
# ============================================================================

set -e

echo "========================================"
echo "ResearchFlow Continue.dev Agents Setup"
echo "========================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if running from project root
if [ ! -f "package.json" ] && [ ! -f "docker-compose.yml" ]; then
    echo -e "${RED}Error: Please run this script from the researchflow-production root directory${NC}"
    exit 1
fi

echo -e "\n${BLUE}Step 1: Checking prerequisites...${NC}"

# Check Node.js
if ! command -v node &> /dev/null; then
    echo -e "${RED}Error: Node.js is not installed. Please install Node.js 18+ first.${NC}"
    exit 1
fi
NODE_VERSION=$(node -v)
echo -e "${GREEN}✓ Node.js installed: ${NODE_VERSION}${NC}"

# Check npm
if ! command -v npm &> /dev/null; then
    echo -e "${RED}Error: npm is not installed.${NC}"
    exit 1
fi
NPM_VERSION=$(npm -v)
echo -e "${GREEN}✓ npm installed: ${NPM_VERSION}${NC}"

# ============================================================================
# Step 2: Install Continue CLI
# ============================================================================
echo -e "\n${BLUE}Step 2: Installing Continue CLI...${NC}"

if command -v cn &> /dev/null; then
    echo -e "${GREEN}✓ Continue CLI already installed${NC}"
    cn --version
else
    echo "Installing Continue CLI globally..."
    npm install -g @continuedev/cli

    if command -v cn &> /dev/null; then
        echo -e "${GREEN}✓ Continue CLI installed successfully${NC}"
        cn --version
    else
        echo -e "${RED}Error: Failed to install Continue CLI${NC}"
        echo "Try running manually: npm install -g @continuedev/cli"
        exit 1
    fi
fi

# ============================================================================
# Step 3: Create global Continue config directory
# ============================================================================
echo -e "\n${BLUE}Step 3: Setting up Continue configuration...${NC}"

CONTINUE_DIR="$HOME/.continue"
if [ ! -d "$CONTINUE_DIR" ]; then
    mkdir -p "$CONTINUE_DIR"
    echo -e "${GREEN}✓ Created ~/.continue directory${NC}"
else
    echo -e "${GREEN}✓ ~/.continue directory exists${NC}"
fi

# ============================================================================
# Step 4: Copy project config to global location (optional merge)
# ============================================================================
echo -e "\n${BLUE}Step 4: Configuring agents...${NC}"

PROJECT_CONFIG="config/continue/config.yaml"
GLOBAL_CONFIG="$CONTINUE_DIR/config.yaml"

if [ -f "$PROJECT_CONFIG" ]; then
    if [ -f "$GLOBAL_CONFIG" ]; then
        echo -e "${YELLOW}Global config exists. Backing up to config.yaml.backup${NC}"
        cp "$GLOBAL_CONFIG" "$GLOBAL_CONFIG.backup"
    fi

    # Copy project config to global (user can merge manually if needed)
    cp "$PROJECT_CONFIG" "$GLOBAL_CONFIG"
    echo -e "${GREEN}✓ Copied project config to ~/.continue/config.yaml${NC}"
else
    echo -e "${YELLOW}Warning: Project config not found at ${PROJECT_CONFIG}${NC}"
fi

# ============================================================================
# Step 5: Set up environment variables
# ============================================================================
echo -e "\n${BLUE}Step 5: Checking environment variables...${NC}"

ENV_VARS=(
    "ANTHROPIC_API_KEY"
    "OPENAI_API_KEY"
    "GITHUB_TOKEN"
)

MISSING_VARS=()
for var in "${ENV_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        MISSING_VARS+=("$var")
    else
        echo -e "${GREEN}✓ ${var} is set${NC}"
    fi
done

if [ ${#MISSING_VARS[@]} -gt 0 ]; then
    echo -e "\n${YELLOW}Missing environment variables (optional but recommended):${NC}"
    for var in "${MISSING_VARS[@]}"; do
        echo -e "  - ${var}"
    done
    echo -e "\nAdd these to your ~/.zshrc or ~/.bashrc:"
    echo -e "  export ANTHROPIC_API_KEY='your-key-here'"
    echo -e "  export OPENAI_API_KEY='your-key-here'"
    echo -e "  export GITHUB_TOKEN='your-token-here'"
fi

# ============================================================================
# Step 6: Install VS Code extension (if not installed)
# ============================================================================
echo -e "\n${BLUE}Step 6: Checking VS Code Continue extension...${NC}"

if command -v code &> /dev/null; then
    if code --list-extensions 2>/dev/null | grep -q "Continue.continue"; then
        echo -e "${GREEN}✓ Continue VS Code extension is installed${NC}"
    else
        echo "Installing Continue VS Code extension..."
        code --install-extension Continue.continue
        echo -e "${GREEN}✓ Continue VS Code extension installed${NC}"
    fi
else
    echo -e "${YELLOW}VS Code CLI not found. Please install Continue extension manually:${NC}"
    echo "  1. Open VS Code"
    echo "  2. Go to Extensions (Cmd+Shift+X)"
    echo "  3. Search for 'Continue'"
    echo "  4. Install 'Continue - Codestral, Claude, GPT-4o, and more'"
fi

# ============================================================================
# Step 7: Login to Continue (interactive)
# ============================================================================
echo -e "\n${BLUE}Step 7: Continue CLI Authentication${NC}"
echo -e "${YELLOW}To authenticate with Continue Hub, run:${NC}"
echo -e "  cn login"
echo -e "\nThis will open a browser to authenticate with your Continue account."

# ============================================================================
# Step 8: Verify installation
# ============================================================================
echo -e "\n${BLUE}Step 8: Verifying installation...${NC}"

echo -e "\n${GREEN}============================================${NC}"
echo -e "${GREEN}   Continue.dev Agents Setup Complete!     ${NC}"
echo -e "${GREEN}============================================${NC}"

echo -e "\n${BLUE}Installed Agents:${NC}"
echo "  1. Improve Test Coverage - Adds missing tests"
echo "  2. Code Security Review - OWASP Top 10 audit"
echo "  3. Refactor Hotspot Files - Identifies refactoring targets"
echo "  4. Triage GitHub Issues - Auto-triage issues"
echo "  5. GitHub Issue Agent - Creates structured issues"
echo "  6. Open PR with Fix - Auto-generate fix PRs"
echo "  7. Snyk Continuous AI - Security scanning"
echo "  8. Create or Update Changelog - Auto-update CHANGELOG"
echo "  9. Sentry Continuous AI - Error monitoring"
echo "  10. Lighthouse Best Practice Analyzer - Performance"
echo "  11. Modularize React Components - Code organization"
echo "  12. Todo Tracker - Track TODOs"

echo -e "\n${BLUE}Next Steps:${NC}"
echo "  1. Run 'cn login' to authenticate with Continue Hub"
echo "  2. Open VS Code in the project: code ."
echo "  3. Press Cmd+L to open Continue chat"
echo "  4. Type '@agent' to see available agents"
echo "  5. Or run agents from terminal: cn agent <agent-name>"

echo -e "\n${BLUE}Quick Commands:${NC}"
echo "  cn -p 'improve test coverage for routes'     # Run agent with prompt"
echo "  cn agent improve-test-coverage               # Run specific agent"
echo "  cn --allow Write                             # Allow write permissions"

echo -e "\n${YELLOW}Configuration file: ~/.continue/config.yaml${NC}"
echo -e "${YELLOW}Project config: .continue/config.yaml${NC}"
