# ResearchFlow Analysis Agents - Quick Start Guide

## 🚀 5-Minute Setup

### 1. Environment Setup

```bash
# Install dependencies
cd services/worker
pip install -r requirements.txt

# Set environment variables
export ANTHROPIC_API_KEY="your-api-key"
export ORCHESTRATOR_URL="http://localhost:3001"
```

### 2. Test Installation

```bash
# Quick import test
python -c "from agents.analysis import create_analysis_pipeline; print('✓ Installation OK')"

# Run demo tests
python agents/analysis/test_agents_demo.py
```

---

## 📖 Basic Usage

### Meta-Analysis (30 seconds)

```python
from agents.analysis import create_meta_analysis_agent, StudyEffect, MetaAnalysisConfig

# Create agent
agent = create_meta_analysis_agent()

# Define studies
studies = [
    StudyEffect(study_id="1", study_label="Smith 2020", effect_estimate=1.45, se=0.23, sample_size=100),
    StudyEffect(study_id="2", study_label="Jones 2021", effect_estimate=1.89, se=0.31, sample_size=75),
    StudyEffect(study_id="3", study_label="Brown 2019", effect_estimate=1.12, se=0.19, sample_size=120),
]

# Configure analysis
config = MetaAnalysisConfig(
    effect_measure="OR",
    model_type="random_effects",
    test_publication_bias=True
)

# Run analysis
result = await agent.execute(studies, config)

# Print results
print(result.format_result())
# Output: "Meta-analysis of 3 studies (n = 295) using random-effects model: 
#          OR = 1.45 (95% CI [1.12, 1.89]), z = 2.34, p = 0.019. 
#          Heterogeneity: I² = 68.5%, τ² = 0.150, χ² = 6.34 (p = 0.042)."
```

### PRISMA Report (45 seconds)

```python
from agents.analysis import create_prisma_agent, PRISMAFlowchartData, SearchStrategy

# Create agent
agent = create_prisma_agent()

# Define flowchart data
flowchart = PRISMAFlowchartData(
    records_identified_databases=1234,
    records_screened=890,
    reports_sought_retrieval=234,
    reports_assessed_eligibility=145,
    new_studies_included=42,
    total_studies_included=42,
    records_excluded=656,
    reports_excluded=103,
    exclusion_reasons={"Wrong population": 35, "No RCT": 40}
)

# Define search strategies
searches = [
    SearchStrategy(
        database="PubMed",
        search_date="2024-01-15",
        search_string='("mindfulness"[MeSH]) AND "anxiety"[Title/Abstract]',
        results_count=567,
        filters_applied=["Humans", "English"]
    ),
]

# Generate report
report = await agent.execute(
    flowchart_data=flowchart,
    search_strategies=searches,
    review_title="Mindfulness for Anxiety: Systematic Review",
    authors=["Smith J", "Doe J"]
)

# Export formats
markdown = agent.generate_report_markdown(report)
html = agent.export_to_html(report)

print(f"PRISMA Checklist: {sum(1 for c in report.checklist if c.reported)}/33 complete")
```

### Full Pipeline (60 seconds)

```python
from agents.analysis import create_analysis_pipeline

# Create pipeline
pipeline = create_analysis_pipeline()

# Execute complete workflow
result = await pipeline.execute_full_workflow(
    research_id="anxiety_review_2024",
    study_context={
        "title": "Mindfulness for Anxiety",
        "authors": ["Smith J"],
        "research_question": "Does mindfulness reduce anxiety?",
        "keywords": ["mindfulness", "anxiety", "RCT"]
    },
    meta_analysis_studies=[
        {"study_id": "1", "study_label": "Smith 2020", "effect_estimate": 1.45, "se": 0.23},
        {"study_id": "2", "study_label": "Jones 2021", "effect_estimate": 1.89, "se": 0.31},
    ],
    pipeline_config={
        "run_lit_search": False,  # Skip if no API keys
        "run_meta_analysis": True,
        "run_prisma_report": True
    }
)

# Check results
print(f"✓ Completed {len(result.stages_completed)} stages")
print(f"✓ Generated {len(result.final_artifacts)} artifacts")
print(f"✓ Duration: {result.total_duration_ms}ms")
```

