"""
Abstract Generator for IMRaD Manuscripts
Generates structured abstracts from research artifacts.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)


class AbstractStyle(Enum):
    """Supported abstract styles."""

    STRUCTURED = "structured"  # Background, Methods, Results, Conclusions
    UNSTRUCTURED = "unstructured"  # Single paragraph
    GRAPHICAL = "graphical"  # Visual abstract outline
    BMJ_STRUCTURED = "bmj_structured"  # Objectives, Design, Setting, etc.
    CONSORT = "consort"  # Per CONSORT guidelines


@dataclass
class AbstractInput:
    """Input data for abstract generation."""

    research_question: str
    hypothesis: str
    study_type: str
    population: str
    intervention: str
    comparator: str
    primary_outcome: str
    key_findings: List[str]
    sample_size: int
    methods_summary: str
    conclusion: Optional[str] = None
    keywords: List[str] = field(default_factory=list)


@dataclass
class AbstractOutput:
    """Generated abstract output."""

    text: str
    style: AbstractStyle
    word_count: int
    sections: Dict[str, str]
    quality_score: float
    suggestions: List[str]
    transparency_log: Dict[str, Any]


class AbstractGenerator:
    """
    Generates structured abstracts for research manuscripts.

    Supports multiple abstract styles and enforces word count constraints.
    Includes AI transparency logging per HTI-1 requirements.
    """

    DEFAULT_WORD_LIMITS = {
        AbstractStyle.STRUCTURED: (200, 350),
        AbstractStyle.UNSTRUCTURED: (150, 250),
        AbstractStyle.GRAPHICAL: (100, 150),
        AbstractStyle.BMJ_STRUCTURED: (250, 400),
        AbstractStyle.CONSORT: (300, 400),
    }

    SECTION_TEMPLATES = {
        AbstractStyle.STRUCTURED: ["Background", "Methods", "Results", "Conclusions"],
        AbstractStyle.BMJ_STRUCTURED: [
            "Objectives",
            "Design",
            "Setting",
            "Participants",
            "Main outcome measures",
            "Results",
            "Conclusions",
        ],
        AbstractStyle.CONSORT: [
            "Background",
            "Methods",
            "Results",
            "Conclusions",
            "Trial registration",
        ],
    }

    def __init__(
        self,
        model_provider: str = "anthropic",
        model_name: str = "claude-sonnet-4-20250514",
        temperature: float = 0.3,
        word_limit: Optional[tuple] = None,
    ):
        self.model_provider = model_provider
        self.model_name = model_name
        self.temperature = temperature
        self.word_limit = word_limit
        self._init_llm()

    def _init_llm(self):
        """Initialize the language model."""
        if self.model_provider == "anthropic":
            self.llm = ChatAnthropic(
                model=self.model_name,
                temperature=self.temperature,
                max_tokens=2000,
            )
        elif self.model_provider == "openai":
            self.llm = ChatOpenAI(
                model=self.model_name,
                temperature=self.temperature,
                max_tokens=2000,
            )
        else:
            raise ValueError(f"Unsupported model provider: {self.model_provider}")

    def _get_word_limits(self, style: AbstractStyle) -> tuple:
        """Get word limits for the given style."""
        if self.word_limit:
            return self.word_limit
        return self.DEFAULT_WORD_LIMITS.get(style, (200, 350))

    def _create_prompt(self, style: AbstractStyle) -> ChatPromptTemplate:
        """Create the generation prompt for the given style."""
        sections = self.SECTION_TEMPLATES.get(
            style, self.SECTION_TEMPLATES[AbstractStyle.STRUCTURED]
        )
        min_words, max_words = self._get_word_limits(style)

        template = f"""You are a scientific writing assistant specializing in research abstracts.
Generate a {style.value} abstract with the following sections: {', '.join(sections)}.

STRICT REQUIREMENTS:
- Word count: {min_words}-{max_words} words total
- Use precise scientific language
- Include specific numerical results where provided
- Avoid jargon unless necessary for the field

RESEARCH DETAILS:
Research Question: {{research_question}}
Hypothesis: {{hypothesis}}
Study Type: {{study_type}}
Population: {{population}}
Intervention: {{intervention}}
Comparator: {{comparator}}
Primary Outcome: {{primary_outcome}}
Sample Size: {{sample_size}}
Methods Summary: {{methods_summary}}
Key Findings: {{key_findings}}
Conclusion: {{conclusion}}

