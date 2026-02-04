"""
Results Section Generator for IMRaD Manuscripts
Generates narrative results from statistical outputs and visualizations.
"""

import logging
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum

from langchain_core.prompts import ChatPromptTemplate
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)


class ResultType(Enum):
    """Types of results to report."""

    PRIMARY_OUTCOME = "primary_outcome"
    SECONDARY_OUTCOME = "secondary_outcome"
    SUBGROUP_ANALYSIS = "subgroup_analysis"
    SENSITIVITY_ANALYSIS = "sensitivity_analysis"
    ADVERSE_EVENTS = "adverse_events"
    FLOW_DIAGRAM = "flow_diagram"


@dataclass
class StatisticalResult:
    """A single statistical result."""

    name: str
    result_type: ResultType
    estimate: float
    ci_lower: Optional[float] = None
    ci_upper: Optional[float] = None
    p_value: Optional[float] = None
    effect_size: Optional[float] = None
    effect_size_type: Optional[str] = None  # Cohen's d, OR, HR, RR, etc.
    n_intervention: Optional[int] = None
    n_control: Optional[int] = None
    units: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class TableReference:
    """Reference to a table in the manuscript."""

    table_number: int
    title: str
    description: str


@dataclass
class FigureReference:
    """Reference to a figure in the manuscript."""

    figure_number: int
    title: str
    description: str
    figure_type: str  # forest_plot, flow_diagram, kaplan_meier, etc.


@dataclass
class ResultsInput:
    """Input data for results generation."""

    study_type: str
    sample_size_analyzed: int
    primary_results: List[StatisticalResult]
    secondary_results: List[StatisticalResult] = field(default_factory=list)
    subgroup_results: List[StatisticalResult] = field(default_factory=list)
    sensitivity_results: List[StatisticalResult] = field(default_factory=list)
    adverse_events: Optional[Dict[str, Any]] = None
    flow_data: Optional[Dict[str, int]] = None  # screened, eligible, randomized, analyzed
    tables: List[TableReference] = field(default_factory=list)
    figures: List[FigureReference] = field(default_factory=list)
    follow_up_completion: Optional[float] = None
    missing_data_summary: Optional[str] = None


@dataclass
class ResultsOutput:
    """Generated results section output."""

    text: str
    word_count: int
    sections: Dict[str, str]
    table_references: List[str]
    figure_references: List[str]
    statistical_statements: List[str]
    transparency_log: Dict[str, Any]


class StatFormatter:
    """Utility class for formatting statistical results."""

    @staticmethod
    def format_p_value(p: float, threshold: float = 0.001) -> str:
        """Format p-value according to APA guidelines."""

        if p < threshold:
            return f"p < {threshold}"
        return f"p = {p:.3f}"

    @staticmethod
    def format_ci(lower: float, upper: float, level: int = 95) -> str:
        """Format confidence interval."""

        return f"{level}% CI [{lower:.2f}, {upper:.2f}]"

    @staticmethod
    def format_effect_size(value: float, es_type: str) -> str:
        """Format effect size with type."""

        type_labels = {
            "cohens_d": "d",
            "or": "OR",
            "hr": "HR",
            "rr": "RR",
            "r": "r",
            "eta_squared": "η²",
        }
        label = type_labels.get(es_type.lower(), es_type)
        return f"{label} = {value:.2f}"

    @staticmethod
    def format_result(result: StatisticalResult) -> str:
        """Format a complete statistical result for narrative."""

        parts: List[str] = []

        if result.units:
            parts.append(f"{result.estimate:.2f} {result.units}")
        else:
            parts.append(f"{result.estimate:.2f}")

        if result.ci_lower is not None and result.ci_upper is not None:
            parts.append(StatFormatter.format_ci(result.ci_lower, result.ci_upper))

        if result.p_value is not None:
            parts.append(StatFormatter.format_p_value(result.p_value))

        if result.effect_size is not None and result.effect_size_type:
            parts.append(
                StatFormatter.format_effect_size(result.effect_size, result.effect_size_type)
            )

        return ", ".join(parts)


