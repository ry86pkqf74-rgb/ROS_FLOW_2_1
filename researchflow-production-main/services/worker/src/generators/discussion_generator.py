"""
Discussion Section Generator for IMRaD Manuscripts
Generates comprehensive discussion sections with literature synthesis.
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

from langchain_core.prompts import ChatPromptTemplate
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)


class DiscussionStyle(Enum):
    """Discussion section styles."""

    STANDARD = "standard"  # Full discussion
    BRIEF = "brief"  # Short communication
    SYSTEMATIC_REVIEW = "systematic_review"
    COMMENTARY = "commentary"


@dataclass
class KeyFinding:
    """A key finding to discuss."""

    finding: str
    statistical_support: str
    clinical_significance: str
    comparison_to_literature: Optional[str] = None


@dataclass
class LiteratureReference:
    """A reference from the literature review."""

    citation: str
    finding: str
    agreement: str  # 'supports', 'contradicts', 'extends', 'neutral'
    notes: Optional[str] = None


@dataclass
class Limitation:
    """A study limitation."""

    category: str  # 'design', 'sample', 'measurement', 'analysis', 'generalizability'
    description: str
    impact: str  # 'minimal', 'moderate', 'substantial'
    mitigation: Optional[str] = None


@dataclass
class DiscussionInput:
    """Input data for discussion generation."""

    study_type: str
    research_question: str
    hypothesis: str
    key_findings: List[KeyFinding]
    literature_context: List[LiteratureReference]
    limitations: List[Limitation]
    clinical_implications: List[str]
    policy_implications: List[str] = field(default_factory=list)
    future_research: List[str] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)
    unexpected_findings: List[str] = field(default_factory=list)


@dataclass
class DiscussionOutput:
    """Generated discussion section output."""

    text: str
    word_count: int
    sections: Dict[str, str]
    literature_citations_used: List[str]
    completeness_score: float
    suggestions: List[str]
    transparency_log: Dict[str, Any]


class DiscussionGenerator:
    """
    Generates discussion sections for research manuscripts.

    Synthesizes findings with literature, acknowledges limitations,
    and suggests implications and future directions.
    """

    SECTION_STRUCTURE = [
        "Principal Findings",
        "Comparison with Literature",
        "Strengths and Limitations",
        "Clinical Implications",
        "Future Research",
        "Conclusions",
    ]

    def __init__(
        self,
        model_provider: str = "anthropic",
        model_name: str = "claude-sonnet-4-20250514",
        temperature: float = 0.3,
    ):
        self.model_provider = model_provider
        self.model_name = model_name
        self.temperature = temperature
        self._init_llm()

    def _init_llm(self):
        """Initialize the language model."""

        if self.model_provider == "anthropic":
            self.llm = ChatAnthropic(
                model=self.model_name,
                temperature=self.temperature,
                max_tokens=5000,
            )
        elif self.model_provider == "openai":
            self.llm = ChatOpenAI(
                model=self.model_name,
                temperature=self.temperature,
                max_tokens=5000,
            )
        else:
            raise ValueError(f"Unsupported model provider: {self.model_provider}")

    def _format_findings(self, findings: List[KeyFinding]) -> str:
        """Format key findings for the prompt."""

        formatted: List[str] = []
        for i, f in enumerate(findings, 1):
            formatted.append(
                f"""Finding {i}: {f.finding}
  - Statistical support: {f.statistical_support}
  - Clinical significance: {f.clinical_significance}
  - Literature comparison: {f.comparison_to_literature or 'Not yet compared'}"""
            )
        return "\n\n".join(formatted)

    def _format_literature(self, refs: List[LiteratureReference]) -> str:
        """Format literature references for synthesis."""

        if not refs:
            return "No literature references provided"

        grouped: Dict[str, List[LiteratureReference]] = {
            "supports": [],
            "contradicts": [],
            "extends": [],
            "neutral": [],
        }
        for ref in refs:
            key = ref.agreement
            if key not in grouped:
                key = "neutral"
            grouped[key].append(ref)

        formatted: List[str] = []
        if grouped["supports"]:
            formatted.append("Supporting studies:")
            for ref in grouped["supports"]:
                formatted.append(f"  - {ref.citation}: {ref.finding}")

        if grouped["contradicts"]:
            formatted.append("\nContradicting studies:")
            for ref in grouped["contradicts"]:
                formatted.append(f"  - {ref.citation}: {ref.finding}")

        if grouped["extends"]:
            formatted.append("\nExtending studies:")
            for ref in grouped["extends"]:
                formatted.append(f"  - {ref.citation}: {ref.finding}")

        if grouped["neutral"]:
            formatted.append("\nAdditional context:")
            for ref in grouped["neutral"]:
                formatted.append(f"  - {ref.citation}: {ref.finding}")

        return "\n".join(formatted)

    def _format_limitations(self, limitations: List[Limitation]) -> str:
        """Format limitations with impact assessment."""

        if not limitations:
            return "No limitations specified"

        formatted: List[str] = []
        for lim in limitations:
            line = f"- [{lim.category.upper()}] {lim.description} (Impact: {lim.impact})"
            if lim.mitigation:
                line += f"\n  Mitigation: {lim.mitigation}"
            formatted.append(line)
        return "\n".join(formatted)

    def _create_prompt(self, style: DiscussionStyle) -> ChatPromptTemplate:
        """Create the discussion generation prompt."""

        template = """You are a scientific writing expert specializing in discussion sections.
