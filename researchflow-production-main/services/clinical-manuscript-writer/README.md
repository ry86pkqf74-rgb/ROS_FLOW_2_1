# Clinical Manuscript Writer - Evidence Synthesis Agent

## Overview
This is a **LangSmith-powered custom agent** specialized in clinical research manuscript writing using the **IMRaD format** (Introduction, Methods, Results, and Discussion). The agent adheres to CONSORT, SPIRIT, and other clinical reporting guidelines.

## Import Details
- **Source**: LangSmith Custom Agent
- **Import Date**: February 7, 2026
- **Location**: `services/clinical-manuscript-writer/`
- **Integration Status**: ✅ Fully aligned with ResearchFlow workflow

## Agent Capabilities

### Core Functions
1. **Clinical Manuscript Drafting**: Creates IMRaD-formatted manuscript sections
2. **Evidence Synthesis**: Integrates published literature and clinical data
3. **Compliance Checking**: Validates against CONSORT/SPIRIT guidelines
4. **Statistical Review**: Audits statistical accuracy and consistency
5. **Data Extraction**: Processes raw clinical data from Google Sheets/URLs
6. **PHI Protection**: Ensures HIPAA-safe language throughout

### Specialized Subagents

#### 1. Literature Research Agent
- Searches published literature for supporting evidence
- Uses Tavily and Exa web search with neural/deep search
- Focuses on "research paper" category for academic sources
- Reads URL content for full text analysis

#### 2. Statistical Review Agent
- Audits Results and Methods sections for statistical accuracy
- Validates test appropriateness and internal consistency
- Checks text-table concordance
- Ensures proper statistical reporting

#### 3. CONSORT/SPIRIT Compliance Agent
- Systematically evaluates manuscripts against clinical reporting standards
- Supports CONSORT, SPIRIT, STROBE, PRISMA, STARD, CARE, ARRIVE checklists
- Validates all extensions and reporting requirements
- Pre-submission compliance verification

#### 4. Data Extraction Agent
- Reads raw clinical data from Google Sheets or URLs
- Produces structured summaries and descriptive statistics
- Generates baseline characteristics tables
- Screens for PHI and data quality issues

## Tool Integration

### Google Workspace
- **Google Docs**: `create_document`, `append_text`, `read_document`, `replace_text`
- **Google Sheets**: `get_spreadsheet`, `read_range`, `create_spreadsheet`, `write_range`, `append_rows`

### Web Search & Research
- **Tavily Web Search**: General web search capabilities
- **Exa Web Search**: Neural/deep search for research papers
- **Read URL Content**: Full text extraction from sources

### Communication
- **Gmail**: Draft email for journal submissions and co-author correspondence

## Workflow Integration

### Within ResearchFlow Pipeline
```
Protocol Generation (Agent 1-4)
    ↓
Literature Synthesis (Agent 7 - Clinical Manuscript Writer)
    ↓ 
Evidence Integration & Validation
    ↓
Manuscript Generation (IMRaD format)
    ↓
Compliance & Statistical Review
    ↓
Final Output to Google Docs
```

### Typical Usage Flow
1. **Input**: Receive clinical data, research protocols, or literature review requests
2. **Analysis**: Extract and structure data using Data Extraction subagent
3. **Research**: Gather supporting literature via Literature Research subagent
4. **Drafting**: Generate manuscript sections following IMRaD format
5. **Validation**: Run Statistical Review and Compliance checks
6. **Output**: Write finalized sections to Google Docs
7. **Tracking**: Maintain Evidence Ledger Spreadsheet for traceability

## Configuration

### LangSmith Setup
The agent is configured via `config.json`:
```json
{
  "name": "Clinical Manuscript Writer",
  "description": "IMRaD format manuscript writer with CONSORT/SPIRIT compliance",
  "visibility_scope": "tenant",
  "triggers_paused": false
}
```

### Environment Requirements
- LangSmith API access
- Google Workspace API credentials (Docs + Sheets)
- OpenAI/Anthropic API keys for LLM backend
- Tavily and Exa search API keys

### API Endpoints
- **LangSmith**: `https://tools.langchain.com`
- **MCP Server**: Agent Builder integration

## Files Structure
```
clinical-manuscript-writer/
├── AGENTS.md           # Main agent instructions and workflow
├── config.json         # Agent configuration
├── tools.json         # Tool definitions and integrations
├── README.md          # This file
└── subagents/
    ├── Literature_Research_Agent/
    ├── Statistical_Review_Agent/
    ├── CONSORT_SPIRIT_Compliance_Agent/
    └── Data_Extraction_Agent/
```

## Integration Points

