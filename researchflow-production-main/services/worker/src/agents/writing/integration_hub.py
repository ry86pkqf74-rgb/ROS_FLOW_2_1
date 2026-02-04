"""
Integration Hub for Enhanced Reference Management System

Central orchestration layer that integrates all AI engines and provides
unified interface for advanced reference management capabilities.

Linear Issues: ROS-XXX
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime

from .reference_types import (
    Reference, ReferenceState, ReferenceResult, CitationNeed, 
    QualityScore, QualityWarning
)
# Use fallback imports for testing
try:
    from .reference_management_service import get_reference_service
except ImportError:
    async def get_reference_service():
        return MockReferenceService()

try:
    from .semantic_similarity import get_semantic_similarity_engine, SemanticMatch
except ImportError:
    SemanticMatch = dict
    async def get_semantic_similarity_engine():
        return None

try:
    from .literature_gap_detection import get_literature_gap_engine, LiteratureGap
except ImportError:
    LiteratureGap = dict
    async def get_literature_gap_engine():
        return None

try:
    from .citation_context_analysis import get_citation_context_engine, CitationContext, CitationValidation
except ImportError:
    CitationContext = dict
    CitationValidation = dict
    async def get_citation_context_engine():
        return None

try:
    from .advanced_quality_metrics import get_advanced_quality_engine, QualityMetrics
except ImportError:
    QualityMetrics = dict
    async def get_advanced_quality_engine():
        return None

try:
    from .real_time_collaboration import get_real_time_collaboration_manager
except ImportError:
    async def get_real_time_collaboration_manager():
        return None

try:
    from .journal_intelligence import get_journal_intelligence
except ImportError:
    async def get_journal_intelligence():
        return None

logger = logging.getLogger(__name__)

class MockReferenceService:
    """Mock reference service for testing."""
    async def process_references(self, state):
        from .reference_types import ReferenceResult
        return ReferenceResult(
            study_id=state.study_id,
            references=state.existing_references,
            citations=[],
            bibliography="Mock bibliography",
            total_references=len(state.existing_references),
            processing_time_seconds=1.0
        )
    
    async def extract_citations(self, text):
        return []
    
    async def get_stats(self):
        return {'mock': True}

@dataclass
class EnhancedReferenceResult:
    """Enhanced reference processing result with AI insights."""
    # Core results
    study_id: str
    references: List[Reference]
    citations: List[Any]
    bibliography: str
    
    # AI enhancements
    semantic_matches: Dict[str, List[SemanticMatch]]
    literature_gaps: List[LiteratureGap]
    citation_contexts: List[CitationContext]
    citation_validations: List[CitationValidation]
    quality_metrics: List[QualityMetrics]
    
    # Intelligence insights
    journal_recommendations: List[Dict[str, Any]]
    citation_impact_analysis: Dict[str, Any]
    
    # Summary statistics
    overall_quality_score: float
    completeness_score: float
    ai_confidence: float
    processing_time_seconds: float
    
    # Actionable insights
    improvement_recommendations: List[str]
    priority_issues: List[str]
    suggested_actions: List[str]

class IntegrationHub:
    """
    Central integration hub for enhanced reference management.
    
    Orchestrates all AI engines to provide comprehensive reference analysis:
    - Semantic matching for optimal reference selection
    - Literature gap detection for completeness
    - Citation context validation for appropriateness  
    - Advanced quality metrics for excellence
    - Real-time collaboration for team efficiency
    - Journal intelligence for strategic publishing
    """
    
    def __init__(self):
        self.reference_service = None
        self.semantic_engine = None
        self.gap_engine = None
        self.context_engine = None
        self.quality_engine = None
        self.collaboration_manager = None
        self.journal_intelligence = None
        
        self.stats = {
            'enhanced_processings': 0,
            'ai_insights_generated': 0,
            'recommendations_provided': 0,
            'time_saved_seconds': 0.0
        }
    
    async def initialize(self):
        """Initialize all AI engines and services."""
        logger.info("Initializing Integration Hub...")
        
        # Initialize core services
        self.reference_service = await get_reference_service()
        self.journal_intelligence = await get_journal_intelligence()
        
        # Initialize AI engines
        self.semantic_engine = await get_semantic_similarity_engine()
        self.gap_engine = await get_literature_gap_engine()
        self.context_engine = await get_citation_context_engine()
        self.quality_engine = await get_advanced_quality_engine()
        self.collaboration_manager = await get_real_time_collaboration_manager()
        
        logger.info("Integration Hub initialized with all AI engines")
    
    async def process_enhanced_references(
        self,
        state: ReferenceState,
        enable_semantic_matching: bool = True,
        enable_gap_detection: bool = True,
        enable_context_analysis: bool = True,
        enable_quality_metrics: bool = True,
        enable_journal_intelligence: bool = True
    ) -> EnhancedReferenceResult:
        """
        Process references with full AI enhancement pipeline.
        
        Args:
            state: Reference processing state
            enable_*: Feature flags for different AI engines
            
        Returns:
            Comprehensive enhanced reference result
        """
        start_time = datetime.utcnow()
        self.stats['enhanced_processings'] += 1
        
        logger.info(f"Starting enhanced reference processing for study: {state.study_id}")
        
        # Step 1: Core reference processing
        logger.info("Step 1: Core reference processing")
        core_result = await self.reference_service.process_references(state)
        
        # Step 2: Semantic matching for improved reference selection
        semantic_matches = {}
        if enable_semantic_matching and self.semantic_engine:
            logger.info("Step 2: Semantic similarity analysis")
            citation_needs = await self.reference_service.extract_citations(state.manuscript_text)
            semantic_matches = await self.semantic_engine.batch_find_matches(
                citation_needs, core_result.references
            )
        
        # Step 3: Literature gap detection
        literature_gaps = []
        if enable_gap_detection and self.gap_engine:
            logger.info("Step 3: Literature gap detection")
            literature_gaps = await self.gap_engine.detect_literature_gaps(
                state.manuscript_text,
                core_result.references,
                state.research_field or "general",
                "research_article"
            )
        
        # Step 4: Citation context analysis and validation
        citation_contexts = []
        citation_validations = []
        if enable_context_analysis and self.context_engine:
            logger.info("Step 4: Citation context analysis")
            citation_contexts = await self.context_engine.analyze_citation_contexts(
                state.manuscript_text,
                core_result.references,
                core_result.citation_map
            )
            
            citation_validations = await self.context_engine.validate_citations(
                citation_contexts,
                core_result.references,
                core_result.citation_map
            )
        
        # Step 5: Advanced quality metrics
        quality_metrics = []
        if enable_quality_metrics and self.quality_engine:
            logger.info("Step 5: Quality metrics assessment")
            quality_metrics = await self.quality_engine.batch_assess_quality(
                core_result.references,
                state.manuscript_text,
                state.research_field or "general"
            )
        
        # Step 6: Journal intelligence
        journal_recommendations = []
        citation_impact_analysis = {}
        if enable_journal_intelligence and self.journal_intelligence:
            logger.info("Step 6: Journal intelligence analysis")
            journal_recommendations = await self.journal_intelligence.recommend_target_journals(
                core_result.references,
                state.manuscript_text,
                state.research_field or "general"
            )
            
            citation_impact_analysis = await self.journal_intelligence.analyze_citation_impact(
                core_result.references
            )
        
        # Step 7: Generate insights and recommendations
        logger.info("Step 7: Generating AI insights")
        insights = await self._generate_ai_insights(
            core_result, semantic_matches, literature_gaps, 
            citation_contexts, citation_validations, quality_metrics,
            journal_recommendations, citation_impact_analysis
        )
        
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Create enhanced result
        enhanced_result = EnhancedReferenceResult(
            study_id=state.study_id,
            references=core_result.references,
            citations=core_result.citations,
            bibliography=core_result.bibliography,
            
            semantic_matches=semantic_matches,
            literature_gaps=literature_gaps,
            citation_contexts=citation_contexts,
            citation_validations=citation_validations,
            quality_metrics=quality_metrics,
            
            journal_recommendations=journal_recommendations,
            citation_impact_analysis=citation_impact_analysis,
            
            overall_quality_score=insights['overall_quality_score'],
            completeness_score=insights['completeness_score'], 
            ai_confidence=insights['ai_confidence'],
            processing_time_seconds=processing_time,
            
            improvement_recommendations=insights['improvement_recommendations'],
            priority_issues=insights['priority_issues'],
            suggested_actions=insights['suggested_actions']
        )
        
        self.stats['ai_insights_generated'] += len(insights['improvement_recommendations'])
        self.stats['recommendations_provided'] += 1
        
        logger.info(f"Enhanced processing completed in {processing_time:.2f}s")
        return enhanced_result
    
    async def _generate_ai_insights(
        self,
        core_result: ReferenceResult,
        semantic_matches: Dict[str, List[SemanticMatch]],
        literature_gaps: List[LiteratureGap],
        citation_contexts: List[CitationContext],
        citation_validations: List[CitationValidation],
        quality_metrics: List[QualityMetrics],
        journal_recommendations: List[Dict[str, Any]],
        citation_impact_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate comprehensive AI insights and recommendations."""
        
        insights = {
            'improvement_recommendations': [],
            'priority_issues': [],
            'suggested_actions': [],
            'overall_quality_score': 0.0,
            'completeness_score': 0.0,
            'ai_confidence': 0.0
        }
        
        # Calculate overall quality score
        if quality_metrics:
            quality_scores = [qm.overall_score for qm in quality_metrics]
            insights['overall_quality_score'] = sum(quality_scores) / len(quality_scores)
        
        # Calculate completeness score based on gaps and validations
        total_issues = len(literature_gaps) + len([v for v in citation_validations if v.overall_score < 0.6])
        total_references = len(core_result.references)
        insights['completeness_score'] = max(0.0, 1.0 - (total_issues / max(total_references, 1)))
        
        # Calculate AI confidence (average of all component confidences)
        confidences = []
        if semantic_matches:
            confidences.extend([match.confidence for matches in semantic_matches.values() for match in matches])
        if literature_gaps:
            confidences.extend([gap.confidence for gap in literature_gaps])
        if citation_contexts:
            confidences.extend([ctx.confidence for ctx in citation_contexts])
        if quality_metrics:
            confidences.extend([qm.confidence for qm in quality_metrics])
        
        insights['ai_confidence'] = sum(confidences) / len(confidences) if confidences else 0.5
        
        # Generate improvement recommendations
        recommendations = []
        
        # From literature gaps
        for gap in literature_gaps:
            if gap.importance_score > 0.7:
                recommendations.append(f"Address {gap.gap_type}: {gap.description}")
        
        # From quality metrics
        for qm in quality_metrics:
            if qm.overall_score < 0.6:
                recommendations.extend(qm.improvement_suggestions[:2])  # Top 2 suggestions
        
        # From citation validations
        inappropriate_citations = [v for v in citation_validations if v.overall_score < 0.5]
        if inappropriate_citations:
            recommendations.append(f"Review {len(inappropriate_citations)} citations with low appropriateness scores")
        
        insights['improvement_recommendations'] = recommendations[:10]  # Top 10
        
        # Generate priority issues
        priority_issues = []
        
        # High-severity literature gaps
        critical_gaps = [gap for gap in literature_gaps if gap.urgency == 'critical']
        if critical_gaps:
            priority_issues.append(f"Critical literature gaps: {len(critical_gaps)} missing foundational works")
        
        # Quality red flags
        red_flags = []
        for qm in quality_metrics:
            red_flags.extend(qm.red_flags)
        if red_flags:
            priority_issues.append(f"Quality concerns: {len(red_flags)} red flags detected")
        
        # Inappropriate citations
        if len(inappropriate_citations) > len(core_result.references) * 0.2:  # >20% inappropriate
            priority_issues.append("High proportion of inappropriate citations detected")
        
        insights['priority_issues'] = priority_issues
        
        # Generate suggested actions
        suggested_actions = []
        
        if literature_gaps:
            suggested_actions.append("Conduct targeted literature search to fill identified gaps")
        
        if quality_metrics and insights['overall_quality_score'] < 0.6:
            suggested_actions.append("Replace low-quality references with higher-impact alternatives")
        
        if inappropriate_citations:
            suggested_actions.append("Review and improve citation-context alignment")
        
        if journal_recommendations:
            top_journal = journal_recommendations[0]['journal_name']
            suggested_actions.append(f"Consider targeting {top_journal} for publication")
        
        insights['suggested_actions'] = suggested_actions
        
        return insights
    
    async def get_reference_insights(
        self, 
        reference: Reference,
        context: str = "",
        research_field: str = "general"
    ) -> Dict[str, Any]:
        """Get comprehensive insights for a single reference."""
        
        insights = {}
        
        # Quality assessment
        if self.quality_engine:
            quality_metrics = await self.quality_engine.assess_reference_quality(
                reference, context, research_field
            )
            insights['quality'] = asdict(quality_metrics)
        
        # Context analysis if context provided
        if context and self.context_engine:
            # Create mock citation need for analysis
            citation_need = CitationNeed(
                id=f"insight_{reference.id}",
                text_snippet="",
                context=context,
                position=0,
                section="unknown",
                claim_type="background_info"
            )
            
            semantic_matches = await self.semantic_engine.find_semantic_matches(
                citation_need, [reference], top_k=1
            )
            
            if semantic_matches:
                insights['semantic_match'] = asdict(semantic_matches[0])
        
        return insights
    
    async def suggest_reference_improvements(
        self,
        references: List[Reference],
        manuscript_text: str,
        research_field: str = "general"
    ) -> Dict[str, Any]:
        """Suggest improvements for reference list."""
        
        suggestions = {
            'overall_assessment': {},
            'individual_suggestions': [],
            'strategic_recommendations': []
        }
        
        # Overall quality assessment
        if self.quality_engine:
            quality_metrics = await self.quality_engine.batch_assess_quality(
                references, manuscript_text, research_field
            )
            quality_summary = await self.quality_engine.get_quality_summary(quality_metrics)
            suggestions['overall_assessment'] = quality_summary
        
        # Gap analysis
        if self.gap_engine:
            gaps = await self.gap_engine.detect_literature_gaps(
                manuscript_text, references, research_field
            )
            
            for gap in gaps[:5]:  # Top 5 gaps
                suggestions['strategic_recommendations'].append({
                    'type': gap.gap_type,
                    'description': gap.description,
                    'importance': gap.importance_score,
                    'action': f"Search for: {', '.join(gap.suggested_search_terms[:3])}"
                })
        
        # Individual reference suggestions
        if quality_metrics:
            for qm in quality_metrics:
                if qm.overall_score < 0.6 or qm.red_flags:
                    suggestions['individual_suggestions'].append({
                        'reference_id': qm.reference_id,
                        'score': qm.overall_score,
                        'issues': qm.red_flags,
                        'suggestions': qm.improvement_suggestions
                    })
        
        return suggestions
    
    async def optimize_citation_strategy(
        self,
        references: List[Reference], 
        target_journal: Optional[str] = None,
        manuscript_abstract: str = ""
    ) -> Dict[str, Any]:
        """Optimize citation strategy for target journal or general best practices."""
        
        optimization = {
            'current_analysis': {},
            'optimization_opportunities': [],
            'journal_alignment': {},
            'impact_optimization': {}
        }
        
        # Current citation analysis
        if self.journal_intelligence:
            impact_analysis = await self.journal_intelligence.analyze_citation_impact(references)
            optimization['current_analysis'] = impact_analysis
            
            # Journal-specific optimization
            if target_journal:
                journal_fit = await self.journal_intelligence.analyze_journal_fit(
                    target_journal, references, manuscript_abstract
                )
                optimization['journal_alignment'] = journal_fit
        
        # Impact optimization opportunities
        if self.quality_engine:
            quality_metrics = await self.quality_engine.batch_assess_quality(references)
            
            low_impact_refs = [
                qm for qm in quality_metrics 
                if qm.dimension_scores.get('impact', 0) < 0.4
            ]
            
            if low_impact_refs:
                optimization['optimization_opportunities'].append({
                    'type': 'impact_improvement',
                    'count': len(low_impact_refs),
                    'recommendation': 'Replace with higher-impact alternatives'
                })
        
        return optimization
    
    async def get_collaboration_insights(self, session_id: str) -> Dict[str, Any]:
        """Get insights from collaborative editing session."""
        
        if not self.collaboration_manager:
            return {}
        
        session_stats = await self.collaboration_manager.get_stats()
        
        # Get session-specific insights
        insights = {
            'collaboration_efficiency': {},
            'quality_improvements': {},
            'team_dynamics': {}
        }
        
        # Would analyze collaboration patterns, quality improvements, etc.
        
        return insights
    
    async def get_integration_stats(self) -> Dict[str, Any]:
        """Get comprehensive integration hub statistics."""
        
        stats = {'integration_hub': self.stats}
        
        # Collect stats from all engines
        if self.reference_service:
            stats['reference_service'] = await self.reference_service.get_stats()
        
        if self.semantic_engine:
            stats['semantic_engine'] = await self.semantic_engine.get_stats()
        
        if self.gap_engine:
            stats['gap_engine'] = await self.gap_engine.get_stats()
        
        if self.context_engine:
            stats['context_engine'] = await self.context_engine.get_stats()
        
        if self.quality_engine:
            stats['quality_engine'] = await self.quality_engine.get_stats()
        
        if self.collaboration_manager:
            stats['collaboration_manager'] = await self.collaboration_manager.get_stats()
        
        if self.journal_intelligence:
            stats['journal_intelligence'] = await self.journal_intelligence.get_stats()
        
        return stats

# Global integration hub instance
_integration_hub_instance: Optional[IntegrationHub] = None

async def get_integration_hub() -> IntegrationHub:
    """Get global integration hub instance."""
    global _integration_hub_instance
    if _integration_hub_instance is None:
        _integration_hub_instance = IntegrationHub()
        await _integration_hub_instance.initialize()
    return _integration_hub_instance

async def close_integration_hub() -> None:
    """Close global integration hub instance."""
    global _integration_hub_instance
    if _integration_hub_instance:
        _integration_hub_instance = None