---

## 🎯 Common Recipes

### Recipe 1: Quick Meta-Analysis with Publication Bias Check

```python
import asyncio
from agents.analysis import create_meta_analysis_agent, StudyEffect, MetaAnalysisConfig

async def quick_meta_analysis():
    agent = create_meta_analysis_agent()
    
    # Your effect sizes (odds ratios with SEs)
    studies = [
        StudyEffect(study_id=str(i), study_label=f"Study {i}", 
                   effect_estimate=effect, se=se)
        for i, (effect, se) in enumerate([
            (1.45, 0.23), (1.89, 0.31), (1.12, 0.19),
            (1.67, 0.28), (1.34, 0.21)
        ], 1)
    ]
    
    config = MetaAnalysisConfig(effect_measure="OR", test_publication_bias=True)
    result = await agent.execute(studies, config)
    
    # Results
    print(f"Pooled OR: {result.pooled_effect:.2f} ({result.ci_lower:.2f}-{result.ci_upper:.2f})")
    print(f"Heterogeneity I²: {result.heterogeneity.i_squared:.1f}%")
    print(f"Publication bias: {result.publication_bias.interpretation}")
    
    return result

# Run it
result = asyncio.run(quick_meta_analysis())
```

### Recipe 2: Generate PRISMA Report from Existing Review

```python
import asyncio
from agents.analysis import create_prisma_agent, PRISMAFlowchartData, SearchStrategy

async def generate_prisma_report():
    agent = create_prisma_agent()
    
    # Your study numbers
    flowchart = PRISMAFlowchartData(
        records_identified_databases=1500,
        records_screened=1000,
        reports_sought_retrieval=300,
        reports_assessed_eligibility=200,
        new_studies_included=50,
        total_studies_included=50,
        records_excluded=700,
        reports_excluded=150,
        exclusion_reasons={
            "Wrong intervention": 40,
            "Wrong population": 35,
            "Not RCT": 45,
            "No relevant outcome": 30
        }
    )
    
    # Your search strategies
    searches = [
        SearchStrategy(
            database="PubMed",
            search_date="2024-01-15",
            search_string='Your complete search string here',
            results_count=800
        ),
        SearchStrategy(
            database="Embase",
            search_date="2024-01-15",
            search_string='Your Embase search',
            results_count=700
        ),
    ]
    
    report = await agent.execute(
        flowchart_data=flowchart,
        search_strategies=searches,
        review_title="Your Review Title",
        authors=["Author 1", "Author 2"],
        registration_number="PROSPERO CRD42024123456"
    )
    
    # Save outputs
    with open("prisma_report.md", "w") as f:
        f.write(agent.generate_report_markdown(report))
    
    with open("prisma_report.html", "w") as f:
        f.write(agent.export_to_html(report))
    
    print("✓ PRISMA report generated")
    return report

# Run it
report = asyncio.run(generate_prisma_report())
```

### Recipe 3: Statistical Analysis + Meta-Analysis Pipeline

