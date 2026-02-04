#!/usr/bin/env python3
"""
ResearchFlow Multi-Agent Orchestrator

This module orchestrates the four specialized agents using LangGraph:
1. DesignOps Agent - Figma → Design Tokens → PR
2. SpecOps Agent - Notion PRD → GitHub Issues
3. Compliance Agent - TRIPOD+AI, CONSORT-AI, FAVES, HTI-1
4. Release Guardian Agent - Deployment Gates

Workflows:
- design_to_code: Figma changes → tokens → validated PR
- prd_to_issues: Notion PRD → GitHub issues with tracking
- compliance_audit: Full compliance validation pipeline
- deployment_pipeline: CI → Evidence → FAVES → Deploy
"""

import os
import json
import logging
import sys
from datetime import datetime
from typing import Dict, Any, Optional, List, Literal, TypedDict, Annotated
from enum import Enum

from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

# Import production utilities
from agents.utils import (
    setup_structured_logging,
    get_agent_logger,
    validate_startup_environment,
    get_agent_health_checker
)

# Import our specialized agents
from agents.design_ops_agent import DesignOpsAgent
from agents.spec_ops_agent import SpecOpsAgent
from agents.compliance_agent import ComplianceAgent
from agents.release_guardian_agent import ReleaseGuardianAgent
from agents.preflight_validation_agent import PreflightValidationAgent, ValidationStatus

# Setup structured logging
log_format_json = os.getenv("LOG_FORMAT", "text") == "json"
log_level = os.getenv("LOG_LEVEL", "INFO")
setup_structured_logging(level=log_level, json_format=log_format_json)

logger = get_agent_logger("Orchestrator")


# =============================================================================
# State Definitions
# =============================================================================

class WorkflowState(TypedDict):
    """Base state for all workflows"""
    messages: List[BaseMessage]
    current_agent: str
    workflow_type: str
    status: str
    results: Dict[str, Any]
    errors: List[str]
    metadata: Dict[str, Any]


class DesignWorkflowState(WorkflowState):
    """State for design-to-code workflow"""
    figma_file_key: str
    design_tokens: Optional[Dict[str, Any]]
    pr_url: Optional[str]
    branch_name: Optional[str]


class PRDWorkflowState(WorkflowState):
    """State for PRD-to-issues workflow"""
    prd_page_id: str
    requirements: List[Dict[str, Any]]
    created_issues: List[Dict[str, Any]]
    milestone_id: Optional[str]


class ComplianceWorkflowState(WorkflowState):
    """State for compliance audit workflow"""
    model_id: str
    model_version: str
    tripod_status: Optional[Dict[str, Any]]
    faves_status: Optional[Dict[str, Any]]
    hti1_disclosure: Optional[str]
    compliance_score: Optional[float]


class DeploymentWorkflowState(WorkflowState):
    """State for deployment pipeline workflow"""
    model_id: str
    model_version: str
    deployment_mode: str  # DEMO, STAGING, LIVE
    gate_results: Dict[str, str]
    evidence_hash: Optional[str]
    approved: bool
    deployed_at: Optional[str]


class PreflightWorkflowState(WorkflowState):
    """State for preflight validation workflow"""
    commit_sha: Optional[str]
    branch: Optional[str]
    skip_services: bool
    skip_api_tests: bool
    validation_results: List[Dict[str, Any]]
    overall_status: str
    recommendations: List[str]
    ready_for_deployment: bool


# =============================================================================
# Orchestrator Class
# =============================================================================

