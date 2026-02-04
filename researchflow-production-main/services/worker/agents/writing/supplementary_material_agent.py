"""
Supplementary Material Agent - Stage 16: Organize and package supplementary materials

This agent handles the organization and packaging of supplementary materials for manuscript submission.
It processes content from the Results Refinement stage and determines what should be included in
the main manuscript versus supplementary materials, then organizes everything according to
journal-specific requirements.

Key responsibilities:
- Content placement decisions (main text vs supplement)  
- Supplementary table organization (S1, S2, S3...)
- Supplementary figure organization (S1, S2, S3...)
- Extended methods compilation 
- Data availability statement generation
- Appendices creation (checklists, forms)
- Package compilation with manifest
- Journal-specific formatting compliance

All LLM calls route through the orchestrator's AI Router for PHI compliance.

See: Linear ROS-67 (Phase D: Remaining Agents) - Stage 16 Enhancement
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid
import logging

from langgraph.graph import StateGraph, END

from ..base.langgraph_base import LangGraphBaseAgent
from ..base.state import AgentState, Message
from .supplementary_types import (
    SupplementaryMaterialState,
    SupplementaryTable,
    SupplementaryFigure,
    Appendix,
    SupplementaryItemType,
    FileFormat,
    JournalFormat,
    PlacementDecision,
    ChecklistType,
    JournalRequirements,
    STROBE_CHECKLIST,
    CONSORT_CHECKLIST,
)

logger = logging.getLogger(__name__)


class SupplementaryMaterialAgent(LangGraphBaseAgent):
    """
    Supplementary Material Agent for Stage 16 of the research workflow.

    Handles the organization and packaging of supplementary materials including:
    - Content placement analysis (main manuscript vs supplement)
    - Table and figure organization with proper numbering
    - Extended methods compilation
    - Data availability statements
    - Appendices with checklists and forms
    - Complete package compilation with manifest
    - Journal-specific formatting compliance

    The agent operates after Results Refinement (Stage 15) and can be optionally
    invoked from the ManuscriptAgent for enhanced submission preparation.
    """

    def __init__(self, llm_bridge: Any, checkpointer: Optional[Any] = None):
        """
        Initialize the SupplementaryMaterial agent.

        Args:
            llm_bridge: AIRouterBridge instance for LLM calls
            checkpointer: Optional LangGraph checkpointer for state persistence
        """
        super().__init__(
            llm_bridge=llm_bridge,
            stages=[16],  # Stage 16: After Results Refinement
            agent_id='supplementary_material',  # Note: extending AgentId type
            checkpointer=checkpointer,
        )

    def get_quality_criteria(self) -> Dict[str, Any]:
        """
        Quality criteria for SupplementaryMaterial agent.

        Returns:
            Dict of criterion name to threshold values
        """
        return {
            'content_placement_decisions': True,     # Main vs supplement decisions made
            'table_organization_complete': True,     # All tables properly numbered (S1, S2...)
            'figure_organization_complete': True,    # All figures properly numbered (S1, S2...)
            'methods_detail_adequate': True,         # Extended methods comprehensive
            'data_statement_complete': True,         # Data availability statement present
            'appendices_organized': True,            # Appendices properly structured
            'package_size_limit': 50.0,            # MB - configurable by journal
            'manifest_complete': True,               # File manifest generated
            'journal_compliance': True,              # Meets target journal requirements
            'cross_references_valid': True,          # All cross-references work
            'numbering_consistent': True,            # Sequential numbering (S1, S2, S3...)
        }

    def build_graph(self) -> StateGraph:
        """
        Build the SupplementaryMaterial agent's LangGraph.

        Graph structure:
        Entry: identify_supplementary_content
        Parallel: organize_tables || organize_figures || compile_methods
        Sequential: generate_data_statement → create_appendices → package_materials
        Exit: quality_gate → (improve_loop or END)

        Returns:
            Compiled StateGraph with checkpointer
        """
        graph = StateGraph(AgentState)

        # Add all nodes
        graph.add_node("identify_supplementary_content", self.identify_supplementary_content_node)
        graph.add_node("organize_supplementary_tables", self.organize_supplementary_tables_node)
        graph.add_node("organize_supplementary_figures", self.organize_supplementary_figures_node)
        graph.add_node("compile_extended_methods", self.compile_extended_methods_node)
        graph.add_node("generate_data_statement", self.generate_data_statement_node)
        graph.add_node("create_appendices", self.create_appendices_node)
        graph.add_node("package_materials", self.package_materials_node)
        graph.add_node("quality_gate", self.quality_gate_node)
        graph.add_node("human_review", self.human_review_node)
        graph.add_node("save_version", self.save_version_node)
        graph.add_node("improve", self.improve_node)

        # Entry point
        graph.set_entry_point("identify_supplementary_content")

        # After content identification, parallel processing
        graph.add_edge("identify_supplementary_content", "organize_supplementary_tables")
        graph.add_edge("identify_supplementary_content", "organize_supplementary_figures")
        graph.add_edge("identify_supplementary_content", "compile_extended_methods")

        # Sequential processing after parallel completion
        graph.add_edge("organize_supplementary_tables", "generate_data_statement")
        graph.add_edge("organize_supplementary_figures", "generate_data_statement")
        graph.add_edge("compile_extended_methods", "generate_data_statement")
        
        graph.add_edge("generate_data_statement", "create_appendices")
        graph.add_edge("create_appendices", "package_materials")
        graph.add_edge("package_materials", "quality_gate")

        # Quality gate routing
        graph.add_conditional_edges(
            "quality_gate",
            self._route_after_quality_gate,
            {
                "human_review": "human_review",
                "save_version": "save_version",
                "end": END,
            }
        )

        graph.add_edge("human_review", "save_version")

        # Improvement loop routing
        graph.add_conditional_edges(
            "save_version",
            self.should_continue_improvement,
            {
                "continue": "improve",
                "complete": END,
            }
        )

        # Route improvement back to appropriate node
        graph.add_conditional_edges(
            "improve",
            self._route_improvement,
            {
                "content_identification": "identify_supplementary_content",
                "table_organization": "organize_supplementary_tables",
                "figure_organization": "organize_supplementary_figures",
                "methods_compilation": "compile_extended_methods",
                "data_statement": "generate_data_statement",
                "appendices": "create_appendices",
                "packaging": "package_materials",
                "full": "identify_supplementary_content",
            }
        )

        return graph.compile(checkpointer=self.checkpointer)

    def _route_after_quality_gate(self, state: AgentState) -> str:
        """Route after quality gate evaluation."""
        gate_status = state.get('gate_status', 'pending')
        governance_mode = state.get('governance_mode', 'DEMO')

        if governance_mode == 'LIVE' and gate_status in ['passed', 'needs_human']:
            return "human_review"

        if gate_status == 'needs_human':
            return "human_review"

        if gate_status == 'passed':
            return "save_version"

        return "save_version"

    def _route_improvement(self, state: AgentState) -> str:
        """Route improvement to specific node based on feedback."""
        feedback = state.get('feedback', '').lower()
        gate_result = state.get('gate_result', {})
        failed_criteria = gate_result.get('criteria_failed', [])

        # Check feedback for specific keywords
        if any(keyword in feedback for keyword in ['placement', 'main text', 'supplement decision']):
            return "content_identification"
        if any(keyword in feedback for keyword in ['table', 'supplementary table', 's1', 's2']):
            return "table_organization"
        if any(keyword in feedback for keyword in ['figure', 'supplementary figure', 'image']):
            return "figure_organization"
        if any(keyword in feedback for keyword in ['method', 'protocol', 'procedure']):
            return "methods_compilation"
        if any(keyword in feedback for keyword in ['data', 'availability', 'sharing']):
            return "data_statement"
        if any(keyword in feedback for keyword in ['appendix', 'checklist', 'form']):
            return "appendices"
        if any(keyword in feedback for keyword in ['package', 'manifest', 'file']):
            return "packaging"

        # Check failed criteria
        if 'content_placement_decisions' in failed_criteria:
            return "content_identification"
        if 'table_organization_complete' in failed_criteria:
            return "table_organization"
        if 'figure_organization_complete' in failed_criteria:
            return "figure_organization"
        if 'methods_detail_adequate' in failed_criteria:
            return "methods_compilation"
        if 'data_statement_complete' in failed_criteria:
            return "data_statement"
        if 'appendices_organized' in failed_criteria:
            return "appendices"
        if 'manifest_complete' in failed_criteria:
            return "packaging"

        return "full"

    # =========================================================================
    # Core Node Implementations - Phase 2A
    # =========================================================================

    async def identify_supplementary_content_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Entry node: Analyze content and decide what goes to main manuscript vs supplement.

        Evaluates all tables, figures, methods, and analyses to determine optimal
        placement based on journal requirements, content importance, and space constraints.
        """
        logger.info(f"[SupplementaryMaterial] Stage 16: Identifying supplementary content", 
                   extra={'run_id': state.get('run_id')})

        messages = state.get('messages', [])
        previous_output = state.get('current_output', '')
        
        # Extract content from previous stages
        user_context = "\n".join([
            m['content'] if isinstance(m, dict) else str(m)
            for m in messages
            if (isinstance(m, dict) and m.get('role') == 'user')
        ])

        # Default journal format if not specified
        journal_format = getattr(state, 'journal_format', 'generic')
        
        # Get journal-specific requirements
        try:
            journal_reqs = JournalRequirements.get_requirements(JournalFormat(journal_format))
        except (ValueError, AttributeError):
            journal_reqs = JournalRequirements.get_requirements(JournalFormat.GENERIC)

        prompt = f"""Analyze this research output and determine content placement for manuscript submission.

Previous Analysis Results:
{previous_output}

Research Context:
{user_context}

Journal Requirements:
- Target Journal: {journal_format.upper()}
- Max supplement size: {journal_reqs.max_size_mb}MB
- Preferred formats: {[f.value for f in journal_reqs.preferred_formats]}
- Max pages: {journal_reqs.max_supplement_pages or 'unlimited'}

CONTENT PLACEMENT ANALYSIS:

For each table, figure, analysis result, and method detail, decide:

1. MAIN MANUSCRIPT (include in primary text if):
   - Essential for understanding main findings
   - Directly supports primary/secondary outcomes
   - Required for study comprehension
   - Space allows within journal limits

2. SUPPLEMENTARY MATERIAL (move to supplement if):
   - Provides additional detail but not essential
   - Secondary analyses or subgroup analyses
   - Detailed methodological information
   - Extended datasets or raw results
   - Additional figures showing same data differently

3. ONLINE ONLY (digital-only supplement if):
   - Very large datasets
   - Interactive content
   - Video/audio materials
   - Code repositories

4. EXCLUDE (don't include if):
   - Preliminary/exploratory analyses
   - Quality control outputs
   - Internal validation results
   - Redundant presentations

PLACEMENT DECISIONS:
Analyze each content element and provide:
- Item type (table/figure/method/analysis)
- Current description
- Placement recommendation (main/supplement/online/exclude)
- Reasoning for placement decision
- Priority level (high/medium/low)

SUPPLEMENT ORGANIZATION PREVIEW:
- Estimated number of supplementary tables needed
- Estimated number of supplementary figures needed
- Key appendices required (methods, checklists, etc.)
- Estimated total package size

Provide a structured analysis with clear recommendations for content organization."""

        content_analysis = await self.call_llm(
            prompt=prompt,
            task_type='content_placement_analysis',
            state=state,
            model_tier='STANDARD',
        )

        message = self.add_assistant_message(
            state,
            f"I've analyzed your content for supplementary material organization:\n\n{content_analysis}"
        )

        return {
            'current_stage': 16,
            'content_placement_analysis': content_analysis,
            'current_output': content_analysis,
            'messages': [message],
        }

    async def organize_supplementary_tables_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Organize tables designated for supplementary material with proper numbering.

        Creates properly formatted supplementary tables with sequential numbering (S1, S2, S3...)
        and appropriate captions, cross-references, and formatting for the target journal.
        """
        logger.info(f"[SupplementaryMaterial] Organizing supplementary tables", 
                   extra={'run_id': state.get('run_id')})

        content_analysis = state.get('content_placement_analysis', '')
        previous_output = state.get('current_output', '')

        prompt = f"""Organize tables designated for supplementary material with proper formatting.

