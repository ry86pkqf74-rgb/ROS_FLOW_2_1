"""
LangGraph Entry Point for LangSmith Deployment

This module exports compiled LangGraph workflows for deployment on LangSmith.
The graphs are initialized from the ResearchFlowOrchestrator class.
"""

import os
from typing import Optional

# Import from parent agents package using relative import
from agents.orchestrator import ResearchFlowOrchestrator

# Initialize the orchestrator with environment variables
orchestrator = ResearchFlowOrchestrator(
    composio_api_key=os.getenv("COMPOSIO_API_KEY"),
    openai_api_key=os.getenv("OPENAI_API_KEY"),
)

# Export compiled graphs for LangSmith deployment
# Main application graph - provides access to all workflows
app = orchestrator.workflows.get("compliance_audit")

# Individual workflow graphs for direct access
design_workflow = orchestrator.workflows.get("design_to_code")
compliance_workflow = orchestrator.workflows.get("compliance_audit")
deployment_workflow = orchestrator.workflows.get("deployment_pipeline")

# Preflight validation workflow
preflight_workflow = orchestrator.workflows.get("preflight_validation")

__all__ = [
    "app",
    "design_workflow",
    "compliance_workflow",
    "deployment_workflow",
    "preflight_workflow",
    "orchestrator",
]
