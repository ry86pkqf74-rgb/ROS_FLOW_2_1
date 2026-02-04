#!/usr/bin/env python3
"""
Compliance Agent - TRIPOD+AI, CONSORT-AI, HTI-1, and FAVES Gate Validation

This agent automates regulatory compliance for AI/ML models:
1. Validates TRIPOD+AI checklist (27 items) for AI/ML model reporting
2. Validates CONSORT-AI checklist (12 items) for clinical trial reporting
3. Generates HTI-1 source attribute disclosures
4. Enforces FAVES gates (Fair, Appropriate, Valid, Effective, Safe)
5. Updates Model Registry in Notion with compliance status
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

# Composio imports - lazy loading with graceful fallback for LangGraph Cloud
try:
    from composio_langchain import ComposioToolSet, Action
    COMPOSIO_AVAILABLE = True
except ImportError as e:
    ComposioToolSet = None
    Action = None
    COMPOSIO_AVAILABLE = False
    import warnings
    warnings.warn(f"Composio not available: {e}. ComplianceAgent will have limited functionality.")

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# LangChain Agent imports - lazy loading for compatibility
try:
    from langchain.agents import AgentExecutor, create_openai_functions_agent
    LANGCHAIN_AGENTS_AVAILABLE = True
except ImportError:
    try:
        from langchain_core.agents import AgentExecutor
        from langchain.agents import create_openai_functions_agent
        LANGCHAIN_AGENTS_AVAILABLE = True
    except ImportError:
        AgentExecutor = None
        create_openai_functions_agent = None
        LANGCHAIN_AGENTS_AVAILABLE = False
        import warnings
        warnings.warn("LangChain agent components not available.")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# TRIPOD+AI Checklist Items (27 items)
TRIPOD_AI_CHECKLIST = [
    {"id": 1, "section": "Title", "item": "Identify the study as developing/validating a prediction model using AI/ML"},
    {"id": 2, "section": "Abstract", "item": "Provide a summary of objectives, study design, setting, participants, sample size, predictors, outcome, statistical analysis, results, and conclusions"},
    {"id": 3, "section": "Introduction", "item": "Explain the medical context and rationale for the prediction model"},
    {"id": 4, "section": "Introduction", "item": "Specify objectives including whether developing/validating model and target population"},
    {"id": 5, "section": "Methods", "item": "Describe the study design (e.g., cohort, case-control)"},
    {"id": 6, "section": "Methods", "item": "Describe the data sources and study setting"},
    {"id": 7, "section": "Methods", "item": "Define eligibility criteria for participants"},
    {"id": 8, "section": "Methods", "item": "Describe the outcome and how it was defined/measured"},
    {"id": 9, "section": "Methods", "item": "Describe the predictors and how they were defined/measured"},
    {"id": 10, "section": "Methods", "item": "Report sample size and how it was determined"},
    {"id": 11, "section": "Methods", "item": "Describe handling of missing data"},
    {"id": 12, "section": "Methods", "item": "Describe the AI/ML modeling approach"},
    {"id": 13, "section": "Methods", "item": "Describe model architecture and hyperparameters"},
    {"id": 14, "section": "Methods", "item": "Describe model training procedure"},
    {"id": 15, "section": "Methods", "item": "Describe internal validation strategy"},
    {"id": 16, "section": "Methods", "item": "Describe external validation if applicable"},
    {"id": 17, "section": "Methods", "item": "Describe performance metrics used"},
    {"id": 18, "section": "Methods", "item": "Describe calibration assessment"},
    {"id": 19, "section": "Methods", "item": "Describe explainability/interpretability methods if used"},
    {"id": 20, "section": "Results", "item": "Report participant flow and characteristics"},
    {"id": 21, "section": "Results", "item": "Report model performance metrics"},
    {"id": 22, "section": "Results", "item": "Report calibration results"},
    {"id": 23, "section": "Results", "item": "Report results of any subgroup analyses"},
    {"id": 24, "section": "Discussion", "item": "Summarize key findings in context of objectives"},
    {"id": 25, "section": "Discussion", "item": "Discuss limitations and potential biases"},
    {"id": 26, "section": "Discussion", "item": "Discuss implications for clinical practice"},
    {"id": 27, "section": "Other", "item": "Provide information on model availability/access"},
]

# CONSORT-AI Checklist Items (12 AI-specific items)
CONSORT_AI_CHECKLIST = [
    {"id": 1, "item": "Indicate that the intervention involves AI in the title/abstract"},
    {"id": 2, "item": "Explain the AI intervention and its intended use"},
    {"id": 3, "item": "Describe the AI system's input data"},
    {"id": 4, "item": "Describe the AI system's output"},
    {"id": 5, "item": "Explain how the AI output was used by participants/clinicians"},
    {"id": 6, "item": "Describe the human-AI interaction"},
    {"id": 7, "item": "Report the AI system's performance during the trial"},
    {"id": 8, "item": "Describe any AI errors or unexpected outputs"},
    {"id": 9, "item": "Report participant compliance with AI recommendations"},
    {"id": 10, "item": "Describe AI version control and updates during trial"},
    {"id": 11, "item": "Discuss implications of AI failures for interpretation"},
    {"id": 12, "item": "Provide AI system access/availability information"},
]

# FAVES Gates
@dataclass
class FAVESGate:
    name: str
    description: str
    required_artifacts: List[str]


FAVES_GATES = {
    "Fair": FAVESGate(
        name="Fair",
        description="Subgroup performance audit exists demonstrating equitable performance across demographic groups",
        required_artifacts=[
            "subgroup_performance_audit.json",
            "demographic_analysis_report.md",
            "bias_assessment.json"
        ]
    ),
    "Appropriate": FAVESGate(
        name="Appropriate",
        description="Intended use and contraindications are documented",
        required_artifacts=[
            "intended_use_statement.md",
            "contraindications.md",
            "clinical_context.md"
        ]
    ),
    "Valid": FAVESGate(
        name="Valid",
        description="Calibration and validation methodology are documented",
        required_artifacts=[
            "validation_report.json",
            "calibration_curves.json",
            "holdout_test_results.json"
        ]
    ),
    "Effective": FAVESGate(
        name="Effective",
        description="Outcome metrics documented or 'research-only' label present",
        required_artifacts=[
            "outcome_metrics.json",
            "clinical_utility_assessment.md"
        ]
    ),
    "Safe": FAVESGate(
        name="Safe",
        description="Monitoring plan, rollback procedure, and incident playbook exist",
        required_artifacts=[
            "monitoring_plan.md",
            "rollback_procedure.md",
            "incident_playbook.md"
        ]
    )
}


# Compliance Agent Configuration
# Actions are only available if Composio is installed
_COMPLIANCE_ACTIONS = []
if COMPOSIO_AVAILABLE and Action is not None:
    _COMPLIANCE_ACTIONS = [
        # Notion Actions
        Action.NOTION_SEARCH_PAGES,
        Action.NOTION_GET_PAGE,
        Action.NOTION_GET_DATABASE,
        Action.NOTION_QUERY_A_DATABASE,
        Action.NOTION_CREATE_A_PAGE,
        Action.NOTION_UPDATE_A_PAGE,
        Action.NOTION_APPEND_BLOCK_CHILDREN,
        # GitHub Actions
        Action.GITHUB_CREATE_AN_ISSUE,
        Action.GITHUB_UPDATE_AN_ISSUE,
        Action.GITHUB_ADD_LABELS_TO_AN_ISSUE,
        Action.GITHUB_GET_A_REPOSITORY,
        Action.GITHUB_GET_REPOSITORY_CONTENT,
        Action.GITHUB_CREATE_OR_UPDATE_FILE_CONTENTS,
    ]

COMPLIANCE_CONFIG = {
    "name": "Compliance Agent",
    "model": "gpt-4o",
    "temperature": 0,
    "toolkits": ["NOTION", "GITHUB"] if COMPOSIO_AVAILABLE else [],
    "actions": _COMPLIANCE_ACTIONS,
    "system_prompt": """You are the Compliance Agent for ResearchFlow.

