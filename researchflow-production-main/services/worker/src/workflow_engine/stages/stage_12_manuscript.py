"""
Stage 12: Manuscript Drafting Agent

Generates complete manuscript drafts with proper section structure, ICMJE compliance,
and citation formatting. This stage creates publication-ready manuscripts including:
- Introduction section
- Methods section
- Results section
- Discussion section
- Conclusion section
- Structured abstract

Uses claude-writer and abstract-generator services via ManuscriptClient bridge.

See: Linear ROS-124
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    from langchain_core.tools import BaseTool
    from langchain_core.prompts import PromptTemplate
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    BaseTool = Any  # type: ignore
    PromptTemplate = Any  # type: ignore

from ..types import StageContext, StageResult
from ..registry import register_stage
from .base_stage_agent import BaseStageAgent

logger = logging.getLogger("workflow_engine.stages.stage_12_manuscript")

# Sentinel values for detecting missing/default fields
SENTINEL_VALUES = {
    "studyTitle": "Research Study",
    "hypothesis": "To investigate the relationship between study variables and outcomes",
    "methods": "Standard statistical analysis methods were applied",
    "results": "Results are presented in the following sections",
}


@register_stage
class ManuscriptDraftingAgent(BaseStageAgent):
    """Manuscript Drafting Agent for Stage 12.

    Generates complete manuscript drafts using the TypeScript
    Claude Writer and Abstract Generator services via ManuscriptClient bridge.
    """

    stage_id = 12
    stage_name = "Manuscript Drafting"

    def get_tools(self) -> List[BaseTool]:
        """Get LangChain tools for manuscript drafting.

        Returns:
            List of LangChain tools (empty for now, can be extended)
        """
        if not LANGCHAIN_AVAILABLE:
            return []
        # Future: Could add tools for citation formatting, ICMJE compliance checking, etc.
        return []

    def get_prompt_template(self) -> PromptTemplate:
        """Get prompt template for manuscript generation.

        Returns:
            LangChain PromptTemplate for manuscript generation
        """
        if not LANGCHAIN_AVAILABLE:
            class _StubTemplate:
                @classmethod
                def from_template(cls, _t): return type("_T", (), {"template": _t, "format": lambda s, **kw: s.template})()
            return _StubTemplate.from_template("{input}")
        return PromptTemplate.from_template(
            "Generate manuscript for research study.\n\n"
            "Study Title: {study_title}\n"
            "Study Type: {study_type}\n"
            "Hypothesis: {hypothesis}\n"
            "Methods: {methods}\n"
            "Results: {results}\n"
            "Discussion Points: {discussion_points}\n"
            "Journal Style: {journal_style}\n"
            "{optional_fields}"
        )

    def _extract_manuscript_data(self, context: StageContext) -> Dict[str, Any]:
        """Extract manuscript data from context with fallbacks.

        Extracts data from multiple sources:
        1. context.config.get("manuscript", {}) (primary)
        2. context.config (root level)
        3. Previous stage outputs (especially Stages 6-9: analysis, stats, interpretation)
        4. Default values

        Args:
            context: Stage execution context

        Returns:
            Dictionary with manuscript generation parameters
        """
        manuscript_config = context.config.get("manuscript", {})
        config = context.config

        # Extract study title
        study_title = (
            manuscript_config.get("study_title") or
            manuscript_config.get("studyTitle") or
            config.get("study_title") or
            config.get("studyTitle") or
            config.get("title") or
            self._extract_title_from_stages(context) or
            "Research Study"
        )

        # Extract study type
        study_type_raw = (
            manuscript_config.get("study_type") or
            manuscript_config.get("studyType") or
            config.get("study_type") or
            config.get("studyType") or
            "observational"
        )
        study_type_map = {
            "observational": "observational",
            "retrospective": "retrospective",
            "prospective": "prospective",
            "clinical_trial": "clinical_trial",
            "clinical trial": "clinical_trial",
            "trial": "clinical_trial",
            "cohort": "cohort",
            "case_control": "case_control",
        }
        study_type = study_type_map.get(study_type_raw.lower(), "observational")

        # Extract hypothesis/research question
        hypothesis = (
            manuscript_config.get("hypothesis") or
            config.get("hypothesis") or
            config.get("research_question") or
            config.get("researchQuestion") or
            self._extract_hypothesis_from_stages(context) or
            "To investigate the relationship between study variables and outcomes"
        )

        # Extract methods from previous stages
        methods = (
            manuscript_config.get("methods") or
            config.get("methods") or
            self._extract_methods_from_stages(context) or
            "Standard statistical analysis methods were applied"
        )

        # Extract results from previous stages
        results = (
            manuscript_config.get("results") or
            config.get("results") or
            self._extract_results_from_stages(context) or
            "Results are presented in the following sections"
        )

        # Extract discussion points
        discussion_points_raw = (
            manuscript_config.get("discussion_points") or
            manuscript_config.get("discussionPoints") or
            config.get("discussion_points") or
            config.get("discussionPoints") or
            []
        )
        if isinstance(discussion_points_raw, str):
            discussion_points = [p.strip() for p in discussion_points_raw.split(",")]
        elif isinstance(discussion_points_raw, list):
            discussion_points = discussion_points_raw
        else:
            discussion_points = []

        # Optional fields
        journal_style = (
            manuscript_config.get("journal_style") or
            manuscript_config.get("journalStyle") or
            config.get("journal_style") or
            config.get("journalStyle") or
            "academic"
        )

        word_limit = (
            manuscript_config.get("word_limit") or
            manuscript_config.get("wordLimit") or
            config.get("word_limit") or
            config.get("wordLimit") or
            None
        )

        citation_format = (
            manuscript_config.get("citation_format") or
            manuscript_config.get("citationFormat") or
            config.get("citation_format") or
            config.get("citationFormat") or
            "numbered"
        )

        return {
            "studyTitle": study_title,
            "studyType": study_type,
            "hypothesis": hypothesis,
            "methods": methods,
            "results": results,
            "discussionPoints": discussion_points,
            "journalStyle": journal_style,
            "wordLimit": word_limit,
            "citationFormat": citation_format,
        }

    def _extract_title_from_stages(self, context: StageContext) -> Optional[str]:
        """Extract study title from previous stage outputs.

        Args:
            context: Stage execution context

        Returns:
            Title string or None
        """
        # Check Stage 1 (Upload) for dataset title
        stage_1_result = context.previous_results.get(1)
        if stage_1_result and stage_1_result.output:
            output = stage_1_result.output
            if isinstance(output, dict):
                return output.get("title") or output.get("study_title")

        # Check Stage 3 (IRB) for protocol title
        stage_3_result = context.previous_results.get(3)
        if stage_3_result and stage_3_result.output:
            output = stage_3_result.output
            if isinstance(output, dict):
                protocol = output.get("protocol", {})
                if isinstance(protocol, dict):
                    return protocol.get("studyTitle") or protocol.get("study_title")

        return None

    def _extract_hypothesis_from_stages(self, context: StageContext) -> Optional[str]:
        """Extract hypothesis from previous stage outputs.

        Args:
            context: Stage execution context

        Returns:
            Hypothesis string or None
        """
        # Check Stage 1 (Upload) for research question
        stage_1_result = context.previous_results.get(1)
        if stage_1_result and stage_1_result.output:
            output = stage_1_result.output
            if isinstance(output, dict):
                return output.get("research_question") or output.get("hypothesis")

        # Check Stage 2 (Literature) for research context
        stage_2_result = context.previous_results.get(2)
        if stage_2_result and stage_2_result.output:
            output = stage_2_result.output
            if isinstance(output, dict):
                return output.get("research_question") or output.get("hypothesis")

        # Check Stage 3 (IRB) for hypothesis
        stage_3_result = context.previous_results.get(3)
        if stage_3_result and stage_3_result.output:
            output = stage_3_result.output
            if isinstance(output, dict):
                protocol = output.get("protocol", {})
                if isinstance(protocol, dict):
                    return protocol.get("hypothesis")

        return None

    def _extract_methods_from_stages(self, context: StageContext) -> Optional[str]:
        """Extract methods from previous stage outputs.

        Args:
            context: Stage execution context

        Returns:
            Methods string or None
        """
        # Check Stage 6 (Analysis) for analysis methods
        stage_6_result = context.previous_results.get(6)
        if stage_6_result and stage_6_result.output:
            output = stage_6_result.output
            if isinstance(output, dict):
                return output.get("methods") or output.get("analysis_methods")

        # Check Stage 7 (Statistics) for statistical methods
        stage_7_result = context.previous_results.get(7)
        if stage_7_result and stage_7_result.output:
            output = stage_7_result.output
            if isinstance(output, dict):
                return output.get("statistical_methods") or output.get("methods")

        return None

    def _extract_results_from_stages(self, context: StageContext) -> Optional[str]:
        """Extract results from previous stage outputs.

        Args:
            context: Stage execution context

        Returns:
            Results string or None
        """
        # Check Stage 6 (Analysis) for analysis results
        stage_6_result = context.previous_results.get(6)
        if stage_6_result and stage_6_result.output:
            output = stage_6_result.output
            if isinstance(output, dict):
                return output.get("results") or output.get("findings") or output.get("summary")

        # Check Stage 7 (Statistics) for statistical results
        stage_7_result = context.previous_results.get(7)
        if stage_7_result and stage_7_result.output:
            output = stage_7_result.output
            if isinstance(output, dict):
                return output.get("results") or output.get("statistical_results")

        # Check Stage 9 (Interpretation) for interpreted results
        stage_9_result = context.previous_results.get(9)
        if stage_9_result and stage_9_result.output:
            output = stage_9_result.output
            if isinstance(output, dict):
                return output.get("interpretation") or output.get("results")

        return None

    async def execute(self, context: StageContext) -> StageResult:
        """Execute manuscript generation.

        Args:
            context: Stage execution context

        Returns:
            StageResult with generated manuscript
        """
        started_at = datetime.utcnow().isoformat() + "Z"
        errors: List[str] = []
        warnings: List[str] = []
        artifacts: List[str] = []
        output: Dict[str, Any] = {}

        logger.info(f"Starting manuscript generation for job {context.job_id}")

        try:
            # Extract manuscript data from context
            manuscript_data = self._extract_manuscript_data(context)

            # Validate required fields
            required_fields = [
                "studyTitle",
                "hypothesis",
            ]
            missing_fields = [
                field for field in required_fields
                if (not manuscript_data.get(field) or 
                    manuscript_data.get(field) == "" or
                    manuscript_data.get(field) == SENTINEL_VALUES.get(field))
            ]

            # In DEMO mode, allow missing fields with warnings
            if missing_fields and context.governance_mode == "DEMO":
                warnings.append(
                    f"Missing required fields in DEMO mode: {', '.join(missing_fields)}. "
                    "Using default values."
                )
                # Fill in defaults
                if "studyTitle" in missing_fields:
                    manuscript_data["studyTitle"] = "Research Study"
                if "hypothesis" in missing_fields:
                    manuscript_data["hypothesis"] = "To investigate the relationship between study variables and outcomes"
            elif missing_fields:
                errors.append(
                    f"Missing required fields: {', '.join(missing_fields)}"
                )
                return self.create_stage_result(
                    context=context,
                    status="failed",
                    started_at=started_at,
                    errors=errors,
                    warnings=warnings,
                )

            logger.info(f"Generating manuscript for: {manuscript_data['studyTitle']}")

            # Generate IMRaD sections using claude-writer
            sections: Dict[str, str] = {}
            imrad_sections = ["introduction", "methods", "results", "discussion", "conclusion"]

            for section_name in imrad_sections:
                try:
                    # Prepare context for this section
                    section_context = f"Study: {manuscript_data['studyTitle']}\n"
                    section_context += f"Type: {manuscript_data['studyType']}\n"
                    section_context += f"Hypothesis: {manuscript_data['hypothesis']}\n"

                    if section_name == "methods":
                        section_context += f"Methods: {manuscript_data['methods']}\n"
                    elif section_name == "results":
                        section_context += f"Results: {manuscript_data['results']}\n"
                    elif section_name == "discussion":
                        if manuscript_data.get("discussionPoints"):
                            section_context += f"Discussion Points: {', '.join(manuscript_data['discussionPoints'])}\n"

                    # Generate paragraph for this section
                    paragraph_result = await self.generate_paragraph(
                        topic=f"{section_name.capitalize()} section",
                        context=section_context,
                        key_points=manuscript_data.get("discussionPoints", []) if section_name == "discussion" else None,
                        section=section_name,
                        tone="formal",
                        target_length=manuscript_data.get("wordLimit"),
                    )

                    sections[section_name] = paragraph_result.get("paragraph", "")
                    logger.info(f"Generated {section_name} section ({paragraph_result.get('metadata', {}).get('wordCount', 0)} words)")

                except Exception as e:
                    error_msg = f"Failed to generate {section_name} section: {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    errors.append(error_msg)
                    # Continue with other sections even if one fails
                    sections[section_name] = f"[{section_name.capitalize()} section generation failed]"

            # Generate abstract using abstract-generator
            abstract_result = None
            try:
                abstract_result = await self.generate_abstract(
                    manuscript_id=context.job_id,
                    style="structured",
                    journal_template=None,  # Can be extracted from config if needed
                    autofill={
                        "studyDesign": manuscript_data["studyType"],
                        "sampleSize": None,  # Could extract from previous stages
                        "primaryOutcome": manuscript_data.get("hypothesis"),
                        "mainFinding": manuscript_data.get("results", "")[:200] if manuscript_data.get("results") else None,
                    },
                    max_words=manuscript_data.get("wordLimit"),
                )
                logger.info(f"Generated abstract ({abstract_result.get('wordCount', 0)} words)")
            except Exception as e:
                error_msg = f"Failed to generate abstract: {str(e)}"
                logger.error(error_msg, exc_info=True)
                # Abstract generation is optional - only add warning, not error
                warnings.append("Abstract generation failed, manuscript will be generated without abstract")

            # Compile complete manuscript
            manuscript = {
                "title": manuscript_data["studyTitle"],
                "abstract": abstract_result.get("text", "") if abstract_result else "",
                "abstract_sections": abstract_result.get("sections", []) if abstract_result else [],
                "sections": sections,
                "word_count": sum(
                    len(s.split()) for s in sections.values()
                ) + (abstract_result.get("wordCount", 0) if abstract_result else 0),
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "journal_style": manuscript_data["journalStyle"],
                "citation_format": manuscript_data["citationFormat"],
            }

            # Store manuscript in output
            output["manuscript"] = manuscript
            output["manuscript_id"] = context.job_id
            output["sections_generated"] = list(sections.keys())

            # Save manuscript as JSON artifact
            os.makedirs(context.artifact_path, exist_ok=True)
            manuscript_filename = f"manuscript_{context.job_id}.json"
            manuscript_path = os.path.join(context.artifact_path, manuscript_filename)

            with open(manuscript_path, "w", encoding="utf-8") as f:
                json.dump(manuscript, f, indent=2, ensure_ascii=False)

            artifacts.append(manuscript_path)
            output["manuscript_file"] = manuscript_filename

            logger.info(
                f"Manuscript generated successfully: {manuscript_filename} "
                f"({manuscript['word_count']} words)"
            )

        except Exception as e:
            error_msg = f"Failed to generate manuscript: {str(e)}"
            logger.error(error_msg, exc_info=True)
            errors.append(error_msg)

        # Create result
        return self.create_stage_result(
            context=context,
            status="failed" if errors else "completed",
            started_at=started_at,
            output=output,
            artifacts=artifacts,
            errors=errors,
            warnings=warnings,
            metadata={
                "governance_mode": context.governance_mode,
                "manuscript_generated": len(errors) == 0,
                "sections_count": len(output.get("sections_generated", [])),
                "word_count": output.get("manuscript", {}).get("word_count", 0),
            },
        )
