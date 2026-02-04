"""
Optimization functions for SupplementaryMaterial Agent.
Stage 1.3 - Optimization Functions

Provides smart optimization capabilities including file size reduction,
compression strategies, format recommendations, and performance enhancements
for large supplementary material packages.

Integrates with supplementary_validators.py for optimization based on validation results.
"""

from typing import List, Dict, Any, Optional, Tuple, Union
import re
import gzip
import zipfile
import tempfile
import shutil
from pathlib import Path
import logging
from datetime import datetime
import json
import pandas as pd
import numpy as np
from dataclasses import dataclass, field
import io
import base64

from .supplementary_types import (
    SupplementaryMaterialState, 
    SupplementaryTable, 
    SupplementaryFigure,
    Appendix,
    JournalRequirements,
    JournalFormat,
    FileFormat
)
from .supplementary_validators import SupplementaryPackageValidator

logger = logging.getLogger(__name__)

@dataclass
class OptimizationResult:
    """Results from optimization operations."""
    original_size_mb: float
    optimized_size_mb: float
    compression_ratio: float
    optimization_type: str
    recommendations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def size_reduction_percent(self) -> float:
        """Calculate size reduction percentage."""
        if self.original_size_mb == 0:
            return 0.0
        return ((self.original_size_mb - self.optimized_size_mb) / self.original_size_mb) * 100

@dataclass
class CompressionStrategy:
    """Compression strategy configuration."""
    name: str
    file_extensions: List[str]
    compression_level: int
    expected_ratio: float
    description: str

