"""
ResearchFlow LangGraph Agents

This module provides the agent registry and factory functions for
the research workflow agents.

Agents:
- DataPrepAgent: Stages 1-2, 4-5 (topic, literature, variables, PHI scanning)
- IRBAgent: Stage 3 (IRB proposal generation)
- AnalysisAgent: Stages 6-9 (schema, scrubbing, validation, statistics)
- QualityAgent: Stages 10-13 (summary, gap analysis, ideation, results interpretation)
- ManuscriptAgent: Stages 14-20 (full manuscript draft, polish, conference prep)
- SpecOpsAgent: Cross-cutting (Notion PRD → GitHub sync)

Stage workers (STAGE_WORKER_SPECS.md):
- ANALYSIS phase (6-11): data collection, validation, gap analysis, synthesis, cross-ref, fact check
- WRITING phase (12-15): outline, draft, revision, final polish
- PUBLISH phase (16-20): formatting, citation generation, quality review, export prep, publish

Linear Issues: ROS-67, ROS-68, ROS-105, ROS-106
"""

from typing import Awaitable, Callable, Dict, Type, Optional, List
from dataclasses import dataclass

from .base_agent import (
    BaseAgent,
    AgentConfig,
    AgentState,
    AgentResult,
    QualityCheckResult,
)
from .dataprep_agent import DataPrepAgent, create_dataprep_agent
from .analysis_agent import AnalysisAgent, create_analysis_agent
from .quality_agent import QualityAgent, create_quality_agent
from .irb_agent import IRBAgent, create_irb_agent
from .manuscript_agent import ManuscriptAgent, create_manuscript_agent
from .spec_ops import SpecOpsAgent, create_spec_ops_agent
from .stage06_data_collection import process as process_stage06
from .stage07_source_validation import process as process_stage07
from .stage08_gap_analysis import process as process_stage08
from .stage09_synthesis import process as process_stage09
from .stage10_cross_reference import process as process_stage10
from .stage11_fact_check import process as process_stage11
from .stage12_outline_generation import process as process_stage12
from .stage13_draft_writing import process as process_stage13
from .stage14_revision import process as process_stage14
from .stage15_final_polish import process as process_stage15
from .stage16_formatting import process as process_stage16
from .stage17_citation_generation import process as process_stage17
from .stage18_quality_review import process as process_stage18
from .stage19_export_prep import process as process_stage19
from .stage20_publish import process as process_stage20

__all__ = [
    # Base classes
    "BaseAgent",
    "AgentConfig",
    "AgentState",
    "AgentResult",
    "QualityCheckResult",
    # Concrete agents
    "DataPrepAgent",
    "AnalysisAgent",
    "QualityAgent",
    "IRBAgent",
    "ManuscriptAgent",
    "SpecOpsAgent",
    # Factory functions
    "create_dataprep_agent",
    "create_analysis_agent",
    "create_quality_agent",
    "create_irb_agent",
    "create_manuscript_agent",
    "create_spec_ops_agent",
    # Registry
    "AGENT_REGISTRY",
    "get_agent_for_stage",
    "get_all_agents",
    # ANALYSIS phase stage workers (Stages 6-11, STAGE_WORKER_SPECS.md)
    "ANALYSIS_PHASE_REGISTRY",
    "get_analysis_stage_process",
    # WRITING phase stage workers (Stages 12-15)
    "WRITING_PHASE_REGISTRY",
    "get_writing_stage_process",
    # PUBLISH phase stage workers (Stages 16-20)
    "PUBLISH_PHASE_REGISTRY",
    "get_publish_stage_process",
    "get_stage_process",
]


@dataclass
class AgentRegistryEntry:
    """Registry entry for an agent."""
    name: str
    description: str
    stages: List[int]
    factory: callable
    agent_class: Type[BaseAgent]


# Agent Registry - maps stages to agents
# Stage mapping aligned with UI workflow (workflowStages.ts):
# 1. Topic Declaration, 2. Literature Search, 3. IRB Proposal, 4. Variable Definition
# 5. PHI Scanning, 6. Schema Extraction, 7. Final Scrubbing, 8. Data Validation
# 9. Summary Characteristics, 10. Literature Gap Analysis, 11. Manuscript Ideation
# 12. Manuscript Selection, 13. Statistical Analysis, 14. Manuscript Drafting
# 15. Polish Manuscript, 16. Submission Readiness, 17. Poster Prep, 18. Symposium
# 19. Presentation Prep, 20. Conference Preparation
AGENT_REGISTRY: Dict[str, AgentRegistryEntry] = {
    "dataprep": AgentRegistryEntry(
        name="DataPrepAgent",
        description="Data validation, cleaning, and preparation",
        stages=[1, 2, 4, 5],  # Stage 3 (IRB) now handled by IRBAgent
        factory=create_dataprep_agent,
        agent_class=DataPrepAgent,
    ),
    "irb": AgentRegistryEntry(
        name="IRBAgent",
        description="IRB proposal generation and compliance",
        stages=[3],  # Stage 3 = IRB Proposal
        factory=create_irb_agent,
        agent_class=IRBAgent,
    ),
    "analysis": AgentRegistryEntry(
        name="AnalysisAgent",
        description="Statistical analysis with assumption checking",
        stages=[6, 7, 8, 9],
        factory=create_analysis_agent,
        agent_class=AnalysisAgent,
    ),
    "quality": AgentRegistryEntry(
        name="QualityAgent",
        description="Figure/table generation, data integrity, and results interpretation",
        stages=[10, 11, 12, 13],  # Stage 13 = Results Interpretation
        factory=create_quality_agent,
        agent_class=QualityAgent,
    ),
    "manuscript": AgentRegistryEntry(
        name="ManuscriptAgent",
        description="IMRaD manuscript writing with citations",
        stages=[14, 15, 16, 17, 18, 19, 20],  # Stage 14 = full manuscript draft
        factory=create_manuscript_agent,
        agent_class=ManuscriptAgent,
    ),
    "spec_ops": AgentRegistryEntry(
        name="SpecOpsAgent",
        description="Notion PRD → GitHub Issues synchronization",
        stages=[],  # Cross-cutting agent, not stage-specific
        factory=create_spec_ops_agent,
        agent_class=SpecOpsAgent,
    ),
}

