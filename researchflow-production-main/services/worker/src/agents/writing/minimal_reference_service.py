"""
Minimal Reference Management Service for Testing
"""

import asyncio
from typing import List, Dict, Any
from datetime import datetime
from .reference_types import ReferenceState, ReferenceResult, Reference, Citation

class MinimalReferenceService:
    """Minimal reference management service."""
    
    def __init__(self):
        self.stats = {
            'references_processed': 0,
            'citations_formatted': 0,
            'service_started': datetime.utcnow().isoformat()
        }
    
    async def process_references(self, state: ReferenceState) -> ReferenceResult:
        """Process references with basic functionality."""
        self.stats['references_processed'] += len(state.existing_references)
        self.stats['citations_formatted'] += len(state.existing_references)
        
        # Create basic citations
        citations = []
        for i, ref in enumerate(state.existing_references):
            citation = Citation(
                reference_id=ref.id,
                formatted_text=self._format_citation(ref, state.target_style),
                style=state.target_style,
                in_text_markers=[f"[{i+1}]"]
            )
            citations.append(citation)
        
        # Create bibliography
        bibliography = self._create_bibliography(state.existing_references, state.target_style)
        
        return ReferenceResult(
            study_id=state.study_id,
            references=state.existing_references,
            citations=citations,
            bibliography=bibliography,
            total_references=len(state.existing_references),
            processing_time_seconds=0.5
        )
    
    def _format_citation(self, ref: Reference, style) -> str:
        """Format a single citation."""
        authors = ", ".join(ref.authors[:3]) if ref.authors else "Unknown"
        if len(ref.authors) > 3:
            authors += " et al"
        
        year = f" ({ref.year})" if ref.year else ""
        journal = f" {ref.journal}." if ref.journal else ""
        
        return f"{authors}{year}. {ref.title}.{journal}"
    
    def _create_bibliography(self, references: List[Reference], style) -> str:
        """Create formatted bibliography."""
        lines = []
        for i, ref in enumerate(references, 1):
            formatted = self._format_citation(ref, style)
            lines.append(f"{i}. {formatted}")
        
        return "\n".join(lines)
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get service statistics."""
        return self.stats

# Global instance
_minimal_service = None

async def get_reference_service() -> MinimalReferenceService:
    """Get minimal reference service instance."""
    global _minimal_service
    if _minimal_service is None:
        _minimal_service = MinimalReferenceService()
    return _minimal_service