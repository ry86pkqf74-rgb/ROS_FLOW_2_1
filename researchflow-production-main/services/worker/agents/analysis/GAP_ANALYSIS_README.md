# GapAnalysisAgent - Stage 10 Documentation

## Overview

The **GapAnalysisAgent** is a specialized AI agent for identifying research gaps, comparing current findings to existing literature, and generating prioritized future research directions. It operates as Stage 10 in the ResearchFlow pipeline.

## Key Features

### 1. Multi-Model Architecture
- **Claude Sonnet 4** (Anthropic): Strategic planning and reasoning
- **Grok-2** (xAI): Fast literature comparison
- **Mercury** (InceptionLabs): Structured data analysis
- **OpenAI Embeddings**: Semantic literature similarity (text-embedding-3-large)

### 2. Gap Identification (6 Dimensions)
- **Theoretical Gaps**: Missing explanatory frameworks
- **Empirical Gaps**: Lacking data or evidence
- **Methodological Gaps**: Design limitations
- **Population Gaps**: Underrepresented demographic groups
- **Temporal Gaps**: Outdated evidence
- **Geographic Gaps**: Limited geographic settings

### 3. PICO Framework Integration
Generates structured research questions using:
- **P**: Population/Patient/Problem
- **I**: Intervention/Exposure
- **C**: Comparison/Control
- **O**: Outcome of interest

### 4. Prioritization Matrix
2x2 Impact vs Feasibility matrix:
- **High Priority**: High impact + High feasibility
- **Strategic**: High impact + Low feasibility (long-term)
- **Quick Wins**: Low impact + High feasibility
- **Low Priority**: Low impact + Low feasibility

### 5. Manuscript-Ready Output
- Structured Discussion section text
- Future Directions section
- APA-formatted citations
- Publication-quality narrative

## Installation & Setup

### Required API Keys

```bash
# Claude for planning
export ANTHROPIC_API_KEY="sk-ant-..."

# Grok for literature comparison (optional)
export XAI_API_KEY="xai-..."
export XAI_BASE_URL="https://api.x.ai/v1"

# Mercury for structured analysis (optional)
export MERCURY_API_KEY="..."
# OR
export INCEPTION_API_KEY="..."

# OpenAI for embeddings
export OPENAI_API_KEY="sk-..."
```

### Python Dependencies

```bash
pip install langchain-anthropic langchain-openai openai numpy pydantic
```

## Usage

### Basic Example

```python
from agents.analysis import (
    GapAnalysisAgent,
    create_gap_analysis_agent,
    StudyContext,
    Paper,
    Finding
)

# Initialize agent
agent = create_gap_analysis_agent()

# Prepare study context
study = StudyContext(
    title="Impact of Mindfulness on Anxiety in College Students",
    research_question="Does mindfulness-based stress reduction reduce anxiety?",
    study_type="Randomized Controlled Trial",
    population="College students aged 18-25 with moderate anxiety",
    intervention="8-week MBSR program",
    outcome="GAD-7 anxiety score"
)

# Literature from Stage 6 (LitSearchAgent)
literature = [
    Paper(
        title="Mindfulness for anxiety: A systematic review",
        authors=["Smith J", "Doe A"],
        year=2020,
        abstract="...",
        doi="10.1234/example"
    ),
    # ... more papers
]

# Findings from Stage 7 (StatisticalAnalysisAgent)
findings = [
    Finding(
        description="MBSR reduced anxiety scores by 30% (p < 0.001)",
        effect_size=0.72,
        significance=0.001,
        confidence="high"
    )
]

# Execute gap analysis
result = await agent.execute(
    study=study,
    literature=literature,
    findings=findings
)

# Access results
print(f"Total gaps identified: {result.total_gaps_identified}")
print(f"High-priority gaps: {result.high_priority_count}")
print(f"\nNarrative:\n{result.narrative}")

# Access prioritization matrix
matrix = result.prioritization_matrix
print(f"High Priority Gaps: {len(matrix.high_priority)}")
print(f"Strategic Gaps: {len(matrix.strategic)}")

# Access research suggestions
for suggestion in result.research_suggestions[:3]:
    print(f"\nResearch Question: {suggestion.research_question}")
    print(f"Study Design: {suggestion.study_design}")
    print(f"Priority Score: {suggestion.calculate_priority():.2f}")
    
    if suggestion.pico_framework:
        print(f"PICO: {suggestion.pico_framework.format_research_question()}")
```

### Advanced Usage

#### Custom Prioritization Weights

```python
from agents.analysis.gap_prioritization import GapPrioritizer

prioritizer = GapPrioritizer()
prioritizer.weights = {
    "impact": 0.40,
    "feasibility": 0.40,
    "urgency": 0.20
}

prioritized_gaps = prioritizer.prioritize_gaps(gaps)
```

#### Semantic Literature Comparison

```python
from agents.analysis.gap_analysis_utils import LiteratureComparator

comparator = LiteratureComparator(model="text-embedding-3-large")

findings_text = [
    "Mindfulness reduced anxiety by 30%",
    "Improvements sustained at 6-month follow-up"
]

literature_abstracts = [
    {
        "paper_id": "paper1",
        "title": "...",
        "abstract": "..."
    }
]

comparisons = await comparator.compare_findings_semantic(
    findings_text,
    literature_abstracts
)

for finding, paper_id, title, similarity in comparisons[:5]:
    print(f"{finding} <-> {title}: {similarity:.3f}")
```

