"""
DOI Validation and Metadata Resolution

Validates DOIs, resolves metadata from CrossRef, and checks for retracted papers.

Linear Issues: ROS-XXX
"""

import re
import logging
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
import asyncio

from .types import DOIValidationResult, Reference
from .api_management import get_api_manager, APIRequest, APIProvider
from .reference_cache import get_cache

logger = logging.getLogger(__name__)


class DOIValidator:
    """DOI validation and metadata resolution service."""
    
    # Valid DOI pattern
    DOI_PATTERN = re.compile(r'^10\.\d{4,}/[^\s]+$')
    
    # Known retracted paper DOIs (would be updated from Retraction Watch)
    RETRACTED_DOIS: Set[str] = set()
    
    def __init__(self):
        """Initialize DOI validator."""
        self.api_manager = None
        self.cache = None
        self.stats = {
            'validations_performed': 0,
            'valid_dois': 0,
            'invalid_dois': 0,
            'resolved_metadata': 0,
            'cache_hits': 0,
            'api_errors': 0,
        }
    
    async def initialize(self) -> None:
        """Initialize dependencies."""
        self.api_manager = await get_api_manager()
        self.cache = await get_cache()
    
    def is_valid_doi_format(self, doi: str) -> bool:
        """
        Check if DOI has valid format.
        
        Args:
            doi: DOI string to validate
            
        Returns:
            True if DOI format is valid
        """
        if not doi:
            return False
        
        # Clean DOI
        clean_doi = self._clean_doi(doi)
        
        # Check pattern
        return bool(self.DOI_PATTERN.match(clean_doi))
    
    def _clean_doi(self, doi: str) -> str:
        """
        Clean and normalize DOI.
        
        Args:
            doi: Raw DOI string
            
        Returns:
            Cleaned DOI
        """
        if not doi:
            return ""
        
        # Remove common prefixes
        cleaned = doi.strip()
        for prefix in ['doi:', 'DOI:', 'https://doi.org/', 'http://doi.org/', 'https://dx.doi.org/', 'http://dx.doi.org/']:
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):]
                break
        
        return cleaned.strip()
    
    async def validate_doi(self, doi: str, fetch_metadata: bool = True) -> DOIValidationResult:
        """
        Validate a single DOI and optionally fetch metadata.
        
        Args:
            doi: DOI to validate
            fetch_metadata: Whether to fetch metadata from CrossRef
            
        Returns:
            DOI validation result
        """
        if not self.api_manager:
            await self.initialize()
        
        self.stats['validations_performed'] += 1
        
        # Check format first
        clean_doi = self._clean_doi(doi)
        if not self.is_valid_doi_format(clean_doi):
            self.stats['invalid_dois'] += 1
            return DOIValidationResult(
                doi=doi,
                is_valid=False,
                is_resolvable=False,
                error_message="Invalid DOI format"
            )
        
        # Check cache first
        if self.cache:
            cached_result = await self.cache.get('validation_results', clean_doi, 'doi_validation')
            if cached_result:
                self.stats['cache_hits'] += 1
                return cached_result
        
        # Validate by attempting to resolve
        metadata = None
        is_resolvable = False
        error_message = None
        
        if fetch_metadata:
            try:
                metadata = await self._fetch_doi_metadata(clean_doi)
                if metadata:
                    is_resolvable = True
                    self.stats['resolved_metadata'] += 1
                else:
                    error_message = "DOI not found in CrossRef database"
            except Exception as e:
                self.stats['api_errors'] += 1
                error_message = f"API error: {str(e)}"
        
        # Create result
        result = DOIValidationResult(
            doi=clean_doi,
            is_valid=True,  # Format is valid
            is_resolvable=is_resolvable,
            metadata=metadata,
            error_message=error_message
        )
        
        # Cache result
        if self.cache:
            await self.cache.set('validation_results', clean_doi, result)
        
        if is_resolvable:
            self.stats['valid_dois'] += 1
        else:
            self.stats['invalid_dois'] += 1
        
        return result
    
    async def validate_dois_batch(self, dois: List[str], fetch_metadata: bool = True) -> Dict[str, DOIValidationResult]:
        """
        Validate multiple DOIs in batch.
        
        Args:
            dois: List of DOIs to validate
            fetch_metadata: Whether to fetch metadata
            
        Returns:
            Dictionary mapping DOI to validation result
        """
        if not dois:
            return {}
        
        if not self.api_manager:
            await self.initialize()
        
        # Clean DOIs and check format
        cleaned_dois = []
        results = {}
        
        for doi in dois:
            clean_doi = self._clean_doi(doi)
            if not self.is_valid_doi_format(clean_doi):
                results[doi] = DOIValidationResult(
                    doi=doi,
                    is_valid=False,
                    is_resolvable=False,
                    error_message="Invalid DOI format"
                )
            else:
                cleaned_dois.append((doi, clean_doi))
        
        if not cleaned_dois:
            return results
        
        # Check cache for existing results
        cache_keys = [clean_doi for _, clean_doi in cleaned_dois]
        cached_results = {}
        if self.cache:
            cached_results = await self.cache.get_many('validation_results', cache_keys, 'doi_validation')
            self.stats['cache_hits'] += len(cached_results)
        
        # Identify DOIs that need validation
        dois_to_validate = [(original, clean) for original, clean in cleaned_dois if clean not in cached_results]
        
        # Add cached results
        for original, clean in cleaned_dois:
            if clean in cached_results:
                results[original] = cached_results[clean]
        
        if not dois_to_validate:
            return results
        
        # Batch fetch metadata for remaining DOIs
        if fetch_metadata:
            clean_dois_to_fetch = [clean for _, clean in dois_to_validate]
            try:
                metadata_results = await self.api_manager.batch_doi_lookups(clean_dois_to_fetch)
                
                # Process results
                validation_results_to_cache = {}
                
                for original, clean in dois_to_validate:
                    metadata = metadata_results.get(clean)
                    
                    result = DOIValidationResult(
                        doi=clean,
                        is_valid=True,
                        is_resolvable=metadata is not None,
                        metadata=metadata,
                        error_message=None if metadata else "DOI not found in CrossRef database"
                    )
                    
                    results[original] = result
                    validation_results_to_cache[clean] = result
                    
                    if metadata:
                        self.stats['resolved_metadata'] += 1
                        self.stats['valid_dois'] += 1
                    else:
                        self.stats['invalid_dois'] += 1
                
                # Cache new results
                if self.cache and validation_results_to_cache:
                    await self.cache.set_many('validation_results', validation_results_to_cache)
                
            except Exception as e:
                logger.error(f"Batch DOI validation failed: {e}")
                self.stats['api_errors'] += 1
                
                # Create error results for uncached DOIs
                for original, clean in dois_to_validate:
                    if original not in results:
                        results[original] = DOIValidationResult(
                            doi=clean,
                            is_valid=True,  # Format is valid
                            is_resolvable=False,
                            error_message=f"Validation failed: {str(e)}"
                        )
        else:
            # Format validation only
            for original, clean in dois_to_validate:
                results[original] = DOIValidationResult(
                    doi=clean,
                    is_valid=True,
                    is_resolvable=False,  # Not checked
                    error_message=None
                )
        
        self.stats['validations_performed'] += len(dois_to_validate)
        return results
    
    async def _fetch_doi_metadata(self, doi: str) -> Optional[Dict[str, Any]]:
        """
        Fetch metadata for DOI from CrossRef.
        
        Args:
            doi: DOI to fetch metadata for
            
        Returns:
            Metadata dictionary or None
        """
        try:
            metadata = await self.api_manager.lookup_doi_metadata(doi)
            if metadata:
                # Cache the metadata separately
                if self.cache:
                    await self.cache.set('doi_metadata', doi, metadata)
            return metadata
        except Exception as e:
            logger.warning(f"Failed to fetch DOI metadata for {doi}: {e}")
            return None
    
    async def enrich_reference_with_doi(self, reference: Reference) -> Reference:
        """
        Enrich reference with DOI-based metadata.
        
        Args:
            reference: Reference to enrich
            
        Returns:
            Enriched reference
        """
        if not reference.doi:
            return reference
        
        validation_result = await self.validate_doi(reference.doi, fetch_metadata=True)
        
        if not validation_result.is_resolvable or not validation_result.metadata:
            return reference
        
        metadata = validation_result.metadata
        
        # Update reference with CrossRef metadata
        updated_reference = reference.model_copy()
        
        # Title
        if not updated_reference.title and metadata.get('title'):
            titles = metadata['title']
            if titles and isinstance(titles, list):
                updated_reference.title = titles[0]
        
        # Authors
        if not updated_reference.authors and metadata.get('author'):
            authors = []
            for author in metadata['author']:
                given = author.get('given', '')
                family = author.get('family', '')
                if family:
                    full_name = f"{given} {family}".strip()
                    authors.append(full_name)
            updated_reference.authors = authors
        
        # Journal
        if not updated_reference.journal and metadata.get('container-title'):
            container_titles = metadata['container-title']
            if container_titles and isinstance(container_titles, list):
                updated_reference.journal = container_titles[0]
        
        # Publication year
        if not updated_reference.year and metadata.get('published'):
            published = metadata['published']
            if published and published.get('date-parts'):
                date_parts = published['date-parts'][0]
                if date_parts:
                    updated_reference.year = date_parts[0]
        
        # Volume and issue
        if not updated_reference.volume and metadata.get('volume'):
            updated_reference.volume = metadata['volume']
        
        if not updated_reference.issue and metadata.get('issue'):
            updated_reference.issue = metadata['issue']
        
        # Pages
        if not updated_reference.pages and metadata.get('page'):
            updated_reference.pages = metadata['page']
        
        # Citation count (if available)
        if metadata.get('is-referenced-by-count'):
            updated_reference.citation_count = metadata['is-referenced-by-count']
        
        # Check if retracted
        if validation_result.doi.lower() in self.RETRACTED_DOIS:
            updated_reference.is_retracted = True
        
        updated_reference.updated_at = datetime.utcnow()
        
        return updated_reference
    
    async def check_retracted_papers(self, references: List[Reference]) -> Dict[str, bool]:
        """
        Check if papers are retracted.
        
        Args:
            references: List of references to check
            
        Returns:
            Dictionary mapping reference ID to retraction status
        """
        results = {}
        
        for reference in references:
            is_retracted = False
            
            # Check DOI against known retracted papers
            if reference.doi:
                clean_doi = self._clean_doi(reference.doi)
                is_retracted = clean_doi.lower() in self.RETRACTED_DOIS
            
            # TODO: In production, query Retraction Watch API
            # This would require integration with Retraction Watch database
            
            results[reference.id] = is_retracted
        
        return results
    
    async def update_retracted_papers_list(self) -> None:
        """Update the list of retracted papers from external sources."""
        # TODO: Implement periodic updates from Retraction Watch API
        # This would require setting up a scheduled task to fetch
        # updated retraction data
        pass
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get validation statistics."""
        total_validations = self.stats['validations_performed']
        success_rate = (self.stats['valid_dois'] / total_validations) if total_validations > 0 else 0.0
        cache_hit_rate = (self.stats['cache_hits'] / total_validations) if total_validations > 0 else 0.0
        
        return {
            **self.stats,
            'success_rate': success_rate,
            'cache_hit_rate': cache_hit_rate,
            'retracted_dois_count': len(self.RETRACTED_DOIS),
        }


async def validate_reference_dois(references: List[Reference]) -> Dict[str, DOIValidationResult]:
    """
    Convenience function to validate DOIs for a list of references.
    
    Args:
        references: List of references
        
    Returns:
        Dictionary mapping reference ID to validation result
    """
    validator = DOIValidator()
    await validator.initialize()
    
    # Extract DOIs
    doi_map = {}
    dois_to_validate = []
    
    for ref in references:
        if ref.doi:
            doi_map[ref.doi] = ref.id
            dois_to_validate.append(ref.doi)
    
    if not dois_to_validate:
        return {}
    
    # Validate DOIs
    validation_results = await validator.validate_dois_batch(dois_to_validate)
    
    # Map back to reference IDs
    results = {}
    for doi, result in validation_results.items():
        if doi in doi_map:
            results[doi_map[doi]] = result
    
    return results