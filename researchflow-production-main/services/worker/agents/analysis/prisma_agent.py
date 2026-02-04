"""
PRISMAAgent - Stage 12: PRISMA 2020 Reporting

Generates PRISMA 2020 compliant systematic review documentation including:
- PRISMA flowchart (identification → screening → included)
- Search strategy documentation
- PRISMA 2020 checklist completion
- Risk of bias summary tables
- Automated report generation

Linear Issues: ROS-XXX (Stage 12 - PRISMA Reporting Agent)
"""

import os
import json
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

# Import base agent
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from agents.base_agent import (
    BaseAgent,
    AgentConfig,
    AgentState,
    QualityCheckResult,
)

# Import PRISMA types
from .prisma_types import (
    PRISMAFlowchartData,
    SearchStrategy,
    PRISMAChecklistItem,
    RiskOfBiasSummary,
    PRISMAReport,
)

logger = logging.getLogger(__name__)



# =============================================================================
# PRISMA 2020 Checklist Items (Full List)
# =============================================================================

PRISMA_2020_CHECKLIST = [
    PRISMAChecklistItem(section="Title", item_number="1", item_description="Identify the report as a systematic review"),
    PRISMAChecklistItem(section="Abstract", item_number="2", item_description="See the PRISMA 2020 for Abstracts checklist"),
    PRISMAChecklistItem(section="Introduction - Rationale", item_number="3", item_description="Describe the rationale for the review in the context of existing knowledge"),
    PRISMAChecklistItem(section="Introduction - Objectives", item_number="4", item_description="Provide an explicit statement of the objective(s) or question(s) the review addresses"),
    PRISMAChecklistItem(section="Methods - Eligibility", item_number="5", item_description="Specify the inclusion and exclusion criteria for the review"),
    PRISMAChecklistItem(section="Methods - Information sources", item_number="6", item_description="Specify all databases, registers, websites, etc. searched"),
    PRISMAChecklistItem(section="Methods - Search strategy", item_number="7", item_description="Present the full search strategies for all databases"),
    PRISMAChecklistItem(section="Methods - Selection process", item_number="8", item_description="Specify the methods used to decide whether a study met the inclusion criteria"),
    PRISMAChecklistItem(section="Methods - Data collection", item_number="9", item_description="Specify the methods used to collect data from reports"),
    PRISMAChecklistItem(section="Methods - Data items", item_number="10a", item_description="List and define all outcomes for which data were sought"),
    PRISMAChecklistItem(section="Methods - Data items", item_number="10b", item_description="List and define all other variables for which data were sought"),
    PRISMAChecklistItem(section="Methods - Risk of bias", item_number="11", item_description="Specify the methods used to assess risk of bias in the included studies"),
    PRISMAChecklistItem(section="Methods - Effect measures", item_number="12", item_description="Specify for each outcome the effect measure(s) used in the synthesis"),
    PRISMAChecklistItem(section="Methods - Synthesis methods", item_number="13a", item_description="Describe the processes used to decide which studies were eligible for each synthesis"),
    PRISMAChecklistItem(section="Methods - Synthesis methods", item_number="13b", item_description="Describe any methods required to prepare the data for synthesis"),
    PRISMAChecklistItem(section="Methods - Synthesis methods", item_number="13c", item_description="Describe any methods used to tabulate or visually display results"),
    PRISMAChecklistItem(section="Methods - Synthesis methods", item_number="13d", item_description="Describe any methods used to synthesize results"),
    PRISMAChecklistItem(section="Methods - Reporting bias", item_number="14", item_description="Describe any methods used to assess risk of bias due to missing results"),
    PRISMAChecklistItem(section="Methods - Certainty assessment", item_number="15", item_description="Describe any methods used to assess certainty of the body of evidence"),
    PRISMAChecklistItem(section="Results - Study selection", item_number="16a", item_description="Describe the results of the search and selection process"),
    PRISMAChecklistItem(section="Results - Study selection", item_number="16b", item_description="Cite studies that might appear to meet the inclusion criteria but were excluded"),
    PRISMAChecklistItem(section="Results - Study characteristics", item_number="17", item_description="Cite each included study and present its characteristics"),
    PRISMAChecklistItem(section="Results - Risk of bias", item_number="18", item_description="Present assessments of risk of bias for each included study"),
    PRISMAChecklistItem(section="Results - Results of syntheses", item_number="19", item_description="For all syntheses, present the results"),
    PRISMAChecklistItem(section="Results - Reporting biases", item_number="20", item_description="Present assessments of risk of bias due to missing results"),
    PRISMAChecklistItem(section="Results - Certainty of evidence", item_number="21", item_description="Present assessments of certainty of evidence"),
    PRISMAChecklistItem(section="Discussion", item_number="22", item_description="Provide a general interpretation of the results"),
    PRISMAChecklistItem(section="Discussion - Limitations", item_number="23", item_description="Discuss limitations of the evidence included in the review"),
    PRISMAChecklistItem(section="Other - Registration", item_number="24a", item_description="Provide registration information, including registration number"),
    PRISMAChecklistItem(section="Other - Protocol", item_number="24b", item_description="Indicate where the review protocol can be accessed"),
    PRISMAChecklistItem(section="Other - Support", item_number="25", item_description="Describe sources of financial or non-financial support"),
    PRISMAChecklistItem(section="Other - Conflicts", item_number="26", item_description="Declare any conflicts of interest"),
    PRISMAChecklistItem(section="Other - Availability", item_number="27", item_description="Report availability of data, code, and other materials"),
]