Content Placement Analysis:
{content_analysis}

Previous Analysis Results:
{previous_output}

SUPPLEMENTARY TABLE ORGANIZATION:

From the content analysis, identify all tables designated for supplementary material and organize them as follows:

**TABLE NUMBERING:**
- Use sequential numbering: S1, S2, S3, S4...
- Maintain logical order (follow manuscript flow)
- Ensure consistent numbering throughout

**FOR EACH SUPPLEMENTARY TABLE:**

1. **Table S[X]: [Descriptive Title]**
   - Clear, informative title
   - Follows journal capitalization style
   - Describes content accurately

2. **Table Content:**
   - Well-formatted table structure
   - Appropriate headers and subheaders
   - Proper alignment and spacing
   - Statistical values with correct precision
   - Missing data indicators (if applicable)

3. **Table Caption:**
   - Comprehensive description of table content
   - Explanation of abbreviations
   - Statistical methods note (if applicable)
   - Data source information
   - Any relevant footnotes

4. **Cross-References:**
   - Note where table is referenced in main text
   - Identify related supplementary materials
   - Link to relevant methods or analyses

**FORMATTING REQUIREMENTS:**
- Maintain consistency across all tables
- Follow target journal style guidelines
- Ensure readability and professional appearance
- Include proper footnotes and legends

