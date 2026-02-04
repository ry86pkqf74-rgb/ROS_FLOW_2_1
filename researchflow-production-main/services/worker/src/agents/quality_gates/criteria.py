"""
Quality Gate Criteria Definitions for LangGraph Agents.

Defines pass/fail criteria for each agent's quality gate.
Each agent evaluates these criteria before allowing output to pass
to the next stage or triggering improvement loops.

See: Linear ROS-66, ROS-67 (Phase C & D)
"""

from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum


class Severity(Enum):
    """Severity levels for quality gate failures."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class QualityCriterion:
    """
    A single quality criterion for gate evaluation.

    Attributes:
        name: Criterion identifier
        description: Human-readable description
        threshold: Pass threshold value
        severity: Failure severity level
        required: Whether this criterion must pass for gate to pass
        evaluation_fn: Optional custom evaluation function
    """
    name: str
    description: str
    threshold: Any
    severity: Severity = Severity.WARNING
    required: bool = True
    evaluation_fn: Optional[Callable[[str, Any], tuple[bool, float]]] = None


@dataclass
class QualityGateCriteria:
    """
    Complete set of criteria for an agent's quality gate.

    Attributes:
        agent_id: Agent this criteria applies to
        criteria: List of quality criteria
        min_score: Minimum overall score to pass (0-1)
        require_all_critical: Whether all critical criteria must pass
    """
    agent_id: str
    criteria: List[QualityCriterion] = field(default_factory=list)
    min_score: float = 0.7
    require_all_critical: bool = True


# =============================================================================
# DataPrep Agent Criteria (Stages 1-5)
# =============================================================================

DATAPREP_CRITERIA = QualityGateCriteria(
    agent_id='dataprep',
    min_score=0.7,
    criteria=[
        QualityCriterion(
            name='min_rows',
            description='Minimum rows for meaningful analysis',
            threshold=30,
            severity=Severity.ERROR,
            required=True,
        ),
        QualityCriterion(
            name='max_missing_percent',
            description='Maximum percentage of missing values allowed',
            threshold=20,
            severity=Severity.WARNING,
            required=False,
        ),
        QualityCriterion(
            name='schema_valid',
            description='Data passes schema validation',
            threshold=True,
            severity=Severity.ERROR,
            required=True,
        ),
        QualityCriterion(
            name='variables_selected',
            description='At least one variable selected for analysis',
            threshold=True,
            severity=Severity.CRITICAL,
            required=True,
        ),
        QualityCriterion(
            name='cohort_defined',
            description='Cohort inclusion/exclusion criteria specified',
            threshold=True,
            severity=Severity.CRITICAL,
            required=True,
        ),
        QualityCriterion(
            name='phi_clean',
            description='No PHI detected in output',
            threshold=True,
            severity=Severity.CRITICAL,
            required=True,
        ),
    ],
)


# =============================================================================
# Analysis Agent Criteria (Stages 6-9)
# =============================================================================

ANALYSIS_CRITERIA = QualityGateCriteria(
    agent_id='analysis',
    min_score=0.75,
    criteria=[
        QualityCriterion(
            name='method_justified',
            description='Statistical method selection is justified',
            threshold=True,
            severity=Severity.ERROR,
            required=True,
        ),
        QualityCriterion(
            name='assumptions_checked',
            description='Statistical assumptions were verified',
            threshold=True,
            severity=Severity.ERROR,
            required=True,
        ),
        QualityCriterion(
            name='p_value_threshold',
            description='Primary p-value below significance threshold',
            threshold=0.05,
            severity=Severity.INFO,
            required=False,  # Not required - non-significant results are valid
        ),
        QualityCriterion(
            name='effect_size_reported',
            description='Effect sizes are included',
            threshold=True,
            severity=Severity.WARNING,
            required=True,
        ),
        QualityCriterion(
            name='confidence_intervals',
            description='Confidence intervals are reported',
            threshold=True,
            severity=Severity.WARNING,
            required=True,
        ),
        QualityCriterion(
            name='sample_size_adequate',
            description='Sample size considerations addressed',
            threshold=True,
            severity=Severity.WARNING,
            required=False,
        ),
        QualityCriterion(
            name='interpretation_appropriate',
            description='Statistical interpretation is appropriate and not overclaimed',
            threshold=True,
            severity=Severity.ERROR,
            required=True,
        ),
    ],
)


# =============================================================================
# Quality Agent Criteria (Stages 10-12)
# =============================================================================

QUALITY_CRITERIA = QualityGateCriteria(
    agent_id='quality',
    min_score=0.8,  # Higher threshold for quality checks
    criteria=[
        QualityCriterion(
            name='sensitivity_performed',
            description='At least one sensitivity analysis conducted',
            threshold=True,
            severity=Severity.ERROR,
            required=True,
        ),
        QualityCriterion(
            name='bias_assessed',
            description='Bias assessment completed',
            threshold=True,
            severity=Severity.ERROR,
            required=True,
        ),
        QualityCriterion(
            name='reproducibility_score',
            description='Reproducibility documentation score',
            threshold=0.8,
            severity=Severity.WARNING,
            required=False,
        ),
        QualityCriterion(
            name='strobe_compliance',
            description='STROBE checklist compliance percentage',
            threshold=0.7,
            severity=Severity.WARNING,
            required=False,
        ),
        QualityCriterion(
            name='documentation_complete',
            description='Methods and analysis fully documented',
            threshold=True,
            severity=Severity.ERROR,
            required=True,
        ),
        QualityCriterion(
            name='figures_generated',
            description='Required figures have been specified',
            threshold=True,
            severity=Severity.WARNING,
            required=False,
        ),
        QualityCriterion(
            name='tables_generated',
            description='Required tables have been specified',
            threshold=True,
            severity=Severity.WARNING,
            required=False,
        ),
    ],
)


# =============================================================================
# IRB Agent Criteria (Stages 13-14)
# =============================================================================

IRB_CRITERIA = QualityGateCriteria(
    agent_id='irb',
    min_score=0.9,  # Highest threshold for IRB compliance
    require_all_critical=True,
    criteria=[
        QualityCriterion(
            name='risk_assessed',
            description='Risk assessment completed',
            threshold=True,
            severity=Severity.CRITICAL,
            required=True,
        ),
        QualityCriterion(
            name='phi_addressed',
            description='PHI protection measures documented',
            threshold=True,
            severity=Severity.CRITICAL,
            required=True,
        ),
        QualityCriterion(
            name='consent_complete',
            description='Informed consent form includes all required elements',
            threshold=True,
            severity=Severity.CRITICAL,
            required=True,
        ),
        QualityCriterion(
            name='protocol_complete',
            description='IRB protocol contains all required sections',
            threshold=True,
            severity=Severity.CRITICAL,
            required=True,
        ),
        QualityCriterion(
            name='vulnerable_pop_addressed',
            description='Vulnerable populations protections considered',
            threshold=True,
            severity=Severity.ERROR,
            required=True,
        ),
        QualityCriterion(
            name='human_reviewed',
            description='Human review completed (MANDATORY)',
            threshold=True,
            severity=Severity.CRITICAL,
            required=True,
        ),
        QualityCriterion(
            name='regulatory_compliance',
            description='Regulatory requirements addressed',
            threshold=True,
            severity=Severity.CRITICAL,
            required=True,
        ),
    ],
)


# =============================================================================
# Manuscript Agent Criteria (Stages 15-20)
# =============================================================================

MANUSCRIPT_CRITERIA = QualityGateCriteria(
    agent_id='manuscript',
    min_score=0.75,
    criteria=[
        QualityCriterion(
            name='introduction_complete',
            description='Introduction section drafted',
            threshold=True,
            severity=Severity.ERROR,
            required=True,
        ),
        QualityCriterion(
            name='methods_complete',
            description='Methods section drafted',
            threshold=True,
            severity=Severity.ERROR,
            required=True,
        ),
        QualityCriterion(
            name='results_complete',
            description='Results section drafted',
            threshold=True,
            severity=Severity.ERROR,
            required=True,
        ),
        QualityCriterion(
            name='discussion_complete',
            description='Discussion section drafted',
            threshold=True,
            severity=Severity.ERROR,
            required=True,
        ),
        QualityCriterion(
            name='citation_count',
            description='Minimum number of citations',
            threshold=10,
            severity=Severity.WARNING,
            required=False,
        ),
        QualityCriterion(
            name='word_limit',
            description='Total word count within limit',
            threshold=5000,
            severity=Severity.WARNING,
            required=False,
        ),
        QualityCriterion(
            name='abstract_word_limit',
            description='Abstract word count within limit',
            threshold=300,
            severity=Severity.WARNING,
            required=True,
        ),
        QualityCriterion(
            name='imrad_structure',
            description='Follows IMRaD structure',
            threshold=True,
            severity=Severity.ERROR,
            required=True,
        ),
        QualityCriterion(
            name='claims_supported',
            description='All claims are supported by data or citations',
            threshold=True,
            severity=Severity.ERROR,
            required=True,
        ),
    ],
)


# =============================================================================
# Quality Gate Registry
# =============================================================================

QUALITY_GATE_REGISTRY: Dict[str, QualityGateCriteria] = {
    'dataprep': DATAPREP_CRITERIA,
    'analysis': ANALYSIS_CRITERIA,
    'quality': QUALITY_CRITERIA,
    'irb': IRB_CRITERIA,
    'manuscript': MANUSCRIPT_CRITERIA,
}


def get_criteria_for_agent(agent_id: str) -> QualityGateCriteria:
    """
    Get quality criteria for a specific agent.

    Args:
        agent_id: Agent identifier

    Returns:
        QualityGateCriteria for the agent

    Raises:
        ValueError: If agent_id is not recognized
    """
    if agent_id not in QUALITY_GATE_REGISTRY:
        raise ValueError(f"Unknown agent: {agent_id}. Valid agents: {list(QUALITY_GATE_REGISTRY.keys())}")
    return QUALITY_GATE_REGISTRY[agent_id]


def evaluate_quality_gate(
    agent_id: str,
    output: str,
    state: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Evaluate quality gate criteria for an agent output.

    Args:
        agent_id: Agent identifier
        output: Agent output to evaluate
        state: Current agent state

    Returns:
        Dict containing:
        - passed: Whether the gate passed
        - score: Overall score (0-1)
        - criteria_results: Individual criterion results
        - criteria_failed: List of failed criteria names
        - reason: Human-readable explanation
    """
    criteria = get_criteria_for_agent(agent_id)

    results = []
    failed = []
    total_weight = 0
    weighted_score = 0

    for criterion in criteria.criteria:
        # Weight critical criteria higher
        weight = 2.0 if criterion.severity == Severity.CRITICAL else 1.0
        total_weight += weight

        # Evaluate criterion
        passed, score = _evaluate_single_criterion(criterion, output, state)

        result = {
            'name': criterion.name,
            'description': criterion.description,
            'passed': passed,
            'score': score,
            'severity': criterion.severity.value,
            'required': criterion.required,
        }
        results.append(result)

        if not passed and criterion.required:
            failed.append(criterion.name)

        weighted_score += score * weight

    # Calculate overall score
    overall_score = weighted_score / total_weight if total_weight > 0 else 0

    # Determine if gate passed
    gate_passed = (
        overall_score >= criteria.min_score and
        len(failed) == 0
    )

    # If require_all_critical, check that all critical criteria passed
    if criteria.require_all_critical and not gate_passed:
        critical_failed = [
            r['name'] for r in results
            if r['severity'] == Severity.CRITICAL.value and not r['passed']
        ]
        if critical_failed:
            gate_passed = False
            failed.extend(critical_failed)

    # Generate reason
    if gate_passed:
        reason = f"Quality gate passed with score {overall_score:.2f}"
    else:
        reason = f"Quality gate failed. Score: {overall_score:.2f}. Failed criteria: {', '.join(set(failed))}"

    return {
        'passed': gate_passed,
        'score': overall_score,
        'criteria_results': results,
        'criteria_failed': list(set(failed)),
        'reason': reason,
        'min_score': criteria.min_score,
    }


