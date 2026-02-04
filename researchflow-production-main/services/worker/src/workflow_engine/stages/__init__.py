"""
Workflow Stages

This module imports all stage implementations to ensure they are
registered with the stage registry on module load.

Stage numbering: Main pipeline uses stages 1-20. Supplementary stages use
letter suffixes (e.g. 4a = Schema Validation) and do not replace the main number.

Available stages:
- Stage 01: Data Ingestion - multi-format file reading, metadata extraction, quality profiling, study type detection
- Stage 02: Literature Review - automated literature search and summary
- Stage 03: IRB Compliance Check
- Stage 04: Hypothesis Refinement - refine research questions based on literature (HypothesisRefinerAgent)
- Stage 4a: Schema Validation - supplementary; validates data structure before PHI scanning
- Stage 05: PHI Scan - detect protected health information
- Stage 06: Study Design - study protocol, methodology, endpoints, sample size, methods outline
- Stage 07: Statistical Modeling - build and validate statistical models
- Stage 08: Data Validation - quality checks
- Stage 09: Interpretation - collaborative result interpretation
- Stage 10: Validation - research validation checklist
- Stage 11: Iteration - analysis iteration with AI routing
- Stage 12: Manuscript Drafting - complete manuscript generation with IMRaD structure
- Stage 13: Internal Review - AI-powered peer review simulation
- Stage 14: Ethical Review - compliance and ethical verification
- Stage 15: Artifact Bundling - package artifacts for sharing/archiving
- Stage 16: Collaboration Handoff - share with collaborators
- Stage 17: Archiving - long-term project archiving
- Stage 18: Impact Assessment - research impact metrics tracking
- Stage 19: Dissemination - publication and sharing preparation
- Stage 20: Conference Report - final output generation
"""

# Export base class
from .base_stage_agent import BaseStageAgent

# Import all stage modules to trigger registration
# Note: Stage 1 registration is handled conditionally based on feature flag
from . import stage_01_upload  # Legacy implementation
from . import stage_01_protocol_design  # New PICO-based implementation
from . import stage_02_literature
from . import stage_03_irb
from . import stage_04_hypothesis
from . import stage_04_validation
from . import stage_04a_schema_validate
from . import stage_05_phi
from . import stage_06_study_design
from . import stage_07_stats
from . import stage_08_validation
from . import stage_09_interpretation
from . import stage_10_validation
from . import stage_11_iteration
from . import stage_12_manuscript
from . import stage_13_internal_review
from . import stage_14_ethical
from . import stage_15_bundling
from . import stage_16_handoff
from . import stage_17_archiving
from . import stage_18_impact
from . import stage_19_dissemination
from . import stage_20_conference

from ..registry import get_stage

# TODO: Set up conditional Stage 1 registration based on feature flag
# setup_stage_1_registration()  # Temporarily disabled for testing

# Map stage_id -> Stage class for main pipeline (1-20); supplementary (e.g. 4a) in registry but not in this map
STAGE_REGISTRY = {i: get_stage(i) for i in range(1, 21) if get_stage(i) is not None}

__all__ = [
    # Registry
    "STAGE_REGISTRY",
    # Base class
    "BaseStageAgent",
    # Stage modules
    "stage_01_upload",
    "stage_01_protocol_design",
    "stage_02_literature",
    "stage_03_irb",
    "stage_04_hypothesis",
    "stage_04_validation",
    "stage_04a_schema_validate",
    "stage_05_phi",
    "stage_06_study_design",
    "stage_07_stats",
    "stage_08_validation",
    "stage_09_interpretation",
    "stage_10_validation",
    "stage_11_iteration",
    "stage_12_manuscript",
    "stage_13_internal_review",
    "stage_14_ethical",
    "stage_15_bundling",
    "stage_16_handoff",
    "stage_17_archiving",
    "stage_18_impact",
    "stage_19_dissemination",
    "stage_20_conference",
]