Generate the abstract with clear section headers."""

        return ChatPromptTemplate.from_template(template)

    def _calculate_quality_score(self, abstract: str, input_data: AbstractInput) -> float:
        """Calculate quality score for generated abstract."""
        score = 100.0
        word_count = len(abstract.split())

        # Word count check
        min_words, max_words = self._get_word_limits(AbstractStyle.STRUCTURED)
        if word_count < min_words:
            score -= (min_words - word_count) * 0.5
        elif word_count > max_words:
            score -= (word_count - max_words) * 0.5

        # Check for key elements
        if input_data.primary_outcome.lower() not in abstract.lower():
            score -= 10
        if str(input_data.sample_size) not in abstract:
            score -= 5

        return max(0, min(100, score))

    def _generate_suggestions(self, abstract: str, quality_score: float) -> List[str]:
        """Generate improvement suggestions."""
        suggestions = []
        word_count = len(abstract.split())

        if word_count < 200:
            suggestions.append(
                "Consider adding more detail to the Methods or Results sections"
            )
        if word_count > 350:
            suggestions.append("Consider condensing the Background section")
        if quality_score < 80:
            suggestions.append(
                "Ensure all key findings are represented with specific numbers"
            )

        return suggestions

    async def generate(
        self,
        input_data: AbstractInput,
        style: AbstractStyle = AbstractStyle.STRUCTURED,
    ) -> AbstractOutput:
        """
        Generate an abstract from research inputs.

        Args:
            input_data: Research data for abstract generation
            style: Abstract style to generate

        Returns:
            AbstractOutput with generated abstract and metadata
        """
        prompt = self._create_prompt(style)

        # Create transparency log for HTI-1 compliance
        transparency_log = {
            "model_provider": self.model_provider,
            "model_name": self.model_name,
            "temperature": self.temperature,
            "style": style.value,
            "input_tokens_estimate": len(str(input_data)) // 4,
            "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
        }

        try:
            chain = prompt | self.llm
            response = await chain.ainvoke(
                {
                    "research_question": input_data.research_question,
                    "hypothesis": input_data.hypothesis,
                    "study_type": input_data.study_type,
                    "population": input_data.population,
                    "intervention": input_data.intervention,
                    "comparator": input_data.comparator,
                    "primary_outcome": input_data.primary_outcome,
                    "sample_size": input_data.sample_size,
                    "methods_summary": input_data.methods_summary,
                    "key_findings": "\n".join(f"- {f}" for f in input_data.key_findings),
                    "conclusion": input_data.conclusion
                    or "To be determined based on findings",
                }
            )

            abstract_text = response.content
            transparency_log["output_tokens_estimate"] = len(abstract_text) // 4
            transparency_log["success"] = True

        except Exception as e:
            logger.error(f"Abstract generation failed: {e}")
            transparency_log["success"] = False
            transparency_log["error"] = str(e)
            raise

        # Parse sections from response
        sections = self._parse_sections(abstract_text, style)
        word_count = len(abstract_text.split())
        quality_score = self._calculate_quality_score(abstract_text, input_data)
        suggestions = self._generate_suggestions(abstract_text, quality_score)

        return AbstractOutput(
            text=abstract_text,
            style=style,
            word_count=word_count,
            sections=sections,
            quality_score=quality_score,
            suggestions=suggestions,
            transparency_log=transparency_log,
        )

    def _parse_sections(self, text: str, style: AbstractStyle) -> Dict[str, str]:
        """Parse abstract text into sections."""
        sections: Dict[str, str] = {}
        section_names = self.SECTION_TEMPLATES.get(
            style, self.SECTION_TEMPLATES[AbstractStyle.STRUCTURED]
        )

        text_lower = text.lower()
        for i, section in enumerate(section_names):
            start_marker = f"{section}:"
            start_marker_lower = start_marker.lower()

            if start_marker_lower in text_lower:
                start_idx = text_lower.index(start_marker_lower)
                end_idx = len(text)

                for next_section in section_names[i + 1 :]:
                    next_marker_lower = f"{next_section}:".lower()
                    if next_marker_lower in text_lower:
                        end_idx = text_lower.index(next_marker_lower)
                        break

                sections[section] = text[start_idx + len(start_marker) : end_idx].strip()

        return sections


def create_abstract_generator(
    model_provider: str = "anthropic",
    model_name: str = "claude-sonnet-4-20250514",
    **kwargs,
) -> AbstractGenerator:
    """Factory function to create an AbstractGenerator instance."""
    return AbstractGenerator(model_provider=model_provider, model_name=model_name, **kwargs)