class ResultsGenerator:
    """
    Generates results sections for research manuscripts.

    Formats statistical outputs into narrative text with proper
    table/figure references and statistical reporting.
    """

    def __init__(
        self,
        model_provider: str = "anthropic",
        model_name: str = "claude-sonnet-4-20250514",
        temperature: float = 0.2,
    ):
        self.model_provider = model_provider
        self.model_name = model_name
        self.temperature = temperature
        self.formatter = StatFormatter()
        self._init_llm()

    def _init_llm(self):
        """Initialize the language model."""

        if self.model_provider == "anthropic":
            self.llm = ChatAnthropic(
                model=self.model_name,
                temperature=self.temperature,
                max_tokens=4000,
            )
        elif self.model_provider == "openai":
            self.llm = ChatOpenAI(
                model=self.model_name,
                temperature=self.temperature,
                max_tokens=4000,
            )
        else:
            raise ValueError(f"Unsupported model provider: {self.model_provider}")

    def _format_flow_diagram_text(self, flow_data: Dict[str, int]) -> str:
        """Generate CONSORT flow diagram narrative."""

        text_parts: List[str] = []

        if "screened" in flow_data:
            text_parts.append(
                f"{flow_data['screened']} individuals were screened for eligibility"
            )
        if "excluded" in flow_data:
            text_parts.append(f"{flow_data['excluded']} were excluded")
        if "randomized" in flow_data:
            text_parts.append(f"{flow_data['randomized']} were randomized")
        if "intervention_allocated" in flow_data and "control_allocated" in flow_data:
            text_parts.append(
                f"{flow_data['intervention_allocated']} allocated to intervention and "
                f"{flow_data['control_allocated']} to control"
            )
        if "analyzed_intervention" in flow_data and "analyzed_control" in flow_data:
            text_parts.append(
                f"{flow_data['analyzed_intervention']} in intervention and "
                f"{flow_data['analyzed_control']} in control were included in the primary analysis"
            )

        return ". ".join(text_parts) + "." if text_parts else ""

    def _create_prompt(self) -> ChatPromptTemplate:
        """Create the results generation prompt."""

        template = """You are a scientific writing expert specializing in results sections.
Generate a comprehensive Results section for a research manuscript.

STRICT REQUIREMENTS:
- Write in past tense
- Report exact statistics as provided (do not round or modify)
- Reference tables and figures by number
- Present results in logical order: participant flow, primary outcomes, secondary outcomes, subgroup analyses
- Use precise scientific language
- Do not interpret results (save for Discussion)

STUDY DATA:
Study Type: {study_type}
Sample Size Analyzed: {sample_size}
Follow-up Completion: {follow_up_completion}

PARTICIPANT FLOW:
{flow_text}

PRIMARY OUTCOMES:
{primary_results}

SECONDARY OUTCOMES:
{secondary_results}

SUBGROUP ANALYSES:
{subgroup_results}

SENSITIVITY ANALYSES:
{sensitivity_results}

ADVERSE EVENTS:
{adverse_events}

TABLES:
{tables}

FIGURES:
{figures}

Generate the Results section with clear subsection headers. Reference all tables and figures appropriately."""

        return ChatPromptTemplate.from_template(template)

    def _format_results_list(self, results: List[StatisticalResult]) -> str:
        """Format a list of results for the prompt."""

        if not results:
            return "None reported"

        formatted: List[str] = []
        for r in results:
            stat_str = self.formatter.format_result(r)
            formatted.append(f"- {r.name}: {stat_str}")
            if r.notes:
                formatted.append(f"  Note: {r.notes}")

        return "\n".join(formatted)

    def _extract_references(self, text: str) -> tuple:
        """Extract table and figure references from generated text."""

        import re

        table_refs = re.findall(r"Table\s+(\d+)", text, re.IGNORECASE)
        figure_refs = re.findall(r"Figure\s+(\d+)", text, re.IGNORECASE)

        return (
            [f"Table {n}" for n in sorted(set(table_refs))],
            [f"Figure {n}" for n in sorted(set(figure_refs))],
        )

    def _extract_statistical_statements(self, text: str) -> List[str]:
        """Extract statistical statements from the text."""

        import re

        patterns = [
            r"[^.]*p\s*[<=]\s*[\d.]+[^.]*\.",
            r"[^.]*\d+%\s*CI\s*\[[^\]]+\][^.]*\.",
            r"[^.]*(?:OR|HR|RR|d)\s*=\s*[\d.]+[^.]*\.",
        ]

        statements: List[str] = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            statements.extend([m.strip() for m in matches])

        return list(set(statements))

    async def generate(self, input_data: ResultsInput) -> ResultsOutput:
        """
        Generate a results section from statistical outputs.

        Args:
            input_data: Statistical results and references

        Returns:
            ResultsOutput with generated results section
        """

        prompt = self._create_prompt()

        flow_text = ""
        if input_data.flow_data:
            flow_text = self._format_flow_diagram_text(input_data.flow_data)

        tables_text = (
            "\n".join(f"- Table {t.table_number}: {t.title}" for t in input_data.tables)
            or "None"
        )

        figures_text = (
            "\n".join(
                f"- Figure {f.figure_number}: {f.title} ({f.figure_type})"
                for f in input_data.figures
            )
            or "None"
        )

        transparency_log = {
            "model_provider": self.model_provider,
            "model_name": self.model_name,
            "temperature": self.temperature,
            "n_primary_results": len(input_data.primary_results),
            "n_secondary_results": len(input_data.secondary_results),
            "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
        }

        try:
            chain = prompt | self.llm
            response = await chain.ainvoke(
                {
                    "study_type": input_data.study_type,
                    "sample_size": input_data.sample_size_analyzed,
                    "follow_up_completion": (
                        f"{input_data.follow_up_completion:.1f}%"
                        if input_data.follow_up_completion
                        else "Not reported"
                    ),
                    "flow_text": flow_text or "Not applicable",
                    "primary_results": self._format_results_list(input_data.primary_results),
                    "secondary_results": self._format_results_list(
                        input_data.secondary_results
                    ),
                    "subgroup_results": self._format_results_list(input_data.subgroup_results),
                    "sensitivity_results": self._format_results_list(
                        input_data.sensitivity_results
                    ),
                    "adverse_events": (
                        str(input_data.adverse_events)
                        if input_data.adverse_events
                        else "None reported"
                    ),
                    "tables": tables_text,
                    "figures": figures_text,
                }
            )

            results_text = response.content
            transparency_log["success"] = True

        except Exception as e:
            logger.error(f"Results generation failed: {e}")
            transparency_log["success"] = False
            transparency_log["error"] = str(e)
            raise

        table_refs, figure_refs = self._extract_references(results_text)
        stat_statements = self._extract_statistical_statements(results_text)

        return ResultsOutput(
            text=results_text,
            word_count=len(results_text.split()),
            sections=self._parse_sections(results_text),
            table_references=table_refs,
            figure_references=figure_refs,
            statistical_statements=stat_statements,
            transparency_log=transparency_log,
        )

    def _parse_sections(self, text: str) -> Dict[str, str]:
        """Parse results into sections."""

        sections: Dict[str, str] = {}
        section_markers = [
            "Participant Flow",
            "Primary Outcome",
            "Secondary Outcome",
            "Subgroup",
            "Sensitivity",
            "Adverse Events",
        ]

        lowered = text.lower()
        for marker in section_markers:
            m_lower = marker.lower()
            if m_lower in lowered:
                start = lowered.find(m_lower)
                sections[marker] = text[start : start + 500]

        return sections


def create_results_generator(model_provider: str = "anthropic", **kwargs) -> ResultsGenerator:
    """Factory function to create a ResultsGenerator instance."""

    return ResultsGenerator(model_provider=model_provider, **kwargs)
