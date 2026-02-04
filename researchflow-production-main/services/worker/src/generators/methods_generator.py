"""
Methods Section Generator for IMRaD Manuscripts
Generates comprehensive methods sections from protocol artifacts.
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

from langchain_core.prompts import ChatPromptTemplate
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)


class StudyType(Enum):
    """Supported study types."""

    RCT = "randomized_controlled_trial"
    COHORT = "cohort"
    CASE_CONTROL = "case_control"
    CROSS_SECTIONAL = "cross_sectional"
    SYSTEMATIC_REVIEW = "systematic_review"
    META_ANALYSIS = "meta_analysis"


class MethodsTemplate(Enum):
    """Methods section templates."""

    CONSORT = "consort"  # For RCTs
    STROBE = "strobe"  # For observational studies
    PRISMA = "prisma"  # For systematic reviews
    TRIPOD = "tripod"  # For prediction models
    STANDARD = "standard"  # Generic template


@dataclass
class MethodsInput:
    """Input data for methods generation."""

    study_type: StudyType
    study_design: str
    setting: str
    participants: Dict[str, Any]  # inclusion, exclusion, recruitment
    intervention: Optional[str] = None
    comparator: Optional[str] = None
    outcomes: Dict[str, List[str]] = field(default_factory=dict)  # primary, secondary
    sample_size: int = 0
    sample_size_justification: str = ""
    randomization: Optional[Dict[str, str]] = None  # method, allocation, blinding
    statistical_plan: str = ""
    ethics_approval: str = ""
    registration: Optional[str] = None  # trial registration
    data_collection: str = ""
    follow_up_period: str = ""
    missing_data_handling: str = ""


@dataclass
class MethodsOutput:
    """Generated methods section output."""

    text: str
    template: MethodsTemplate
    word_count: int
    sections: Dict[str, str]
    completeness_score: float
    compliance_items: Dict[str, bool]  # CONSORT/STROBE checklist items
    suggestions: List[str]
    transparency_log: Dict[str, Any]


class MethodsGenerator:
    """
    Generates methods sections for research manuscripts.

    Supports multiple study types and reporting guidelines.
    Checks compliance with CONSORT, STROBE, PRISMA, TRIPOD.
    """

    SECTION_STRUCTURE = {
        MethodsTemplate.CONSORT: [
            "Study Design",
            "Participants",
            "Interventions",
            "Outcomes",
            "Sample Size",
            "Randomization",
            "Blinding",
            "Statistical Analysis",
        ],
        MethodsTemplate.STROBE: [
            "Study Design",
            "Setting",
            "Participants",
            "Variables",
            "Data Sources",
            "Bias",
            "Study Size",
            "Statistical Methods",
        ],
        MethodsTemplate.PRISMA: [
            "Protocol and Registration",
            "Eligibility Criteria",
            "Information Sources",
            "Search Strategy",
            "Selection Process",
            "Data Collection",
            "Risk of Bias Assessment",
            "Synthesis Methods",
        ],
        MethodsTemplate.STANDARD: [
            "Study Design",
            "Participants",
            "Procedures",
            "Outcomes",
            "Statistical Analysis",
        ],
    }

    STUDY_TYPE_TEMPLATE_MAP = {
        StudyType.RCT: MethodsTemplate.CONSORT,
        StudyType.COHORT: MethodsTemplate.STROBE,
        StudyType.CASE_CONTROL: MethodsTemplate.STROBE,
        StudyType.CROSS_SECTIONAL: MethodsTemplate.STROBE,
        StudyType.SYSTEMATIC_REVIEW: MethodsTemplate.PRISMA,
        StudyType.META_ANALYSIS: MethodsTemplate.PRISMA,
    }

    def __init__(
        self,
        model_provider: str = "anthropic",
        model_name: str = "claude-sonnet-4-20250514",
        temperature: float = 0.2,
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

    def _get_template(self, study_type: StudyType) -> MethodsTemplate:
        """Get the appropriate template for the study type."""

        return self.STUDY_TYPE_TEMPLATE_MAP.get(study_type, MethodsTemplate.STANDARD)

    def _create_prompt(self, template: MethodsTemplate) -> ChatPromptTemplate:
        """Create the generation prompt for the template."""

        sections = self.SECTION_STRUCTURE.get(
            template, self.SECTION_STRUCTURE[MethodsTemplate.STANDARD]
        )

        prompt_text = f"""You are a scientific writing expert specializing in research methodology.
Generate a comprehensive Methods section following the {template.value.upper()} guidelines.

Required sections: {', '.join(sections)}

STRICT REQUIREMENTS:
- Write in past tense for completed studies
- Be specific about procedures, timing, and measurements
- Include all details needed for reproducibility
- Reference any validated instruments or scales used
- Specify statistical software and version

STUDY DETAILS:
Study Type: {{study_type}}
Study Design: {{study_design}}
Setting: {{setting}}
Participants: {{participants}}
Intervention: {{intervention}}
Comparator: {{comparator}}
Outcomes: {{outcomes}}
Sample Size: {{sample_size}} (Justification: {{sample_size_justification}})
Randomization: {{randomization}}
Statistical Plan: {{statistical_plan}}
Ethics: {{ethics_approval}}
Registration: {{registration}}
Data Collection: {{data_collection}}
Follow-up: {{follow_up_period}}
Missing Data: {{missing_data_handling}}