**OUTPUT FORMAT:**
Provide each organized table with:
- Table number (S1, S2, etc.)
- Table title
- Formatted table content
- Complete caption
- Cross-reference notes
- File format recommendation

Create a comprehensive organization of all supplementary tables that meets publication standards."""

        table_organization = await self.call_llm(
            prompt=prompt,
            task_type='supplementary_table_organization',
            state=state,
            model_tier='STANDARD',
        )

        return {
            'supplementary_tables_organized': table_organization,
            'current_output': table_organization,
        }

    async def organize_supplementary_figures_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Organize figures designated for supplementary material with proper numbering.

        Creates properly formatted supplementary figures with sequential numbering (S1, S2, S3...)
        and appropriate captions, legends, and cross-references for the target journal.
        """
        logger.info(f"[SupplementaryMaterial] Organizing supplementary figures", 
                   extra={'run_id': state.get('run_id')})

        content_analysis = state.get('content_placement_analysis', '')
        previous_output = state.get('current_output', '')

        prompt = f"""Organize figures designated for supplementary material with proper formatting.

Content Placement Analysis:
{content_analysis}

Previous Analysis Results:
{previous_output}

SUPPLEMENTARY FIGURE ORGANIZATION:

From the content analysis, identify all figures designated for supplementary material and organize them as follows:

**FIGURE NUMBERING:**
- Use sequential numbering: S1, S2, S3, S4...
- Maintain logical order (follow manuscript narrative)
- Coordinate with table numbering (may interleave)
- Ensure consistency throughout package

**FOR EACH SUPPLEMENTARY FIGURE:**

1. **Figure S[X]: [Descriptive Title]**
   - Clear, informative title
   - Accurately describes the visualization
   - Follows journal capitalization conventions

2. **Figure Specifications:**
   - Recommended file format (PDF, PNG, etc.)
   - Resolution requirements (300 DPI minimum)
   - Size specifications for journal
   - Color vs. grayscale considerations

3. **Figure Caption:**
   - Comprehensive description of what is shown
   - Explanation of symbols, lines, colors
   - Statistical test information
   - Sample sizes and data sources
   - Interpretation guidance for readers

4. **Figure Legend (if applicable):**
   - Symbol definitions
   - Line style explanations
   - Color coding keys
   - Panel descriptions (A, B, C...)

5. **Cross-References:**
   - Where figure is mentioned in main text
   - Related tables or other figures
   - Relevant methods sections

**FORMATTING REQUIREMENTS:**
- Consistent style across all figures
- High-quality, publication-ready specifications
- Clear labeling and annotations
- Professional appearance
- Accessibility considerations (colorblind-friendly if possible)

**OUTPUT FORMAT:**
Provide each organized figure with:
- Figure number (S1, S2, etc.)
- Figure title
- Technical specifications
- Complete caption and legend
- Cross-reference information
- File handling recommendations

Create a comprehensive organization of all supplementary figures that meets publication standards."""

        figure_organization = await self.call_llm(
            prompt=prompt,
            task_type='supplementary_figure_organization',
            state=state,
            model_tier='STANDARD',
        )

        return {
            'supplementary_figures_organized': figure_organization,
            'current_output': figure_organization,
        }

    # =========================================================================
    # Extended Processing Nodes - Phase 2B & 2C Implementation
    # =========================================================================

    async def compile_extended_methods_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Compile detailed methodological information for supplementary material.

        Creates comprehensive methodological documentation that provides
        detailed protocols, procedures, and technical specifications beyond
        what is included in the main manuscript methods section.
        """
        logger.info(f"[SupplementaryMaterial] Compiling extended methods", 
                   extra={'run_id': state.get('run_id')})

        content_analysis = state.get('content_placement_analysis', '')
        previous_output = state.get('current_output', '')
        
        # Extract any existing methods information
        messages = state.get('messages', [])
        user_context = "\n".join([
            m['content'] if isinstance(m, dict) else str(m)
            for m in messages
            if (isinstance(m, dict) and m.get('role') == 'user')
        ])

        prompt = f"""Compile detailed methodological information for supplementary material.