Your responsibilities:
1. Validate TRIPOD+AI checklist (27 items) for AI/ML model reporting
2. Validate CONSORT-AI checklist (12 items) for clinical trial AI reporting
3. Enforce FAVES gates for model deployments:
   - Fair: Subgroup performance audit exists
   - Appropriate: Intended use + contraindications documented
   - Valid: Calibration + validation methodology documented
   - Effective: Outcome metrics or "research-only" label present
   - Safe: Monitoring plan + rollback procedure + incident playbook exist
4. Generate HTI-1 source attribute disclosures
5. Update Model Registry in Notion with compliance status
6. Create GitHub issues for missing compliance items

Evidence pack location: evidence/models/{model_version}/
Output files:
- tripodai_checklist.json
- consortai_checklist.json
- hti1_disclosure.md
- faves_assessment.json

CRITICAL RULES:
- Never approve a LIVE deployment without all FAVES gates passing
- Always document compliance gaps with specific remediation steps
- Generate detailed compliance reports for regulatory review
- Link all compliance artifacts in the Model Registry

HTI-1 Disclosure Format:
## Algorithm Transparency Disclosure (HTI-1 Compliant)

### Basic Information
- Algorithm Name: [name]
- Version: [version]
- Intended Use: [description]

### Source Attributes
- Developer: [organization]
- Training Data Sources: [list]
- Training Data Demographics: [summary]
- Validation Data Sources: [list]

