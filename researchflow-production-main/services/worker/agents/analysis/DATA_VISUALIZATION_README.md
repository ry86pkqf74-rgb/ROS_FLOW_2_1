# DataVisualizationAgent - Stage 8

## Overview

The **DataVisualizationAgent** generates publication-quality figures, charts, and visualizations from research data. It supports multiple chart types, journal-specific styling, accessibility features, and AI-generated captions.

## Architecture

Follows the **LangGraph** Planner → Retriever → Executor → Reflector pattern:

1. **PLAN** (Claude): Determine optimal visualizations for data type and journal requirements
2. **RETRIEVE**: Get visualization guidelines from RAG (journal requirements, best practices)
3. **EXECUTE** (Mercury/Advanced): Generate figures using matplotlib/seaborn
4. **REFLECT**: Quality check (clarity, accessibility, journal compliance)

## Capabilities

### Visualization Types

- **Statistical Plots**
  - Bar charts (vertical/horizontal with error bars)
  - Line charts (with markers, confidence bands)
  - Scatter plots (with trendlines, correlation coefficients)
  - Box plots (with outliers, means, individual points)
  - Violin plots
  - Histograms
  - Heatmaps

- **Clinical Plots**
  - Kaplan-Meier survival curves (with risk tables, confidence intervals)
  - Forest plots for meta-analysis (with diamond summaries, heterogeneity stats)
  - Funnel plots for publication bias

- **Study Flow Diagrams**
  - CONSORT diagrams for clinical trials
  - PRISMA diagrams for systematic reviews

### Journal-Specific Styling

Pre-configured presets for major journals:
- **Nature** (single column: 89mm, double: 183mm)
- **JAMA** (84mm / 174mm)
- **NEJM** (86mm / 180mm)
- **The Lancet** (85mm / 175mm)

### Accessibility Features

- **Colorblind-Safe Palettes** (Okabe & Ito 2008)
- **Alt Text Generation** for screen readers
- **High Contrast** modes

### Export Formats

- PNG, SVG, PDF, EPS, WebP
- Configurable DPI (default: 300 for print quality)

## Usage

### Basic Example

```python
import pandas as pd
from agents.analysis.data_visualization_agent import (
    create_data_visualization_agent,
    VizRequest,
    VizType,
    BarChartConfig,
    StudyContext,
    JournalStyle,
)

# Initialize agent
agent = create_data_visualization_agent()

# Prepare data
data = pd.DataFrame({
    "group": ["Control", "Treatment A", "Treatment B"],
    "outcome": [5.2, 6.8, 7.3],
    "std": [1.1, 1.3, 1.0],
})

# Create visualization request
viz_request = VizRequest(
    viz_type=VizType.BAR_CHART,
    data_columns={"x": "group", "y": "outcome"},
    title="Mean Outcome by Treatment Group",
    config=BarChartConfig(
        show_error_bars=True,
        error_bar_type="std",
    )
)

# Study context
context = StudyContext(
    study_title="Efficacy of Novel Treatments",
    outcome_variable="Pain Score (0-10)",
    sample_size=150,
)

# Generate figure
figure = agent.create_bar_chart(data, viz_request.config)
```

## Implementation Status

### ✅ Complete
- Type definitions
- BaseAgent integration
- Style presets
- Color palettes
- Quality checks

### 🚧 TODO (Mercury)
- Matplotlib rendering
- Lifelines integration (Kaplan-Meier)
- Forest plot generation
- CONSORT/PRISMA diagrams
- Format conversion
- Caption generation with LLM

## Testing

```bash
pytest services/worker/tests/test_data_visualization_agent.py -v
```

## Dependencies

```
matplotlib>=3.5.0
seaborn>=0.12.0
pandas>=1.5.0
numpy>=1.23.0
lifelines>=0.27.0
pillow>=9.0.0
```

## Integration

Part of ResearchFlow Stage 8 pipeline:
- **Input**: Data from Stage 7 (Statistical Analysis)
- **Output**: Figures for Stage 9 (Manuscript Generation)

## References

- Okabe & Ito (2008): Color Universal Design
- Tufte, E. (2001): The Visual Display of Quantitative Information
- Nature Figure Guidelines
- CONSORT Statement
- PRISMA Statement