```python
import asyncio
from agents.analysis import create_analysis_pipeline

async def stats_to_meta_pipeline():
    pipeline = create_analysis_pipeline()
    
    result = await pipeline.execute_full_workflow(
        research_id="my_review_2024",
        study_context={
            "title": "My Systematic Review",
            "authors": ["Me"],
        },
        statistical_data={
            "groups": ["treatment", "control"],
            "outcomes": {"primary_outcome": [5.2, 6.1, 7.8, 6.5]},  # Your data
            "group_assignment": [0, 0, 1, 1],
            "metadata": {"study_title": "My Study"}
        },
        meta_analysis_studies=[
            {"study_id": "1", "study_label": "Study 1", "effect_estimate": 1.5, "se": 0.2},
            {"study_id": "2", "study_label": "Study 2", "effect_estimate": 1.8, "se": 0.3},
        ],
        pipeline_config={
            "run_lit_search": False,
            "run_statistical_analysis": True,
            "run_meta_analysis": True,
            "run_prisma_report": True
        }
    )
    
    print(f"✓ Pipeline complete: {len(result.stages_completed)} stages")
    for stage_name, stage_result in result.stage_results.items():
        print(f"  - {stage_name}: {'✓' if stage_result.success else '✗'}")
    
    return result

# Run it
result = asyncio.run(stats_to_meta_pipeline())
```

---

## 🔧 Configuration Tips

### Adjust Quality Thresholds

```python
from agents.base_agent import AgentConfig

# More lenient quality check (faster, less strict)
config = AgentConfig(
    name="MetaAnalysisAgent",
    quality_threshold=0.70,  # Default: 0.80
    max_iterations=2,        # Default: 3
)

# Stricter quality check (slower, more thorough)
config = AgentConfig(
    name="PRISMAAgent",
    quality_threshold=0.90,  # Default: 0.85
    max_iterations=4,
)
```

### Use Local Models (No API costs)

```python
from agents.base_agent import AgentConfig

config = AgentConfig(
    name="MyAgent",
    model_provider="local",          # Use Ollama
    model_name="qwen2.5-coder:7b",   # Local model
)
```

### Enable PHI Scanning

```python
config = AgentConfig(
    name="MyAgent",
    phi_safe=True,  # Scan for Protected Health Information
)
```

---

## 📊 Output Formats

### Meta-Analysis Result

```python
result = await agent.execute(studies, config)

# Formatted summary
print(result.format_result())

# Full dictionary
data = result.to_dict()

# Access specific components
print(f"Pooled effect: {result.pooled_effect}")
print(f"I²: {result.heterogeneity.i_squared}%")
print(f"Publication bias p: {result.publication_bias.p_value}")
```

### PRISMA Report

```python
report = await agent.execute(...)

# Markdown format
markdown = agent.generate_report_markdown(report)

# HTML format
html = agent.export_to_html(report)

# Flowchart (Mermaid)
flowchart = report.generate_flowchart_mermaid()

# Dictionary
data = report.to_dict()
```

---

## ❓ FAQ

**Q: Do I need API keys to run the agents?**  
A: For full functionality, yes (Anthropic API). But you can use local models (Ollama) for free.

**Q: Can I run agents without literature search?**  
A: Yes! Each agent works independently. Use only the ones you need.

**Q: How do I handle errors?**  
A: Agents return `success: bool` and `error: str`. Check `result.success` and handle accordingly.

**Q: Can I customize the prompts?**  
A: Yes! Override `_get_*_prompt()` methods in your subclass.

**Q: What if quality checks keep failing?**  
A: Review `QualityCheckResult.feedback` for specific issues. Lower `quality_threshold` if needed.

---

## 📚 More Information

- **Complete Guide**: See `ANALYSIS_AGENTS_README.md`
- **Implementation Details**: See `COMPLETION_SUMMARY_FULL.md`
- **Demo Tests**: Run `python test_agents_demo.py`
- **Integration**: See `INTEGRATION_CHECKLIST.md`

---

## 🎉 You're Ready!

**That's it!** You now have:
- ✅ Meta-analysis with publication bias detection
- ✅ PRISMA 2020 compliant reporting
- ✅ Multi-stage analysis pipelines
- ✅ Complete quality assurance

**Next Steps**:
1. Run demo tests: `python test_agents_demo.py`
2. Try the recipes above with your data
3. Integrate into your workflow

**Need Help?** Check the comprehensive docs in `ANALYSIS_AGENTS_README.md`

---

**Happy Analyzing! 🔬📊**