### With Existing ResearchFlow Services

#### 1. Protocol Worker Integration
- Receives protocol outputs from `services/worker/`
- Uses protocol data as input for manuscript Methods sections
- Aligns protocol generation with manuscript requirements

#### 2. Literature Review Integration
- Complements systematic review workflows
- Provides evidence synthesis for protocol enhancement
- Creates structured evidence ledgers

#### 3. Compliance Integration
- Works alongside security review agents (Agent 1-2)
- Ensures HIPAA compliance in manuscript outputs
- Validates PHI protection in all generated content

#### 4. Quality Assurance Integration
- Coordinates with test coverage agent (Agent 3)
- Validates manuscript outputs against quality standards
- Ensures reproducible evidence synthesis

## Usage Examples

### Example 1: Generate Introduction Section
```
Request: "Generate an Introduction section for our RCT on diabetes management"
Process: 
  1. Data Extraction Agent: Parse study objectives
  2. Literature Research Agent: Find relevant background studies
  3. Draft Introduction with proper citations
  4. Compliance Agent: Validate structure
  5. Output to Google Docs
```

### Example 2: Create Results Section from Data
```
Request: "Analyze trial data and create Results section"
Process:
  1. Data Extraction Agent: Load data from Google Sheets
  2. Generate descriptive statistics and tables
  3. Statistical Review Agent: Verify accuracy
  4. Draft Results with statistical tests
  5. Compliance Agent: Check CONSORT adherence
  6. Output formatted tables and text
```

### Example 3: Full Manuscript Generation
```
Request: "Create complete manuscript from protocol and data"
Process:
  1. Extract protocol and clinical data
  2. Literature search for each section
  3. Generate all IMRaD sections in sequence
  4. Run comprehensive compliance check
  5. Statistical validation across all sections
  6. Create Evidence Ledger Spreadsheet
  7. Output complete manuscript to Google Docs
```

## Best Practices

### 1. Always Validate Data
- Use Data Extraction Agent before drafting
- Verify data quality and completeness
- Screen for PHI before processing

### 2. Maintain Evidence Traceability
- Create Evidence Ledger Spreadsheets
- Link all claims to source data/literature
- Document search strategies

### 3. Run Compliance Checks
- Validate against appropriate checklist (CONSORT/SPIRIT/etc.)
- Check before final submission
- Address all compliance items

### 4. Statistical Rigor
- Use Statistical Review Agent after drafting Results
- Verify test appropriateness
- Ensure text-table concordance

### 5. Iterative Refinement
- Draft → Review → Refine cycle
- Address all subagent feedback
- Multiple compliance passes if needed

## Deployment Status

| Component | Status | Notes |
|-----------|--------|-------|
| Agent Files | ✅ Imported | All files copied successfully |
| Directory Structure | ✅ Created | `/services/clinical-manuscript-writer/` |
| Documentation | ✅ Complete | README and integration docs |
| Workflow Alignment | ✅ Complete | Integrated into agent coordination |
| LangSmith Config | ⚠️ Pending | Requires API credentials setup |
| Google Workspace API | ⚠️ Pending | Requires OAuth configuration |
| Search APIs | ⚠️ Pending | Requires Tavily/Exa API keys |

## Next Steps

### Immediate Actions
1. ✅ Import agent files to repository
2. ✅ Document agent capabilities
3. ✅ Align with workflow coordination
4. ⏳ Set up API credentials
5. ⏳ Test manuscript generation pipeline
6. ⏳ Validate integration with protocol workers

### Configuration Required
1. Set up LangSmith API access
2. Configure Google Workspace OAuth
3. Add Tavily API key
4. Add Exa search API key
5. Set OpenAI/Anthropic API key
6. Test subagent communication

### Testing & Validation
1. Run Literature Research Agent test
2. Validate Data Extraction from sample data
3. Test CONSORT compliance checking
4. Verify Statistical Review accuracy
5. End-to-end manuscript generation test
6. Integration test with protocol outputs

## Support & Documentation

- **Agent Instructions**: See `AGENTS.md` for detailed workflow
- **Tool Definitions**: See `tools.json` for API configurations
- **Subagents**: Each subagent has its own directory with instructions
- **Integration Guide**: See main ResearchFlow documentation

## Contact & Maintenance

- **Imported By**: GitHub user (ry86pkqf74-rgb)
- **Repository**: ROS_FLOW_2_1
- **Branch**: chore/inventory-capture
- **Pull Request**: #32

---

**Status**: ✅ **IMPORTED & OPERATIONALLY ALIGNED**  
**Ready for**: API configuration and integration testing  
**Blocking**: None - can be configured independently