### Performance Characteristics
- Primary Metrics: [list with values]
- Known Limitations: [list]
- Contraindications: [list]

### Fairness Assessment
- Tested Demographic Groups: [list]
- Subgroup Performance: [summary table]
- Known Disparities: [list if any]

### Updates and Monitoring
- Version History: [summary]
- Monitoring Plan: [reference]
- Incident Reporting: [contact/process]
"""
}


class ComplianceAgent:
    """Compliance Agent for TRIPOD+AI, CONSORT-AI, HTI-1, and FAVES validation"""

    def __init__(
        self,
        composio_api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        entity_id: str = "default",
        github_repo: str = "ry86pkqf74-rgb/researchflow-production",
        notion_databases: Optional[Dict[str, str]] = None
    ):
        self.composio_api_key = composio_api_key or os.getenv("COMPOSIO_API_KEY")
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.entity_id = entity_id
        self.github_repo = github_repo
        self.notion_databases = notion_databases or {
            "model_registry": os.getenv("NOTION_MODEL_REGISTRY_DB", ""),
            "risk_register": os.getenv("NOTION_RISK_REGISTER_DB", ""),
        }

        # Initialize Composio toolset
        self.toolset = ComposioToolSet(
            api_key=self.composio_api_key,
            entity_id=self.entity_id
        )

        # Initialize LLM
        self.llm = ChatOpenAI(
            model=COMPLIANCE_CONFIG["model"],
            temperature=COMPLIANCE_CONFIG["temperature"],
            api_key=self.openai_api_key
        )

        # Get tools
        self.tools = self.toolset.get_tools(actions=COMPLIANCE_CONFIG["actions"])

        # Create agent
        self.agent = self._create_agent()

    def _create_agent(self) -> AgentExecutor:
        """Create the LangChain agent with Composio tools"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", COMPLIANCE_CONFIG["system_prompt"]),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        agent = create_openai_functions_agent(self.llm, self.tools, prompt)

        return AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=20,
            return_intermediate_steps=True
        )

    def validate_tripod_ai(
        self,
        model_id: str,
        documentation_path: str
    ) -> Dict[str, Any]:
        """Validate TRIPOD+AI checklist for a model"""
        logger.info(f"Validating TRIPOD+AI checklist for model: {model_id}")

        checklist_json = json.dumps(TRIPOD_AI_CHECKLIST, indent=2)

        result = self.agent.invoke({
            "input": f"""Validate TRIPOD+AI compliance for model: {model_id}

TRIPOD+AI Checklist (27 items):
{checklist_json}

Steps:
1. Fetch model documentation from: {documentation_path}
2. For each checklist item:
   - Check if the item is addressed in documentation
   - Rate compliance: "met", "partially_met", or "not_met"
   - Provide evidence location or gap description
3. Generate a compliance summary with:
   - Overall compliance percentage
   - List of gaps requiring attention
   - Recommendations for each gap
4. Save results to evidence/models/{model_id}/tripodai_checklist.json
5. Update the Model Registry in Notion with TRIPOD+AI status

Repository: {self.github_repo}"""
        })

        return result

    def validate_consort_ai(
        self,
        trial_id: str,
        protocol_path: str
    ) -> Dict[str, Any]:
        """Validate CONSORT-AI checklist for a clinical trial"""
        logger.info(f"Validating CONSORT-AI checklist for trial: {trial_id}")

        checklist_json = json.dumps(CONSORT_AI_CHECKLIST, indent=2)

        result = self.agent.invoke({
            "input": f"""Validate CONSORT-AI compliance for trial: {trial_id}

CONSORT-AI Checklist (12 AI-specific items):
{checklist_json}

Steps:
1. Fetch trial protocol and documentation from: {protocol_path}
2. For each checklist item:
   - Assess if the item is documented
   - Rate: "met", "partially_met", or "not_met"
   - Note evidence location or gap
3. Generate compliance report with gaps and recommendations
4. Save to evidence/trials/{trial_id}/consortai_checklist.json
5. Create GitHub issues for critical gaps

Repository: {self.github_repo}"""
        })

        return result

    def validate_faves_gates(
        self,
        model_id: str,
        model_version: str,
        deployment_mode: str = "DEMO"
    ) -> Dict[str, Any]:
        """Validate FAVES gates for model deployment"""
        logger.info(f"Validating FAVES gates for model: {model_id} v{model_version}")

        faves_info = {
            name: {
                "description": gate.description,
                "required_artifacts": gate.required_artifacts
            }
            for name, gate in FAVES_GATES.items()
        }

        result = self.agent.invoke({
            "input": f"""Validate FAVES gates for model deployment:
- Model ID: {model_id}
- Version: {model_version}
- Deployment Mode: {deployment_mode}

FAVES Gates:
{json.dumps(faves_info, indent=2)}

Evidence location: evidence/models/{model_version}/

Steps:
1. For each FAVES gate (Fair, Appropriate, Valid, Effective, Safe):
   - Check if all required artifacts exist in evidence folder
   - Verify artifact content meets requirements
   - Rate gate: "pass", "fail", or "waived" (for DEMO mode only)
2. Generate FAVES assessment report
3. For LIVE deployments: ALL gates must pass
4. For DEMO deployments: Failed gates are advisory warnings
5. Save results to evidence/models/{model_version}/faves_assessment.json
6. Update Model Registry with FAVES status
7. If any gate fails for LIVE deployment:
   - Block deployment
   - Create GitHub issue with failures
   - List specific remediation steps

Repository: {self.github_repo}"""
        })

        return result

    def generate_hti1_disclosure(
        self,
        model_id: str,
        model_version: str
    ) -> Dict[str, Any]:
        """Generate HTI-1 compliant source attribute disclosure"""
        logger.info(f"Generating HTI-1 disclosure for model: {model_id}")

        result = self.agent.invoke({
            "input": f"""Generate HTI-1 Source Attribute Disclosure:

Model: {model_id}
Version: {model_version}

Steps:
1. Fetch model metadata from Model Registry in Notion
2. Fetch validation results from evidence/models/{model_version}/
3. Generate disclosure document with:
   - Basic Information (name, version, intended use)
   - Source Attributes (developer, training data, demographics)
   - Performance Characteristics (metrics, limitations, contraindications)
   - Fairness Assessment (demographic testing, subgroup performance)
   - Updates and Monitoring (version history, monitoring plan)
4. Format in markdown per HTI-1 requirements
5. Save to evidence/models/{model_version}/hti1_disclosure.md
6. Commit to GitHub repository

Repository: {self.github_repo}

Ensure all required HTI-1 fields are included and properly formatted."""
        })

        return result

    def run_full_compliance_audit(
        self,
        model_id: str,
        model_version: str,
        deployment_mode: str = "DEMO"
    ) -> Dict[str, Any]:
        """Run complete compliance audit for a model"""
        logger.info(f"Running full compliance audit for: {model_id} v{model_version}")

        result = self.agent.invoke({
            "input": f"""Run complete compliance audit:

Model: {model_id}
Version: {model_version}
Deployment Mode: {deployment_mode}

Execute all compliance validations:

1. TRIPOD+AI Validation:
   - Check all 27 checklist items
   - Document gaps and recommendations

2. FAVES Gate Validation:
   - Fair: Check subgroup performance audit
   - Appropriate: Check intended use documentation
   - Valid: Check validation methodology
   - Effective: Check outcome metrics
   - Safe: Check monitoring and rollback plans

3. HTI-1 Disclosure Generation:
   - Generate source attribute disclosure
   - Include all required transparency fields

4. Summary Report:
   - Overall compliance status
   - Critical gaps requiring attention
   - Deployment readiness assessment
   - Timeline for gap remediation

5. Notion Updates:
   - Update Model Registry with compliance status
   - Link all generated artifacts

6. GitHub Issues:
   - Create issues for each compliance gap
   - Add labels: "compliance", "priority:high"
   - Assign to appropriate team members

Repository: {self.github_repo}

For LIVE deployments: Block if any FAVES gate fails.
For DEMO deployments: Allow with warnings for failed gates."""
        })

        return result

    def create_compliance_issues(
        self,
        model_id: str,
        gaps: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """Create GitHub issues for compliance gaps"""
        logger.info(f"Creating compliance issues for model: {model_id}")

        gaps_json = json.dumps(gaps, indent=2)

        result = self.agent.invoke({
            "input": f"""Create GitHub issues for compliance gaps:

Model: {model_id}
Gaps:
{gaps_json}

For each gap, create a GitHub issue with:
- Title: "[Compliance] {gap_type}: {brief_description}"
- Labels: "compliance", "from-audit", priority label
- Body including:
  - Description of the gap
  - Compliance framework reference (TRIPOD+AI/FAVES/etc.)
  - Required remediation steps
  - Due date recommendation
  - Link to Model Registry entry

Repository: {self.github_repo}"""
        })

        return result

    def run(self, task: str) -> Dict[str, Any]:
        """Run the agent with a custom task"""
        return self.agent.invoke({"input": task})


def main():
    """Demo the Compliance agent"""
    print("📋 Compliance Agent - Regulatory Compliance Automation")
    print("=" * 60)

    # Check for required environment variables
    if not os.getenv("COMPOSIO_API_KEY"):
        print("⚠️  Set COMPOSIO_API_KEY environment variable")
        return
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  Set OPENAI_API_KEY environment variable")
        return

    agent = ComplianceAgent()

    # List available tools
    print("\n📦 Available tools:")
    for tool in agent.tools:
        print(f"  - {tool.name}")

    # Show FAVES gates
    print("\n🚦 FAVES Gates:")
    for name, gate in FAVES_GATES.items():
        print(f"  - {name}: {gate.description}")

    # Example task
    print("\n🚀 Running example task...")
    result = agent.run(
        "Search for models in the Model Registry that need compliance review"
    )
    print(f"\n📋 Result: {result['output']}")


if __name__ == "__main__":
    main()