Generate a comprehensive Discussion section that synthesizes findings with literature.

STYLE: {style}

STRICT REQUIREMENTS:
- Begin with principal findings (answer the research question)
- Compare findings to existing literature with proper citations
- Acknowledge all limitations honestly
- Discuss clinical/policy implications
- Suggest specific future research directions
- End with a concise conclusion
- Maintain objective, scientific tone
- Do NOT overstate findings or implications

STUDY CONTEXT:
Study Type: {study_type}
Research Question: {research_question}
Hypothesis: {hypothesis}

KEY FINDINGS:
{key_findings}

LITERATURE CONTEXT:
{literature_context}

STRENGTHS:
{strengths}

LIMITATIONS:
{limitations}

UNEXPECTED FINDINGS:
{unexpected_findings}

CLINICAL IMPLICATIONS:
{clinical_implications}

POLICY IMPLICATIONS:
{policy_implications}

FUTURE RESEARCH DIRECTIONS:
{future_research}

Generate the Discussion section with clear subsection headers."""

        return ChatPromptTemplate.from_template(template)

    def _calculate_completeness(self, text: str, input_data: DiscussionInput) -> float:
        """Calculate completeness score."""

        score = 100.0
        lowered = text.lower()

        checks = [
            (
                ("principal finding" in lowered or "main finding" in lowered),
                15,
            ),
            (
                ("literature" in lowered or "previous" in lowered or "prior" in lowered),
                15,
            ),
            ("limitation" in lowered, 15),
            ("implication" in lowered, 10),
            (("future" in lowered or "further research" in lowered), 10),
            ("conclusion" in lowered, 10),
            (
                any(
                    ref.citation.lower() in lowered
                    for ref in (input_data.literature_context[:3] or [])
                ),
                15,
            ),
            (len(text.split()) >= 500, 10),
        ]

        for passed, points in checks:
            if not passed:
                score -= points

        return max(0.0, score)

    def _extract_citations(self, text: str, refs: List[LiteratureReference]) -> List[str]:
        """Extract which citations were used in the text."""

        used: List[str] = []
        lowered = text.lower()
        for ref in refs:
            if ref.citation.split(",")[0].lower() in lowered:
                used.append(ref.citation)
        return used

    def _generate_suggestions(
        self, text: str, completeness: float, input_data: DiscussionInput
    ) -> List[str]:
        """Generate improvement suggestions."""

        suggestions: List[str] = []
        lowered = text.lower()

        if completeness < 80:
            suggestions.append("Discussion may be missing key components")

        if "limitation" not in lowered:
            suggestions.append("Add explicit discussion of study limitations")

        if input_data.literature_context:
            citations_used = self._extract_citations(text, input_data.literature_context)
            if len(citations_used) < len(input_data.literature_context) // 2:
                suggestions.append("Consider incorporating more literature references")

        word_count = len(text.split())
        if word_count < 400:
            suggestions.append("Discussion may be too brief; consider expanding key sections")
        if word_count > 2000:
            suggestions.append("Discussion is lengthy; consider condensing")

        return suggestions

    async def generate(
        self,
        input_data: DiscussionInput,
        style: DiscussionStyle = DiscussionStyle.STANDARD,
    ) -> DiscussionOutput:
        """
        Generate a discussion section from study findings.

        Args:
            input_data: Study findings and context
            style: Discussion style to generate

        Returns:
            DiscussionOutput with generated discussion
        """

        prompt = self._create_prompt(style)

        transparency_log: Dict[str, Any] = {
            "model_provider": self.model_provider,
            "model_name": self.model_name,
            "temperature": self.temperature,
            "style": style.value,
            "n_findings": len(input_data.key_findings),
            "n_literature_refs": len(input_data.literature_context),
            "n_limitations": len(input_data.limitations),
            "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
        }

        try:
            chain = prompt | self.llm
            response = await chain.ainvoke(
                {
                    "style": style.value,
                    "study_type": input_data.study_type,
                    "research_question": input_data.research_question,
                    "hypothesis": input_data.hypothesis,
                    "key_findings": self._format_findings(input_data.key_findings),
                    "literature_context": self._format_literature(
                        input_data.literature_context
                    ),
                    "strengths": (
                        "\n".join(f"- {s}" for s in input_data.strengths)
                        or "Not specified"
                    ),
                    "limitations": self._format_limitations(input_data.limitations),
                    "unexpected_findings": (
                        "\n".join(f"- {u}" for u in input_data.unexpected_findings)
                        or "None"
                    ),
                    "clinical_implications": "\n".join(
                        f"- {c}" for c in input_data.clinical_implications
                    ),
                    "policy_implications": (
                        "\n".join(f"- {p}" for p in input_data.policy_implications)
                        or "Not applicable"
                    ),
                    "future_research": (
                        "\n".join(f"- {f}" for f in input_data.future_research)
                        or "To be determined"
                    ),
                }
            )

            discussion_text = response.content
            transparency_log["success"] = True

        except Exception as e:
            logger.error(f"Discussion generation failed: {e}")
            transparency_log["success"] = False
            transparency_log["error"] = str(e)
            raise

        completeness = self._calculate_completeness(discussion_text, input_data)
        citations_used = self._extract_citations(discussion_text, input_data.literature_context)
        suggestions = self._generate_suggestions(discussion_text, completeness, input_data)

        return DiscussionOutput(
            text=discussion_text,
            word_count=len(discussion_text.split()),
            sections=self._parse_sections(discussion_text),
            literature_citations_used=citations_used,
            completeness_score=completeness,
            suggestions=suggestions,
            transparency_log=transparency_log,
        )

    def _parse_sections(self, text: str) -> Dict[str, str]:
        """Parse discussion into sections."""

        sections: Dict[str, str] = {}
        lowered = text.lower()
        for section in self.SECTION_STRUCTURE:
            if section.lower() in lowered:
                sections[section] = "Found"
        return sections


def create_discussion_generator(model_provider: str = "anthropic", **kwargs) -> DiscussionGenerator:
    """Factory function to create a DiscussionGenerator instance."""

    return DiscussionGenerator(model_provider=model_provider, **kwargs)