Generate the Methods section with clear subsection headers."""

        return ChatPromptTemplate.from_template(prompt_text)

    def _check_compliance(self, text: str, template: MethodsTemplate) -> Dict[str, bool]:
        """Check compliance with reporting guidelines."""

        compliance: Dict[str, bool] = {}
        lowered = text.lower()

        if template == MethodsTemplate.CONSORT:
            compliance["trial_design"] = "design" in lowered
            compliance["eligibility_criteria"] = (
                "eligib" in lowered or "inclusion" in lowered
            )
            compliance["interventions"] = "intervention" in lowered
            compliance["outcomes_defined"] = "outcome" in lowered
            compliance["sample_size"] = "sample size" in lowered or "power" in lowered
            compliance["randomization_described"] = "random" in lowered
            compliance["blinding"] = "blind" in lowered or "mask" in lowered
            compliance["statistical_methods"] = "statistic" in lowered

        elif template == MethodsTemplate.STROBE:
            compliance["study_design"] = "design" in lowered
            compliance["setting"] = "setting" in lowered or "conducted" in lowered
            compliance["participants"] = "participant" in lowered
            compliance["variables"] = "variable" in lowered or "outcome" in lowered
            compliance["data_sources"] = "data" in lowered
            compliance["bias"] = "bias" in lowered or "confound" in lowered
            compliance["study_size"] = "sample" in lowered
            compliance["statistical_methods"] = "statistic" in lowered

        return compliance

    def _calculate_completeness(self, compliance: Dict[str, bool]) -> float:
        """Calculate completeness score from compliance items."""

        if not compliance:
            return 0.0
        return sum(compliance.values()) / len(compliance) * 100

    def _generate_suggestions(self, compliance: Dict[str, bool], text: str) -> List[str]:
        """Generate improvement suggestions based on compliance."""

        suggestions: List[str] = []

        for item, present in compliance.items():
            if not present:
                readable_item = item.replace("_", " ").title()
                suggestions.append(f"Consider adding details about: {readable_item}")

        word_count = len(text.split())
        if word_count < 500:
            suggestions.append(
                "Methods section may be too brief; consider adding more procedural detail"
            )
        if word_count > 2000:
            suggestions.append(
                "Methods section is lengthy; consider moving some details to supplementary materials"
            )

        return suggestions

    async def generate(
        self,
        input_data: MethodsInput,
        template: Optional[MethodsTemplate] = None,
    ) -> MethodsOutput:
        """
        Generate a methods section from protocol inputs.

        Args:
            input_data: Protocol and study design data
            template: Override template (auto-detected from study type if None)

        Returns:
            MethodsOutput with generated methods and compliance info
        """

        if template is None:
            template = self._get_template(input_data.study_type)

        prompt = self._create_prompt(template)

        # Transparency log for HTI-1
        transparency_log: Dict[str, Any] = {
            "model_provider": self.model_provider,
            "model_name": self.model_name,
            "temperature": self.temperature,
            "template": template.value,
            "study_type": input_data.study_type.value,
            "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
        }

        try:
            chain = prompt | self.llm
            response = await chain.ainvoke(
                {
                    "study_type": input_data.study_type.value,
                    "study_design": input_data.study_design,
                    "setting": input_data.setting,
                    "participants": str(input_data.participants),
                    "intervention": input_data.intervention or "N/A",
                    "comparator": input_data.comparator or "N/A",
                    "outcomes": str(input_data.outcomes),
                    "sample_size": input_data.sample_size,
                    "sample_size_justification": input_data.sample_size_justification,
                    "randomization": (
                        str(input_data.randomization) if input_data.randomization else "N/A"
                    ),
                    "statistical_plan": input_data.statistical_plan,
                    "ethics_approval": input_data.ethics_approval,
                    "registration": input_data.registration or "N/A",
                    "data_collection": input_data.data_collection,
                    "follow_up_period": input_data.follow_up_period,
                    "missing_data_handling": input_data.missing_data_handling,
                }
            )

            methods_text = response.content
            transparency_log["success"] = True

        except Exception as e:
            logger.error(f"Methods generation failed: {e}")
            transparency_log["success"] = False
            transparency_log["error"] = str(e)
            raise

        sections = self._parse_sections(methods_text, template)
        compliance = self._check_compliance(methods_text, template)
        completeness = self._calculate_completeness(compliance)
        suggestions = self._generate_suggestions(compliance, methods_text)

        return MethodsOutput(
            text=methods_text,
            template=template,
            word_count=len(methods_text.split()),
            sections=sections,
            completeness_score=completeness,
            compliance_items=compliance,
            suggestions=suggestions,
            transparency_log=transparency_log,
        )

    def _parse_sections(self, text: str, template: MethodsTemplate) -> Dict[str, str]:
        """Parse methods text into sections."""

        sections: Dict[str, str] = {}
        section_names = self.SECTION_STRUCTURE.get(template, [])

        for i, section in enumerate(section_names):
            for variant in (section, section.lower(), section.upper()):
                if variant in text:
                    start_idx = text.index(variant)
                    end_idx = len(text)

                    for next_section in section_names[i + 1 :]:
                        for next_variant in (next_section, next_section.lower()):
                            search_start = start_idx + len(variant)
                            found_at = text.find(next_variant, search_start)
                            if found_at != -1:
                                end_idx = found_at
                                break
                        if end_idx != len(text):
                            break

                    sections[section] = text[start_idx:end_idx].strip()
                    break

        return sections


def create_methods_generator(
    model_provider: str = "anthropic",
    model_name: str = "claude-sonnet-4-20250514",
    **kwargs,
) -> MethodsGenerator:
    """Factory function to create a MethodsGenerator instance."""

    return MethodsGenerator(model_provider=model_provider, model_name=model_name, **kwargs)