class PackageSizeOptimizer:
    """
    Optimizes the overall size of supplementary material packages
    through intelligent content analysis and compression recommendations.
    """
    
    def __init__(self, max_target_size_mb: float = 50.0):
        self.max_target_size_mb = max_target_size_mb
        self.optimization_strategies = self._initialize_strategies()
        
    def _initialize_strategies(self) -> List[Dict[str, Any]]:
        """Initialize available optimization strategies."""
        return [
            {
                "name": "table_content_compression",
                "priority": 1,
                "target_types": ["table"],
                "expected_reduction": 0.3,
                "description": "Optimize table content formatting and remove redundancy"
            },
            {
                "name": "figure_format_optimization", 
                "priority": 2,
                "target_types": ["figure"],
                "expected_reduction": 0.4,
                "description": "Convert figures to optimal formats and compression"
            },
            {
                "name": "content_deduplication",
                "priority": 3,
                "target_types": ["table", "figure", "appendix"],
                "expected_reduction": 0.2,
                "description": "Remove duplicate content across items"
            },
            {
                "name": "appendix_consolidation",
                "priority": 4,
                "target_types": ["appendix"],
                "expected_reduction": 0.25,
                "description": "Consolidate related appendix sections"
            }
        ]
    
    def optimize_package_size(self, state: SupplementaryMaterialState) -> OptimizationResult:
        """
        Optimize the overall package size using multiple strategies.
        """
        logger.info("Starting package size optimization")
        
        original_size = state.package_size_mb
        current_size = original_size
        applied_optimizations = []
        recommendations = []
        warnings = []
        
        # Apply optimization strategies in priority order
        for strategy in sorted(self.optimization_strategies, key=lambda x: x["priority"]):
            try:
                if current_size <= self.max_target_size_mb:
                    break
                    
                result = self._apply_optimization_strategy(state, strategy, current_size)
                
                if result["size_reduction"] > 0:
                    current_size -= result["size_reduction"]
                    applied_optimizations.append(strategy["name"])
                    recommendations.extend(result.get("recommendations", []))
                    
                logger.debug(f"Applied {strategy['name']}: {result['size_reduction']:.2f}MB reduction")
                
            except Exception as e:
                warning = f"Failed to apply {strategy['name']}: {str(e)}"
                warnings.append(warning)
                logger.warning(warning)
        
        # Calculate final compression ratio
        compression_ratio = current_size / original_size if original_size > 0 else 1.0
        
        # Generate additional recommendations if still too large
        if current_size > self.max_target_size_mb:
            recommendations.extend(self._generate_size_reduction_recommendations(state, current_size))
        
        return OptimizationResult(
            original_size_mb=original_size,
            optimized_size_mb=current_size,
            compression_ratio=compression_ratio,
            optimization_type="package_size_optimization",
            recommendations=recommendations,
            warnings=warnings,
            metadata={
                "applied_strategies": applied_optimizations,
                "target_size_mb": self.max_target_size_mb,
                "size_limit_achieved": current_size <= self.max_target_size_mb
            }
        )
    
    def _apply_optimization_strategy(self, state: SupplementaryMaterialState, 
                                   strategy: Dict[str, Any], current_size: float) -> Dict[str, Any]:
        """Apply a specific optimization strategy."""
        
        if strategy["name"] == "table_content_compression":
            return self._optimize_table_content(state)
        elif strategy["name"] == "figure_format_optimization":
            return self._optimize_figure_formats(state)
        elif strategy["name"] == "content_deduplication":
            return self._deduplicate_content(state)
        elif strategy["name"] == "appendix_consolidation":
            return self._consolidate_appendices(state)
        else:
            return {"size_reduction": 0, "recommendations": []}
    
    def _optimize_table_content(self, state: SupplementaryMaterialState) -> Dict[str, Any]:
        """Optimize table content for size reduction."""
        total_reduction = 0.0
        recommendations = []
        
        for table in state.supplementary_tables:
            # Estimate current table size
            content_size = len(table.content.encode('utf-8')) / (1024 * 1024)  # MB
            
            # Apply optimizations
            optimized_content = self._compress_table_content(table.content)
            optimized_size = len(optimized_content.encode('utf-8')) / (1024 * 1024)  # MB
            
            reduction = content_size - optimized_size
            total_reduction += reduction
            
            if reduction > 0.1:  # Only update if significant reduction
                table.content = optimized_content
                recommendations.append(f"Optimized Table {table.number} content ({reduction:.2f}MB saved)")
        
        return {
            "size_reduction": total_reduction,
            "recommendations": recommendations
        }
    
    def _optimize_figure_formats(self, state: SupplementaryMaterialState) -> Dict[str, Any]:
        """Optimize figure formats for size reduction."""
        total_reduction = 0.0
        recommendations = []
        
        for figure in state.supplementary_figures:
            # Estimate potential reduction based on format
            current_format = getattr(figure, 'format', 'unknown')
            
            if current_format in ['png', 'jpeg'] and hasattr(figure, 'file_path'):
                # Estimate 30% reduction from format optimization
                estimated_size = 2.0  # Average figure size estimate
                reduction = estimated_size * 0.3
                total_reduction += reduction
                
                recommendations.append(
                    f"Convert Figure {figure.number} to PDF for {reduction:.2f}MB reduction"
                )
        
        return {
            "size_reduction": total_reduction,
            "recommendations": recommendations
        }
    
    def _deduplicate_content(self, state: SupplementaryMaterialState) -> Dict[str, Any]:
        """Remove duplicate content across supplementary items."""
        total_reduction = 0.0
        recommendations = []
        
        # Find duplicate table content
        table_contents = {}
        for table in state.supplementary_tables:
            content_hash = hash(table.content)
            if content_hash in table_contents:
                # Found duplicate
                reduction = len(table.content.encode('utf-8')) / (1024 * 1024) * 0.5  # Estimate
                total_reduction += reduction
                recommendations.append(
                    f"Duplicate content found between Table {table.number} and Table {table_contents[content_hash]}"
                )
            else:
                table_contents[content_hash] = table.number
        
        return {
            "size_reduction": total_reduction,
            "recommendations": recommendations
        }
    
    def _consolidate_appendices(self, state: SupplementaryMaterialState) -> Dict[str, Any]:
        """Consolidate related appendix sections."""
        if len(state.appendices) <= 1:
            return {"size_reduction": 0, "recommendations": []}
        
        # Estimate reduction from consolidation
        total_appendix_size = sum(
            len(appendix.content.encode('utf-8')) for appendix in state.appendices
        ) / (1024 * 1024)
        
        estimated_reduction = total_appendix_size * 0.15  # 15% reduction estimate
        
        return {
            "size_reduction": estimated_reduction,
            "recommendations": [
                f"Consider consolidating {len(state.appendices)} appendices into {max(1, len(state.appendices) // 2)} sections"
            ]
        }
    
    def _compress_table_content(self, content: str) -> str:
        """Compress table content by removing redundancy."""
        # Remove excessive whitespace
        compressed = re.sub(r'\s+', ' ', content.strip())
        
        # Remove empty lines
        compressed = re.sub(r'\n\s*\n', '\n', compressed)
        
        # Optimize HTML table formatting if present
        if '<table>' in compressed.lower():
            # Remove unnecessary HTML attributes
            compressed = re.sub(r'\s*(class|style|id)="[^"]*"', '', compressed)
            # Minimize spacing in HTML
            compressed = re.sub(r'>\s+<', '><', compressed)
        
        return compressed
    
    def _generate_size_reduction_recommendations(self, state: SupplementaryMaterialState, 
                                               current_size: float) -> List[str]:
        """Generate additional recommendations when package is still too large."""
        recommendations = []
        excess_size = current_size - self.max_target_size_mb
        
        recommendations.append(
            f"Package size ({current_size:.1f}MB) exceeds target ({self.max_target_size_mb:.1f}MB) by {excess_size:.1f}MB"
        )
        
        if len(state.supplementary_tables) > 5:
            recommendations.append("Consider moving some tables to online-only supplements")
        
        if len(state.supplementary_figures) > 3:
            recommendations.append("Consider creating figure panels instead of separate figures")
        
        if state.include_raw_data:
            recommendations.append("Consider providing raw data via external repository link instead")
        
        recommendations.append("Use ZIP compression for the final package")
        
        return recommendations


