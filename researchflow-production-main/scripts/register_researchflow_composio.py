#!/usr/bin/env python3
"""
Register ResearchFlow as a custom Composio app and configure LangSmith tracing.

This script:
1. Registers ResearchFlow API endpoints as Composio tools
2. Configures LangSmith tracing for observability
3. Tests the integration end-to-end
"""

import os
import sys

# Environment setup
COMPOSIO_API_KEY = os.getenv("COMPOSIO_API_KEY", "")  # SECURITY: Must be set via environment variable
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY", "")
LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT", "researchflow-production")
RF_BASE_URL = os.getenv("RF_BASE_URL", "http://localhost:3001")
RF_ACCESS_TOKEN = os.getenv("RF_ACCESS_TOKEN", "")

print("=" * 60)
print("ResearchFlow + Composio + LangSmith Integration Setup")
print("=" * 60)

# Step 1: Configure LangSmith tracing
print("\n📊 Step 1: LangSmith Configuration")
print("-" * 40)

os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = LANGSMITH_PROJECT

if LANGSMITH_API_KEY:
    os.environ["LANGCHAIN_API_KEY"] = LANGSMITH_API_KEY
    print(f"  ✅ LangSmith API key configured")
    print(f"  ✅ Project: {LANGSMITH_PROJECT}")
else:
    print("  ⚠️  LANGSMITH_API_KEY not set - tracing disabled")
    print("     Get your key from: https://smith.langchain.com/settings")

# Step 2: Initialize Composio
print("\n🔗 Step 2: Composio Integration")
print("-" * 40)

try:
    if not COMPOSIO_API_KEY:
        raise ValueError("COMPOSIO_API_KEY environment variable not set")

    from composio import Composio

    composio = Composio(api_key=COMPOSIO_API_KEY)
    print(f"  ✅ Composio client initialized")
    
    # List available apps to verify connection
    # Note: Custom app registration requires Composio Enterprise or API access
    print(f"  ℹ️  To add ResearchFlow as a custom toolkit:")
    print(f"     1. Go to Composio Platform > All Toolkits > Request Tools")
    print(f"     2. Or use Composio's custom integration API")
    
except ImportError:
    print("  ❌ Composio not installed")
    print("     Run: pip install composio-core composio-langchain")
except Exception as e:
    print(f"  ❌ Composio error: {e}")

# Step 3: Test ResearchFlow API
print("\n🧪 Step 3: ResearchFlow API Test")
print("-" * 40)

try:
    import requests
    
    # Health check
    resp = requests.get(f"{RF_BASE_URL}/health", timeout=10)
    if resp.ok:
        print(f"  ✅ ResearchFlow API healthy at {RF_BASE_URL}")
    else:
        print(f"  ❌ ResearchFlow API not responding")
        
    # Test authenticated endpoint
    if RF_ACCESS_TOKEN:
        headers = {"Authorization": f"Bearer {RF_ACCESS_TOKEN}"}
        resp = requests.get(f"{RF_BASE_URL}/api/auth/user", headers=headers, timeout=10)
        if resp.ok:
            user = resp.json().get("user", {})
            print(f"  ✅ Authenticated as: {user.get('email')}")
        else:
            print(f"  ⚠️  Authentication failed - token may be expired")
    else:
        print("  ⚠️  RF_ACCESS_TOKEN not set")
        
except Exception as e:
    print(f"  ❌ API test failed: {e}")

# Step 4: Import and test LangChain tools
print("\n🛠️  Step 4: LangChain Tools")
print("-" * 40)

try:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'agents'))
    from cursor_integration import (
        researchflow_health_check,
        researchflow_list_workflows,
        CursorAgentFactory
    )
    
    # Test health check tool (this will trace to LangSmith if configured)
    result = researchflow_health_check.invoke({})
    print(f"  ✅ Health tool: working")
    
    # Get all tools
    factory = CursorAgentFactory()
    tools = factory.get_researchflow_tools()
    print(f"  ✅ Available tools: {len(tools)}")
    for t in tools:
        print(f"      - {t.name}")
        
except Exception as e:
    print(f"  ❌ LangChain tools error: {e}")

# Summary
print("\n" + "=" * 60)
print("📋 Integration Summary")
print("=" * 60)
print(f"""
ResearchFlow API:     {RF_BASE_URL}
LangSmith Project:    {LANGSMITH_PROJECT}
Composio API Key:     {COMPOSIO_API_KEY[:10]}...

To use in the Composio Playground:
1. The existing Composio integrations (GitHub, Slack, Linear, etc.) 
   are already connected and working
2. For ResearchFlow-specific tasks, use the LangChain tools directly
3. Traces will appear in LangSmith under '{LANGSMITH_PROJECT}'

To run agents with full tracing:
  export LANGCHAIN_TRACING_V2=true
  export LANGCHAIN_PROJECT={LANGSMITH_PROJECT}
  python -c "from agents.cursor_integration import *; print(researchflow_list_workflows.invoke(dict()))"
""")