class ResearchFlowOrchestrator:
    """
    Multi-agent orchestrator for ResearchFlow using LangGraph.

    Coordinates workflows across specialized agents:
    - DesignOps: Design system management
    - SpecOps: Requirements management
    - Compliance: Regulatory compliance
    - Release Guardian: Deployment management
    """

    def __init__(
        self,
        composio_api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        entity_id: str = "default",
        github_repo: str = "ry86pkqf74-rgb/researchflow-production"
    ):
        self.composio_api_key = composio_api_key or os.getenv("COMPOSIO_API_KEY")
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.entity_id = entity_id
        self.github_repo = github_repo

        # Initialize specialized agents
        self._init_agents()

        # Build workflow graphs
        self.workflows = {
            "design_to_code": self._build_design_workflow(),
            "prd_to_issues": self._build_prd_workflow(),
            "compliance_audit": self._build_compliance_workflow(),
            "deployment_pipeline": self._build_deployment_workflow(),
            "preflight_validation": self._build_preflight_workflow(),
        }

    def _init_agents(self):
        """Initialize all specialized agents"""
        logger.info("Initializing specialized agents...")

        self.design_ops = DesignOpsAgent(
            composio_api_key=self.composio_api_key,
            openai_api_key=self.openai_api_key,
            entity_id=self.entity_id,
            github_repo=self.github_repo
        )

        self.spec_ops = SpecOpsAgent(
            composio_api_key=self.composio_api_key,
            openai_api_key=self.openai_api_key,
            entity_id=self.entity_id,
            github_repo=self.github_repo
        )

        self.compliance = ComplianceAgent(
            composio_api_key=self.composio_api_key,
            openai_api_key=self.openai_api_key,
            entity_id=self.entity_id,
            github_repo=self.github_repo
        )

        self.release_guardian = ReleaseGuardianAgent(
            composio_api_key=self.composio_api_key,
            openai_api_key=self.openai_api_key,
            entity_id=self.entity_id,
            github_repo=self.github_repo
        )

        self.preflight = PreflightValidationAgent(
            composio_api_key=self.composio_api_key,
            openai_api_key=self.openai_api_key,
            entity_id=self.entity_id,
            github_repo=self.github_repo
        )

        logger.info("All agents initialized successfully")

    # =========================================================================
    # Design-to-Code Workflow
    # =========================================================================

    def _build_design_workflow(self) -> StateGraph:
        """Build the design-to-code workflow graph"""

        def extract_tokens(state: DesignWorkflowState) -> DesignWorkflowState:
            """Extract design tokens from Figma"""
            logger.info(f"Extracting tokens from Figma: {state['figma_file_key']}")
            state["current_agent"] = "DesignOps"
            state["status"] = "extracting_tokens"

            try:
                result = self.design_ops.extract_design_tokens(state["figma_file_key"])
                state["design_tokens"] = result.get("output", {})
                state["results"]["token_extraction"] = "success"
            except Exception as e:
                state["errors"].append(f"Token extraction failed: {str(e)}")
                state["results"]["token_extraction"] = "failed"

            return state

        def create_pr(state: DesignWorkflowState) -> DesignWorkflowState:
            """Create PR with design token changes"""
            logger.info("Creating PR with design tokens")
            state["status"] = "creating_pr"

            if state["results"].get("token_extraction") != "success":
                state["errors"].append("Skipping PR creation due to extraction failure")
                return state

            try:
                timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                state["branch_name"] = f"design-tokens/update-{timestamp}"

                result = self.design_ops.create_design_tokens_pr(
                    state["figma_file_key"],
                    state["branch_name"]
                )
                state["pr_url"] = result.get("output", {}).get("pr_url")
                state["results"]["pr_creation"] = "success"
            except Exception as e:
                state["errors"].append(f"PR creation failed: {str(e)}")
                state["results"]["pr_creation"] = "failed"

            return state

        def finalize_design(state: DesignWorkflowState) -> DesignWorkflowState:
            """Finalize design workflow"""
            state["status"] = "completed"
            state["current_agent"] = "Orchestrator"

            # Summary
            state["results"]["summary"] = {
                "figma_file": state["figma_file_key"],
                "tokens_extracted": state["design_tokens"] is not None,
                "pr_created": state["pr_url"] is not None,
                "pr_url": state["pr_url"],
                "errors": state["errors"]
            }

            return state

        # Build graph
        workflow = StateGraph(DesignWorkflowState)
        workflow.add_node("extract_tokens", extract_tokens)
        workflow.add_node("create_pr", create_pr)
        workflow.add_node("finalize", finalize_design)

        workflow.set_entry_point("extract_tokens")
        workflow.add_edge("extract_tokens", "create_pr")
        workflow.add_edge("create_pr", "finalize")
        workflow.add_edge("finalize", END)

        return workflow.compile()

    # =========================================================================
    # PRD-to-Issues Workflow
    # =========================================================================

    def _build_prd_workflow(self) -> StateGraph:
        """Build the PRD-to-issues workflow graph"""

        def sync_prd(state: PRDWorkflowState) -> PRDWorkflowState:
            """Sync PRD from Notion to GitHub issues"""
            logger.info(f"Syncing PRD: {state['prd_page_id']}")
            state["current_agent"] = "SpecOps"
            state["status"] = "syncing_prd"

            try:
                result = self.spec_ops.sync_prd_to_issues(state["prd_page_id"])
                state["created_issues"] = result.get("output", {}).get("issues", [])
                state["results"]["prd_sync"] = "success"
            except Exception as e:
                state["errors"].append(f"PRD sync failed: {str(e)}")
                state["results"]["prd_sync"] = "failed"

            return state

        def finalize_prd(state: PRDWorkflowState) -> PRDWorkflowState:
            """Finalize PRD workflow"""
            state["status"] = "completed"
            state["current_agent"] = "Orchestrator"

            state["results"]["summary"] = {
                "prd_page": state["prd_page_id"],
                "issues_created": len(state.get("created_issues", [])),
                "milestone": state.get("milestone_id"),
                "errors": state["errors"]
            }

            return state

        # Build graph
        workflow = StateGraph(PRDWorkflowState)
        workflow.add_node("sync_prd", sync_prd)
        workflow.add_node("finalize", finalize_prd)

        workflow.set_entry_point("sync_prd")
        workflow.add_edge("sync_prd", "finalize")
        workflow.add_edge("finalize", END)

        return workflow.compile()

    # =========================================================================
    # Compliance Audit Workflow
    # =========================================================================

    def _build_compliance_workflow(self) -> StateGraph:
        """Build the compliance audit workflow graph"""

        def validate_tripod(state: ComplianceWorkflowState) -> ComplianceWorkflowState:
            """Validate TRIPOD+AI checklist"""
            logger.info(f"Validating TRIPOD+AI for model: {state['model_id']}")
            state["current_agent"] = "Compliance"
            state["status"] = "validating_tripod"

            try:
                result = self.compliance.validate_tripod_ai(
                    state["model_id"],
                    f"evidence/models/{state['model_version']}/"
                )
                state["tripod_status"] = result.get("output", {})
                state["results"]["tripod_validation"] = "success"
            except Exception as e:
                state["errors"].append(f"TRIPOD validation failed: {str(e)}")
                state["results"]["tripod_validation"] = "failed"

            return state

        def validate_faves(state: ComplianceWorkflowState) -> ComplianceWorkflowState:
            """Validate FAVES gates"""
            logger.info(f"Validating FAVES gates for model: {state['model_id']}")
            state["status"] = "validating_faves"

            try:
                result = self.compliance.validate_faves_gates(
                    state["model_id"],
                    state["model_version"],
                    state.get("metadata", {}).get("deployment_mode", "DEMO")
                )
                state["faves_status"] = result.get("output", {})
                state["results"]["faves_validation"] = "success"
            except Exception as e:
                state["errors"].append(f"FAVES validation failed: {str(e)}")
                state["results"]["faves_validation"] = "failed"

            return state

        def generate_disclosure(state: ComplianceWorkflowState) -> ComplianceWorkflowState:
            """Generate HTI-1 disclosure"""
            logger.info(f"Generating HTI-1 disclosure for model: {state['model_id']}")
            state["status"] = "generating_disclosure"

            try:
                result = self.compliance.generate_hti1_disclosure(
                    state["model_id"],
                    state["model_version"]
                )
                state["hti1_disclosure"] = result.get("output", {}).get("disclosure_path")
                state["results"]["hti1_generation"] = "success"
            except Exception as e:
                state["errors"].append(f"HTI-1 generation failed: {str(e)}")
                state["results"]["hti1_generation"] = "failed"

            return state

        def calculate_score(state: ComplianceWorkflowState) -> ComplianceWorkflowState:
            """Calculate overall compliance score"""
            state["status"] = "calculating_score"

            # Simple scoring: each passed component = 33.3%
            score = 0
            if state["results"].get("tripod_validation") == "success":
                score += 33.3
            if state["results"].get("faves_validation") == "success":
                score += 33.3
            if state["results"].get("hti1_generation") == "success":
                score += 33.4

            state["compliance_score"] = round(score, 1)
            return state

        def finalize_compliance(state: ComplianceWorkflowState) -> ComplianceWorkflowState:
            """Finalize compliance workflow"""
            state["status"] = "completed"
            state["current_agent"] = "Orchestrator"

            state["results"]["summary"] = {
                "model": f"{state['model_id']} v{state['model_version']}",
                "compliance_score": state["compliance_score"],
                "tripod_passed": state["results"].get("tripod_validation") == "success",
                "faves_passed": state["results"].get("faves_validation") == "success",
                "hti1_generated": state["hti1_disclosure"] is not None,
                "deployment_ready": state["compliance_score"] >= 100,
                "errors": state["errors"]
            }

            return state

        # Build graph
        workflow = StateGraph(ComplianceWorkflowState)
        workflow.add_node("validate_tripod", validate_tripod)
        workflow.add_node("validate_faves", validate_faves)
        workflow.add_node("generate_disclosure", generate_disclosure)
        workflow.add_node("calculate_score", calculate_score)
        workflow.add_node("finalize", finalize_compliance)

        workflow.set_entry_point("validate_tripod")
        workflow.add_edge("validate_tripod", "validate_faves")
        workflow.add_edge("validate_faves", "generate_disclosure")
        workflow.add_edge("generate_disclosure", "calculate_score")
        workflow.add_edge("calculate_score", "finalize")
        workflow.add_edge("finalize", END)

        return workflow.compile()

    # =========================================================================
    # Deployment Pipeline Workflow
    # =========================================================================

    def _build_deployment_workflow(self) -> StateGraph:
        """Build the deployment pipeline workflow graph"""

        def check_ci(state: DeploymentWorkflowState) -> DeploymentWorkflowState:
            """Check CI/CD status"""
            logger.info(f"Checking CI for deployment: {state['model_id']}")
            state["current_agent"] = "ReleaseGuardian"
            state["status"] = "checking_ci"

            try:
                result = self.release_guardian.check_ci_status()
                ci_passed = result.get("output", {}).get("status") == "passed"
                state["gate_results"]["ci_checks"] = "passed" if ci_passed else "failed"
                state["results"]["ci_check"] = "success"
            except Exception as e:
                state["errors"].append(f"CI check failed: {str(e)}")
                state["gate_results"]["ci_checks"] = "failed"
                state["results"]["ci_check"] = "failed"

            return state

        def compute_hash(state: DeploymentWorkflowState) -> DeploymentWorkflowState:
            """Compute evidence pack hash"""
            logger.info(f"Computing evidence hash for: {state['model_version']}")
            state["status"] = "computing_hash"

            try:
                result = self.release_guardian.compute_evidence_hash(state["model_version"])
                state["evidence_hash"] = result.get("output", {}).get("hash")
                state["gate_results"]["evidence_pack"] = "passed" if state["evidence_hash"] else "failed"
                state["results"]["hash_computation"] = "success"
            except Exception as e:
                state["errors"].append(f"Hash computation failed: {str(e)}")
                state["gate_results"]["evidence_pack"] = "failed"
                state["results"]["hash_computation"] = "failed"

            return state

        def validate_faves_gate(state: DeploymentWorkflowState) -> DeploymentWorkflowState:
            """Validate FAVES gates for deployment"""
            logger.info(f"Validating FAVES for deployment: {state['model_id']}")
            state["status"] = "validating_faves_gate"

            if state["deployment_mode"] == "DEMO":
                # FAVES is advisory for DEMO
                state["gate_results"]["faves_gate"] = "waived"
                return state

            try:
                result = self.compliance.validate_faves_gates(
                    state["model_id"],
                    state["model_version"],
                    state["deployment_mode"]
                )
                faves_passed = all(
                    v == "pass" for v in result.get("output", {}).get("gates", {}).values()
                )
                state["gate_results"]["faves_gate"] = "passed" if faves_passed else "failed"
            except Exception as e:
                state["errors"].append(f"FAVES validation failed: {str(e)}")
                state["gate_results"]["faves_gate"] = "failed"

            return state

        def validate_gates(state: DeploymentWorkflowState) -> DeploymentWorkflowState:
            """Run full gate validation"""
            logger.info(f"Validating all gates for: {state['model_id']}")
            state["status"] = "validating_gates"

            try:
                result = self.release_guardian.validate_deployment(
                    state["model_id"],
                    state["model_version"],
                    state["deployment_mode"]
                )

                # Update gate results from validation
                validation_output = result.get("output", {})
                if isinstance(validation_output, dict):
                    for gate, status in validation_output.get("gates", {}).items():
                        if gate not in state["gate_results"]:
                            state["gate_results"][gate] = status

                state["results"]["gate_validation"] = "success"
            except Exception as e:
                state["errors"].append(f"Gate validation failed: {str(e)}")
                state["results"]["gate_validation"] = "failed"

            return state

        def determine_approval(state: DeploymentWorkflowState) -> DeploymentWorkflowState:
            """Determine if deployment is approved"""
            state["status"] = "determining_approval"

            # Check required gates based on deployment mode
            required_gates = {
                "DEMO": ["ci_checks", "evidence_pack"],
                "STAGING": ["ci_checks", "evidence_pack", "rollback_plan"],
                "LIVE": ["ci_checks", "evidence_pack", "faves_gate", "rollback_plan", "monitoring"]
            }

            mode_gates = required_gates.get(state["deployment_mode"], required_gates["DEMO"])
            failed_gates = [
                gate for gate in mode_gates
                if state["gate_results"].get(gate, "failed") == "failed"
            ]

            state["approved"] = len(failed_gates) == 0

            if not state["approved"]:
                state["errors"].append(f"Failed gates: {', '.join(failed_gates)}")

            return state

        def finalize_deployment(state: DeploymentWorkflowState) -> DeploymentWorkflowState:
            """Finalize deployment workflow"""
            state["status"] = "completed"
            state["current_agent"] = "Orchestrator"

            if state["approved"]:
                state["deployed_at"] = datetime.now().isoformat()

            state["results"]["summary"] = {
                "model": f"{state['model_id']} v{state['model_version']}",
                "mode": state["deployment_mode"],
                "approved": state["approved"],
                "gates": state["gate_results"],
                "evidence_hash": state["evidence_hash"],
                "deployed_at": state.get("deployed_at"),
                "errors": state["errors"]
            }

            return state

        # Build graph
        workflow = StateGraph(DeploymentWorkflowState)
        workflow.add_node("check_ci", check_ci)
        workflow.add_node("compute_hash", compute_hash)
        workflow.add_node("validate_faves_gate", validate_faves_gate)
        workflow.add_node("validate_gates", validate_gates)
        workflow.add_node("determine_approval", determine_approval)
        workflow.add_node("finalize", finalize_deployment)

        workflow.set_entry_point("check_ci")
        workflow.add_edge("check_ci", "compute_hash")
        workflow.add_edge("compute_hash", "validate_faves_gate")
        workflow.add_edge("validate_faves_gate", "validate_gates")
        workflow.add_edge("validate_gates", "determine_approval")
        workflow.add_edge("determine_approval", "finalize")
        workflow.add_edge("finalize", END)

        return workflow.compile()

    # =========================================================================
    # Preflight Validation Workflow
    # =========================================================================

    def _build_preflight_workflow(self) -> StateGraph:
        """Build the preflight validation workflow graph"""

        def run_file_validation(state: PreflightWorkflowState) -> PreflightWorkflowState:
            """Validate file structure"""
            logger.info("Running file structure validation...")
            state["current_agent"] = "Preflight"
            state["status"] = "validating_files"

            try:
                results = self.preflight.validate_file_structure()
                state["validation_results"].extend([
                    {"name": r.name, "status": r.status.value, "message": r.message}
                    for r in results
                ])
                state["results"]["file_validation"] = "success"
            except Exception as e:
                state["errors"].append(f"File validation failed: {str(e)}")
                state["results"]["file_validation"] = "failed"

            return state

        def run_code_validation(state: PreflightWorkflowState) -> PreflightWorkflowState:
            """Validate code syntax"""
            logger.info("Running code validation...")
            state["status"] = "validating_code"

            try:
                results = self.preflight.validate_typescript_syntax()
                state["validation_results"].extend([
                    {"name": r.name, "status": r.status.value, "message": r.message}
                    for r in results
                ])
                state["results"]["code_validation"] = "success"
            except Exception as e:
                state["errors"].append(f"Code validation failed: {str(e)}")
                state["results"]["code_validation"] = "failed"

            return state

        def run_migration_validation(state: PreflightWorkflowState) -> PreflightWorkflowState:
            """Validate database migrations"""
            logger.info("Running migration validation...")
            state["status"] = "validating_migrations"

            try:
                results = self.preflight.validate_migrations()
                state["validation_results"].extend([
                    {"name": r.name, "status": r.status.value, "message": r.message}
                    for r in results
                ])
                state["results"]["migration_validation"] = "success"
            except Exception as e:
                state["errors"].append(f"Migration validation failed: {str(e)}")
                state["results"]["migration_validation"] = "failed"

            return state

        def run_docker_validation(state: PreflightWorkflowState) -> PreflightWorkflowState:
            """Validate Docker configuration"""
            logger.info("Running Docker validation...")
            state["status"] = "validating_docker"

            try:
                results = self.preflight.validate_docker_config()
                state["validation_results"].extend([
                    {"name": r.name, "status": r.status.value, "message": r.message}
                    for r in results
                ])
                state["results"]["docker_validation"] = "success"
            except Exception as e:
                state["errors"].append(f"Docker validation failed: {str(e)}")
                state["results"]["docker_validation"] = "failed"

            return state

        def determine_readiness(state: PreflightWorkflowState) -> PreflightWorkflowState:
            """Determine if ready for deployment"""
            state["status"] = "determining_readiness"

            # Count failures
            failed_count = sum(
                1 for r in state["validation_results"]
                if r.get("status") == "failed"
            )
            warning_count = sum(
                1 for r in state["validation_results"]
                if r.get("status") == "warning"
            )

            if failed_count > 0:
                state["overall_status"] = "failed"
                state["ready_for_deployment"] = False
                state["recommendations"].append(
                    f"Fix {failed_count} failed checks before deployment"
                )
            elif warning_count > 0:
                state["overall_status"] = "warning"
                state["ready_for_deployment"] = True
                state["recommendations"].append(
                    f"Review {warning_count} warnings - deployment possible but not recommended"
                )
            else:
                state["overall_status"] = "passed"
                state["ready_for_deployment"] = True
                state["recommendations"].append("All checks passed - ready for deployment!")

            return state

        def finalize_preflight(state: PreflightWorkflowState) -> PreflightWorkflowState:
            """Finalize preflight workflow"""
            state["status"] = "completed"
            state["current_agent"] = "Orchestrator"

            # Build summary
            passed = sum(1 for r in state["validation_results"] if r.get("status") == "passed")
            failed = sum(1 for r in state["validation_results"] if r.get("status") == "failed")
            warnings = sum(1 for r in state["validation_results"] if r.get("status") == "warning")

            state["results"]["summary"] = {
                "commit": state.get("commit_sha"),
                "branch": state.get("branch"),
                "overall_status": state["overall_status"],
                "ready_for_deployment": state["ready_for_deployment"],
                "checks": {
                    "passed": passed,
                    "failed": failed,
                    "warnings": warnings,
                    "total": len(state["validation_results"])
                },
                "recommendations": state["recommendations"],
                "errors": state["errors"]
            }

            return state

        # Build graph
        workflow = StateGraph(PreflightWorkflowState)
        workflow.add_node("file_validation", run_file_validation)
        workflow.add_node("code_validation", run_code_validation)
        workflow.add_node("migration_validation", run_migration_validation)
        workflow.add_node("docker_validation", run_docker_validation)
        workflow.add_node("determine_readiness", determine_readiness)
        workflow.add_node("finalize", finalize_preflight)

        workflow.set_entry_point("file_validation")
        workflow.add_edge("file_validation", "code_validation")
        workflow.add_edge("code_validation", "migration_validation")
        workflow.add_edge("migration_validation", "docker_validation")
        workflow.add_edge("docker_validation", "determine_readiness")
        workflow.add_edge("determine_readiness", "finalize")
        workflow.add_edge("finalize", END)

        return workflow.compile()

    # =========================================================================
    # Public API
    # =========================================================================

    def run_design_workflow(self, figma_file_key: str) -> Dict[str, Any]:
        """Run the design-to-code workflow"""
        logger.info(f"Starting design workflow for: {figma_file_key}")

        initial_state: DesignWorkflowState = {
            "messages": [],
            "current_agent": "Orchestrator",
            "workflow_type": "design_to_code",
            "status": "started",
            "results": {},
            "errors": [],
            "metadata": {},
            "figma_file_key": figma_file_key,
            "design_tokens": None,
            "pr_url": None,
            "branch_name": None
        }

        result = self.workflows["design_to_code"].invoke(initial_state)
        return result["results"]

    def run_prd_workflow(self, prd_page_id: str, milestone: Optional[str] = None) -> Dict[str, Any]:
        """Run the PRD-to-issues workflow"""
        logger.info(f"Starting PRD workflow for: {prd_page_id}")

        initial_state: PRDWorkflowState = {
            "messages": [],
            "current_agent": "Orchestrator",
            "workflow_type": "prd_to_issues",
            "status": "started",
            "results": {},
            "errors": [],
            "metadata": {"milestone": milestone},
            "prd_page_id": prd_page_id,
            "requirements": [],
            "created_issues": [],
            "milestone_id": milestone
        }

        result = self.workflows["prd_to_issues"].invoke(initial_state)
        return result["results"]

    def run_compliance_workflow(
        self,
        model_id: str,
        model_version: str,
        deployment_mode: str = "DEMO"
    ) -> Dict[str, Any]:
        """Run the compliance audit workflow"""
        logger.info(f"Starting compliance workflow for: {model_id} v{model_version}")

        initial_state: ComplianceWorkflowState = {
            "messages": [],
            "current_agent": "Orchestrator",
            "workflow_type": "compliance_audit",
            "status": "started",
            "results": {},
            "errors": [],
            "metadata": {"deployment_mode": deployment_mode},
            "model_id": model_id,
            "model_version": model_version,
            "tripod_status": None,
            "faves_status": None,
            "hti1_disclosure": None,
            "compliance_score": None
        }

        result = self.workflows["compliance_audit"].invoke(initial_state)
        return result["results"]

    def run_deployment_workflow(
        self,
        model_id: str,
        model_version: str,
        deployment_mode: str = "DEMO"
    ) -> Dict[str, Any]:
        """Run the deployment pipeline workflow"""
        logger.info(f"Starting deployment workflow for: {model_id} v{model_version} ({deployment_mode})")

        initial_state: DeploymentWorkflowState = {
            "messages": [],
            "current_agent": "Orchestrator",
            "workflow_type": "deployment_pipeline",
            "status": "started",
            "results": {},
            "errors": [],
            "metadata": {},
            "model_id": model_id,
            "model_version": model_version,
            "deployment_mode": deployment_mode,
            "gate_results": {},
            "evidence_hash": None,
            "approved": False,
            "deployed_at": None
        }

        result = self.workflows["deployment_pipeline"].invoke(initial_state)
        return result["results"]

    def run_preflight_workflow(
        self,
        commit_sha: Optional[str] = None,
        branch: Optional[str] = None,
        skip_services: bool = False,
        skip_api_tests: bool = False
    ) -> Dict[str, Any]:
        """Run the preflight validation workflow"""
        logger.info(f"Starting preflight workflow for commit: {commit_sha or 'HEAD'}")

        initial_state: PreflightWorkflowState = {
            "messages": [],
            "current_agent": "Orchestrator",
            "workflow_type": "preflight_validation",
            "status": "started",
            "results": {},
            "errors": [],
            "metadata": {},
            "commit_sha": commit_sha,
            "branch": branch,
            "skip_services": skip_services,
            "skip_api_tests": skip_api_tests,
            "validation_results": [],
            "overall_status": "pending",
            "recommendations": [],
            "ready_for_deployment": False
        }

        result = self.workflows["preflight_validation"].invoke(initial_state)
        return result["results"]

    def list_workflows(self) -> List[str]:
        """List available workflows"""
        return list(self.workflows.keys())

    def get_agent_status(self) -> Dict[str, str]:
        """Get status of all agents"""
        return {
            "DesignOps": "ready" if self.design_ops else "not_initialized",
            "SpecOps": "ready" if self.spec_ops else "not_initialized",
            "Compliance": "ready" if self.compliance else "not_initialized",
            "ReleaseGuardian": "ready" if self.release_guardian else "not_initialized"
        }


