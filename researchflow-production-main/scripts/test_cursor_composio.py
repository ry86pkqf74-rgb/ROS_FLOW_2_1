#!/usr/bin/env python3
"""
Test script for Cursor ↔ LangChain ↔ Composio integration
Updated for LangChain v1.2+ / LangGraph API
"""

import os
import sys

# Add agents directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'agents'))

# Set environment variables
os.environ['RF_BASE_URL'] = 'http://localhost:3001'
os.environ['RF_ACCESS_TOKEN'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJlM2NmZGRlMy0xODk0LTQ3ZTMtYmUzNS1jNzkzNDczZGM0NDciLCJlbWFpbCI6ImN1cnNvci10ZXN0QHJlc2VhcmNoZmxvdy5kZXYiLCJyb2xlIjoiUkVTRUFSQ0hFUiIsImlhdCI6MTc2OTc5NDM1MywiZXhwIjoxNzY5ODgwNzUzLCJhdWQiOiJyZXNlYXJjaGZsb3ctYXBpIiwiaXNzIjoicmVzZWFyY2hmbG93In0.AaYlbh_S6wtGVZYcQE6qqHldwMvp2jnt_sAeWorxLs0'

print("🔗 Cursor ↔ LangChain ↔ Composio Integration Test")
print("=" * 60)

# Test 1: Direct API Access
print("\n📋 Test 1: Direct API Access")
print("-" * 40)
import requests

config = {
    'base_url': os.environ['RF_BASE_URL'],
    'token': os.environ['RF_ACCESS_TOKEN']
}
headers = {
    'Authorization': f"Bearer {config['token']}",
    'Content-Type': 'application/json'
}

try:
    resp = requests.get(f"{config['base_url']}/health", timeout=10)
    print(f"  ✅ Health: {resp.json().get('status')}")
except Exception as e:
    print(f"  ❌ Health check failed: {e}")

try:
    resp = requests.get(f"{config['base_url']}/api/auth/user", headers=headers, timeout=10)
    user = resp.json().get('user', {})
    print(f"  ✅ Auth: {user.get('email')} ({user.get('role')})")
except Exception as e:
    print(f"  ❌ Auth failed: {e}")

try:
    resp = requests.get(f"{config['base_url']}/api/workflows", headers=headers, timeout=10)
    workflows = resp.json().get('workflows', [])
    print(f"  ✅ Workflows: {len(workflows)} found")
except Exception as e:
    print(f"  ❌ Workflows failed: {e}")

# Test 2: LangChain Tools
print("\n📋 Test 2: LangChain Tools")
print("-" * 40)
try:
    from cursor_integration import (
        researchflow_health_check,
        researchflow_list_workflows,
        CursorAgentFactory
    )
    
    result = researchflow_health_check.invoke({})
    print(f"  ✅ Health tool works")
    
    result = researchflow_list_workflows.invoke({})
    print(f"  ✅ List workflows tool works")
    
    factory = CursorAgentFactory()
    tools = factory.get_researchflow_tools()
    print(f"  ✅ Factory: {len(tools)} tools")
    for t in tools:
        print(f"      - {t.name}")
        
except Exception as e:
    print(f"  ❌ LangChain test failed: {e}")
    import traceback
    traceback.print_exc()

# Test 3: Composio
print("\n📋 Test 3: Composio Integration")
print("-" * 40)
try:
    from composio_langchain import ComposioToolSet
    print("  ✅ Composio LangChain imported")
    
    api_key = os.getenv('COMPOSIO_API_KEY')
    if api_key:
        toolset = ComposioToolSet(api_key=api_key)
        print("  ✅ Composio toolset initialized")
    else:
        print("  ⚠️  COMPOSIO_API_KEY not set")
except ImportError as e:
    print(f"  ⚠️  Composio import: {e}")
except Exception as e:
    print(f"  ❌ Composio failed: {e}")

# Test 4: Agent
print("\n📋 Test 4: Agent Creation")
print("-" * 40)
openai_key = os.getenv('OPENAI_API_KEY')
if openai_key:
    try:
        factory = CursorAgentFactory()
        agent = factory.create_agent(include_composio=False)
        if isinstance(agent, dict):
            print(f"  ✅ Agent (fallback): {len(agent.get('tools', []))} tools")
        else:
            print(f"  ✅ Agent created (LangGraph)")
    except Exception as e:
        print(f"  ❌ Agent failed: {e}")
else:
    print("  ⚠️  OPENAI_API_KEY not set")

# Summary
print("\n" + "=" * 60)
print("📊 Setup Complete!")
print("=" * 60)
print(f"""
Environment file: ~/researchflow-production/.env.cursor

To use in Cursor or Python:
  export RF_BASE_URL={config['base_url']}
  export RF_ACCESS_TOKEN=<your_token>
  
  from agents.cursor_integration import CursorAgentFactory
  factory = CursorAgentFactory()
  tools = factory.get_researchflow_tools()
  
  # Call tools directly:
  from agents.cursor_integration import researchflow_list_workflows
  result = researchflow_list_workflows.invoke({{}})
""")
