# Gap Analysis Agent - Quick Start

## 1. Install Dependencies

```bash
pip install langchain-anthropic langchain-openai openai numpy pydantic
```

## 2. Set API Keys

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-..."
export XAI_API_KEY="xai-..." # Optional
export MERCURY_API_KEY="..." # Optional
```

## 3. Basic Usage

```python
from agents.analysis import create_gap_analysis_agent, StudyContext, Paper

# Initialize
agent = create_gap_analysis_agent()

# Define study
study = StudyContext(
    title="Your Study Title",
    research_question="Your RQ?",
    study_type="RCT"
)

# Add literature
literature = [
    Paper(title="Paper 1", authors=["Smith"], year=2020, abstract="...")
]

# Run analysis
result = await agent.execute(study, literature)

# Print results
print(f"Gaps: {result.total_gaps_identified}")
print(result.narrative)
```

## 4. Access Results

```python
# High-priority gaps
for gap in result.prioritization_matrix.high_priority:
    print(gap['description'])

# Research suggestions
for suggestion in result.research_suggestions:
    print(suggestion.research_question)
    print(suggestion.pico_framework.format_research_question())
```

## 5. Run Tests

```bash
pytest test_gap_analysis_agent.py -v
```

Done! See GAP_ANALYSIS_README.md for full documentation.