Content Placement Analysis:
{content_analysis}

Research Context and Methods:
{user_context}

Previous Analysis:
{previous_output}

CREATE SUPPLEMENTARY METHODS SECTION:

Provide expanded methodological details that support the main manuscript but are too detailed for the primary methods section:

**1. DETAILED STUDY DESIGN**
- Comprehensive study protocol
- Timeline and workflow
- Quality control procedures
- Data collection protocols
- Standardization procedures

**2. EXPANDED PARTICIPANT INFORMATION**
- Detailed eligibility criteria
- Recruitment procedures and timelines
- Screening processes
- Consent procedures
- Follow-up protocols

**3. MEASUREMENT PROCEDURES**
- Detailed measurement protocols
- Instrument specifications and validation
- Calibration procedures
- Inter-rater reliability methods
- Quality assurance measures

**4. STATISTICAL ANALYSIS DETAILS**
- Complete statistical analysis plan
- Model specifications and assumptions
- Sensitivity analysis procedures
- Missing data handling details
- Software versions and settings
- Power calculations and sample size derivation

**5. DATA MANAGEMENT**
- Data collection and entry procedures
- Database design and validation
- Data cleaning and preparation steps
- Version control and audit trails
- Security and privacy measures

**6. QUALITY CONTROL MEASURES**
- Standard operating procedures (SOPs)
- Training and certification requirements
- Monitoring and evaluation procedures
- Error checking and correction protocols
- Documentation requirements

**7. TECHNICAL SPECIFICATIONS**
- Equipment and software details
- Reagent and material specifications
- Environmental conditions
- Technical parameters and settings
- Troubleshooting procedures

**FORMATTING:**
- Organize as numbered appendices (e.g., Appendix A: Study Protocol)
- Include appropriate subheadings
- Use clear, precise technical language
- Reference relevant standards (e.g., ICH-GCP, ISO)
- Include diagrams or flowcharts where helpful