class CompressionEngine:
    """
    Smart compression engine that selects optimal compression strategies
    based on file types and content characteristics.
    """
    
    def __init__(self):
        self.compression_strategies = self._initialize_compression_strategies()
        
    def _initialize_compression_strategies(self) -> List[CompressionStrategy]:
        """Initialize available compression strategies."""
        return [
            CompressionStrategy(
                name="gzip_text",
                file_extensions=['.txt', '.csv', '.json', '.xml'],
                compression_level=9,
                expected_ratio=0.3,
                description="High compression for text-based files"
            ),
            CompressionStrategy(
                name="zip_mixed",
                file_extensions=['.pdf', '.docx', '.xlsx'],
                compression_level=6,
                expected_ratio=0.8,
                description="Moderate compression for mixed content"
            ),
            CompressionStrategy(
                name="lossless_images",
                file_extensions=['.png', '.tiff'],
                compression_level=9,
                expected_ratio=0.7,
                description="Lossless compression for images"
            ),
            CompressionStrategy(
                name="archive_package",
                file_extensions=['.zip', '.tar.gz'],
                compression_level=6,
                expected_ratio=0.6,
                description="Package-level compression"
            )
        ]
    
    def compress_content(self, content: str, content_type: str = "text") -> OptimizationResult:
        """Compress text content using appropriate strategy."""
        logger.debug(f"Compressing {content_type} content ({len(content)} chars)")
        
        original_size = len(content.encode('utf-8')) / (1024 * 1024)  # MB
        
        try:
            # Use gzip compression for text content
            compressed_data = gzip.compress(content.encode('utf-8'))
            compressed_size = len(compressed_data) / (1024 * 1024)  # MB
            
            compression_ratio = compressed_size / original_size if original_size > 0 else 1.0
            
            return OptimizationResult(
                original_size_mb=original_size,
                optimized_size_mb=compressed_size,
                compression_ratio=compression_ratio,
                optimization_type="content_compression",
                recommendations=[f"Content compressed with {(1-compression_ratio)*100:.1f}% size reduction"],
                metadata={
                    "compression_method": "gzip",
                    "compression_level": 9
                }
            )
            
        except Exception as e:
            logger.error(f"Compression failed: {e}")
            return OptimizationResult(
                original_size_mb=original_size,
                optimized_size_mb=original_size,
                compression_ratio=1.0,
                optimization_type="content_compression",
                warnings=[f"Compression failed: {str(e)}"]
            )

