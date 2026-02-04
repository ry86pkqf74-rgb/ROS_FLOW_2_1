"""IMRaD Manuscript Assembler

Orchestrates IMRaD section generators (Abstract, Methods, Results, Discussion)
into a complete manuscript with:
- Section ordering/formatting
- Cross-reference resolution
- Bibliography assembly
- Supplementary materials bundling
- Journal + citation style application
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Tuple

from .abstract_generator import AbstractGenerator, AbstractInput
from .methods_generator import MethodsGenerator, MethodsInput, StudyType
from .results_generator import (
    ResultsGenerator,
    ResultsInput,
    StatisticalResult,
    TableReference,
    FigureReference,
    ResultType,
)
from .discussion_generator import (
    DiscussionGenerator,
    DiscussionInput,
    KeyFinding,
    LiteratureReference,
    Limitation,
)

from .manuscript_types import ManuscriptReference
from .styles.journal_styles import JournalStyle, JournalStylePreset, get_journal_style
from .styles.citation_styles import CitationStyle, CitationStylePreset, get_citation_style
from .validators.manuscript_validator import ManuscriptValidator
from .validators.word_count_checker import WordCountChecker
from .validators.reference_validator import ReferenceValidator


IMRaDSection = Literal["title", "abstract", "methods", "results", "discussion", "references", "supplementary"]


@dataclass
class ManuscriptSection:
    name: IMRaDSection
    heading: str
    text: str
    word_count: int
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ManuscriptBundle:
    manuscript_id: str
    version: int
    created_at: str
    title: str
    journal_style: JournalStylePreset
    citation_style: CitationStylePreset
    sections: Dict[IMRaDSection, ManuscriptSection]
    references: List[ManuscriptReference]
    supplementary: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "manuscript_id": self.manuscript_id,
            "version": self.version,
            "created_at": self.created_at,
            "title": self.title,
            "journal_style": self.journal_style,
            "citation_style": self.citation_style,
            "sections": {
                k: {
                    "name": v.name,
                    "heading": v.heading,
                    "text": v.text,
                    "word_count": v.word_count,
                    "metadata": v.metadata,
                }
                for k, v in self.sections.items()
            },
            "references": [r.__dict__ for r in self.references],
            "supplementary": self.supplementary,
            "warnings": self.warnings,
        }


@dataclass
class IMRaDAssembleInput:
    title: str = "Untitled Manuscript"
    data: Dict[str, Any] = field(default_factory=dict)

    journal_style: JournalStylePreset = "JAMA"
    citation_style: CitationStylePreset = "Vancouver"

    section_order: Optional[List[IMRaDSection]] = None
    include_supplementary: bool = True

    enforce_word_limits: bool = True
    word_limits: Optional[Dict[str, int]] = None

    manuscript_id: Optional[str] = None
    previous_version: Optional[int] = None


class IMRaDAssembler:
    DEFAULT_ORDER: List[IMRaDSection] = [
        "title",
        "abstract",
        "methods",
        "results",
        "discussion",
        "references",
        "supplementary",
    ]

    def __init__(
        self,
        *,
        abstract_generator: Optional[AbstractGenerator] = None,
        methods_generator: Optional[MethodsGenerator] = None,
        results_generator: Optional[ResultsGenerator] = None,
        discussion_generator: Optional[DiscussionGenerator] = None,
        manuscript_validator: Optional[ManuscriptValidator] = None,
        word_count_checker: Optional[WordCountChecker] = None,
        reference_validator: Optional[ReferenceValidator] = None,
    ):
        self.abstract_generator = abstract_generator or AbstractGenerator()
        self.methods_generator = methods_generator or MethodsGenerator()
        self.results_generator = results_generator or ResultsGenerator()
        self.discussion_generator = discussion_generator or DiscussionGenerator()

        self.manuscript_validator = manuscript_validator or ManuscriptValidator()
        self.word_count_checker = word_count_checker or WordCountChecker()
        self.reference_validator = reference_validator or ReferenceValidator()

    async def generate_section(self, section: IMRaDSection, input_data: IMRaDAssembleInput) -> ManuscriptSection:
        if section == "title":
            text = self._format_title_block(input_data.title, input_data)
            return ManuscriptSection("title", "", text, self._count_words(text), {"generated": True})

        if section == "abstract":
            abs_in = self._build_abstract_input(input_data)
            out = await self.abstract_generator.generate(abs_in)
            text = getattr(out, "text", None) or str(out)
            text = self._apply_section_style("abstract", text, input_data)
            return ManuscriptSection("abstract", self._heading_for("abstract", input_data), text, self._count_words(text), {"generator": "AbstractGenerator"})

        if section == "methods":
            meth_in = self._build_methods_input(input_data)
            out = await self.methods_generator.generate(meth_in)
            text = getattr(out, "text", None) or str(out)
            text = self._apply_section_style("methods", text, input_data)
            return ManuscriptSection("methods", self._heading_for("methods", input_data), text, self._count_words(text), {"generator": "MethodsGenerator"})

        if section == "results":
            res_in = self._build_results_input(input_data)
            out = await self.results_generator.generate(res_in)
            text = getattr(out, "text", None) or str(out)
            text = self._apply_section_style("results", text, input_data)
            return ManuscriptSection("results", self._heading_for("results", input_data), text, self._count_words(text), {"generator": "ResultsGenerator"})

        if section == "discussion":
            disc_in = self._build_discussion_input(input_data)
            out = await self.discussion_generator.generate(disc_in)
            text = getattr(out, "text", None) or str(out)
            text = self._apply_section_style("discussion", text, input_data)
            return ManuscriptSection("discussion", self._heading_for("discussion", input_data), text, self._count_words(text), {"generator": "DiscussionGenerator"})

        if section == "references":
            return ManuscriptSection("references", self._heading_for("references", input_data), "", 0, {"generated": False})

        if section == "supplementary":
            supp = self._bundle_supplementary(input_data) if input_data.include_supplementary else {}
            text = self._format_supplementary_text(supp)
            return ManuscriptSection("supplementary", self._heading_for("supplementary", input_data), text, self._count_words(text), {"generated": True})

        raise ValueError(f"Unknown section: {section}")

    async def assemble(self, input_data: IMRaDAssembleInput) -> ManuscriptBundle:
        manuscript_id = input_data.manuscript_id or str(uuid.uuid4())
        version = (input_data.previous_version or 0) + 1

        journal_style: JournalStyle = get_journal_style(input_data.journal_style)
        citation_style: CitationStyle = get_citation_style(input_data.citation_style)

        order = input_data.section_order or list(self.DEFAULT_ORDER)
        sections: Dict[IMRaDSection, ManuscriptSection] = {}
        warnings: List[str] = []

        for sec in order:
            if sec == "references":
                continue
            sections[sec] = await self.generate_section(sec, input_data)

        resolved_texts, extracted_citations = self._resolve_cross_references({k: v.text for k, v in sections.items()})
        for k, t in resolved_texts.items():
            if k in sections:
                sections[k].text = t
                sections[k].word_count = self._count_words(t)

        references = self._assemble_bibliography(extracted_citations, input_data)
        ref_warnings = self.reference_validator.validate(references, resolved_texts)
        if ref_warnings:
            warnings.extend(ref_warnings)

        ref_text = citation_style.format_bibliography(references)
        ref_text = journal_style.apply_references_block(ref_text)
        sections["references"] = ManuscriptSection(
            "references",
            self._heading_for("references", input_data),
            ref_text,
            self._count_words(ref_text),
            {"style": citation_style.name},
        )

        for sec_name, sec in list(sections.items()):
            if sec_name in ("title", "references"):
                continue
            sec.text = journal_style.apply_section(sec_name, sec.text)
            sec.word_count = self._count_words(sec.text)

        supplementary: Dict[str, Any] = self._bundle_supplementary(input_data) if input_data.include_supplementary else {}

        validation_errors = self.manuscript_validator.validate(sections)
        if validation_errors:
            warnings.extend(validation_errors)

        if input_data.enforce_word_limits:
            limits = input_data.word_limits or journal_style.word_limits
            warnings.extend(self.word_count_checker.check(sections, limits))

        return ManuscriptBundle(
            manuscript_id=manuscript_id,
            version=version,
            created_at=datetime.utcnow().isoformat() + "Z",
            title=journal_style.apply_title(input_data.title),
            journal_style=input_data.journal_style,
            citation_style=input_data.citation_style,
            sections=sections,
            references=references,
            supplementary=supplementary,
            warnings=warnings,
        )

    # ---------------------- Input mapping ----------------------

    def _build_abstract_input(self, inp: IMRaDAssembleInput) -> AbstractInput:
        p = inp.data or {}
        return AbstractInput(
            research_question=str(p.get("research_question") or p.get("question") or ""),
            hypothesis=str(p.get("hypothesis") or ""),
            study_type=str(p.get("study_type") or p.get("studyType") or ""),
            population=str(p.get("population") or ""),
            intervention=str(p.get("intervention") or ""),
            comparator=str(p.get("comparator") or ""),
            primary_outcome=str(p.get("primary_outcome") or p.get("primaryOutcome") or ""),
            key_findings=list(p.get("key_findings") or p.get("keyFindings") or []),
            sample_size=int(p.get("sample_size") or p.get("sampleSize") or 0),
            methods_summary=str(p.get("methods_summary") or p.get("methodsSummary") or p.get("methods") or ""),
            conclusion=p.get("conclusion") or p.get("conclusions"),
            keywords=list(p.get("keywords") or []),
        )

    def _build_methods_input(self, inp: IMRaDAssembleInput) -> MethodsInput:
        p = inp.data or {}
        st = p.get("study_type") or p.get("studyType") or "cohort"
        try:
            study_type = StudyType(st) if not isinstance(st, StudyType) else st
        except Exception:
            study_type = StudyType.COHORT
        participants = p.get("participants")
        if not isinstance(participants, dict):
            participants = {
                "inclusion": p.get("inclusion") or "",
                "exclusion": p.get("exclusion") or "",
                "recruitment": p.get("recruitment") or "",
            }
        outcomes = p.get("outcomes")
        if not isinstance(outcomes, dict):
            outcomes = {
                "primary": list(p.get("primary_outcomes") or []),
                "secondary": list(p.get("secondary_outcomes") or []),
            }
        return MethodsInput(
            study_type=study_type,
            study_design=str(p.get("study_design") or p.get("design") or ""),
            setting=str(p.get("setting") or ""),
            participants=participants,
            intervention=p.get("intervention"),
            comparator=p.get("comparator"),
            outcomes=outcomes,
            sample_size=int(p.get("sample_size") or 0),
            sample_size_justification=str(p.get("sample_size_justification") or ""),
            randomization=p.get("randomization") if isinstance(p.get("randomization"), dict) else None,
            statistical_plan=str(p.get("statistical_plan") or p.get("statistical_analysis") or ""),
            ethics_approval=str(p.get("ethics_approval") or p.get("ethics") or ""),
            registration=p.get("registration"),
            data_collection=str(p.get("data_collection") or ""),
            follow_up_period=str(p.get("follow_up_period") or ""),
            missing_data_handling=str(p.get("missing_data_handling") or ""),
        )

    def _build_results_input(self, inp: IMRaDAssembleInput) -> ResultsInput:
        p = inp.data or {}

        def to_stat_result(d: Any) -> StatisticalResult:
            if isinstance(d, StatisticalResult):
                return d
            if not isinstance(d, dict):
                d = {"name": str(d)}
            rt = d.get("result_type") or d.get("resultType") or "primary_outcome"
            try:
                result_type = ResultType(rt) if not isinstance(rt, ResultType) else rt
            except Exception:
                result_type = ResultType.PRIMARY_OUTCOME
            return StatisticalResult(
                name=str(d.get("name") or "Result"),
                result_type=result_type,
                estimate=float(d.get("estimate") or 0.0),
                ci_lower=d.get("ci_lower"),
                ci_upper=d.get("ci_upper"),
                p_value=d.get("p_value"),
                effect_size=d.get("effect_size"),
                effect_size_type=d.get("effect_size_type"),
                n_intervention=d.get("n_intervention"),
                n_control=d.get("n_control"),
                units=d.get("units"),
                notes=d.get("notes"),
            )

        def to_table(d: Any) -> TableReference:
            if isinstance(d, TableReference):
                return d
            if not isinstance(d, dict):
                d = {"table_number": int(d) if str(d).isdigit() else 1, "title": "Table", "description": ""}
            return TableReference(
                table_number=int(d.get("table_number") or d.get("tableNumber") or 1),
                title=str(d.get("title") or ""),
                description=str(d.get("description") or ""),
            )

        def to_figure(d: Any) -> FigureReference:
            if isinstance(d, FigureReference):
                return d
            if not isinstance(d, dict):
                d = {"figure_number": int(d) if str(d).isdigit() else 1, "title": "Figure", "description": "", "figure_type": ""}
            return FigureReference(
                figure_number=int(d.get("figure_number") or d.get("figureNumber") or 1),
                title=str(d.get("title") or ""),
                description=str(d.get("description") or ""),
                figure_type=str(d.get("figure_type") or d.get("figureType") or ""),
            )

        prim = [to_stat_result(x) for x in (p.get("primary_results") or p.get("primaryResults") or [])]
        sec = [to_stat_result(x) for x in (p.get("secondary_results") or p.get("secondaryResults") or [])]
        sub = [to_stat_result(x) for x in (p.get("subgroup_results") or p.get("subgroupResults") or [])]
        sens = [to_stat_result(x) for x in (p.get("sensitivity_results") or p.get("sensitivityResults") or [])]

        return ResultsInput(
            study_type=str(p.get("study_type") or p.get("studyType") or ""),
            sample_size_analyzed=int(p.get("sample_size_analyzed") or p.get("sampleSizeAnalyzed") or p.get("sample_size") or 0),
            primary_results=prim,
            secondary_results=sec,
            subgroup_results=sub,
            sensitivity_results=sens,
            adverse_events=p.get("adverse_events") or p.get("adverseEvents"),
            flow_data=p.get("flow_data") or p.get("flowData"),
            tables=[to_table(x) for x in (p.get("tables") or [])],
            figures=[to_figure(x) for x in (p.get("figures") or [])],
            follow_up_completion=p.get("follow_up_completion") or p.get("followUpCompletion"),
            missing_data_summary=p.get("missing_data_summary") or p.get("missingDataSummary"),
        )

    def _build_discussion_input(self, inp: IMRaDAssembleInput) -> DiscussionInput:
        p = inp.data or {}

        def to_key_finding(d: Any) -> KeyFinding:
            if isinstance(d, KeyFinding):
                return d
            if not isinstance(d, dict):
                d = {"finding": str(d), "statistical_support": "", "clinical_significance": ""}
            return KeyFinding(
                finding=str(d.get("finding") or ""),
                statistical_support=str(d.get("statistical_support") or d.get("statisticalSupport") or ""),
                clinical_significance=str(d.get("clinical_significance") or d.get("clinicalSignificance") or ""),
                comparison_to_literature=d.get("comparison_to_literature") or d.get("comparisonToLiterature"),
            )

        def to_lit_ref(d: Any) -> LiteratureReference:
            if isinstance(d, LiteratureReference):
                return d
            if not isinstance(d, dict):
                d = {"citation": str(d), "finding": "", "agreement": "neutral"}
            return LiteratureReference(
                citation=str(d.get("citation") or ""),
                finding=str(d.get("finding") or ""),
                agreement=str(d.get("agreement") or "neutral"),
                notes=d.get("notes"),
            )

        def to_lim(d: Any) -> Limitation:
            if isinstance(d, Limitation):
                return d
            if not isinstance(d, dict):
                d = {"category": "design", "description": str(d), "impact": "moderate"}
            return Limitation(
                category=str(d.get("category") or "design"),
                description=str(d.get("description") or ""),
                impact=str(d.get("impact") or "moderate"),
                mitigation=d.get("mitigation"),
            )

        return DiscussionInput(
            study_type=str(p.get("study_type") or p.get("studyType") or ""),
            research_question=str(p.get("research_question") or p.get("question") or ""),
            hypothesis=str(p.get("hypothesis") or ""),
            key_findings=[to_key_finding(x) for x in (p.get("key_findings_structured") or p.get("keyFindingsStructured") or [])] or [to_key_finding(x) for x in (p.get("key_findings") or p.get("keyFindings") or [])],
            literature_context=[to_lit_ref(x) for x in (p.get("literature_context") or p.get("literatureContext") or [])],
            limitations=[to_lim(x) for x in (p.get("limitations") or [])],
            clinical_implications=list(p.get("clinical_implications") or p.get("clinicalImplications") or []),
            policy_implications=list(p.get("policy_implications") or p.get("policyImplications") or []),
            future_research=list(p.get("future_research") or p.get("futureResearch") or []),
            strengths=list(p.get("strengths") or []),
            unexpected_findings=list(p.get("unexpected_findings") or p.get("unexpectedFindings") or []),
        )

    # ---------------------- Formatting ----------------------

    def _heading_for(self, section: IMRaDSection, inp: IMRaDAssembleInput) -> str:
        journal_style = get_journal_style(inp.journal_style)
        return journal_style.section_headings.get(section, section.capitalize())

    def _format_title_block(self, title: str, inp: IMRaDAssembleInput) -> str:
        journal_style = get_journal_style(inp.journal_style)
        return journal_style.apply_title(title)

    def _apply_section_style(self, section: IMRaDSection, text: str, inp: IMRaDAssembleInput) -> str:
        journal_style = get_journal_style(inp.journal_style)
        return journal_style.apply_section(section, text)

    def _resolve_cross_references(self, texts: Dict[IMRaDSection, str]) -> Tuple[Dict[IMRaDSection, str], List[str]]:
        citations: List[str] = []

        def repl_fig(m: re.Match) -> str:
            return f"Figure {m.group(1)}"

        def repl_tbl(m: re.Match) -> str:
            return f"Table {m.group(1)}"

        def collect_cite(m: re.Match) -> str:
            key = m.group(1)
            citations.append(key)
            return f"{{CITE:{key}}}"

        out: Dict[IMRaDSection, str] = {}
        for sec, t in texts.items():
            t = str(t or "")
            t2 = re.sub(r"\[FIGURE:(\d+)\]", repl_fig, t)
            t2 = re.sub(r"\[TABLE:(\d+)\]", repl_tbl, t2)
            t2 = re.sub(r"\[@([^\]]+)\]", collect_cite, t2)
            out[sec] = t2

        seen = set()
        uniq: List[str] = []
        for c in citations:
            if c not in seen:
                seen.add(c)
                uniq.append(c)
        return out, uniq

    def _assemble_bibliography(self, cite_keys: List[str], inp: IMRaDAssembleInput) -> List[ManuscriptReference]:
        registry = (inp.data or {}).get("references") or {}
        refs: List[ManuscriptReference] = []
        for key in cite_keys:
            meta = registry.get(key) if isinstance(registry, dict) else None
            if isinstance(meta, dict):
                refs.append(
                    ManuscriptReference(
                        id=key,
                        title=str(meta.get("title", "")),
                        authors=list(meta.get("authors") or []),
                        year=meta.get("year"),
                        journal=str(meta.get("journal", "")),
                        doi=meta.get("doi"),
                        url=meta.get("url"),
                        raw=meta.get("raw"),
                    )
                )
            else:
                refs.append(ManuscriptReference(id=key, raw=str(meta) if meta is not None else None))
        return refs

    def _bundle_supplementary(self, inp: IMRaDAssembleInput) -> Dict[str, Any]:
        p = inp.data or {}
        supp = {
            "appendix": p.get("appendix") or "",
            "protocol": p.get("protocol") or {},
            "analysis_code": p.get("analysis_code") or {},
            "data_dictionary": p.get("data_dictionary") or {},
        }
        return {k: v for k, v in supp.items() if v not in (None, "", [], {})}

    def _format_supplementary_text(self, supp: Dict[str, Any]) -> str:
        if not supp:
            return ""
        lines = ["Supplementary Materials"]
        for k, v in supp.items():
            if isinstance(v, dict):
                lines.append(f"- {k}: {len(v)} field(s)")
            elif isinstance(v, (list, tuple)):
                lines.append(f"- {k}: {len(v)} item(s)")
            else:
                lines.append(f"- {k}: provided")
        return "\n".join(lines)

    @staticmethod
    def _count_words(text: str) -> int:
        return len([w for w in re.split(r"\s+", (text or "").strip()) if w])
