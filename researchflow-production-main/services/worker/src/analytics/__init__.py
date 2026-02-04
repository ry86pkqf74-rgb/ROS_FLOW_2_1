"""
Analytics Module

This module provides comprehensive analytics capabilities for the research platform:
- Citation network analysis
- Performance monitoring and optimization
- Research trend analysis
- Publication impact metrics
- Cross-reference validation
- Quality assessment algorithms

Exports:
- CitationNetworkAnalyzer: Complete citation analysis system
- EnhancedMonitor: Advanced system monitoring
- PerformanceOptimizer: Automated performance optimization
- QualityMetrics: Research quality assessment
"""

# Core analytics components
from ..analysis.citation_network_analyzer import (
    CitationNetworkAnalyzer,
    CitationNode,
    CitationEdge,
    NetworkAnalysisResult,
    get_citation_analyzer
)

# Monitoring imports with error handling
try:
    from ..monitoring.enhanced_monitoring import (
        EnhancedMonitor,
        OptimizationRecommendation,
        ResourceUsage,
        get_enhanced_monitor
    )
    from ..monitoring.performance_dashboard import (
        PerformanceMonitor,
        PerformanceMetric,
        SystemHealth,
        get_performance_monitor
    )
except ImportError as e:
    import logging
    logging.warning(f"Monitoring modules not available: {e}")
    # Provide dummy classes for compatibility
    class EnhancedMonitor: pass
    class OptimizationRecommendation: pass
    class ResourceUsage: pass
    class PerformanceMonitor: pass
    class PerformanceMetric: pass
    class SystemHealth: pass
    def get_enhanced_monitor(): return EnhancedMonitor()
    def get_performance_monitor(): return PerformanceMonitor()

__all__ = [
    # Citation analysis
    'CitationNetworkAnalyzer',
    'CitationNode', 
    'CitationEdge',
    'NetworkAnalysisResult',
    'get_citation_analyzer',
    
    # Enhanced monitoring
    'EnhancedMonitor',
    'OptimizationRecommendation',
    'ResourceUsage',
    'get_enhanced_monitor',
    
    # Performance monitoring
    'PerformanceMonitor',
    'PerformanceMetric',
    'SystemHealth',
    'get_performance_monitor',
]

# Version info
__version__ = '2.0.0'
__author__ = 'ResearchFlow Analytics Team'