Provide comprehensive methodological documentation suitable for supplementary material."""

        extended_methods = await self.call_llm(
            prompt=prompt,
            task_type='extended_methods_compilation',
            state=state,
            model_tier='STANDARD',
        )

        return {
            'extended_methods_compiled': extended_methods,
            'current_output': extended_methods,
        }

    async def generate_data_statement_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Generate data availability and sharing statement.

        Creates comprehensive statement about data availability, sharing policies,
        access procedures, and compliance with funding agency and journal requirements.
        """
        logger.info(f"[SupplementaryMaterial] Generating data availability statement", 
                   extra={'run_id': state.get('run_id')})

        content_analysis = state.get('content_placement_analysis', '')
        extended_methods = state.get('extended_methods_compiled', '')
        previous_output = state.get('current_output', '')
        
        # Extract context about data sources and types
        messages = state.get('messages', [])
        user_context = "\n".join([
            m['content'] if isinstance(m, dict) else str(m)
            for m in messages
            if (isinstance(m, dict) and m.get('role') == 'user')
        ])

        prompt = f"""Generate a comprehensive data availability and sharing statement.

Content Analysis:
{content_analysis}

Extended Methods:
{extended_methods[:1000]}...

Research Context:
{user_context}

CREATE DATA AVAILABILITY STATEMENT:

Address all required elements for journal submission and regulatory compliance:

**1. DATA AVAILABILITY DECLARATION**
- Clear statement of data availability status
- Types of data collected in the study
- Data formats and organization
- Whether data can be shared publicly

**2. DATA SHARING POLICY**
Choose appropriate category:

*Option A - Publicly Available:*
"The datasets generated and/or analyzed during the current study are available in the [repository name] repository, [URL or DOI]."

*Option B - Available on Request:*
"The datasets generated and/or analyzed during the current study are available from the corresponding author on reasonable request."

*Option C - Restricted Access:*
"The datasets generated and/or analyzed during the current study are not publicly available due to [privacy/ethical/legal restrictions] but are available from the corresponding author on reasonable request and with appropriate permissions."

*Option D - Not Available:*
"The datasets generated and/or analyzed during the current study are not available due to [specific restrictions - e.g., patient privacy, proprietary data, etc.]."

**3. DATA REPOSITORY INFORMATION** (if applicable)
- Repository name and URL
- DOI or accession numbers
- Data submission date
- Access requirements or procedures
- Embargo periods

**4. CODE AND SOFTWARE AVAILABILITY**
- Analysis code availability
- Software versions used
- Code repository information (GitHub, etc.)
- Custom scripts or algorithms

**5. SUPPORTING MATERIALS**
- Study protocol availability
- Data collection instruments
- Analysis plans and specifications
- Additional documentation

**6. ETHICAL AND LEGAL CONSIDERATIONS**
- IRB/Ethics approval limitations
- Informed consent restrictions
- Privacy protection measures
- Data de-identification procedures
- Compliance with data protection regulations (GDPR, HIPAA, etc.)

**7. CONTACT INFORMATION**
- Data access contact person
- Institution and affiliation
- Email and contact details
- Response timeframe expectations

**8. FUNDING AGENCY REQUIREMENTS**
- NIH data sharing policy compliance
- Other funder requirements
- Grant-specific obligations
- Public access mandates

**TEMPLATE COMPLIANCE:**
Ensure the statement meets requirements for major journals:
- Nature journals
- JAMA family
- NEJM
- PLOS ONE
- BMJ

Provide a complete, compliant data availability statement that addresses journal requirements and ethical considerations."""

        data_statement = await self.call_llm(
            prompt=prompt,
            task_type='data_availability_statement',
            state=state,
            model_tier='STANDARD',
        )

        return {
            'data_statement_generated': data_statement,
            'current_output': data_statement,
        }

    async def create_appendices_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Create appendices including checklists, forms, and additional materials.

        Generates organized appendices with reporting checklists (STROBE, CONSORT),
        data collection forms, protocols, and other supporting materials required
        for comprehensive manuscript submission.
        """
        logger.info(f"[SupplementaryMaterial] Creating appendices and checklists", 
                   extra={'run_id': state.get('run_id')})

        content_analysis = state.get('content_placement_analysis', '')
        extended_methods = state.get('extended_methods_compiled', '')
        data_statement = state.get('data_statement_generated', '')
        previous_output = state.get('current_output', '')
        
        # Determine study type for appropriate checklist
        messages = state.get('messages', [])
        user_context = "\n".join([
            m['content'] if isinstance(m, dict) else str(m)
            for m in messages
            if (isinstance(m, dict) and m.get('role') == 'user')
        ])

        prompt = f"""Create comprehensive appendices for supplementary material submission.

Content Analysis:
{content_analysis}

Extended Methods:
{extended_methods[:800]}...

Data Statement:
{data_statement[:500]}...

Research Context:
{user_context}

CREATE SUPPLEMENTARY APPENDICES:

**APPENDIX A: REPORTING CHECKLIST**

Determine appropriate checklist based on study type:
- STROBE (observational studies)
- CONSORT (randomized controlled trials) 
- PRISMA (systematic reviews/meta-analyses)
- STARD (diagnostic accuracy studies)
- SQUIRE (quality improvement studies)
- SPIRIT (protocols)

For the identified checklist type:
1. List all required items with item numbers
2. Indicate page numbers where each item is addressed
3. Provide brief descriptions of how each item is met
4. Flag any items that may not be applicable (N/A)