# =============================================================================
# PRISMAAgent
# =============================================================================

class PRISMAAgent(BaseAgent):
    """
    Agent for generating PRISMA 2020 compliant systematic review reports.
    
    Capabilities:
    - PRISMA 2020 flowchart generation (Mermaid + data)
    - Complete search strategy documentation
    - Automated checklist completion
    - Risk of bias summary tables
    - Integrated report generation (Markdown + HTML)
    - Export to Word-compatible formats
    
    Uses LangGraph architecture:
    1. PLAN: Determine what documentation is available and needed
    2. RETRIEVE: Get PRISMA guidelines from RAG
    3. EXECUTE: Generate all PRISMA components
    4. REFLECT: Quality check for completeness and compliance
    """

    def __init__(self):
        config = AgentConfig(
            name="PRISMAAgent",
            description="Generate PRISMA 2020 compliant systematic review documentation",
            stages=[12],
            rag_collections=["prisma_guidelines", "systematic_review_standards"],
            max_iterations=2,
            quality_threshold=0.85,
            timeout_seconds=180,
            phi_safe=True,
            model_provider="anthropic",
            model_name="claude-sonnet-4-20250514",
        )
        super().__init__(config)


    # =========================================================================
    # BaseAgent Abstract Methods Implementation
    # =========================================================================

    def _get_system_prompt(self) -> str:
        """System prompt for PRISMA reporting expertise."""
        return """You are a PRISMA Reporting Agent specialized in systematic review documentation.

Your expertise includes:
- PRISMA 2020 guidelines and checklist
- Systematic review methodology
- Transparent reporting standards
- Risk of bias assessment tools (RoB 2.0, ROBINS-I)
- Search strategy documentation
- GRADE quality of evidence framework

Key principles:
1. Follow PRISMA 2020 guidelines precisely
2. Ensure complete and transparent reporting
3. Document all search strategies with reproducible detail
4. Provide clear flowcharts showing study flow
5. Report all exclusions with reasons
6. Assess and report risk of bias systematically
7. Enable reproducibility of the systematic review

You prioritize clarity, completeness, and adherence to reporting standards."""

    def _get_planning_prompt(self, state: AgentState) -> str:
        """Planning prompt for PRISMA report generation."""
        task_data = json.loads(state["messages"][0].content)
        
        return f"""Plan PRISMA 2020 report generation:

Available Data:
{json.dumps({k: str(v)[:200] for k, v in task_data.items()}, indent=2)}

Your plan should include:
1. Data validation (required fields present)
2. PRISMA flowchart generation
3. Search strategy documentation
4. Checklist completion status
5. Risk of bias summary
6. Report format (Markdown, HTML, etc.)
7. Required visualizations

Output as JSON:
{{
    "steps": ["validate_data", "generate_flowchart", "document_searches", "create_checklist", "compile_report"],
    "has_flowchart_data": true,
    "has_search_strategies": true,
    "has_rob_assessment": true,
    "checklist_completeness": 85,
    "output_formats": ["markdown", "html"],
    "initial_query": "PRISMA 2020 flowchart requirements",
    "primary_collection": "prisma_guidelines"
}}"""

    def _get_execution_prompt(self, state: AgentState, context: str) -> str:
        """Execution prompt with RAG context."""
        task_data = json.loads(state["messages"][0].content)
        plan = state.get("plan", {})
        
        return f"""Generate PRISMA 2020 compliant documentation:

Plan: {json.dumps(plan, indent=2)}

PRISMA Guidelines Context:
{context}

Tasks:
1. Generate PRISMA flowchart data and Mermaid diagram
2. Document all search strategies with complete details
3. Complete PRISMA 2020 checklist (mark reported items)
4. Create risk of bias summary tables
5. Generate formatted report sections
6. Ensure all exclusion reasons are documented
7. Verify registration and protocol information

Return JSON:
{{
    "flowchart": {{
        "records_identified_databases": 1234,
        "records_screened": 890,
        "reports_assessed_eligibility": 145,
        "total_studies_included": 42
    }},
    "search_strategies": [
        {{
            "database": "PubMed",
            "search_date": "2024-01-15",
            "search_string": "...",
            "results_count": 567
        }}
    ],
    "checklist_items_reported": 28,
    "checklist_total": 33,
    "report_summary": "..."
}}"""

    def _parse_execution_result(self, response: str) -> Dict[str, Any]:
        """Parse LLM response into structured result."""
        try:
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
                return json.loads(json_str)
            elif "{" in response:
                start = response.index("{")
                end = response.rindex("}") + 1
                return json.loads(response[start:end])
            else:
                raise ValueError("No JSON in response")
        except Exception as e:
            logger.error(f"Failed to parse execution result: {e}")
            return {}

    async def _check_quality(self, state: AgentState) -> QualityCheckResult:
        """Quality check for PRISMA report completeness."""
        result = state.get("execution_result", {})
        criteria_scores = {}
        feedback_parts = []
        
        # 1. Flowchart completeness (25% weight)
        flowchart = result.get("flowchart", {})
        required_flowchart_fields = [
            "records_identified_databases",
            "records_screened",
            "reports_assessed_eligibility",
            "total_studies_included",
        ]
        flowchart_complete = sum(1 for f in required_flowchart_fields if f in flowchart)
        criteria_scores["flowchart"] = flowchart_complete / len(required_flowchart_fields)
        
        if criteria_scores["flowchart"] < 1.0:
            feedback_parts.append("PRISMA flowchart incomplete")
        
        # 2. Search strategy documentation (25% weight)
        searches = result.get("search_strategies", [])
        if searches and len(searches) >= 2:
            criteria_scores["search_documentation"] = 1.0
        elif searches and len(searches) >= 1:
            criteria_scores["search_documentation"] = 0.7
            feedback_parts.append("Document additional databases searched")
        else:
            criteria_scores["search_documentation"] = 0.0
            feedback_parts.append("Search strategies not documented")
        
        # 3. Checklist completion (20% weight)
        checklist_reported = result.get("checklist_items_reported", 0)
        checklist_total = result.get("checklist_total", 33)
        checklist_percentage = checklist_reported / checklist_total if checklist_total > 0 else 0
        criteria_scores["checklist"] = checklist_percentage
        
        if checklist_percentage < 0.85:
            feedback_parts.append(f"Checklist only {checklist_percentage*100:.0f}% complete (target 85%+)")
        
        # 4. Risk of bias assessment (15% weight)
        has_rob = "rob_summary" in result or "risk_of_bias" in result
        criteria_scores["rob_assessment"] = 1.0 if has_rob else 0.0
        
        if not has_rob:
            feedback_parts.append("Risk of bias assessment missing")
        
        # 5. Report formatting (15% weight)
        has_report = result.get("report_summary") or result.get("formatted_report")
        criteria_scores["formatting"] = 1.0 if has_report else 0.3
        
        if not has_report:
            feedback_parts.append("Generate formatted report sections")
        
        # Calculate overall score
        weights = {
            "flowchart": 0.25,
            "search_documentation": 0.25,
            "checklist": 0.20,
            "rob_assessment": 0.15,
            "formatting": 0.15,
        }
        
        overall = sum(criteria_scores.get(k, 0) * weights[k] for k in weights)
        feedback = "; ".join(feedback_parts) if feedback_parts else "PRISMA report meets quality standards"
        
        return QualityCheckResult(
            passed=overall >= self.config.quality_threshold,
            score=overall,
            feedback=feedback,
            criteria_scores=criteria_scores,
        )


    # =========================================================================
    # Core PRISMA Generation Methods
    # =========================================================================

    async def execute(
        self,
        flowchart_data: PRISMAFlowchartData,
        search_strategies: List[SearchStrategy],
        review_title: str,
        authors: List[str],
        rob_summary: Optional[RiskOfBiasSummary] = None,
        registration_number: Optional[str] = None,
        protocol_doi: Optional[str] = None,
    ) -> PRISMAReport:
        """
        Execute complete PRISMA report generation.
        
        Args:
            flowchart_data: PRISMA flowchart numbers
            search_strategies: List of database search strategies
            review_title: Title of systematic review
            authors: List of authors
            rob_summary: Optional risk of bias summary
            registration_number: Optional PROSPERO/OSF registration
            protocol_doi: Optional protocol DOI
        
        Returns:
            PRISMAReport object with all components
        """
        logger.info(f"[PRISMAAgent] Generating PRISMA report: {review_title}")
        
        input_data = {
            "flowchart_data": flowchart_data.model_dump(),
            "search_strategies": [s.model_dump() for s in search_strategies],
            "review_title": review_title,
            "authors": authors,
            "rob_summary": rob_summary.model_dump() if rob_summary else None,
            "registration_number": registration_number,
            "protocol_doi": protocol_doi,
        }
        
        agent_result = await self.run(
            task_id=f"prisma_report_{datetime.utcnow().timestamp()}",
            stage_id=12,
            research_id=review_title,
            input_data=input_data,
        )
        
        if not agent_result.success:
            logger.error(f"PRISMA report generation failed: {agent_result.error}")
            return self._create_empty_report(review_title, authors)
        
        # Build complete report
        checklist = self.generate_checklist(input_data)
        
        report = PRISMAReport(
            flowchart_data=flowchart_data,
            search_strategies=search_strategies,
            checklist=checklist,
            rob_summary=rob_summary,
            review_title=review_title,
            authors=authors,
            registration_number=registration_number,
            protocol_doi=protocol_doi,
        )
        
        return report

    def generate_checklist(self, review_data: Dict[str, Any]) -> List[PRISMAChecklistItem]:
        """
        Generate PRISMA 2020 checklist with completion status.
        
        Args:
            review_data: Dictionary with review components
        
        Returns:
            List of PRISMAChecklistItem with reported status
        """
        checklist = []
        
        for template_item in PRISMA_2020_CHECKLIST:
            item = PRISMAChecklistItem(
                section=template_item.section,
                item_number=template_item.item_number,
                item_description=template_item.item_description,
                reported=False,
                location=None,
                notes=None,
            )
            
            # Auto-detect if item is likely reported based on available data
            if "Methods - Search strategy" in item.section and review_data.get("search_strategies"):
                item.reported = True
                item.location = "Appendix A"
            
            elif "Methods - Eligibility" in item.section and review_data.get("flowchart_data"):
                item.reported = True
                item.location = "Methods section"
            
            elif "Results - Risk of bias" in item.section and review_data.get("rob_summary"):
                item.reported = True
                item.location = "Results section, Risk of Bias"
            
            elif "Registration" in item.item_description and review_data.get("registration_number"):
                item.reported = True
                item.location = "Methods"
                item.notes = f"Registration: {review_data.get('registration_number')}"
            
            elif "Protocol" in item.item_description and review_data.get("protocol_doi"):
                item.reported = True
                item.location = "Methods"
                item.notes = f"Protocol DOI: {review_data.get('protocol_doi')}"
            
            checklist.append(item)
        
        return checklist

    def generate_report_markdown(self, report: PRISMAReport) -> str:
        """
        Generate complete PRISMA report in Markdown format.
        
        Args:
            report: PRISMAReport object
        
        Returns:
            Formatted Markdown string
        """
        sections = []
        
        # Title page
        sections.append(f"# {report.review_title}")
        sections.append(f"\n**Authors:** {', '.join(report.authors)}\n")
        
        if report.registration_number:
            sections.append(f"**Registration:** {report.registration_number}")
        if report.protocol_doi:
            sections.append(f"**Protocol:** {report.protocol_doi}")
        
        sections.append(f"\n**Report Generated:** {report.generated_at}\n")
        sections.append("---\n")
        
        # PRISMA Flowchart
        sections.append("## PRISMA 2020 Flow Diagram\n")
        sections.append(report.generate_flowchart_mermaid())
        sections.append("\n### Study Flow Summary\n")
        
        data = report.flowchart_data
        sections.append(f"- **Records identified:** {data.total_identified}")
        sections.append(f"- **Records screened:** {data.records_screened}")
        sections.append(f"- **Reports assessed for eligibility:** {data.reports_assessed_eligibility}")
        sections.append(f"- **Studies included in review:** {data.total_studies_included}")
        sections.append(f"- **Duplicates removed:** {data.records_removed_before_screening}")
        sections.append(f"- **Records excluded at screening:** {data.records_excluded}")
        sections.append(f"- **Reports excluded (with reasons):** {data.reports_excluded}\n")
        
        if data.exclusion_reasons:
            sections.append("#### Exclusion Reasons\n")
            for reason, count in data.exclusion_reasons.items():
                sections.append(f"- {reason}: {count}")
            sections.append("")
        
        # Search Strategies
        sections.append("## Appendix A: Search Strategies\n")
        sections.append(report.generate_search_appendix())
        
        # PRISMA Checklist
        sections.append("\n## PRISMA 2020 Checklist\n")
        sections.append(report.generate_checklist_table())
        
        completed = sum(1 for item in report.checklist if item.reported)
        total = len(report.checklist)
        percentage = (completed / total * 100) if total > 0 else 0
        sections.append(f"\n**Completion:** {completed}/{total} items reported ({percentage:.0f}%)\n")
        
        # Risk of Bias Summary
        if report.rob_summary:
            sections.append("\n## Risk of Bias Assessment\n")
            sections.append(f"**Tool Used:** {report.rob_summary.tool_used}\n")
            sections.append(f"**Domains Assessed:** {', '.join(report.rob_summary.domains)}\n")
            sections.append(f"\n**Overall Risk of Bias:**")
            sections.append(f"- Low risk: {report.rob_summary.low_risk_studies} studies")
            sections.append(f"- Some concerns: {report.rob_summary.some_concerns_studies} studies")
            sections.append(f"- High risk: {report.rob_summary.high_risk_studies} studies\n")
        
        return "\n".join(sections)

    def export_to_html(self, report: PRISMAReport) -> str:
        """
        Export PRISMA report to HTML format.
        
        Args:
            report: PRISMAReport object
        
        Returns:
            HTML string
        """
        markdown_content = self.generate_report_markdown(report)
        
        # Basic Markdown to HTML conversion (could use markdown library)
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{report.review_title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 900px; margin: 40px auto; padding: 20px; }}
        h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; margin-top: 30px; border-bottom: 2px solid #ecf0f1; padding-bottom: 8px; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #3498db; color: white; }}
        tr:nth-child(even) {{ background-color: #f2f2f2; }}
        .metadata {{ color: #7f8c8d; font-size: 0.9em; }}
        .flowchart {{ background: #ecf0f1; padding: 20px; border-radius: 5px; margin: 20px 0; }}
    </style>
</head>
<body>
"""
        # Convert markdown sections (simplified)
        for line in markdown_content.split("\n"):
            if line.startswith("# "):
                html += f"<h1>{line[2:]}</h1>\n"
            elif line.startswith("## "):
                html += f"<h2>{line[3:]}</h2>\n"
            elif line.startswith("### "):
                html += f"<h3>{line[4:]}</h3>\n"
            elif line.startswith("**") and line.endswith("**"):
                html += f"<p><strong>{line[2:-2]}</strong></p>\n"
            elif line.startswith("- "):
                html += f"<li>{line[2:]}</li>\n"
            elif line == "---":
                html += "<hr>\n"
            elif line.strip():
                html += f"<p>{line}</p>\n"
        
        html += """
</body>
</html>
"""
        return html

    def _create_empty_report(self, title: str, authors: List[str]) -> PRISMAReport:
        """Create empty report for error cases."""
        return PRISMAReport(
            flowchart_data=PRISMAFlowchartData(
                records_identified_databases=0,
                records_screened=0,
                reports_sought_retrieval=0,
                reports_assessed_eligibility=0,
                new_studies_included=0,
                total_studies_included=0,
                reports_excluded=0,
            ),
            search_strategies=[],
            checklist=[],
            review_title=title,
            authors=authors,
        )


# =============================================================================
# Factory Function
# =============================================================================

def create_prisma_agent() -> PRISMAAgent:
    """Factory function for creating PRISMAAgent."""
    return PRISMAAgent()

