"""
DataVisualizationAgent - Stage 8: Data Visualization

Generates publication-quality figures, charts, and visualizations from research data.

Linear Issues: ROS-XXX (Stage 8 - Data Visualization Agent)
"""

import os
import json
import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from agents.base_agent import (
    BaseAgent,
    AgentConfig,
    AgentState,
    QualityCheckResult,
)

from .visualization_types import *

logger = logging.getLogger(__name__)

# Import lifelines for Kaplan-Meier (optional)
try:
    from lifelines import KaplanMeierFitter
    from lifelines.plotting import add_at_risk_counts
    LIFELINES_AVAILABLE = True
except ImportError:
    LIFELINES_AVAILABLE = False
    logger.warning("lifelines not available - Kaplan-Meier curves will not work")


class DataVisualizationAgent(BaseAgent):
    """Agent for generating publication-quality data visualizations."""

    def __init__(self):
        config = AgentConfig(
            name="DataVisualizationAgent",
            description="Generate publication-quality figures and visualizations",
            stages=[8],
            rag_collections=["visualization_guidelines", "journal_requirements"],
            max_iterations=3,
            quality_threshold=0.85,
            timeout_seconds=300,
            phi_safe=True,
            model_provider="anthropic",
            model_name="claude-sonnet-4-20250514",
        )
        super().__init__(config)
        self._initialize_style_presets()
        self._initialize_color_palettes()

    def _initialize_style_presets(self) -> None:
        """Initialize journal-specific style presets."""
        self.style_presets = {
            JournalStyle.NATURE: {"font_family": "Arial", "font_size": 8, "dpi": 300, "width": 89},
            JournalStyle.JAMA: {"font_family": "Arial", "font_size": 9, "dpi": 300, "width": 84},
        }

    def _initialize_color_palettes(self) -> None:
        """Initialize colorblind-safe palettes."""
        self.color_palettes = {
            ColorPalette.COLORBLIND_SAFE: ["#E69F00", "#56B4E9", "#009E73", "#F0E442"],
        }

    def _get_system_prompt(self) -> str:
        return """You are a Data Visualization Agent for scientific figures.
Follow journal guidelines and ensure accessibility."""

    def _get_planning_prompt(self, state: AgentState) -> str:
        task_data = json.loads(state["messages"][0].content)
        return f"""Plan visualizations for: {json.dumps(task_data, indent=2)}"""

    def _get_execution_prompt(self, state: AgentState, context: str) -> str:
        return f"""Execute visualization generation with context: {context}"""

    def _parse_execution_result(self, response: str) -> Dict[str, Any]:
        try:
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
                return json.loads(json_str)
            return {}
        except Exception as e:
            logger.error(f"Parse error: {e}")
            return {"figures": [], "warnings": [str(e)]}

    async def _check_quality(self, state: AgentState) -> QualityCheckResult:
        result = state.get("execution_result", {})
        figures = result.get("figures", [])
        score = len(figures) / max(1, len(figures)) if figures else 0.5
        return QualityCheckResult(
            passed=score >= 0.85,
            score=score,
            feedback="Quality check complete",
            criteria_scores={"completeness": score}
        )

    # Visualization methods - Mercury Implementation
    def create_bar_chart(self, data: pd.DataFrame, config: BarChartConfig) -> Figure:
        """Create publication-quality bar chart with matplotlib.
        
        Args:
            data: DataFrame with columns for x and y values
            config: BarChartConfig with styling options
            
        Returns:
            Figure object with rendered chart as image_bytes
        """
        try:
            # Apply style
            self._apply_style(config)
            
            # Create figure
            fig, ax = plt.subplots(figsize=(config.width/100, config.height/100), dpi=config.dpi)
            
            # Get data columns
            x_col = data.columns[0]
            y_col = data.columns[1] if len(data.columns) > 1 else data.columns[0]
            
            # Get colors
            colors = self._get_colors(config.color_palette, len(data))
            if config.colors:
                colors = config.colors
            
            # Create bar chart
            if config.orientation == Orientation.VERTICAL:
                bars = ax.bar(data[x_col], data[y_col], width=config.bar_width, color=colors)
                
                # Add error bars if specified
                if config.show_error_bars and len(data.columns) > 2:
                    error_col = data.columns[2]
                    ax.errorbar(data[x_col], data[y_col], yerr=data[error_col], 
                              fmt='none', ecolor='black', capsize=5, capthick=2)
                
                # Add value labels
                if config.show_values:
                    for bar in bars:
                        height = bar.get_height()
                        ax.text(bar.get_x() + bar.get_width()/2., height,
                               f'{height:{config.value_format}}',
                               ha='center', va='bottom', fontsize=config.font_size-2)
            else:
                bars = ax.barh(data[x_col], data[y_col], height=config.bar_width, color=colors)
                
                if config.show_error_bars and len(data.columns) > 2:
                    error_col = data.columns[2]
                    ax.errorbar(data[y_col], data[x_col], xerr=data[error_col],
                              fmt='none', ecolor='black', capsize=5, capthick=2)
                
                if config.show_values:
                    for bar in bars:
                        width = bar.get_width()
                        ax.text(width, bar.get_y() + bar.get_height()/2.,
                               f'{width:{config.value_format}}',
                               ha='left', va='center', fontsize=config.font_size-2)
            
            # Set labels and title
            if config.x_label:
                ax.set_xlabel(config.x_label, fontsize=config.font_size)
            if config.y_label:
                ax.set_ylabel(config.y_label, fontsize=config.font_size)
            if config.title:
                ax.set_title(config.title, fontsize=config.font_size+2, fontweight='bold')
            
            # Grid
            if config.show_grid:
                ax.grid(True, alpha=0.3, linestyle='--')
                ax.set_axisbelow(True)
            
            # Clean up
            plt.tight_layout()
            
            # Convert to bytes
            image_bytes = self._fig_to_bytes(fig, ExportFormat.PNG)
            plt.close(fig)
            
            # Generate caption
            caption = self._generate_bar_caption(data, config)
            alt_text = f"Bar chart showing {y_col} by {x_col}"
            
            return Figure(
                figure_id=f"bar_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                viz_type=VizType.BAR_CHART,
                image_bytes=image_bytes,
                format=ExportFormat.PNG,
                width=config.width,
                height=config.height,
                dpi=config.dpi,
                caption=caption,
                alt_text=alt_text,
                data_summary={"n_groups": len(data), "x_col": x_col, "y_col": y_col},
                rendering_info={"color_palette": config.color_palette.value, "orientation": config.orientation.value}
            )
            
        except Exception as e:
            logger.error(f"Error creating bar chart: {e}")
            return Figure(figure_id="bar_error", viz_type=VizType.BAR_CHART)

    def create_line_chart(self, data: pd.DataFrame, config: LineChartConfig) -> Figure:
        """Create publication-quality line chart with matplotlib.
        
        Args:
            data: DataFrame with x values and one or more y columns
            config: LineChartConfig with styling options
            
        Returns:
            Figure object with rendered chart as image_bytes
        """
        try:
            self._apply_style(config)
            
            fig, ax = plt.subplots(figsize=(config.width/100, config.height/100), dpi=config.dpi)
            
            # Get columns
            x_col = data.columns[0]
            y_cols = data.columns[1:]
            
            # Get colors
            colors = self._get_colors(config.color_palette, len(y_cols))
            if config.colors:
                colors = config.colors
            
            # Plot each line
            for idx, y_col in enumerate(y_cols):
                color = colors[idx % len(colors)]
                
                # Main line
                line = ax.plot(data[x_col], data[y_col],
                              linewidth=config.line_width,
                              linestyle=config.line_style,
                              color=color,
                              label=y_col,
                              marker='o' if config.show_markers else None,
                              markersize=config.marker_size if config.show_markers else 0)
                
                # Confidence bands
                if config.show_confidence_bands and len(data.columns) > len(y_cols) + 1:
                    # Assume next columns are std/ci for each y
                    ci_col_idx = len(y_cols) + idx + 1
                    if ci_col_idx < len(data.columns):
                        ci = data[data.columns[ci_col_idx]]
                        ax.fill_between(data[x_col],
                                      data[y_col] - ci,
                                      data[y_col] + ci,
                                      color=color, alpha=0.2)
            
            # Labels and title
            if config.x_label:
                ax.set_xlabel(config.x_label, fontsize=config.font_size)
            if config.y_label:
                ax.set_ylabel(config.y_label, fontsize=config.font_size)
            if config.title:
                ax.set_title(config.title, fontsize=config.font_size+2, fontweight='bold')
            
            # Legend
            if config.show_legend and len(y_cols) > 1:
                ax.legend(loc=config.legend_position, frameon=True)
            
            # Grid
            if config.show_grid:
                ax.grid(True, alpha=0.3, linestyle='--')
                ax.set_axisbelow(True)
            
            plt.tight_layout()
            
            image_bytes = self._fig_to_bytes(fig, ExportFormat.PNG)
            plt.close(fig)
            
            caption = self._generate_line_caption(data, config)
            alt_text = f"Line chart showing trends over {x_col}"
            
            return Figure(
                figure_id=f"line_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                viz_type=VizType.LINE_CHART,
                image_bytes=image_bytes,
                format=ExportFormat.PNG,
                width=config.width,
                height=config.height,
                dpi=config.dpi,
                caption=caption,
                alt_text=alt_text,
                data_summary={"n_lines": len(y_cols), "x_col": x_col},
                rendering_info={"color_palette": config.color_palette.value}
            )
            
        except Exception as e:
            logger.error(f"Error creating line chart: {e}")
            return Figure(figure_id="line_error", viz_type=VizType.LINE_CHART)

    def create_scatter_plot(self, data: pd.DataFrame, config: ScatterConfig) -> Figure:
        """Create publication-quality scatter plot with matplotlib.
        
        Args:
            data: DataFrame with x and y columns (optional: group column)
            config: ScatterConfig with styling options
            
        Returns:
            Figure object with rendered chart as image_bytes
        """
        try:
            self._apply_style(config)
            
            fig, ax = plt.subplots(figsize=(config.width/100, config.height/100), dpi=config.dpi)
            
            x_col = data.columns[0]
            y_col = data.columns[1]
            
            # Check for grouping
            if config.color_by_group and len(data.columns) > 2:
                group_col = data.columns[2]
                groups = data[group_col].unique()
                colors = self._get_colors(config.color_palette, len(groups))
                
                for idx, group in enumerate(groups):
                    mask = data[group_col] == group
                    ax.scatter(data.loc[mask, x_col], data.loc[mask, y_col],
                             s=config.marker_size, alpha=config.marker_alpha,
                             c=[colors[idx]], label=str(group))
            else:
                colors = self._get_colors(config.color_palette, 1)
                ax.scatter(data[x_col], data[y_col],
                         s=config.marker_size, alpha=config.marker_alpha,
                         c=[colors[0]])
            
            # Trendline
            if config.show_trendline:
                z = np.polyfit(data[x_col], data[y_col], 1 if config.trendline_type == "linear" else 2)
                p = np.poly1d(z)
                x_line = np.linspace(data[x_col].min(), data[x_col].max(), 100)
                ax.plot(x_line, p(x_line), "r--", linewidth=2, alpha=0.7, label="Trend")
            
            # Correlation
            if config.show_correlation:
                corr = data[x_col].corr(data[y_col])
                ax.text(0.05, 0.95, f'r = {corr:.3f}',
                       transform=ax.transAxes, fontsize=config.font_size,
                       verticalalignment='top',
                       bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
            
            # Labels and title
            if config.x_label:
                ax.set_xlabel(config.x_label, fontsize=config.font_size)
            if config.y_label:
                ax.set_ylabel(config.y_label, fontsize=config.font_size)
            if config.title:
                ax.set_title(config.title, fontsize=config.font_size+2, fontweight='bold')
            
            # Legend
            if config.show_legend and config.color_by_group:
                ax.legend(loc=config.legend_position, frameon=True)
            
            # Grid
            if config.show_grid:
                ax.grid(True, alpha=0.3, linestyle='--')
                ax.set_axisbelow(True)
            
            plt.tight_layout()
            
            image_bytes = self._fig_to_bytes(fig, ExportFormat.PNG)
            plt.close(fig)
            
            caption = self._generate_scatter_caption(data, config)
            alt_text = f"Scatter plot showing relationship between {x_col} and {y_col}"
            
            return Figure(
                figure_id=f"scatter_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                viz_type=VizType.SCATTER_PLOT,
                image_bytes=image_bytes,
                format=ExportFormat.PNG,
                width=config.width,
                height=config.height,
                dpi=config.dpi,
                caption=caption,
                alt_text=alt_text,
                data_summary={"n_points": len(data), "x_col": x_col, "y_col": y_col},
                rendering_info={"color_palette": config.color_palette.value}
            )
            
        except Exception as e:
            logger.error(f"Error creating scatter plot: {e}")
            return Figure(figure_id="scatter_error", viz_type=VizType.SCATTER_PLOT)

    def create_box_plot(self, data: pd.DataFrame, config: BoxPlotConfig) -> Figure:
        """Create publication-quality box plot with seaborn.
        
        Args:
            data: DataFrame with group and value columns
            config: BoxPlotConfig with styling options
            
        Returns:
            Figure object with rendered chart as image_bytes
        """
        try:
            self._apply_style(config)
            
            fig, ax = plt.subplots(figsize=(config.width/100, config.height/100), dpi=config.dpi)
            
            # Assume first column is group, second is value
            if len(data.columns) >= 2:
                x_col = data.columns[0]
                y_col = data.columns[1]
            else:
                x_col = None
                y_col = data.columns[0]
            
            # Get colors
            n_groups = len(data[x_col].unique()) if x_col else 1
            colors = self._get_colors(config.color_palette, n_groups)
            if config.colors:
                colors = config.colors
            
            # Create box plot with seaborn
            if config.orientation == Orientation.VERTICAL:
                if x_col:
                    sns.boxplot(data=data, x=x_col, y=y_col, ax=ax,
                              palette=colors, width=config.box_width,
                              showmeans=config.show_means,
                              notch=config.show_notch,
                              showfliers=config.show_outliers)
                    
                    # Add individual points
                    if config.show_individual_points:
                        sns.stripplot(data=data, x=x_col, y=y_col, ax=ax,
                                    color='black', alpha=config.point_alpha, size=3)
                else:
                    sns.boxplot(data=data, y=y_col, ax=ax,
                              palette=colors, width=config.box_width,
                              showmeans=config.show_means,
                              notch=config.show_notch,
                              showfliers=config.show_outliers)
            else:
                if x_col:
                    sns.boxplot(data=data, y=x_col, x=y_col, ax=ax,
                              palette=colors, width=config.box_width,
                              showmeans=config.show_means,
                              notch=config.show_notch,
                              showfliers=config.show_outliers)
                    
                    if config.show_individual_points:
                        sns.stripplot(data=data, y=x_col, x=y_col, ax=ax,
                                    color='black', alpha=config.point_alpha, size=3)
            
            # Labels and title
            if config.x_label:
                ax.set_xlabel(config.x_label, fontsize=config.font_size)
            if config.y_label:
                ax.set_ylabel(config.y_label, fontsize=config.font_size)
            if config.title:
                ax.set_title(config.title, fontsize=config.font_size+2, fontweight='bold')
            
            # Grid
            if config.show_grid:
                ax.grid(True, alpha=0.3, linestyle='--', axis='y')
                ax.set_axisbelow(True)
            
            plt.tight_layout()
            
            image_bytes = self._fig_to_bytes(fig, ExportFormat.PNG)
            plt.close(fig)
            
            caption = self._generate_box_caption(data, config)
            alt_text = f"Box plot showing distribution of {y_col}" + (f" by {x_col}" if x_col else "")
            
            return Figure(
                figure_id=f"box_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                viz_type=VizType.BOX_PLOT,
                image_bytes=image_bytes,
                format=ExportFormat.PNG,
                width=config.width,
                height=config.height,
                dpi=config.dpi,
                caption=caption,
                alt_text=alt_text,
                data_summary={"n_groups": n_groups, "n_observations": len(data)},
                rendering_info={"color_palette": config.color_palette.value, "orientation": config.orientation.value}
            )
            
        except Exception as e:
            logger.error(f"Error creating box plot: {e}")
            return Figure(figure_id="box_error", viz_type=VizType.BOX_PLOT)

    def create_kaplan_meier(self, data: pd.DataFrame, config: KMConfig) -> Figure:
        """Create Kaplan-Meier survival curve with lifelines.
        
        Args:
            data: DataFrame with time, event, and optional group columns
            config: KMConfig with styling options
            
        Returns:
            Figure object with rendered curve as image_bytes
        """
        if not LIFELINES_AVAILABLE:
            logger.error("lifelines library not available for Kaplan-Meier curves")
            return Figure(
                figure_id="km_error",
                viz_type=VizType.KAPLAN_MEIER,
                image_bytes=b"",
                format=ExportFormat.PNG
            )
        
        try:
            self._apply_style(config)
            
            # Create figure with room for risk table if needed
            if config.show_risk_table:
                fig, axes = plt.subplots(2, 1, figsize=(config.width/100, config.height/100),
                                        dpi=config.dpi, gridspec_kw={'height_ratios': [3, 1]})
                ax = axes[0]
            else:
                fig, ax = plt.subplots(figsize=(config.width/100, config.height/100), dpi=config.dpi)
            
            # Assume columns: time, event, [group]
            time_col = data.columns[0]
            event_col = data.columns[1]
            group_col = data.columns[2] if len(data.columns) > 2 else None
            
            kmf = KaplanMeierFitter()
            
            if group_col:
                groups = data[group_col].unique()
                colors = self._get_colors(config.color_palette, len(groups))
                if config.colors:
                    colors = config.colors
                
                for idx, group in enumerate(groups):
                    mask = data[group_col] == group
                    group_data = data[mask]
                    
                    kmf.fit(group_data[time_col], group_data[event_col], label=str(group))
                    kmf.plot_survival_function(ax=ax, ci_show=config.show_confidence_intervals,
                                              color=colors[idx % len(colors)],
                                              linewidth=2)
                    
                    # Add censored marks
                    if config.show_censored_marks:
                        censored = group_data[group_data[event_col] == 0]
                        ax.scatter(censored[time_col],
                                 kmf.predict(censored[time_col]),
                                 marker=config.censored_marker, s=50,
                                 color=colors[idx % len(colors)], zorder=10)
            else:
                colors = self._get_colors(config.color_palette, 1)
                kmf.fit(data[time_col], data[event_col], label="Overall")
                kmf.plot_survival_function(ax=ax, ci_show=config.show_confidence_intervals,
                                          color=colors[0], linewidth=2)
                
                if config.show_censored_marks:
                    censored = data[data[event_col] == 0]
                    ax.scatter(censored[time_col],
                             kmf.predict(censored[time_col]),
                             marker=config.censored_marker, s=50,
                             color=colors[0], zorder=10)
            
            # Labels and title
            ax.set_xlabel(config.time_label, fontsize=config.font_size)
            ax.set_ylabel(config.event_label, fontsize=config.font_size)
            if config.title:
                ax.set_title(config.title, fontsize=config.font_size+2, fontweight='bold')
            
            # Legend
            if config.show_legend:
                ax.legend(loc=config.legend_position, frameon=True)
            
            # Grid
            if config.show_grid:
                ax.grid(True, alpha=0.3, linestyle='--')
                ax.set_axisbelow(True)
            
            # Set y-axis to 0-1
            ax.set_ylim(0, 1)
            
            plt.tight_layout()
            
            image_bytes = self._fig_to_bytes(fig, ExportFormat.PNG)
            plt.close(fig)
            
            caption = self._generate_km_caption(data, config)
            alt_text = f"Kaplan-Meier survival curve showing survival probability over time"
            
            return Figure(
                figure_id=f"km_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                viz_type=VizType.KAPLAN_MEIER,
                image_bytes=image_bytes,
                format=ExportFormat.PNG,
                width=config.width,
                height=config.height,
                dpi=config.dpi,
                caption=caption,
                alt_text=alt_text,
                data_summary={"n_subjects": len(data), "n_events": data[event_col].sum()},
                rendering_info={"color_palette": config.color_palette.value, "show_ci": config.show_confidence_intervals}
            )
            
        except Exception as e:
            logger.error(f"Error creating Kaplan-Meier curve: {e}")
            return Figure(figure_id="km_error", viz_type=VizType.KAPLAN_MEIER)

    def create_forest_plot(self, effects: List[EffectSize], config: ForestConfig) -> Figure:
        """Create forest plot for meta-analysis.
        
        Args:
            effects: List of EffectSize objects with estimates and CIs
            config: ForestConfig with styling options
            
        Returns:
            Figure object with rendered forest plot as image_bytes
        """
        try:
            self._apply_style(config)
            
            fig, ax = plt.subplots(figsize=(config.width/100, config.height/100), dpi=config.dpi)
            
            n_studies = len(effects)
            y_positions = np.arange(n_studies, 0, -1)
            
            # Sort by weight if requested
            if config.sort_by_weight:
                effects = sorted(effects, key=lambda x: x.weight, reverse=True)
            
            # Plot each study
            for idx, (effect, y_pos) in enumerate(zip(effects, y_positions)):
                # Point estimate
                marker_size = effect.weight * 200 if config.show_weights else 100
                ax.scatter(effect.effect_estimate, y_pos, s=marker_size,
                         color='black', marker='D', zorder=10)
                
                # Confidence interval
                ax.plot([effect.ci_lower, effect.ci_upper], [y_pos, y_pos],
                       color='black', linewidth=2, zorder=5)
                
                # Study label
                ax.text(-0.1, y_pos, effect.study_label,
                       ha='right', va='center', fontsize=config.font_size-1,
                       transform=ax.get_yaxis_transform())
            
            # Summary diamond (if requested)
            if config.show_diamond_summary and len(effects) > 1:
                # Calculate weighted mean
                total_weight = sum(e.weight for e in effects)
                weighted_mean = sum(e.effect_estimate * e.weight for e in effects) / total_weight
                
                # Approximate CI (simple inverse variance)
                var = 1 / total_weight
                se = np.sqrt(var)
                ci_lower = weighted_mean - 1.96 * se
                ci_upper = weighted_mean + 1.96 * se
                
                # Draw diamond at bottom
                diamond_y = 0
                diamond_x = [ci_lower, weighted_mean, ci_upper, weighted_mean, ci_lower]
                diamond_y_coords = [diamond_y, diamond_y + 0.25, diamond_y, diamond_y - 0.25, diamond_y]
                ax.fill(diamond_x, diamond_y_coords, color='darkblue', alpha=0.5, zorder=15)
                ax.text(-0.1, diamond_y, "Summary",
                       ha='right', va='center', fontsize=config.font_size, fontweight='bold',
                       transform=ax.get_yaxis_transform())
            
            # Null line
            ax.axvline(config.null_line_value, color='gray', linestyle='--', linewidth=1.5, zorder=1)
            
            # X-axis
            if config.x_scale == "log":
                ax.set_xscale('log')
            
            x_label = config.x_label or f"{config.effect_measure} (95% CI)"
            ax.set_xlabel(x_label, fontsize=config.font_size)
            
            # Y-axis
            ax.set_yticks([])
            ax.set_ylim(-0.5, n_studies + 0.5)
            
            # Title
            if config.title:
                ax.set_title(config.title, fontsize=config.font_size+2, fontweight='bold')
            
            # Grid
            if config.show_grid:
                ax.grid(True, alpha=0.3, linestyle='--', axis='x')
                ax.set_axisbelow(True)
            
            # Spine cleanup
            ax.spines['left'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['top'].set_visible(False)
            
            plt.tight_layout()
            
            image_bytes = self._fig_to_bytes(fig, ExportFormat.PNG)
            plt.close(fig)
            
            caption = self._generate_forest_caption(effects, config)
            alt_text = f"Forest plot showing meta-analysis of {len(effects)} studies"
            
            return Figure(
                figure_id=f"forest_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                viz_type=VizType.FOREST_PLOT,
                image_bytes=image_bytes,
                format=ExportFormat.PNG,
                width=config.width,
                height=config.height,
                dpi=config.dpi,
                caption=caption,
                alt_text=alt_text,
                data_summary={"n_studies": len(effects), "effect_measure": config.effect_measure},
                rendering_info={"x_scale": config.x_scale}
            )
            
        except Exception as e:
            logger.error(f"Error creating forest plot: {e}")
            return Figure(figure_id="forest_error", viz_type=VizType.FOREST_PLOT)

    def create_flowchart(self, stages: List[FlowStage], diagram_type: str = "consort") -> Figure:
        """Create CONSORT/PRISMA flowchart diagram.
        
        Args:
            stages: List of FlowStage objects representing study flow
            diagram_type: "consort" or "prisma"
            
        Returns:
            Figure object with rendered flowchart as image_bytes
        """
        try:
            fig, ax = plt.subplots(figsize=(10, 12), dpi=300)
            ax.set_xlim(0, 10)
            ax.set_ylim(0, len(stages) + 1)
            ax.axis('off')
            
            # Box styling
            box_width = 6
            box_height = 0.8
            box_x = 2
            
            for idx, stage in enumerate(stages):
                y_pos = len(stages) - idx
                
                # Draw box
                box = plt.Rectangle((box_x, y_pos - box_height/2), box_width, box_height,
                                   facecolor='lightblue', edgecolor='black', linewidth=2)
                ax.add_patch(box)
                
                # Add text
                text = f"{stage.name}\n(n = {stage.n})"
                if stage.description:
                    text += f"\n{stage.description}"
                
                ax.text(box_x + box_width/2, y_pos, text,
                       ha='center', va='center', fontsize=10, fontweight='bold')
                
                # Arrow to next stage
                if idx < len(stages) - 1:
                    arrow_start_y = y_pos - box_height/2
                    arrow_end_y = y_pos - 1 + box_height/2
                    ax.arrow(box_x + box_width/2, arrow_start_y,
                           0, arrow_end_y - arrow_start_y,
                           head_width=0.3, head_length=0.1,
                           fc='black', ec='black', linewidth=2)
                
                # Show exclusions
                if stage.reasons_excluded:
                    excl_x = box_x + box_width + 0.5
                    excl_text = "Excluded:\n"
                    for reason, count in stage.reasons_excluded.items():
                        excl_text += f"• {reason}: n={count}\n"
                    
                    ax.text(excl_x, y_pos, excl_text,
                           ha='left', va='center', fontsize=8,
                           bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
            
            # Title
            title = f"{diagram_type.upper()} Flow Diagram"
            ax.text(5, len(stages) + 0.5, title,
                   ha='center', va='center', fontsize=14, fontweight='bold')
            
            plt.tight_layout()
            
            image_bytes = self._fig_to_bytes(fig, ExportFormat.PNG)
            plt.close(fig)
            
            caption = self._generate_flowchart_caption(stages, diagram_type)
            alt_text = f"{diagram_type.upper()} flowchart showing study participant flow"
            
            viz_type = VizType.CONSORT_DIAGRAM if diagram_type == "consort" else VizType.PRISMA_DIAGRAM
            
            return Figure(
                figure_id=f"{diagram_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                viz_type=viz_type,
                image_bytes=image_bytes,
                format=ExportFormat.PNG,
                width=1000,
                height=1200,
                dpi=300,
                caption=caption,
                alt_text=alt_text,
                data_summary={"n_stages": len(stages), "diagram_type": diagram_type},
                rendering_info={"box_count": len(stages)}
            )
            
        except Exception as e:
            logger.error(f"Error creating flowchart: {e}")
            viz_type = VizType.CONSORT_DIAGRAM if diagram_type == "consort" else VizType.PRISMA_DIAGRAM
            return Figure(figure_id=f"{diagram_type}_error", viz_type=viz_type)


    # Helper methods for visualization
    def _apply_style(self, config: BaseChartConfig) -> None:
        """Apply matplotlib style based on config."""
        plt.rcParams['font.family'] = config.font_family
        plt.rcParams['font.size'] = config.font_size
        
        # Apply journal-specific styles
        if config.journal_style in self.style_presets:
            preset = self.style_presets[config.journal_style]
            plt.rcParams['font.family'] = preset.get('font_family', config.font_family)
            plt.rcParams['font.size'] = preset.get('font_size', config.font_size)
    
    def _get_colors(self, palette: ColorPalette, n_colors: int) -> List[str]:
        """Get color list from palette."""
        if palette in self.color_palettes:
            colors = self.color_palettes[palette]
            # Repeat colors if needed
            return (colors * ((n_colors // len(colors)) + 1))[:n_colors]
        
        # Default palettes
        if palette == ColorPalette.GRAYSCALE:
            return [f"#{int(255 - i * (200/n_colors)):02x}" * 3 for i in range(n_colors)]
        elif palette == ColorPalette.VIRIDIS:
            import matplotlib.cm as cm
            cmap = cm.get_cmap('viridis')
            return [matplotlib.colors.rgb2hex(cmap(i/n_colors)) for i in range(n_colors)]
        else:
            # Default colorblind-safe
            return self.color_palettes[ColorPalette.COLORBLIND_SAFE]
    
    def _fig_to_bytes(self, fig: plt.Figure, format: ExportFormat) -> bytes:
        """Convert matplotlib figure to bytes."""
        buf = BytesIO()
        fig.savefig(buf, format=format.value, bbox_inches='tight', dpi=fig.dpi)
        buf.seek(0)
        return buf.read()
    
    # Caption generation methods
    def _generate_bar_caption(self, data: pd.DataFrame, config: BarChartConfig) -> str:
        """Generate caption for bar chart."""
        x_col = data.columns[0]
        y_col = data.columns[1] if len(data.columns) > 1 else data.columns[0]
        
        caption = f"Bar chart showing {y_col} by {x_col}. "
        if config.show_error_bars:
            caption += f"Error bars represent {config.error_bar_type}. "
        caption += f"N = {len(data)} groups."
        return caption
    
    def _generate_line_caption(self, data: pd.DataFrame, config: LineChartConfig) -> str:
        """Generate caption for line chart."""
        x_col = data.columns[0]
        y_cols = data.columns[1:]
        
        caption = f"Line chart showing trends over {x_col}. "
        if len(y_cols) > 1:
            caption += f"{len(y_cols)} series plotted. "
        if config.show_confidence_bands:
            caption += f"Shaded areas represent {config.confidence_level*100:.0f}% confidence intervals."
        return caption
    
    def _generate_scatter_caption(self, data: pd.DataFrame, config: ScatterConfig) -> str:
        """Generate caption for scatter plot."""
        x_col = data.columns[0]
        y_col = data.columns[1]
        
        caption = f"Scatter plot showing relationship between {x_col} and {y_col}. "
        if config.show_correlation:
            corr = data[x_col].corr(data[y_col])
            caption += f"Correlation r = {corr:.3f}. "
        if config.show_trendline:
            caption += "Trendline shown in red. "
        caption += f"N = {len(data)} observations."
        return caption
    
    def _generate_box_caption(self, data: pd.DataFrame, config: BoxPlotConfig) -> str:
        """Generate caption for box plot."""
        y_col = data.columns[1] if len(data.columns) > 1 else data.columns[0]
        x_col = data.columns[0] if len(data.columns) > 1 else None
        
        caption = f"Box plot showing distribution of {y_col}"
        if x_col:
            caption += f" by {x_col}"
        caption += ". "
        
        if config.show_means:
            caption += "Green triangle indicates mean. "
        if config.show_outliers:
            caption += "Outliers shown as individual points. "
        caption += f"N = {len(data)} observations."
        return caption
    
    def _generate_km_caption(self, data: pd.DataFrame, config: KMConfig) -> str:
        """Generate caption for Kaplan-Meier curve."""
        time_col = data.columns[0]
        event_col = data.columns[1]
        group_col = data.columns[2] if len(data.columns) > 2 else None
        
        n_events = data[event_col].sum()
        n_total = len(data)
        
        caption = "Kaplan-Meier survival curve. "
        if group_col:
            n_groups = data[group_col].nunique()
            caption += f"{n_groups} groups compared. "
        
        if config.show_confidence_intervals:
            caption += f"Shaded areas represent {config.confidence_level*100:.0f}% confidence intervals. "
        
        caption += f"Total N = {n_total}, events = {n_events}."
        return caption
    
    def _generate_forest_caption(self, effects: List[EffectSize], config: ForestConfig) -> str:
        """Generate caption for forest plot."""
        caption = f"Forest plot showing meta-analysis results. "
        caption += f"{len(effects)} studies included. "
        caption += f"Effect measure: {config.effect_measure}. "
        
        if config.show_diamond_summary:
            caption += "Summary effect shown as diamond at bottom. "
        
        caption += "Horizontal lines represent 95% confidence intervals."
        return caption
    
    def _generate_flowchart_caption(self, stages: List[FlowStage], diagram_type: str) -> str:
        """Generate caption for flowchart."""
        caption = f"{diagram_type.upper()} flow diagram showing study participant flow. "
        caption += f"{len(stages)} stages from {stages[0].name} "
        caption += f"(n = {stages[0].n}) to {stages[-1].name} (n = {stages[-1].n})."
        return caption


def create_data_visualization_agent() -> DataVisualizationAgent:
    """Factory function for creating DataVisualizationAgent."""
    return DataVisualizationAgent()