**APPENDIX B: DATA COLLECTION INSTRUMENTS**
- Case report forms (CRF)
- Questionnaires and surveys
- Interview guides
- Assessment tools and scales
- Measurement protocols
- Data extraction forms

**APPENDIX C: STATISTICAL ANALYSIS PLAN** 
- Detailed analysis procedures
- Variable definitions and coding
- Model specifications
- Sensitivity analysis plans
- Missing data handling
- Interim analysis procedures (if applicable)

**APPENDIX D: STUDY PROTOCOLS AND PROCEDURES**
- Standard operating procedures (SOPs)
- Training materials
- Quality control procedures
- Monitoring plans
- Adverse event procedures

**APPENDIX E: REGULATORY DOCUMENTS** (if applicable)
- IRB/Ethics approval letters
- Informed consent forms
- HIPAA authorization forms
- Trial registration information
- Protocol amendments

**APPENDIX F: ADDITIONAL ANALYSES**
- Exploratory analyses
- Subgroup analyses details
- Sensitivity analyses results
- Post-hoc analyses
- Secondary outcomes

**APPENDIX G: TECHNICAL SPECIFICATIONS**
- Laboratory methods and protocols
- Equipment specifications
- Software and algorithm details
- Validation procedures
- Quality assurance measures

**FORMATTING GUIDELINES:**
- Clear section headings and numbering
- Professional presentation
- Consistent formatting throughout
- Appropriate cross-references
- Page numbers and table of contents
- Proper citation of instruments and methods

Organize all appendices in a logical sequence that supports the main manuscript and provides comprehensive documentation for study replication and evaluation."""

        appendices = await self.call_llm(
            prompt=prompt,
            task_type='appendices_creation',
            state=state,
            model_tier='STANDARD',
        )

        return {
            'appendices_created': appendices,
            'current_output': appendices,
        }

    async def package_materials_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Package all supplementary materials with manifest generation.

        Compiles all supplementary tables, figures, methods, statements, and appendices
        into a complete submission package with detailed manifest, file organization,
        and journal-specific formatting compliance.
        """
        logger.info(f"[SupplementaryMaterial] Packaging complete submission materials", 
                   extra={'run_id': state.get('run_id')})

        # Gather all components
        content_analysis = state.get('content_placement_analysis', '')
        tables_organized = state.get('supplementary_tables_organized', '')
        figures_organized = state.get('supplementary_figures_organized', '')
        extended_methods = state.get('extended_methods_compiled', '')
        data_statement = state.get('data_statement_generated', '')
        appendices = state.get('appendices_created', '')
        
        # Get journal requirements
        journal_format = getattr(state, 'journal_format', 'generic')
        try:
            journal_reqs = JournalRequirements.get_requirements(JournalFormat(journal_format))
        except (ValueError, AttributeError):
            journal_reqs = JournalRequirements.get_requirements(JournalFormat.GENERIC)

        prompt = f"""Package all supplementary materials into a complete submission package.

JOURNAL REQUIREMENTS:
- Target Journal: {journal_format.upper()}
- Max Package Size: {journal_reqs.max_size_mb}MB
- Preferred Formats: {[f.value for f in journal_reqs.preferred_formats]}
- Table Format: {journal_reqs.table_format}
- Figure Format: {journal_reqs.figure_format}
- Naming Convention: {journal_reqs.naming_convention}

SUPPLEMENTARY MATERIALS TO PACKAGE:

1. Content Placement Analysis:
{content_analysis[:500]}...

2. Supplementary Tables:
{tables_organized[:500]}...

3. Supplementary Figures:
{figures_organized[:500]}...

4. Extended Methods:
{extended_methods[:500]}...

5. Data Availability Statement:
{data_statement[:300]}...

6. Appendices:
{appendices[:500]}...

CREATE COMPLETE SUBMISSION PACKAGE:

**PACKAGE STRUCTURE:**

```
Supplementary_Material_Package/
├── 00_Submission_Manifest.pdf
├── 01_Supplementary_Tables/
│   ├── Table_S1_[descriptive_name].{journal_reqs.table_format}
│   ├── Table_S2_[descriptive_name].{journal_reqs.table_format}
│   └── [...]
├── 02_Supplementary_Figures/
│   ├── Figure_S1_[descriptive_name].{journal_reqs.figure_format}
│   ├── Figure_S2_[descriptive_name].{journal_reqs.figure_format}
│   └── [...]
├── 03_Extended_Methods/
│   ├── Extended_Methods_Section.pdf
│   └── Protocols_and_Procedures.pdf
├── 04_Data_Availability/
│   ├── Data_Availability_Statement.pdf
│   └── Repository_Information.txt
├── 05_Appendices/
│   ├── Appendix_A_Reporting_Checklist.pdf
│   ├── Appendix_B_Data_Collection_Forms.pdf
│   ├── Appendix_C_Statistical_Analysis_Plan.pdf
│   └── [...]
└── 06_Supporting_Materials/
    ├── README.txt
    └── Technical_Specifications.pdf
```

**1. SUBMISSION MANIFEST**
Create comprehensive manifest including:
- Package overview and contents
- File descriptions and purposes
- Cross-reference guide (main text → supplement)
- Version information and timestamps
- Contact information
- Submission checklist

**2. FILE NAMING CONVENTION**
Apply journal-specific naming:
- Consistent numbering (S1, S2, S3...)
- Descriptive but concise names
- Appropriate file extensions
- Version control indicators

**3. QUALITY ASSURANCE CHECKLIST**
✓ All files properly formatted
✓ Cross-references validated
✓ Numbering sequential and consistent
✓ File sizes within limits
✓ Required elements present
✓ Journal guidelines followed
✓ Accessibility compliance
✓ Professional presentation

**4. PACKAGE SUMMARY**
Provide:
- Total number of supplementary items
- Estimated file sizes
- Format compliance confirmation
- Review completion status
- Submission readiness assessment

**5. SUBMISSION INSTRUCTIONS**
- How to submit package to journal
- Required cover letter elements
- Online submission procedures
- Contact information for questions
- Timeline and next steps

**OUTPUT REQUIREMENTS:**
1. Complete package organization plan
2. Detailed file manifest with descriptions
3. Quality assurance confirmation
4. Size and format compliance verification
5. Submission readiness assessment
6. Next steps guidance

Ensure the package is publication-ready and meets all journal requirements."""

        package_compilation = await self.call_llm(
            prompt=prompt,
            task_type='materials_packaging',
            state=state,
            model_tier='PREMIUM',  # Important final compilation
        )

        message = self.add_assistant_message(
            state,
            f"I've compiled your complete supplementary material package:\n\n{package_compilation}"
        )

        return {
            'materials_packaged': package_compilation,
            'package_complete': True,
            'current_output': package_compilation,
            'messages': [message],
        }

    # =========================================================================
    # Improvement Loop Node
    # =========================================================================

    async def improve_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Improvement node for iterating based on feedback.

        Analyzes feedback and quality gate results to improve specific aspects
        of the supplementary material organization and packaging.
        """
        logger.info(f"[SupplementaryMaterial] Improving based on feedback")
        
        feedback = state.get('feedback', '')
        current_output = state.get('current_output', '')
        gate_result = state.get('gate_result', {})

        prompt = f"""Improve the supplementary material organization based on feedback.