def _evaluate_single_criterion(
    criterion: QualityCriterion,
    output: str,
    state: Dict[str, Any],
) -> tuple[bool, float]:
    """
    Evaluate a single criterion.

    Args:
        criterion: Criterion to evaluate
        output: Agent output
        state: Agent state

    Returns:
        Tuple of (passed, score)
    """
    # Use custom evaluation function if provided
    if criterion.evaluation_fn:
        return criterion.evaluation_fn(output, criterion.threshold)

    # Default evaluation based on criterion name
    output_lower = output.lower()

    # Boolean thresholds
    if isinstance(criterion.threshold, bool):
        # Look for indicators based on criterion name
        indicators = _get_indicators_for_criterion(criterion.name)
        found = any(ind in output_lower for ind in indicators)
        return found == criterion.threshold, 1.0 if found == criterion.threshold else 0.0

    # Numeric thresholds
    if isinstance(criterion.threshold, (int, float)):
        import re

        # Try to extract relevant number from output
        pattern = _get_pattern_for_criterion(criterion.name)
        matches = re.findall(pattern, output_lower)

        if matches:
            try:
                value = float(matches[0])
                # Check if it's a maximum or minimum threshold
                if criterion.name.startswith('max_') or criterion.name.endswith('_limit'):
                    passed = value <= criterion.threshold
                    score = 1.0 - (value / criterion.threshold) if passed else 0.0
                else:
                    passed = value >= criterion.threshold
                    score = min(1.0, value / criterion.threshold) if criterion.threshold > 0 else 1.0
                return passed, max(0, min(1, score))
            except (ValueError, IndexError):
                pass

        # Can't determine - give partial score
        return True, 0.7

    return True, 0.5


