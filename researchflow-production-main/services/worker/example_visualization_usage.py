#!/usr/bin/env python3
"""
Example usage of DataVisualizationAgent

This script demonstrates how to generate various chart types
without requiring a running server or database.
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "agents" / "analysis"))

# Import the agent
from visualization_types import (
    BarChartConfig,
    LineChartConfig,
    ScatterConfig,
    BoxPlotConfig,
    ColorPalette,
    JournalStyle,
    Orientation,
)

# Import matplotlib for non-interactive backend
import matplotlib
matplotlib.use('Agg')

print("=" * 70)
print("DataVisualizationAgent Usage Examples")
print("=" * 70)

# Import the agent factory
from data_visualization_agent import create_data_visualization_agent

# Create agent instance
print("\n1. Creating DataVisualizationAgent...")
agent = create_data_visualization_agent()
print("   ✓ Agent created successfully")

# Example 1: Simple Bar Chart
print("\n2. Generating Bar Chart...")
bar_data = pd.DataFrame({
    'group': ['Control', 'Treatment A', 'Treatment B'],
    'outcome': [5.2, 6.8, 7.3],
    'std': [1.1, 1.3, 1.0],
})

bar_config = BarChartConfig(
    title="Treatment Outcomes Comparison",
    x_label="Treatment Group",
    y_label="Pain Score (0-10 scale)",
    show_error_bars=True,
    error_bar_type="std",
    color_palette=ColorPalette.COLORBLIND_SAFE,
    dpi=150,  # Lower DPI for demo
)

bar_figure = agent.create_bar_chart(bar_data, bar_config)
print(f"   ✓ Bar chart generated: {len(bar_figure.image_bytes):,} bytes")
print(f"   ✓ Caption: {bar_figure.caption[:80]}...")
print(f"   ✓ Alt text: {bar_figure.alt_text[:80]}...")

# Save to file
output_dir = Path("./visualization_examples")
output_dir.mkdir(exist_ok=True)
bar_path = output_dir / "example_bar_chart.png"
with open(bar_path, 'wb') as f:
    f.write(bar_figure.image_bytes)
print(f"   ✓ Saved to: {bar_path}")

# Example 2: Line Chart with Multiple Series
print("\n3. Generating Line Chart...")
np.random.seed(42)
time_points = list(range(0, 25, 4))
line_data = pd.DataFrame({
    'time': time_points * 3,
    'value': (
        [5.0, 4.8, 4.2, 3.9, 3.5, 3.2] +  # Group A
        [5.0, 5.2, 5.5, 5.8, 6.0, 6.2] +  # Group B
        [5.0, 4.5, 4.0, 3.8, 3.5, 3.3]    # Group C
    ),
    'group': ['Group A'] * 6 + ['Group B'] * 6 + ['Group C'] * 6,
})

line_config = LineChartConfig(
    title="Treatment Response Over Time",
    x_label="Time (weeks)",
    y_label="Symptom Score",
    show_markers=True,
    show_legend=True,
    color_palette=ColorPalette.COLORBLIND_SAFE,
    dpi=150,
)

line_figure = agent.create_line_chart(line_data, line_config)
print(f"   ✓ Line chart generated: {len(line_figure.image_bytes):,} bytes")
line_path = output_dir / "example_line_chart.png"
with open(line_path, 'wb') as f:
    f.write(line_figure.image_bytes)
print(f"   ✓ Saved to: {line_path}")

# Example 3: Scatter Plot with Correlation
print("\n4. Generating Scatter Plot...")
np.random.seed(42)
n_points = 50
x_data = np.random.randn(n_points) * 10 + 50
y_data = x_data * 1.5 + np.random.randn(n_points) * 8 + 10

scatter_data = pd.DataFrame({
    'x': x_data,
    'y': y_data,
})

scatter_config = ScatterConfig(
    title="Age vs. Recovery Time Correlation",
    x_label="Age (years)",
    y_label="Recovery Time (days)",
    show_trendline=True,
    show_correlation=True,
    color_palette=ColorPalette.COLORBLIND_SAFE,
    dpi=150,
)

scatter_figure = agent.create_scatter_plot(scatter_data, scatter_config)
print(f"   ✓ Scatter plot generated: {len(scatter_figure.image_bytes):,} bytes")
scatter_path = output_dir / "example_scatter_plot.png"
with open(scatter_path, 'wb') as f:
    f.write(scatter_figure.image_bytes)
print(f"   ✓ Saved to: {scatter_path}")

# Example 4: Box Plot
print("\n5. Generating Box Plot...")
np.random.seed(42)
groups = ['Control', 'Low Dose', 'High Dose']
box_data = pd.DataFrame({
    'group': np.repeat(groups, 30),
    'value': np.concatenate([
        np.random.normal(5.0, 1.2, 30),   # Control
        np.random.normal(6.5, 1.5, 30),   # Low dose
        np.random.normal(7.8, 1.3, 30),   # High dose
    ])
})

box_config = BoxPlotConfig(
    title="Efficacy by Dose Level",
    x_label="Treatment Group",
    y_label="Efficacy Score",
    show_outliers=True,
    show_means=True,
    color_palette=ColorPalette.COLORBLIND_SAFE,
    dpi=150,
)

box_figure = agent.create_box_plot(box_data, box_config)
print(f"   ✓ Box plot generated: {len(box_figure.image_bytes):,} bytes")
box_path = output_dir / "example_box_plot.png"
with open(box_path, 'wb') as f:
    f.write(box_figure.image_bytes)
print(f"   ✓ Saved to: {box_path}")

# Example 5: Publication-Quality Chart (JAMA Style)
print("\n6. Generating Publication-Quality Chart (JAMA style)...")
jama_data = pd.DataFrame({
    'category': ['Baseline', 'Month 1', 'Month 3', 'Month 6'],
    'control': [45.2, 43.8, 42.1, 40.5],
    'treatment': [45.0, 40.2, 35.8, 32.1],
})

# Reshape for plotting
jama_long = pd.DataFrame({
    'time': jama_data['category'].tolist() * 2,
    'value': jama_data['control'].tolist() + jama_data['treatment'].tolist(),
    'group': ['Control'] * 4 + ['Treatment'] * 4,
})

jama_config = LineChartConfig(
    title="Primary Outcome: Pain Score Over Time",
    x_label="Time Point",
    y_label="Pain Score (0-100)",
    show_markers=True,
    show_legend=True,
    journal_style=JournalStyle.JAMA,
    color_palette=ColorPalette.JOURNAL_JAMA,
    dpi=300,  # Publication quality
)

jama_figure = agent.create_line_chart(jama_long, jama_config)
print(f"   ✓ JAMA-style chart generated: {len(jama_figure.image_bytes):,} bytes")
jama_path = output_dir / "example_jama_style.png"
with open(jama_path, 'wb') as f:
    f.write(jama_figure.image_bytes)
print(f"   ✓ Saved to: {jama_path}")

# Summary
print("\n" + "=" * 70)
print("Summary")
print("=" * 70)
print(f"✓ Generated 5 example charts")
print(f"✓ All files saved to: {output_dir.absolute()}")
print(f"\nFiles created:")
print(f"  1. {bar_path.name} - Bar chart with error bars")
print(f"  2. {line_path.name} - Multi-series line chart")
print(f"  3. {scatter_path.name} - Scatter plot with trendline")
print(f"  4. {box_path.name} - Box plot with outliers")
print(f"  5. {jama_path.name} - Publication-quality JAMA style")

print("\n" + "=" * 70)
print("Integration with API")
print("=" * 70)
print("To use this in your API endpoint:")
print("")
print("```python")
print("from agents.analysis import create_data_visualization_agent")
print("from agents.analysis import BarChartConfig, ColorPalette")
print("")
print("agent = create_data_visualization_agent()")
print("df = pd.DataFrame(request_data)")
print("config = BarChartConfig(**request_config)")
print("figure = agent.create_bar_chart(df, config)")
print("")
print("# Convert to base64 for JSON response")
print("import base64")
print("image_base64 = base64.b64encode(figure.image_bytes).decode('utf-8')")
print("```")

print("\n" + "=" * 70)
print("Available Configuration Options")
print("=" * 70)
print("\nJournal Styles:")
for style in JournalStyle:
    print(f"  - {style.value}")

print("\nColor Palettes:")
for palette in ColorPalette:
    print(f"  - {palette.value}")

print("\n" + "=" * 70)
print("✅ Example script complete!")
print("=" * 70)