Current Output:
{current_output}

Feedback:
{feedback}

Quality Gate Results:
- Score: {gate_result.get('score', 'N/A')}
- Failed Criteria: {gate_result.get('criteria_failed', [])}
- Reason: {gate_result.get('reason', 'N/A')}

Address the specific issues raised, focusing on:
1. Content placement decisions
2. Table and figure organization
3. Numbering consistency
4. Cross-reference accuracy
5. Journal compliance requirements
6. Package completeness

Provide improved supplementary material organization that addresses all concerns."""

        improved_result = await self.call_llm(
            prompt=prompt,
            task_type='supplementary_improvement',
            state=state,
            model_tier='STANDARD',
        )

        return {
            'current_output': improved_result,
            'feedback': None,
        }

    # =========================================================================
    # Quality Criteria Evaluation - SupplementaryMaterial-specific
    # =========================================================================

    def _evaluate_criterion(
        self,
        criterion: str,
        threshold: Any,
        output: str,
        state: AgentState,
    ) -> tuple[bool, float]:
        """Evaluate SupplementaryMaterial-specific criteria."""
        output_lower = output.lower()

        if criterion == 'content_placement_decisions':
            placement_indicators = ['main manuscript', 'supplement', 'placement', 'decision']
            has_placement = sum(1 for indicator in placement_indicators if indicator in output_lower) >= 2
            return has_placement or bool(state.get('content_placement_analysis')), 1.0 if has_placement else 0.5

        if criterion == 'table_organization_complete':
            table_indicators = ['table s1', 'table s2', 'supplementary table', 'organized']
            has_tables = sum(1 for indicator in table_indicators if indicator in output_lower) >= 2
            return has_tables or bool(state.get('supplementary_tables_organized')), 1.0 if has_tables else 0.5

        if criterion == 'figure_organization_complete':
            figure_indicators = ['figure s1', 'figure s2', 'supplementary figure', 'organized']
            has_figures = sum(1 for indicator in figure_indicators if indicator in output_lower) >= 2
            return has_figures or bool(state.get('supplementary_figures_organized')), 1.0 if has_figures else 0.5

        if criterion == 'methods_detail_adequate':
            methods_indicators = ['extended method', 'detailed protocol', 'procedure', 'methodology']
            has_methods = sum(1 for indicator in methods_indicators if indicator in output_lower) >= 2
            return has_methods or bool(state.get('extended_methods_compiled')), 1.0 if has_methods else 0.5

        if criterion == 'data_statement_complete':
            data_indicators = ['data availability', 'data sharing', 'repository', 'access']
            has_data = sum(1 for indicator in data_indicators if indicator in output_lower) >= 2
            return has_data or bool(state.get('data_statement_generated')), 1.0 if has_data else 0.5

        if criterion == 'appendices_organized':
            appendix_indicators = ['appendix', 'checklist', 'form', 'additional']
            has_appendices = sum(1 for indicator in appendix_indicators if indicator in output_lower) >= 2
            return has_appendices or bool(state.get('appendices_created')), 1.0 if has_appendices else 0.5

        if criterion == 'package_size_limit' and isinstance(threshold, (int, float)):
            # Estimate package size from content (simplified)
            estimated_size = len(output) / 1000000  # Rough estimate: 1MB per 1M chars
            passed = estimated_size <= threshold
            score = 1.0 if passed else max(0, 1 - (estimated_size - threshold) / threshold)
            return passed, score

        if criterion == 'manifest_complete':
            manifest_indicators = ['manifest', 'file list', 'package content', 'submission']
            has_manifest = sum(1 for indicator in manifest_indicators if indicator in output_lower) >= 2
            return has_manifest or bool(state.get('materials_packaged')), 1.0 if has_manifest else 0.5

        if criterion == 'journal_compliance':
            compliance_indicators = ['journal', 'format', 'requirement', 'guideline']
            has_compliance = sum(1 for indicator in compliance_indicators if indicator in output_lower) >= 2
            return has_compliance, 1.0 if has_compliance else 0.6

        if criterion == 'cross_references_valid':
            reference_indicators = ['reference', 'cross-reference', 's1', 's2', 'table', 'figure']
            has_references = sum(1 for indicator in reference_indicators if indicator in output_lower) >= 3
            return has_references, 1.0 if has_references else 0.7

        if criterion == 'numbering_consistent':
            numbering_indicators = ['s1', 's2', 's3', 'sequential', 'numbering']
            has_numbering = sum(1 for indicator in numbering_indicators if indicator in output_lower) >= 2
            return has_numbering, 1.0 if has_numbering else 0.7

        return super()._evaluate_criterion(criterion, threshold, output, state)


# =============================================================================
# Utility Functions for Supplementary Material Agent
# =============================================================================

def create_supplementary_material_state(
    study_id: str,
    manuscript_id: str,
    project_id: str,
    main_manuscript: str = '',
    all_tables: List[Dict[str, Any]] = None,
    all_figures: List[Dict[str, Any]] = None,
    detailed_methods: str = '',
    journal_format: JournalFormat = JournalFormat.GENERIC,
    **kwargs
) -> SupplementaryMaterialState:
    """
    Factory function to create a SupplementaryMaterialState.

    Args:
        study_id: Unique study identifier
        manuscript_id: Manuscript identifier
        project_id: Research project ID
        main_manuscript: Main manuscript text
        all_tables: List of all generated tables
        all_figures: List of all generated figures
        detailed_methods: Detailed methods from protocol
        journal_format: Target journal format
        **kwargs: Additional state parameters

    Returns:
        Initialized SupplementaryMaterialState
    """
    return SupplementaryMaterialState(
        study_id=study_id,
        manuscript_id=manuscript_id,
        project_id=project_id,
        main_manuscript=main_manuscript,
        all_tables=all_tables or [],
        all_figures=all_figures or [],
        detailed_methods=detailed_methods,
        journal_format=journal_format,
        **kwargs
    )


def validate_supplementary_package(
    state: SupplementaryMaterialState,
    journal_requirements: Optional[JournalRequirements] = None
) -> List[str]:
    """
    Validate a supplementary material package for completeness and compliance.

    Args:
        state: SupplementaryMaterialState to validate
        journal_requirements: Optional journal-specific requirements

    Returns:
        List of validation issues found (empty if valid)
    """
    issues = []
    
    # Use built-in validation from state
    issues.extend(state.validate_completeness())
    
    # Additional validation against journal requirements
    if journal_requirements:
        if state.package_size_mb > journal_requirements.max_size_mb:
            issues.append(f"Package size ({state.package_size_mb:.1f}MB) exceeds journal limit ({journal_requirements.max_size_mb}MB)")
        
        if journal_requirements.max_supplement_pages and state.total_supplement_pages > journal_requirements.max_supplement_pages:
            issues.append(f"Page count ({state.total_supplement_pages}) exceeds journal limit ({journal_requirements.max_supplement_pages})")
    
    return issues


def estimate_package_size(
    tables: List[SupplementaryTable],
    figures: List[SupplementaryFigure],
    appendices: List[Appendix]
) -> float:
    """
    Estimate the total package size in MB.

    Args:
        tables: List of supplementary tables
        figures: List of supplementary figures  
        appendices: List of appendices

    Returns:
        Estimated package size in MB
    """
    size_mb = 0.0
    
    # Estimate table sizes (text-based)
    for table in tables:
        size_mb += len(table.content) / 1000000  # ~1MB per 1M characters
    
    # Estimate figure sizes (assume larger for graphics)
    for figure in figures:
        if figure.format in [FileFormat.PDF, FileFormat.PNG]:
            size_mb += 2.0  # Estimate 2MB per high-res figure
        else:
            size_mb += 0.5  # Smaller formats
    
    # Estimate appendix sizes
    for appendix in appendices:
        size_mb += len(appendix.content) / 2000000  # Smaller factor for text
    
    return size_mb