def _get_indicators_for_criterion(name: str) -> List[str]:
    """Get search indicators for a boolean criterion."""
    indicator_map = {
        'schema_valid': ['valid', 'passed', 'no errors', 'schema matches'],
        'variables_selected': ['variable', 'outcome', 'predictor', 'exposure'],
        'cohort_defined': ['inclusion', 'exclusion', 'cohort', 'criteria'],
        'phi_clean': ['no phi', 'phi free', 'deidentified'],
        'method_justified': ['because', 'since', 'rationale', 'justified'],
        'assumptions_checked': ['normality', 'homoscedasticity', 'assumption'],
        'effect_size_reported': ['effect size', "cohen's d", 'odds ratio'],
        'confidence_intervals': ['confidence interval', '95% ci', 'ci:'],
        'sensitivity_performed': ['sensitivity', 'robustness'],
        'bias_assessed': ['bias', 'confounding', 'selection'],
        'documentation_complete': ['documented', 'specified', 'described'],
        'introduction_complete': ['introduction', 'background', 'objective'],
        'methods_complete': ['method', 'design', 'participant', 'statistical'],
        'results_complete': ['result', 'finding', 'outcome', 'table', 'figure'],
        'discussion_complete': ['discussion', 'limitation', 'implication'],
        'imrad_structure': ['introduction', 'method', 'result', 'discussion'],
        'human_reviewed': ['approved', 'reviewed', 'confirmed'],
    }
    return indicator_map.get(name, [name.replace('_', ' ')])


def _get_pattern_for_criterion(name: str) -> str:
    """Get regex pattern for extracting numeric values for a criterion."""
    pattern_map = {
        'min_rows': r'(\d+)\s*(?:row|record|subject|participant)',
        'max_missing_percent': r'(\d+(?:\.\d+)?)\s*%?\s*(?:missing|null)',
        'p_value_threshold': r'p\s*[=<>]\s*(\d+\.?\d*)',
        'reproducibility_score': r'reproducibility.*?(\d+)',
        'strobe_compliance': r'compliance.*?(\d+)',
        'citation_count': r'(\d+)\s*(?:citation|reference)',
        'word_limit': r'(\d+)\s*(?:word)',
        'abstract_word_limit': r'abstract.*?(\d+)\s*word',
    }
    return pattern_map.get(name, r'(\d+\.?\d*)')