#### Generate PICO from Gap

```python
from agents.analysis.pico_generator import PICOGenerator

generator = PICOGenerator()

# From a gap
pico = generator.generate_from_gap(gap, study_context)
print(pico.format_research_question())

# Generate PubMed query
pubmed_query = pico.generate_pubmed_query()
print(f"PubMed Query: {pubmed_query}")
```

## Output Structure

### GapAnalysisResult

```python
{
    "comparisons": {
        "consistent_with": [...],
        "contradicts": [...],
        "novel_findings": [...],
        "extends": [...]
    },
    "gaps": {
        "knowledge": [...],
        "methodological": [...],
        "population": [...],
        "temporal": [...],
        "geographic": [...]
    },
    "prioritized_gaps": [
        {
            "gap": {...},
            "priority_score": 7.5,
            "priority_level": "high",
            "rationale": "...",
            "expected_impact": "..."
        }
    ],
    "prioritization_matrix": {
        "high_priority": [...],
        "strategic": [...],
        "quick_wins": [...],
        "low_priority": [...]
    },
    "research_suggestions": [
        {
            "research_question": "...",
            "pico_framework": {...},
            "study_design": "RCT",
            "priority_score": 8.2
        }
    ],
    "narrative": "...",
    "summary": {
        "total_gaps": 12,
        "high_priority": 3,
        "gap_diversity": 0.83
    }
}
```

## Quality Checks

The agent performs multi-dimensional quality assessment:

1. **Gap Diversity** (20%): Coverage of multiple gap types
2. **PICO Completeness** (20%): All research suggestions have PICO
3. **Literature Grounding** (25%): Each gap linked to citations
4. **Prioritization Clarity** (20%): Matrix and scores provided
5. **Narrative Quality** (15%): 300+ word manuscript-ready text

**Minimum passing score**: 0.80 (80%)

## Integration with Pipeline

### Input Sources
- **Stage 6**: Literature papers from LitSearchAgent
- **Stage 7**: Statistical findings from StatisticalAnalysisAgent
- **Stage 8**: Visualizations from DataVisualizationAgent (optional)

### Output Consumers
- **Stage 11**: ManuscriptGenerationAgent (Discussion & Future Directions)
- **Stage 12**: Grant proposal generation
- **Research Database**: Systematic review protocols

### Workflow Integration

```python
# In orchestrator workflow
async def run_complete_analysis(research_id: str):
    # Stage 6: Literature Search
    lit_result = await lit_search_agent.execute(study_context)
    
    # Stage 7: Statistical Analysis
    stats_result = await stats_agent.execute(study_data)
    
    # Stage 10: Gap Analysis
    gap_result = await gap_analysis_agent.execute(
        study=study_context,
        literature=lit_result.papers,
        findings=stats_result.findings
    )
    
    # Stage 11: Use gaps in manuscript
    manuscript = await manuscript_agent.generate(
        gap_analysis=gap_result
    )
    
    return manuscript
```

## Configuration

### Agent Config

```python
AgentConfig(
    name="GapAnalysisAgent",
    stages=[10],
    rag_collections=["research_methods", "gap_analysis_methods"],
    max_iterations=3,
    quality_threshold=0.80,
    timeout_seconds=300,
    phi_safe=True,
    model_provider="anthropic",
    model_name="claude-sonnet-4-20250514"
)
```

### RAG Collections

Add to vector database:
- GRADE guidelines for evidence quality
- Future Directions section examples from top journals
- PICO framework methodology guides
- Gap taxonomy from systematic reviews

## Performance

### Typical Execution Time
- **Small study** (10 papers): ~30 seconds
- **Medium study** (30 papers): ~60 seconds
- **Large study** (50+ papers): ~120 seconds

### API Costs (Approximate)
- Claude Sonnet 4: ~$0.10 per analysis
- Grok-2: ~$0.02 per analysis
- OpenAI Embeddings: ~$0.01 per 50 papers
- **Total**: ~$0.13 per analysis

## Limitations

1. **Semantic comparison** requires OpenAI API key
2. **Quality** depends on literature quality and quantity
3. **PICO extraction** may need manual refinement
4. **Sample size guidance** is educational, not statistical
5. **Priority scores** are heuristic-based

## Troubleshooting

### Issue: No semantic comparison
**Solution**: Set `OPENAI_API_KEY` for embeddings

### Issue: Low quality scores
**Causes**:
- Insufficient literature (<10 papers)
- Vague study description
- Missing findings data

**Solution**: Improve input quality, increase iteration limit

### Issue: Gaps too generic
**Solution**: 
- Provide detailed study metadata
- Include specific findings
- Use RAG with domain-specific guidelines

## Examples

See `/examples/gap_analysis_examples.md` for:
- RCT gap analysis
- Meta-analysis gap identification
- Qualitative study gaps
- Multi-phase trial gaps

## Contributing

Enhancements welcome:
- Additional gap categorization heuristics
- Improved PICO extraction algorithms
- Alternative prioritization schemes
- Integration with grant databases

## License

Part of ResearchFlow - See main LICENSE file

## Support

- Documentation: `docs/gap_analysis/`
- Issues: GitHub Issues
- Email: support@researchflow.ai