class FormatRecommendationEngine:
    """
    Recommends optimal file formats based on content type,
    journal requirements, and file size considerations.
    """
    
    def __init__(self):
        self.format_profiles = self._initialize_format_profiles()
        
    def _initialize_format_profiles(self) -> Dict[str, Dict[str, Any]]:
        """Initialize format recommendation profiles."""
        return {
            "table": {
                "primary_formats": [FileFormat.XLSX, FileFormat.CSV],
                "fallback_formats": [FileFormat.PDF],
                "size_efficient": FileFormat.CSV,
                "feature_rich": FileFormat.XLSX,
                "universal": FileFormat.PDF
            },
            "figure": {
                "primary_formats": [FileFormat.PDF, FileFormat.PNG],
                "fallback_formats": [FileFormat.JPEG],
                "size_efficient": FileFormat.PNG,
                "feature_rich": FileFormat.PDF,
                "universal": FileFormat.PDF
            },
            "appendix": {
                "primary_formats": [FileFormat.PDF, FileFormat.DOCX],
                "fallback_formats": [FileFormat.ZIP],
                "size_efficient": FileFormat.DOCX,
                "feature_rich": FileFormat.PDF,
                "universal": FileFormat.PDF
            }
        }
    
    def recommend_formats(self, state: SupplementaryMaterialState) -> Dict[str, Any]:
        """Recommend optimal formats for all content in the package."""
        logger.info("Generating format recommendations")
        
        journal_requirements = JournalRequirements.get_requirements(state.journal_format)
        recommendations = {
            "overall_strategy": self._determine_overall_strategy(state, journal_requirements),
            "table_recommendations": [],
            "figure_recommendations": [], 
            "appendix_recommendations": [],
            "package_recommendations": [],
            "size_impact": {}
        }
        
        # Table format recommendations
        for table in state.supplementary_tables:
            table_rec = self._recommend_table_format(table, journal_requirements)
            recommendations["table_recommendations"].append(table_rec)
        
        # Figure format recommendations
        for figure in state.supplementary_figures:
            figure_rec = self._recommend_figure_format(figure, journal_requirements)
            recommendations["figure_recommendations"].append(figure_rec)
        
        # Appendix format recommendations
        for appendix in state.appendices:
            appendix_rec = self._recommend_appendix_format(appendix, journal_requirements)
            recommendations["appendix_recommendations"].append(appendix_rec)
        
        # Package-level recommendations
        package_rec = self._recommend_package_format(state, journal_requirements)
        recommendations["package_recommendations"] = package_rec
        
        # Size impact analysis
        recommendations["size_impact"] = self._analyze_size_impact(state, recommendations)
        
        return recommendations
    
    def _determine_overall_strategy(self, state: SupplementaryMaterialState,
                                  requirements: JournalRequirements) -> str:
        """Determine overall format strategy."""
        if state.package_size_mb > requirements.max_size_mb * 0.8:
            return "size_optimization"
        elif len(state.supplementary_tables + state.supplementary_figures + state.appendices) > 10:
            return "organization_focus"
        else:
            return "quality_focus"
    
    def _recommend_table_format(self, table: SupplementaryTable,
                               requirements: JournalRequirements) -> Dict[str, Any]:
        """Recommend format for a specific table."""
        
        # Analyze table content characteristics
        content_analysis = self._analyze_table_content(table)
        
        # Determine best format based on content and requirements
        if content_analysis["has_complex_formatting"]:
            recommended_format = FileFormat.PDF
            reasoning = "Complex formatting best preserved in PDF"
        elif content_analysis["data_rows"] > 1000:
            recommended_format = FileFormat.CSV
            reasoning = "Large dataset optimized as CSV for size and accessibility"
        elif requirements.table_format == "excel":
            recommended_format = FileFormat.XLSX
            reasoning = f"Journal prefers Excel format"
        else:
            recommended_format = FileFormat.PDF
            reasoning = "PDF provides universal compatibility"
        
        return {
            "table_id": table.number,
            "current_format": "html",  # Assumed from content
            "recommended_format": recommended_format.value,
            "reasoning": reasoning,
            "priority": "high" if content_analysis["data_rows"] > 500 else "medium",
            "estimated_size_change": self._estimate_format_size_change(
                "table", "html", recommended_format.value, len(table.content)
            ),
            "content_analysis": content_analysis
        }
    
    def _recommend_figure_format(self, figure: SupplementaryFigure,
                                requirements: JournalRequirements) -> Dict[str, Any]:
        """Recommend format for a specific figure."""
        
        current_format = getattr(figure, 'format', 'unknown')
        
        # Determine optimal format
        if requirements.figure_format == "pdf":
            recommended_format = FileFormat.PDF
            reasoning = "Journal requires PDF format for figures"
        elif current_format in ['jpeg', 'jpg'] and getattr(figure, 'dpi', 0) >= 300:
            recommended_format = FileFormat.PNG
            reasoning = "Convert JPEG to PNG for better quality preservation"
        else:
            recommended_format = FileFormat.PDF
            reasoning = "PDF provides scalable vector graphics and universal support"
        
        return {
            "figure_id": figure.number,
            "current_format": current_format,
            "recommended_format": recommended_format.value,
            "reasoning": reasoning,
            "priority": "high",
            "estimated_size_change": self._estimate_format_size_change(
                "figure", current_format, recommended_format.value, 2048  # Estimate 2MB
            )
        }
    
    def _recommend_appendix_format(self, appendix: Appendix,
                                  requirements: JournalRequirements) -> Dict[str, Any]:
        """Recommend format for a specific appendix."""
        
        content_length = len(appendix.content)
        
        if content_length > 50000:  # Long content
            recommended_format = FileFormat.PDF
            reasoning = "Long content formatted as PDF for readability"
        elif appendix.type.value == "code":
            recommended_format = FileFormat.ZIP
            reasoning = "Code files packaged as ZIP archive"
        else:
            recommended_format = FileFormat.DOCX
            reasoning = "Standard document format for text content"
        
        return {
            "appendix_id": appendix.id,
            "current_format": "text",
            "recommended_format": recommended_format.value,
            "reasoning": reasoning,
            "priority": "medium",
            "estimated_size_change": 0.0  # Minimal change for appendices
        }
    
    def _analyze_table_content(self, table: SupplementaryTable) -> Dict[str, Any]:
        """Analyze table content characteristics."""
        content = table.content.lower()
        
        # Estimate number of data rows
        data_rows = max(content.count('<tr>'), content.count('\n')) - 1  # Exclude header
        
        # Check for complex formatting
        has_complex_formatting = any(tag in content for tag in [
            '<span', '<div', 'style=', 'class=', '<img', 'rowspan', 'colspan'
        ])
        
        # Check for numeric data density
        numeric_content = len(re.findall(r'\d+\.?\d*', content))
        total_words = len(content.split())
        numeric_density = numeric_content / max(total_words, 1)
        
        return {
            "data_rows": max(1, data_rows),
            "has_complex_formatting": has_complex_formatting,
            "numeric_density": numeric_density,
            "content_length": len(content),
            "estimated_columns": max(content.count('<th>'), content.count(','))
        }
    
    def _estimate_format_size_change(self, item_type: str, current_format: str, 
                                   new_format: str, content_size: int) -> float:
        """Estimate size change from format conversion."""
        # Size change multipliers (rough estimates)
        format_multipliers = {
            "html_to_pdf": 1.2,
            "html_to_csv": 0.6,
            "html_to_xlsx": 0.8,
            "png_to_pdf": 0.9,
            "jpeg_to_png": 1.1,
            "text_to_pdf": 1.3,
            "text_to_docx": 0.9
        }
        
        conversion_key = f"{current_format}_to_{new_format}"
        multiplier = format_multipliers.get(conversion_key, 1.0)
        
        # Convert content size to MB estimate
        size_mb = content_size / (1024 * 1024)
        size_change = size_mb * (multiplier - 1.0)
        
        return round(size_change, 3)
    
    def _analyze_size_impact(self, state: SupplementaryMaterialState, 
                           recommendations: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze overall size impact of format recommendations."""
        
        total_current_size = state.package_size_mb
        estimated_new_size = total_current_size
        
        # Sum up estimated changes
        for table_rec in recommendations["table_recommendations"]:
            estimated_new_size += table_rec["estimated_size_change"]
        
        for figure_rec in recommendations["figure_recommendations"]:
            estimated_new_size += figure_rec["estimated_size_change"]
        
        return {
            "current_size_mb": total_current_size,
            "estimated_new_size_mb": max(0, estimated_new_size),
            "estimated_change_mb": estimated_new_size - total_current_size,
            "estimated_change_percent": ((estimated_new_size - total_current_size) / total_current_size * 100) if total_current_size > 0 else 0
        }


class ContentOptimizer:
    """
    Optimizes content quality, organization, and presentation
    for supplementary materials.
    """
    
    def __init__(self):
        self.optimization_rules = self._initialize_optimization_rules()
    
    def _initialize_optimization_rules(self) -> Dict[str, Any]:
        """Initialize content optimization rules."""
        return {
            "table_optimization": {
                "min_caption_length": 100,
                "max_decimal_places": 3,
                "preferred_thousand_separator": ",",
                "require_units": True,
                "require_statistical_notation": True
            },
            "figure_optimization": {
                "min_caption_length": 150,
                "require_scale_bars": True,
                "require_legend": True,
                "min_dpi": 300,
                "preferred_font_size": 12
            },
            "appendix_optimization": {
                "max_section_length": 5000,
                "require_subsections": True,
                "min_heading_levels": 2
            }
        }
    
    def optimize_content(self, state: SupplementaryMaterialState) -> OptimizationResult:
        """Optimize all content in the supplementary package."""
        logger.info("Starting content optimization")
        
        optimizations_applied = []
        recommendations = []
        warnings = []
        
        # Optimize tables
        table_results = self._optimize_tables(state)
        optimizations_applied.extend(table_results["optimizations"])
        recommendations.extend(table_results["recommendations"])
        
        # Optimize figures
        figure_results = self._optimize_figures(state)
        optimizations_applied.extend(figure_results["optimizations"])
        recommendations.extend(figure_results["recommendations"])
        
        # Optimize appendices
        appendix_results = self._optimize_appendices(state)
        optimizations_applied.extend(appendix_results["optimizations"])
        recommendations.extend(appendix_results["recommendations"])
        
        # Optimize cross-references
        reference_results = self._optimize_cross_references(state)
        optimizations_applied.extend(reference_results["optimizations"])
        recommendations.extend(reference_results["recommendations"])
        
        return OptimizationResult(
            original_size_mb=state.package_size_mb,
            optimized_size_mb=state.package_size_mb,  # Content optimization doesn't change size significantly
            compression_ratio=1.0,
            optimization_type="content_optimization",
            recommendations=recommendations,
            warnings=warnings,
            metadata={
                "optimizations_applied": optimizations_applied,
                "tables_optimized": len(state.supplementary_tables),
                "figures_optimized": len(state.supplementary_figures),
                "appendices_optimized": len(state.appendices)
            }
        )
    
    def _optimize_tables(self, state: SupplementaryMaterialState) -> Dict[str, Any]:
        """Optimize table content and formatting."""
        optimizations = []
        recommendations = []
        
        for table in state.supplementary_tables:
            # Check caption length
            if len(table.caption) < self.optimization_rules["table_optimization"]["min_caption_length"]:
                recommendations.append(f"Table {table.number}: Caption should be more detailed (current: {len(table.caption)} chars)")
            
            # Check for statistical notation
            if not self._has_statistical_notation(table.content):
                recommendations.append(f"Table {table.number}: Consider adding statistical significance notation")
            
            # Optimize numeric formatting
            optimized_content = self._optimize_numeric_formatting(table.content)
            if optimized_content != table.content:
                table.content = optimized_content
                optimizations.append(f"Optimized numeric formatting for Table {table.number}")
        
        return {
            "optimizations": optimizations,
            "recommendations": recommendations
        }
    
    def _optimize_figures(self, state: SupplementaryMaterialState) -> Dict[str, Any]:
        """Optimize figure content and metadata."""
        optimizations = []
        recommendations = []
        
        for figure in state.supplementary_figures:
            # Check caption length
            if len(figure.caption) < self.optimization_rules["figure_optimization"]["min_caption_length"]:
                recommendations.append(f"Figure {figure.number}: Caption should be more detailed (current: {len(figure.caption)} chars)")
            
            # Check for legend
            if not figure.legend or len(figure.legend.strip()) < 50:
                recommendations.append(f"Figure {figure.number}: Consider adding detailed legend")
            
            # Check DPI
            if hasattr(figure, 'dpi') and figure.dpi < self.optimization_rules["figure_optimization"]["min_dpi"]:
                recommendations.append(f"Figure {figure.number}: DPI ({figure.dpi}) below recommended minimum (300)")
        
        return {
            "optimizations": optimizations,
            "recommendations": recommendations
        }
    
    def _optimize_appendices(self, state: SupplementaryMaterialState) -> Dict[str, Any]:
        """Optimize appendix content and structure."""
        optimizations = []
        recommendations = []
        
        for appendix in state.appendices:
            content_length = len(appendix.content)
            
            # Check section length
            if content_length > self.optimization_rules["appendix_optimization"]["max_section_length"]:
                recommendations.append(f"Appendix {appendix.id}: Consider breaking into subsections (current: {content_length} chars)")
            
            # Check for subsections
            if content_length > 2000 and not self._has_subsections(appendix.content):
                recommendations.append(f"Appendix {appendix.id}: Consider adding subsection headings for better organization")
        
        return {
            "optimizations": optimizations,
            "recommendations": recommendations
        }
    
    def _optimize_cross_references(self, state: SupplementaryMaterialState) -> Dict[str, Any]:
        """Optimize cross-reference formatting and completeness."""
        optimizations = []
        recommendations = []
        
        # Standardize cross-reference format
        all_content = [
            state.main_manuscript,
            *[table.caption + " " + table.content for table in state.supplementary_tables],
            *[figure.caption for figure in state.supplementary_figures],
            *[appendix.content for appendix in state.appendices]
        ]
        
        reference_issues = []
        for i, content in enumerate(all_content):
            if content:
                standardized_content = self._standardize_references(content)
                if standardized_content != content:
                    optimizations.append(f"Standardized cross-reference format in content section {i+1}")
        
        return {
            "optimizations": optimizations,
            "recommendations": recommendations
        }
    
    def _has_statistical_notation(self, content: str) -> bool:
        """Check if content has statistical significance notation."""
        stat_indicators = ['*', '†', '‡', 'p<', 'p =', 'CI', '95%', 'SD', 'SE']
        return any(indicator in content for indicator in stat_indicators)
    
    def _optimize_numeric_formatting(self, content: str) -> str:
        """Optimize numeric formatting in content."""
        # Standardize decimal places (max 3)
        content = re.sub(r'(\d+\.\d{4,})', lambda m: f"{float(m.group(1)):.3f}", content)
        
        # Add thousand separators to large numbers
        def add_thousands_separator(match):
            number = match.group(1)
            if len(number) > 3:
                return f"{int(number):,}"
            return number
        
        content = re.sub(r'\b(\d{4,})\b', add_thousands_separator, content)
        
        return content
    
    def _has_subsections(self, content: str) -> bool:
        """Check if content has subsection headings."""
        # Look for common heading patterns
        heading_patterns = [
            r'^[A-Z][A-Za-z\s]+:$',  # Title Case:
            r'^\d+\.\s+[A-Z]',        # 1. Numbered
            r'^[A-Z][A-Z\s]+$',       # ALL CAPS
            r'^#{1,3}\s+',            # Markdown headers
        ]
        
        for pattern in heading_patterns:
            if re.search(pattern, content, re.MULTILINE):
                return True
        return False
    
    def _standardize_references(self, content: str) -> str:
        """Standardize cross-reference formatting."""
        # Standardize table references
        content = re.sub(r'\b[Tt]able\s+[Ss](\d+)\b', r'Table S\1', content)
        
        # Standardize figure references
        content = re.sub(r'\b[Ff]igure\s+[Ss](\d+)\b', r'Figure S\1', content)
        
        # Standardize appendix references
        content = re.sub(r'\b[Aa]ppendix\s+([A-Z]\d*)\b', r'Appendix \1', content)
        
        return content


class PerformanceMonitor:
    """
    Monitors optimization performance and provides analytics
    for large supplementary material packages.
    """
    
    def __init__(self):
        self.performance_metrics = {}
        self.optimization_history = []
    
    def track_optimization(self, operation: str, start_time: float, end_time: float, 
                          result: OptimizationResult):
        """Track optimization performance metrics."""
        duration = end_time - start_time
        
        if operation not in self.performance_metrics:
            self.performance_metrics[operation] = {
                "total_runs": 0,
                "total_time": 0.0,
                "avg_time": 0.0,
                "total_size_reduction": 0.0,
                "avg_compression_ratio": 0.0
            }
        
        metrics = self.performance_metrics[operation]
        metrics["total_runs"] += 1
        metrics["total_time"] += duration
        metrics["avg_time"] = metrics["total_time"] / metrics["total_runs"]
        metrics["total_size_reduction"] += result.size_reduction_percent
        metrics["avg_compression_ratio"] = (metrics["avg_compression_ratio"] * (metrics["total_runs"] - 1) + result.compression_ratio) / metrics["total_runs"]
        
        # Store in history
        self.optimization_history.append({
            "timestamp": datetime.now(),
            "operation": operation,
            "duration": duration,
            "result": result
        })
        
        logger.info(f"Optimization {operation} completed in {duration:.3f}s")
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Generate performance report."""
        return {
            "metrics": dict(self.performance_metrics),
            "total_optimizations": len(self.optimization_history),
            "total_time": sum(entry["duration"] for entry in self.optimization_history),
            "avg_optimization_time": np.mean([entry["duration"] for entry in self.optimization_history]) if self.optimization_history else 0,
            "most_effective_operation": max(
                self.performance_metrics.items(),
                key=lambda x: x[1]["total_size_reduction"],
                default=("none", {"total_size_reduction": 0})
            )[0] if self.performance_metrics else "none"
        }


# Main optimization interface
class SupplementaryOptimizer:
    """
    Main optimizer that coordinates all optimization operations
    for supplementary material packages.
    """
    
    def __init__(self, max_package_size_mb: float = 50.0):
        self.package_optimizer = PackageSizeOptimizer(max_package_size_mb)
        self.compression_engine = CompressionEngine()
        self.format_recommender = FormatRecommendationEngine()
        self.content_optimizer = ContentOptimizer()
        self.performance_monitor = PerformanceMonitor()
        
    def optimize_package(self, state: SupplementaryMaterialState,
                        optimization_goals: List[str] = None) -> Dict[str, Any]:
        """
        Run comprehensive optimization of supplementary material package.
        
        Args:
            state: Current supplementary material state
            optimization_goals: List of optimization goals
                ['size', 'format', 'content', 'compression']
        """
        logger.info(f"Starting comprehensive optimization for study {state.study_id}")
        
        if optimization_goals is None:
            optimization_goals = ['size', 'format', 'content', 'compression']
        
        results = {
            "optimization_summary": {
                "study_id": state.study_id,
                "original_size_mb": state.package_size_mb,
                "optimization_goals": optimization_goals,
                "timestamp": datetime.now()
            },
            "optimizations": {},
            "recommendations": [],
            "warnings": [],
            "performance": {}
        }
        
        total_start_time = datetime.now()
        
        # Size optimization
        if 'size' in optimization_goals:
            start_time = time.time()
            size_result = self.package_optimizer.optimize_package_size(state)
            end_time = time.time()
            
            self.performance_monitor.track_optimization("size_optimization", start_time, end_time, size_result)
            results["optimizations"]["size"] = size_result
            results["recommendations"].extend(size_result.recommendations)
            results["warnings"].extend(size_result.warnings)
        
        # Format recommendations
        if 'format' in optimization_goals:
            start_time = time.time()
            format_recommendations = self.format_recommender.recommend_formats(state)
            end_time = time.time()
            
            results["optimizations"]["format"] = format_recommendations
            results["recommendations"].extend([
                rec["reasoning"] for rec in format_recommendations["table_recommendations"]
            ])
        
        # Content optimization
        if 'content' in optimization_goals:
            start_time = time.time()
            content_result = self.content_optimizer.optimize_content(state)
            end_time = time.time()
            
            self.performance_monitor.track_optimization("content_optimization", start_time, end_time, content_result)
            results["optimizations"]["content"] = content_result
            results["recommendations"].extend(content_result.recommendations)
        
        # Compression
        if 'compression' in optimization_goals:
            start_time = time.time()
            compression_result = self.compression_engine.create_compressed_package(state)
            end_time = time.time()
            
            self.performance_monitor.track_optimization("compression", start_time, end_time, compression_result)
            results["optimizations"]["compression"] = compression_result
            results["recommendations"].extend(compression_result.recommendations)
        
        # Calculate final metrics
        total_time = (datetime.now() - total_start_time).total_seconds()
        final_size = min(
            result.optimized_size_mb for result in results["optimizations"].values()
            if hasattr(result, 'optimized_size_mb')
        ) if any(hasattr(result, 'optimized_size_mb') for result in results["optimizations"].values()) else state.package_size_mb
        
        results["optimization_summary"].update({
            "final_size_mb": final_size,
            "total_reduction_mb": state.package_size_mb - final_size,
            "total_reduction_percent": ((state.package_size_mb - final_size) / state.package_size_mb * 100) if state.package_size_mb > 0 else 0,
            "optimization_time_seconds": total_time,
            "optimizations_applied": len([k for k, v in results["optimizations"].items() if hasattr(v, 'recommendations') and v.recommendations])
        })
        
        results["performance"] = self.performance_monitor.get_performance_report()
        
        logger.info(f"Optimization completed in {total_time:.2f}s. Size reduced by {results['optimization_summary']['total_reduction_percent']:.1f}%")
        
        return results


# Utility functions
def optimize_supplementary_package(state: SupplementaryMaterialState,
                                 goals: List[str] = None,
                                 max_size_mb: float = 50.0) -> Dict[str, Any]:
    """Convenience function for package optimization."""
    optimizer = SupplementaryOptimizer(max_size_mb)
    return optimizer.optimize_package(state, goals)


def get_size_recommendations(state: SupplementaryMaterialState,
                           target_size_mb: float = 50.0) -> List[str]:
    """Get size reduction recommendations."""
    optimizer = PackageSizeOptimizer(target_size_mb)
    result = optimizer.optimize_package_size(state)
    return result.recommendations


def get_format_recommendations(state: SupplementaryMaterialState) -> Dict[str, Any]:
    """Get format optimization recommendations."""
    recommender = FormatRecommendationEngine()
    return recommender.recommend_formats(state)


def create_optimized_package(state: SupplementaryMaterialState,
                           output_path: str = None) -> OptimizationResult:
    """Create optimized package with compression."""
    engine = CompressionEngine()
    return engine.create_compressed_package(state, output_path)


# Performance monitoring
import time

def performance_monitor_decorator(operation_name: str):
    """Decorator for monitoring optimization performance."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                end_time = time.time()
                
                # Log performance
                duration = end_time - start_time
                logger.info(f"{operation_name} completed in {duration:.3f}s")
                
                return result
            except Exception as e:
                end_time = time.time()
                logger.error(f"{operation_name} failed after {end_time - start_time:.3f}s: {e}")
                raise
        return wrapper
    return decorator


if __name__ == "__main__":
    # Example usage
    from .supplementary_types import SupplementaryMaterialState, JournalFormat
    
    # Create example state
    state = SupplementaryMaterialState(
        study_id="example_001",
        manuscript_id="ms_001",
        project_id="proj_001",
        journal_format=JournalFormat.PLOS_ONE,
        package_size_mb=75.0  # Oversized package
    )
    
    # Add some example content
    state.add_supplementary_table(
        title="Patient Demographics",
        content="<table><tr><th>Variable</th><th>Value</th></tr><tr><td>Age</td><td>65.5 ± 12.3</td></tr></table>",
        caption="Baseline characteristics of study participants"
    )
    
    # Run optimization
    optimizer = SupplementaryOptimizer(max_package_size_mb=50.0)
    results = optimizer.optimize_package(state)
    
    print(f"Optimization Results:")
    print(f"Original size: {results['optimization_summary']['original_size_mb']:.2f} MB")
    print(f"Final size: {results['optimization_summary']['final_size_mb']:.2f} MB")
    print(f"Reduction: {results['optimization_summary']['total_reduction_percent']:.1f}%")
    print(f"Recommendations: {len(results['recommendations'])}")