# =============================================================================
# CLI and Main
# =============================================================================

def main():
    """Demo the orchestrator"""
    print("🎯 ResearchFlow Multi-Agent Orchestrator")
    print("=" * 60)

    # Validate environment at startup
    print("\n🔍 Validating environment...")
    if not validate_startup_environment():
        print("\n❌ Environment validation failed!")
        print("Please fix the issues above before continuing.")
        sys.exit(1)
    print("✅ Environment validation passed!")

    # Initialize orchestrator
    print("\n🚀 Initializing orchestrator...")
    orchestrator = ResearchFlowOrchestrator()

    # Show status
    print("\n📊 Agent Status:")
    for agent, status in orchestrator.get_agent_status().items():
        emoji = "✅" if status == "ready" else "❌"
        print(f"  {emoji} {agent}: {status}")

    print("\n📋 Available Workflows:")
    for workflow in orchestrator.list_workflows():
        print(f"  - {workflow}")

    # Example: Run a workflow
    print("\n🧪 Example: Running compliance audit workflow...")
    print("(This would normally connect to real services)")

    # Simulated run
    print("""
To run a workflow:

    orchestrator.run_design_workflow("figma-file-key")
    orchestrator.run_prd_workflow("notion-page-id")
    orchestrator.run_compliance_workflow("model-id", "v1.0.0", "DEMO")
    orchestrator.run_deployment_workflow("model-id", "v1.0.0", "LIVE")
""")


async def health_check_demo():
    """Demo health checking"""
    print("\n💚 Running health checks...")
    checker = get_agent_health_checker()
    health = await checker.check_all()
    
    print(f"Overall Status: {health.status.value}")
    print(f"Uptime: {health.uptime_seconds:.2f}s")
    print("\nComponent Status:")
    for component in health.components:
        icon = "✅" if component.status.value == "healthy" else "❌"
        print(f"  {icon} {component.name}: {component.status.value}")
        if component.response_time_ms:
            print(f"     Response time: {component.response_time_ms:.0f}ms")


if __name__ == "__main__":
    main()
    
    # Run health check demo
    import asyncio
    asyncio.run(health_check_demo())