# Stage to agent mapping
STAGE_AGENT_MAP: Dict[int, str] = {}
for agent_key, entry in AGENT_REGISTRY.items():
    for stage in entry.stages:
        STAGE_AGENT_MAP[stage] = agent_key


# ANALYSIS phase stage workers (Stages 6-11) — async process(workflow_id, stage_data) -> dict
# See docs/stages/STAGE_WORKER_SPECS.md
ProcessStage = Callable[[str, dict], Awaitable[dict]]
ANALYSIS_PHASE_REGISTRY: Dict[int, ProcessStage] = {
    6: process_stage06,
    7: process_stage07,
    8: process_stage08,
    9: process_stage09,
    10: process_stage10,
    11: process_stage11,
}

WRITING_PHASE_REGISTRY: Dict[int, ProcessStage] = {
    12: process_stage12,
    13: process_stage13,
    14: process_stage14,
    15: process_stage15,
}

PUBLISH_PHASE_REGISTRY: Dict[int, ProcessStage] = {
    16: process_stage16,
    17: process_stage17,
    18: process_stage18,
    19: process_stage19,
    20: process_stage20,
}


def get_analysis_stage_process(stage_id: int) -> Optional[ProcessStage]:
    """
    Get the async process function for an ANALYSIS phase stage (6-11).

    Args:
        stage_id: Stage number (6-11)

    Returns:
        Async process(workflow_id, stage_data) -> dict, or None
    """
    return ANALYSIS_PHASE_REGISTRY.get(stage_id)


def get_writing_stage_process(stage_id: int) -> Optional[ProcessStage]:
    """
    Get the async process function for a WRITING phase stage (12-15).

    Args:
        stage_id: Stage number (12-15)

    Returns:
        Async process(workflow_id, stage_data) -> dict, or None
    """
    return WRITING_PHASE_REGISTRY.get(stage_id)


def get_publish_stage_process(stage_id: int) -> Optional[ProcessStage]:
    """
    Get the async process function for a PUBLISH phase stage (16-20).

    Args:
        stage_id: Stage number (16-20)

    Returns:
        Async process(workflow_id, stage_data) -> dict, or None
    """
    return PUBLISH_PHASE_REGISTRY.get(stage_id)


def get_stage_process(stage_id: int) -> Optional[ProcessStage]:
    """
    Get the async process function for ANALYSIS (6-11), WRITING (12-15), or PUBLISH (16-20) stage.

    Args:
        stage_id: Stage number (6-20)

    Returns:
        Async process(workflow_id, stage_data) -> dict, or None
    """
    return (
        get_analysis_stage_process(stage_id)
        or get_writing_stage_process(stage_id)
        or get_publish_stage_process(stage_id)
    )


def get_agent_for_stage(stage_id: int) -> Optional[BaseAgent]:
    """
    Get the appropriate agent for a workflow stage.
    
    Args:
        stage_id: The workflow stage number (1-20)
    
    Returns:
        Instantiated agent or None if no agent handles this stage
    """
    agent_key = STAGE_AGENT_MAP.get(stage_id)
    if agent_key and agent_key in AGENT_REGISTRY:
        return AGENT_REGISTRY[agent_key].factory()
    return None


def get_all_agents() -> Dict[str, BaseAgent]:
    """
    Get instances of all registered agents.
    
    Returns:
        Dictionary mapping agent keys to agent instances
    """
    return {key: entry.factory() for key, entry in AGENT_REGISTRY.items()}


def get_agent_by_name(name: str) -> Optional[BaseAgent]:
    """
    Get an agent by its registry key or class name.
    
    Args:
        name: Agent key (e.g., "dataprep") or class name (e.g., "DataPrepAgent")
    
    Returns:
        Instantiated agent or None
    """
    # Try direct key lookup
    if name in AGENT_REGISTRY:
        return AGENT_REGISTRY[name].factory()
    
    # Try by class name
    for entry in AGENT_REGISTRY.values():
        if entry.name.lower() == name.lower():
            return entry.factory()
    
    return None


def list_agents() -> List[Dict[str, any]]:
    """
    List all registered agents with their metadata.
    
    Returns:
        List of agent info dictionaries
    """
    return [
        {
            "key": key,
            "name": entry.name,
            "description": entry.description,
            "stages": entry.stages,
        }
        for key, entry in AGENT_REGISTRY.items()
    ]
