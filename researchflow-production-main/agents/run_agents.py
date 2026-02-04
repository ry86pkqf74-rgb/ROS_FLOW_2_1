#!/usr/bin/env python3
"""
ResearchFlow Agent Runner

Run individual agents or the full orchestration pipeline.

Usage:
    python -m agents.run_agents --agent design_ops
    python -m agents.run_agents --agent spec_ops
    python -m agents.run_agents --agent compliance
    python -m agents.run_agents --agent release_guardian
    python -m agents.run_agents --all
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.base.langchain_agents import (
    ResearchFlowAgentFactory,
    AgentType,
    AGENT_CONFIGS
)


def check_environment() -> bool:
    """Check that required environment variables are set"""
    required = ["COMPOSIO_API_KEY", "OPENAI_API_KEY"]
    missing = [var for var in required if not os.getenv(var)]

    if missing:
        print("❌ Missing required environment variables:")
        for var in missing:
            print(f"   - {var}")
        print("\nSet them in your .env file or export them:")
        print("   export COMPOSIO_API_KEY=your_key")
        print("   export OPENAI_API_KEY=your_key")
        return False

    return True


def run_design_ops_agent(factory: ResearchFlowAgentFactory, task: Optional[str] = None):
    """Run the DesignOps agent"""
    print("\n🎨 Running DesignOps Agent...")
    print("   Toolkits: Figma, GitHub")
    print("   Purpose: Figma → design tokens → PR automation")

    agent = factory.create_design_ops_agent()

    default_task = """
    Check for any recent Figma design changes and:
    1. Extract the latest design tokens
    2. Generate updated Tailwind configuration
    3. Create a PR with the changes if any updates are needed
    """

    result = agent.invoke({"input": task or default_task})
    print(f"\n✅ Result:\n{result['output']}")
    return result


def run_spec_ops_agent(factory: ResearchFlowAgentFactory, task: Optional[str] = None):
    """Run the SpecOps agent"""
    print("\n📋 Running SpecOps Agent...")
    print("   Toolkits: Notion, GitHub")
    print("   Purpose: Notion PRD → GitHub issues synchronization")

    agent = factory.create_spec_ops_agent()

    default_task = """
    Scan the Problem Registry in Notion for any new or updated PRDs.
    For each PRD that needs sync:
    1. Extract requirements and acceptance criteria
    2. Create corresponding GitHub issues with proper labels
    3. Update the Notion page with GitHub issue links
    """

    result = agent.invoke({"input": task or default_task})
    print(f"\n✅ Result:\n{result['output']}")
    return result


def run_compliance_agent(factory: ResearchFlowAgentFactory, task: Optional[str] = None):
    """Run the Compliance agent"""
    print("\n✅ Running Compliance Agent...")
    print("   Toolkits: Notion, GitHub")
    print("   Purpose: TRIPOD+AI, CONSORT-AI, HTI-1 compliance validation")

    agent = factory.create_compliance_agent()

    default_task = """
    For the latest model version in evidence/models/:
    1. Validate TRIPOD+AI checklist (27 items)
    2. Validate CONSORT-AI checklist if applicable (12 items)
    3. Check all FAVES gates:
       - Fair: Subgroup performance audit
       - Appropriate: Intended use documented
       - Valid: Calibration methodology documented
       - Effective: Outcome metrics present
       - Safe: Monitoring + rollback plans exist
    4. Generate compliance status report
    5. Update Model Registry in Notion
    6. Create GitHub issues for any missing items
    """

    result = agent.invoke({"input": task or default_task})
    print(f"\n✅ Result:\n{result['output']}")
    return result


def run_release_guardian_agent(factory: ResearchFlowAgentFactory, task: Optional[str] = None):
    """Run the Release Guardian agent"""
    print("\n🛡️ Running Release Guardian Agent...")
    print("   Toolkits: GitHub, Notion")
    print("   Purpose: Pre-deploy gate enforcement")

    agent = factory.create_release_guardian_agent()

    default_task = """
    Check deployment readiness for the current release:
    1. Verify all CI checks have passed on main branch
    2. Confirm evidence pack hash is computed and recorded
    3. Validate FAVES gate status (required for LIVE mode)
    4. Check rollback plan documentation exists
    5. Verify monitoring dashboard is configured
    6. Report any blocking issues
    7. Approve or block the deployment
    """

    result = agent.invoke({"input": task or default_task})
    print(f"\n✅ Result:\n{result['output']}")
    return result


def run_wiring_audit_agent(factory: ResearchFlowAgentFactory, task: Optional[str] = None):
    """Run the Wiring Audit agent"""
    print("\n🧭 Running Wiring Audit Agent...")
    print("   Toolkits: GitHub")
    print("   Purpose: Docs ↔ Code ↔ Runtime wiring audit")

    agent = factory.create_wiring_audit_agent()

    default_task = """
    Review wiring documentation and verify actual runtime wiring:
    1. Compare docs/audit/WIRING_TRUTH_TABLE.md with docker-compose.yml
    2. Validate route mounts in services/orchestrator/src/index.ts
    3. Check frontend API calls for /api/manuscripts and /api/manuscript/*
    4. Produce a wiring report with gaps and fixes
    """

    result = agent.invoke({"input": task or default_task})
    print(f"\n✅ Result:\n{result['output']}")
    return result


def run_orchestration_fix_agent(factory: ResearchFlowAgentFactory, task: Optional[str] = None):
    """Run the Orchestration Fix agent"""
    print("\n🧩 Running Orchestration Fix Agent...")
    print("   Toolkits: GitHub")
    print("   Purpose: Frontend ↔ backend wiring remediation")

    agent = factory.create_orchestration_fix_agent()

    default_task = """
    Fix wiring gaps between frontend and backend:
    1. Align API endpoints for manuscripts UI
    2. Update backend routes if needed
    3. Update docker-compose.yml and .env.example
    4. Summarize changes and affected files
    """

    result = agent.invoke({"input": task or default_task})
    print(f"\n✅ Result:\n{result['output']}")
    return result


def run_docker_stack_agent(factory: ResearchFlowAgentFactory, task: Optional[str] = None):
    """Run the Docker Stack Launch agent"""
    print("\n🐳 Running Docker Stack Launch Agent...")
    print("   Toolkits: Docker, GitHub")
    print("   Purpose: Docker stack wiring & web launch readiness")

    agent = factory.create_docker_stack_agent()

    default_task = """
    Verify Docker stack launch readiness:
    1. Validate docker-compose.yml wiring for web/orchestrator/worker/collab
    2. Confirm Vite build args and nginx proxy settings
    3. Produce a launch checklist with health checks
    """

    result = agent.invoke({"input": task or default_task})
    print(f"\n✅ Result:\n{result['output']}")
    return result


def main():
    parser = argparse.ArgumentParser(
        description="ResearchFlow Agent Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python -m agents.run_agents --agent design_ops
    python -m agents.run_agents --agent compliance --task "Validate model v1.2.0"
    python -m agents.run_agents --list
        """
    )

    parser.add_argument(
        "--agent",
        choices=[
            "design_ops",
            "spec_ops",
            "compliance",
            "release_guardian",
            "wiring_audit",
            "orchestration_fix",
            "docker_stack",
        ],
        help="Agent to run"
    )
    parser.add_argument(
        "--task",
        type=str,
        help="Custom task for the agent (optional)"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all agents in sequence"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available agents and their capabilities"
    )

    args = parser.parse_args()

    # List agents
    if args.list:
        print("\n🤖 ResearchFlow Agents")
        print("=" * 60)
        for agent_type in AgentType:
            config = AGENT_CONFIGS[agent_type]
            print(f"\n{agent_type.value}:")
            print(f"   Name: {config.name}")
            print(f"   Description: {config.description}")
            print(f"   Toolkits: {', '.join(config.toolkits)}")
            print(f"   Model: {config.model}")
            print(f"   Actions: {len(config.actions)} configured")
        return

    # Check environment
    if not check_environment():
        sys.exit(1)

    # Create factory
    factory = ResearchFlowAgentFactory()

    # Run agents
    if args.all:
        print("\n🚀 Running all agents...")
        run_design_ops_agent(factory, args.task)
        run_spec_ops_agent(factory, args.task)
        run_compliance_agent(factory, args.task)
        run_release_guardian_agent(factory, args.task)
        run_wiring_audit_agent(factory, args.task)
        run_orchestration_fix_agent(factory, args.task)
        run_docker_stack_agent(factory, args.task)
        print("\n✅ All agents completed!")

    elif args.agent == "design_ops":
        run_design_ops_agent(factory, args.task)

    elif args.agent == "spec_ops":
        run_spec_ops_agent(factory, args.task)

    elif args.agent == "compliance":
        run_compliance_agent(factory, args.task)

    elif args.agent == "release_guardian":
        run_release_guardian_agent(factory, args.task)

    elif args.agent == "wiring_audit":
        run_wiring_audit_agent(factory, args.task)

    elif args.agent == "orchestration_fix":
        run_orchestration_fix_agent(factory, args.task)

    elif args.agent == "docker_stack":
        run_docker_stack_agent(factory, args.task)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
