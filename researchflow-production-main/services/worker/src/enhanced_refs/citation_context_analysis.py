"""
Citation Context Analysis Engine

Advanced analysis of citation contexts to understand WHY citations are needed,
validate appropriateness of references, and suggest improvements.

Linear Issues: ROS-XXX
"""

import asyncio
import logging
import re
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import hashlib

from .reference_types import Reference, CitationNeed
from .semantic_similarity import get_semantic_similarity_engine
from .reference_cache import get_cache

logger = logging.getLogger(__name__)

class CitationPurpose(Enum):
    """Different purposes for citations."""
    BACKGROUND_INFO = "background_information"
    EVIDENCE_SUPPORT = "evidence_support"  
    METHODOLOGY_REFERENCE = "methodology_reference"
    COMPARATIVE_ANALYSIS = "comparative_analysis"
    THEORETICAL_FOUNDATION = "theoretical_foundation"
    STATISTICAL_SUPPORT = "statistical_support"
    DEFINITION = "definition"
    CRITICISM = "criticism"
    ACKNOWLEDGMENT = "acknowledgment"
    FUTURE_WORK = "future_work"

class CitationAppropriatenessLevel(Enum):
    """Levels of citation appropriateness."""
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    QUESTIONABLE = "questionable"
    INAPPROPRIATE = "inappropriate"

@dataclass
class CitationContext:
    """Analysis of citation context."""
    citation_id: str
    text_before: str
    text_after: str
    sentence: str
    paragraph: str
    section: str
    purpose: CitationPurpose
    claim_strength: str  # weak, moderate, strong, absolute
    evidence_type: str  # empirical, theoretical, anecdotal, expert_opinion
    temporal_relevance: str  # current, recent, historical, timeless
    confidence: float

@dataclass
class CitationValidation:
    """Validation result for a citation."""
    citation_id: str
    reference_id: str
    appropriateness: CitationAppropriatenessLevel
    purpose_match_score: float
    content_relevance_score: float
    temporal_appropriateness: float
    overall_score: float
    issues: List[str]
    suggestions: List[str]
    explanation: str

@dataclass
class ContextualMismatch:
    """Represents a mismatch between citation context and reference."""
    citation_id: str
    reference_id: str
    mismatch_type: str
    severity: str  # low, medium, high, critical
    description: str
    suggested_alternatives: List[str]
    fix_suggestions: List[str]

class CitationContextAnalysisEngine:
    """
    Advanced citation context analysis system.
    
    Analyzes:
    - Citation purpose and intent
    - Appropriateness of references for context
    - Temporal relevance of citations
    - Claim strength vs evidence strength
    - Context-reference semantic alignment
    - Citation density and distribution patterns
    """
    
    # Linguistic patterns for different citation purposes
    PURPOSE_PATTERNS = {
        CitationPurpose.BACKGROUND_INFO: [
            r'as shown by', r'according to', r'as described', r'as reported',
            r'previous studies?', r'earlier research', r'literature shows?'
        ],
        CitationPurpose.EVIDENCE_SUPPORT: [
            r'evidence suggests?', r'studies? demonstrate', r'research shows?',
            r'findings indicate', r'data reveals?', r'proven', r'established'
        ],
        CitationPurpose.METHODOLOGY_REFERENCE: [
            r'using the method', r'following the protocol', r'as described by',
            r'methodology adapted from', r'procedure outlined', r'technique developed'
        ],
        CitationPurpose.COMPARATIVE_ANALYSIS: [
            r'compared to', r'in contrast to', r'unlike', r'similar to',
            r'better than', r'worse than', r'outperforms', r'versus'
        ],
        CitationPurpose.THEORETICAL_FOUNDATION: [
            r'based on the theory', r'theoretical framework', r'model proposed',
            r'conceptual framework', r'grounded in', r'theory suggests?'
        ],
        CitationPurpose.STATISTICAL_SUPPORT: [
            r'statistically significant', r'p\s*[<>=]', r'\d+%', r'odds ratio',
            r'confidence interval', r'correlation', r'regression analysis'
        ],
        CitationPurpose.DEFINITION: [
            r'defined as', r'definition of', r'refers to', r'characterized by',
            r'described as', r'understood as'
        ]
    }
    
    # Claim strength indicators
    CLAIM_STRENGTH_PATTERNS = {
        'absolute': [r'always', r'never', r'all', r'none', r'every', r'completely'],
        'strong': [r'significant', r'substantial', r'major', r'considerable', r'marked'],
        'moderate': [r'may', r'might', r'could', r'appears?', r'seems?', r'suggests?'],
        'weak': [r'possibly', r'perhaps', r'potentially', r'preliminarily', r'tentatively']
    }
    
    def __init__(self):
        self.cache = None
        self.semantic_engine = None
        self.stats = {
            'contexts_analyzed': 0,
            'validations_performed': 0,
            'mismatches_detected': 0,
            'purpose_classifications': 0
        }
    
    async def initialize(self):
        """Initialize the citation context analysis engine."""
        self.cache = await get_cache()
        self.semantic_engine = await get_semantic_similarity_engine()
        logger.info("Citation context analysis engine initialized")
    
    async def analyze_citation_contexts(
        self,
        manuscript_text: str,
        references: List[Reference],
        citation_map: Dict[str, str]
    ) -> List[CitationContext]:
        """
        Analyze contexts of all citations in manuscript.
        
        Args:
            manuscript_text: Full manuscript text
            references: List of references
            citation_map: Mapping from citation markers to reference IDs
            
        Returns:
            List of citation context analyses
        """
        contexts = []
        
        # Find all citation markers and their positions
        citation_positions = self._find_citation_positions(manuscript_text)
        
        for position_info in citation_positions:
            try:
                context = await self._analyze_single_citation_context(
                    manuscript_text, position_info, references, citation_map
                )
                contexts.append(context)
                self.stats['contexts_analyzed'] += 1
            except Exception as e:
                logger.warning(f"Failed to analyze citation context: {e}")
        
        return contexts
    
    async def validate_citations(
        self,
        contexts: List[CitationContext],
        references: List[Reference],
        citation_map: Dict[str, str]
    ) -> List[CitationValidation]:
        """
        Validate appropriateness of citations based on context analysis.
        
        Args:
            contexts: Citation context analyses
            references: List of references
            citation_map: Citation to reference mapping
            
        Returns:
            List of validation results
        """
        validations = []
        ref_lookup = {ref.id: ref for ref in references}
        
        for context in contexts:
            try:
                # Find corresponding reference
                ref_id = citation_map.get(context.citation_id)
                if not ref_id or ref_id not in ref_lookup:
                    continue
                
                reference = ref_lookup[ref_id]
                validation = await self._validate_citation_appropriateness(context, reference)
                validations.append(validation)
                self.stats['validations_performed'] += 1
                
            except Exception as e:
                logger.warning(f"Failed to validate citation {context.citation_id}: {e}")
        
        return validations
    
    async def detect_contextual_mismatches(
        self,
        validations: List[CitationValidation],
        contexts: List[CitationContext],
        references: List[Reference]
    ) -> List[ContextualMismatch]:
        """
        Detect mismatches between citation contexts and references.
        
        Args:
            validations: Citation validation results
            contexts: Citation contexts
            references: List of references
            
        Returns:
            List of detected mismatches
        """
        mismatches = []
        
        for validation in validations:
            if validation.appropriateness in [CitationAppropriatenessLevel.QUESTIONABLE, CitationAppropriatenessLevel.INAPPROPRIATE]:
                mismatch = await self._create_mismatch_report(validation, contexts, references)
                if mismatch:
                    mismatches.append(mismatch)
                    self.stats['mismatches_detected'] += 1
        
        return mismatches
    
    def _find_citation_positions(self, text: str) -> List[Dict[str, Any]]:
        """Find all citation markers and their positions in text."""
        
        citation_patterns = [
            (r'\[(\d+(?:[-,\s]*\d+)*)\]', 'numbered_bracket'),
            (r'\((\d+(?:[-,\s]*\d+)*)\)', 'numbered_parenthesis'),
            (r'\[(\w+(?:\s+et\s+al\.?)?,?\s*\d{4}[a-z]?)\]', 'author_year_bracket'),
            (r'\((\w+(?:\s+et\s+al\.?)?,?\s*\d{4}[a-z]?)\)', 'author_year_parenthesis')
        ]
        
        positions = []
        
        for pattern, style in citation_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                position_info = {
                    'citation_marker': match.group(),
                    'citation_content': match.group(1),
                    'start_pos': match.start(),
                    'end_pos': match.end(),
                    'style': style
                }
                positions.append(position_info)
        
        # Sort by position
        positions.sort(key=lambda x: x['start_pos'])
        return positions
    
    async def _analyze_single_citation_context(
        self,
        text: str,
        position_info: Dict[str, Any],
        references: List[Reference],
        citation_map: Dict[str, str]
    ) -> CitationContext:
        """Analyze context of a single citation."""
        
        start_pos = position_info['start_pos']
        end_pos = position_info['end_pos']
        
        # Extract surrounding text
        context_window = 200
        text_before = text[max(0, start_pos - context_window):start_pos]
        text_after = text[end_pos:min(len(text), end_pos + context_window)]
        
        # Extract sentence containing citation
        sentence_start = text.rfind('.', 0, start_pos) + 1
        sentence_end = text.find('.', end_pos)
        if sentence_end == -1:
            sentence_end = len(text)
        sentence = text[sentence_start:sentence_end].strip()
        
        # Extract paragraph
        para_start = max(text.rfind('\n\n', 0, start_pos), 0)
        para_end = text.find('\n\n', end_pos)
        if para_end == -1:
            para_end = len(text)
        paragraph = text[para_start:para_end].strip()
        
        # Determine section
        section = self._identify_section(text, start_pos)
        
        # Classify citation purpose
        purpose = await self._classify_citation_purpose(sentence, text_before, text_after)
        
        # Analyze claim strength
        claim_strength = self._analyze_claim_strength(sentence)
        
        # Determine evidence type needed
        evidence_type = self._classify_evidence_type(sentence, purpose)
        
        # Assess temporal relevance requirement
        temporal_relevance = self._assess_temporal_relevance(sentence, purpose, section)
        
        # Calculate confidence
        confidence = self._calculate_context_confidence(sentence, purpose, claim_strength)
        
        citation_id = f"citation_{hashlib.md5(position_info['citation_marker'].encode()).hexdigest()[:8]}"
        
        return CitationContext(
            citation_id=citation_id,
            text_before=text_before[-100:],  # Last 100 chars
            text_after=text_after[:100],     # First 100 chars
            sentence=sentence,
            paragraph=paragraph[:500],       # First 500 chars
            section=section,
            purpose=purpose,
            claim_strength=claim_strength,
            evidence_type=evidence_type,
            temporal_relevance=temporal_relevance,
            confidence=confidence
        )
    
    async def _classify_citation_purpose(self, sentence: str, text_before: str, text_after: str) -> CitationPurpose:
        """Classify the purpose of a citation based on context."""
        
        combined_text = f"{text_before[-50:]} {sentence} {text_after[:50]}".lower()
        
        # Score each purpose based on pattern matches
        purpose_scores = {}
        
        for purpose, patterns in self.PURPOSE_PATTERNS.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, combined_text, re.IGNORECASE))
                score += matches
            
            if score > 0:
                purpose_scores[purpose] = score
        
        # Return highest scoring purpose, or default to background
        if purpose_scores:
            best_purpose = max(purpose_scores.items(), key=lambda x: x[1])[0]
            return best_purpose
        
        return CitationPurpose.BACKGROUND_INFO
    
    def _analyze_claim_strength(self, sentence: str) -> str:
        """Analyze the strength of claims in the sentence."""
        
        sentence_lower = sentence.lower()
        
        for strength, patterns in self.CLAIM_STRENGTH_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, sentence_lower):
                    return strength
        
        return 'moderate'  # Default
    
    def _classify_evidence_type(self, sentence: str, purpose: CitationPurpose) -> str:
        """Classify what type of evidence is needed."""
        
        sentence_lower = sentence.lower()
        
        # Empirical evidence indicators
        if any(word in sentence_lower for word in ['study', 'data', 'experiment', 'trial', 'analysis']):
            return 'empirical'
        
        # Theoretical evidence indicators
        if any(word in sentence_lower for word in ['theory', 'model', 'framework', 'concept']):
            return 'theoretical'
        
        # Expert opinion indicators
        if any(word in sentence_lower for word in ['expert', 'authority', 'consensus', 'opinion']):
            return 'expert_opinion'
        
        # Purpose-based classification
        if purpose in [CitationPurpose.STATISTICAL_SUPPORT, CitationPurpose.EVIDENCE_SUPPORT]:
            return 'empirical'
        elif purpose == CitationPurpose.THEORETICAL_FOUNDATION:
            return 'theoretical'
        
        return 'general'
    
    def _assess_temporal_relevance(self, sentence: str, purpose: CitationPurpose, section: str) -> str:
        """Assess what temporal relevance is needed for the citation."""
        
        sentence_lower = sentence.lower()
        
        # Recent/current indicators
        if any(word in sentence_lower for word in ['recent', 'current', 'latest', 'modern', 'contemporary']):
            return 'current'
        
        # Historical indicators  
        if any(word in sentence_lower for word in ['historically', 'traditionally', 'originally', 'early']):
            return 'historical'
        
        # Purpose-based assessment
        if purpose == CitationPurpose.BACKGROUND_INFO and section == 'introduction':
            return 'recent'
        elif purpose == CitationPurpose.EVIDENCE_SUPPORT:
            return 'current'
        elif purpose == CitationPurpose.THEORETICAL_FOUNDATION:
            return 'timeless'
        
        return 'general'
    
    def _calculate_context_confidence(self, sentence: str, purpose: CitationPurpose, claim_strength: str) -> float:
        """Calculate confidence in context analysis."""
        
        confidence = 0.5  # Base confidence
        
        # Boost confidence for clear patterns
        sentence_lower = sentence.lower()
        patterns = self.PURPOSE_PATTERNS.get(purpose, [])
        
        pattern_matches = sum(1 for pattern in patterns if re.search(pattern, sentence_lower))
        confidence += min(pattern_matches * 0.15, 0.3)
        
        # Adjust for claim strength clarity
        strength_confidence = {
            'absolute': 0.9,
            'strong': 0.8,
            'moderate': 0.6,
            'weak': 0.7
        }
        confidence = 0.7 * confidence + 0.3 * strength_confidence.get(claim_strength, 0.5)
        
        return min(confidence, 1.0)
    
    def _identify_section(self, text: str, position: int) -> str:
        """Identify which section of the manuscript contains the citation."""
        
        text_before = text[:position].lower()
        
        section_markers = {
            'abstract': ['abstract'],
            'introduction': ['introduction', 'background'],
            'literature_review': ['literature review', 'related work'],
            'methods': ['methods', 'methodology', 'materials and methods'],
            'results': ['results', 'findings'],
            'discussion': ['discussion', 'interpretation'],
            'conclusion': ['conclusion', 'conclusions']
        }
        
        current_section = 'unknown'
        last_section_pos = -1
        
        for section, markers in section_markers.items():
            for marker in markers:
                marker_pos = text_before.rfind(marker)
                if marker_pos > last_section_pos:
                    current_section = section
                    last_section_pos = marker_pos
        
        return current_section
    
    async def _validate_citation_appropriateness(
        self,
        context: CitationContext,
        reference: Reference
    ) -> CitationValidation:
        """Validate appropriateness of a citation for its context."""
        
        # Purpose match score
        purpose_match = await self._calculate_purpose_match_score(context, reference)
        
        # Content relevance score
        content_relevance = await self._calculate_content_relevance_score(context, reference)
        
        # Temporal appropriateness
        temporal_appropriateness = self._calculate_temporal_appropriateness(context, reference)
        
        # Overall score
        overall_score = 0.4 * purpose_match + 0.4 * content_relevance + 0.2 * temporal_appropriateness
        
        # Determine appropriateness level
        if overall_score >= 0.8:
            appropriateness = CitationAppropriatenessLevel.EXCELLENT
        elif overall_score >= 0.7:
            appropriateness = CitationAppropriatenessLevel.GOOD
        elif overall_score >= 0.6:
            appropriateness = CitationAppropriatenessLevel.ACCEPTABLE
        elif overall_score >= 0.4:
            appropriateness = CitationAppropriatenessLevel.QUESTIONABLE
        else:
            appropriateness = CitationAppropriatenessLevel.INAPPROPRIATE
        
        # Identify issues
        issues = self._identify_validation_issues(context, reference, purpose_match, content_relevance, temporal_appropriateness)
        
        # Generate suggestions
        suggestions = self._generate_improvement_suggestions(context, reference, issues)
        
        # Generate explanation
        explanation = self._generate_validation_explanation(context, reference, overall_score, appropriateness)
        
        return CitationValidation(
            citation_id=context.citation_id,
            reference_id=reference.id,
            appropriateness=appropriateness,
            purpose_match_score=purpose_match,
            content_relevance_score=content_relevance,
            temporal_appropriateness=temporal_appropriateness,
            overall_score=overall_score,
            issues=issues,
            suggestions=suggestions,
            explanation=explanation
        )
    
    async def _calculate_purpose_match_score(self, context: CitationContext, reference: Reference) -> float:
        """Calculate how well the reference matches the citation purpose."""
        
        ref_text = f"{reference.title} {reference.abstract or ''}".lower()
        
        # Purpose-specific scoring
        if context.purpose == CitationPurpose.METHODOLOGY_REFERENCE:
            method_indicators = ['method', 'procedure', 'technique', 'protocol', 'approach']
            score = sum(1 for indicator in method_indicators if indicator in ref_text)
            return min(score / len(method_indicators), 1.0)
        
        elif context.purpose == CitationPurpose.STATISTICAL_SUPPORT:
            stats_indicators = ['statistical', 'analysis', 'significance', 'test', 'model']
            score = sum(1 for indicator in stats_indicators if indicator in ref_text)
            return min(score / len(stats_indicators), 1.0)
        
        elif context.purpose == CitationPurpose.EVIDENCE_SUPPORT:
            evidence_indicators = ['study', 'research', 'findings', 'results', 'evidence']
            score = sum(1 for indicator in evidence_indicators if indicator in ref_text)
            return min(score / len(evidence_indicators), 1.0)
        
        elif context.purpose == CitationPurpose.THEORETICAL_FOUNDATION:
            theory_indicators = ['theory', 'theoretical', 'framework', 'model', 'concept']
            score = sum(1 for indicator in theory_indicators if indicator in ref_text)
            return min(score / len(theory_indicators), 1.0)
        
        # Default scoring for other purposes
        return 0.6
    
    async def _calculate_content_relevance_score(self, context: CitationContext, reference: Reference) -> float:
        """Calculate content relevance using semantic similarity."""
        
        if self.semantic_engine:
            try:
                # Create a mock citation need for semantic matching
                citation_need = CitationNeed(
                    id=context.citation_id,
                    text_snippet=context.sentence,
                    context=context.paragraph,
                    position=0,
                    section=context.section,
                    claim_type=context.purpose.value
                )
                
                matches = await self.semantic_engine.find_semantic_matches(
                    citation_need, [reference], top_k=1, min_similarity=0.0
                )
                
                if matches:
                    return matches[0].similarity_score
                
            except Exception as e:
                logger.warning(f"Semantic similarity failed: {e}")
        
        # Fallback to keyword overlap
        context_words = set(context.sentence.lower().split())
        ref_words = set(f"{reference.title} {reference.abstract or ''}".lower().split())
        
        if context_words and ref_words:
            overlap = len(context_words.intersection(ref_words))
            return min(overlap / max(len(context_words), len(ref_words)), 1.0)
        
        return 0.3
    
    def _calculate_temporal_appropriateness(self, context: CitationContext, reference: Reference) -> float:
        """Calculate temporal appropriateness of the reference."""
        
        if not reference.year:
            return 0.5  # Unknown year gets neutral score
        
        current_year = datetime.now().year
        ref_age = current_year - reference.year
        
        # Age appropriateness based on temporal relevance requirement
        if context.temporal_relevance == 'current':
            if ref_age <= 3:
                return 1.0
            elif ref_age <= 5:
                return 0.8
            elif ref_age <= 10:
                return 0.6
            else:
                return 0.3
        
        elif context.temporal_relevance == 'recent':
            if ref_age <= 5:
                return 1.0
            elif ref_age <= 10:
                return 0.8
            elif ref_age <= 15:
                return 0.6
            else:
                return 0.4
        
        elif context.temporal_relevance == 'historical':
            if ref_age >= 10:
                return 1.0
            elif ref_age >= 5:
                return 0.8
            else:
                return 0.6
        
        elif context.temporal_relevance == 'timeless':
            # Theoretical works don't have strong temporal requirements
            return 0.9
        
        # Default scoring
        if ref_age <= 10:
            return 0.8
        elif ref_age <= 20:
            return 0.6
        else:
            return 0.4
    
    def _identify_validation_issues(
        self,
        context: CitationContext,
        reference: Reference,
        purpose_match: float,
        content_relevance: float,
        temporal_appropriateness: float
    ) -> List[str]:
        """Identify specific issues with the citation."""
        
        issues = []
        
        if purpose_match < 0.5:
            issues.append(f"Reference may not match the citation purpose ({context.purpose.value})")
        
        if content_relevance < 0.4:
            issues.append("Low content relevance between context and reference")
        
        if temporal_appropriateness < 0.4:
            ref_age = datetime.now().year - reference.year if reference.year else None
            if ref_age and ref_age > 15:
                issues.append(f"Reference is quite old ({ref_age} years) for this context")
            elif context.temporal_relevance == 'current':
                issues.append("Citation context requires recent literature")
        
        if context.claim_strength == 'absolute' and content_relevance < 0.7:
            issues.append("Strong claims require highly relevant supporting evidence")
        
        if context.evidence_type == 'empirical' and not any(
            keyword in (reference.title or '').lower() 
            for keyword in ['study', 'trial', 'experiment', 'data', 'analysis']
        ):
            issues.append("Context requires empirical evidence but reference appears non-empirical")
        
        return issues
    
    def _generate_improvement_suggestions(
        self,
        context: CitationContext,
        reference: Reference,
        issues: List[str]
    ) -> List[str]:
        """Generate suggestions for improving the citation."""
        
        suggestions = []
        
        if "purpose" in ' '.join(issues).lower():
            suggestions.append(f"Consider finding references specifically about {context.purpose.value.replace('_', ' ')}")
        
        if "relevance" in ' '.join(issues).lower():
            suggestions.append("Look for references with higher topical relevance to the citation context")
        
        if "old" in ' '.join(issues).lower():
            suggestions.append("Consider supplementing with more recent literature")
        
        if "empirical" in ' '.join(issues).lower():
            suggestions.append("Replace with empirical studies or experimental data")
        
        if context.claim_strength == 'absolute':
            suggestions.append("Strong claims may benefit from multiple supporting references")
        
        return suggestions
    
    def _generate_validation_explanation(
        self,
        context: CitationContext,
        reference: Reference,
        overall_score: float,
        appropriateness: CitationAppropriatenessLevel
    ) -> str:
        """Generate human-readable explanation of validation result."""
        
        explanations = []
        
        # Overall assessment
        if appropriateness == CitationAppropriatenessLevel.EXCELLENT:
            explanations.append("This citation is excellent for its context")
        elif appropriateness == CitationAppropriatenessLevel.GOOD:
            explanations.append("This citation is well-suited for its context")
        elif appropriateness == CitationAppropriatenessLevel.ACCEPTABLE:
            explanations.append("This citation is acceptable but could be improved")
        elif appropriateness == CitationAppropriatenessLevel.QUESTIONABLE:
            explanations.append("This citation may not be ideal for its context")
        else:
            explanations.append("This citation appears inappropriate for its context")
        
        # Context details
        explanations.append(f"Citation purpose: {context.purpose.value.replace('_', ' ')}")
        explanations.append(f"Claim strength: {context.claim_strength}")
        
        # Reference details
        if reference.year:
            age = datetime.now().year - reference.year
            explanations.append(f"Reference age: {age} years")
        
        return ". ".join(explanations)
    
    async def _create_mismatch_report(
        self,
        validation: CitationValidation,
        contexts: List[CitationContext],
        references: List[Reference]
    ) -> Optional[ContextualMismatch]:
        """Create a detailed mismatch report."""
        
        # Find the context
        context = next((c for c in contexts if c.citation_id == validation.citation_id), None)
        if not context:
            return None
        
        # Determine mismatch type and severity
        issues = validation.issues
        
        if validation.purpose_match_score < 0.3:
            mismatch_type = "purpose_mismatch"
            severity = "high"
        elif validation.content_relevance_score < 0.3:
            mismatch_type = "content_mismatch"
            severity = "high"
        elif validation.temporal_appropriateness < 0.3:
            mismatch_type = "temporal_mismatch"
            severity = "medium"
        else:
            mismatch_type = "general_mismatch"
            severity = "low"
        
        # Generate description
        description = f"Citation context expects {context.purpose.value.replace('_', ' ')} but reference may not be appropriate"
        
        return ContextualMismatch(
            citation_id=validation.citation_id,
            reference_id=validation.reference_id,
            mismatch_type=mismatch_type,
            severity=severity,
            description=description,
            suggested_alternatives=[],  # Would be populated with alternative references
            fix_suggestions=validation.suggestions
        )
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get citation context analysis statistics."""
        return self.stats

# Global citation context analysis engine instance
_context_analysis_instance: Optional[CitationContextAnalysisEngine] = None

async def get_citation_context_engine() -> CitationContextAnalysisEngine:
    """Get global citation context analysis engine instance."""
    global _context_analysis_instance
    if _context_analysis_instance is None:
        _context_analysis_instance = CitationContextAnalysisEngine()
        await _context_analysis_instance.initialize()
    return _context_analysis_instance

async def close_citation_context_engine() -> None:
    """Close global citation context analysis engine instance."""
    global _context_analysis_instance
    if _context_analysis_instance:
        _context_analysis_instance = None