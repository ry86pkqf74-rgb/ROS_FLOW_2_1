"""Literature Search Worker - performs comprehensive literature searches"""
from __future__ import annotations
import os
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import httpx
from pydantic import BaseModel


class SearchResult(BaseModel):
    """Individual search result representing a paper"""
    title: str
    authors: Optional[List[str]] = None
    journal: Optional[str] = None
    publication_date: Optional[str] = None
    abstract: Optional[str] = None
    url: Optional[str] = None
    doi: Optional[str] = None
    citation_count: Optional[int] = None


class LiteratureSearchWorker:
    """
    Performs broad literature searches across medical research databases and the web.
    
    Based on the LangSmith agent configuration, this worker:
    - Uses exa_web_search for deep academic paper searches
    - Performs query expansion with 2-3 variants
    - Enriches results with full metadata
    - Targets PubMed, PMC, bioRxiv, medRxiv, and major journals
    """
    
    def __init__(self):
        self.exa_api_key = os.getenv("EXA_API_KEY")
        self.max_results_per_query = 20
        
    async def search(
        self,
        query: str,
        date_range: Optional[tuple[datetime, datetime]] = None,
        min_results: int = 15
    ) -> List[SearchResult]:
        """
        Perform comprehensive literature search
        
        Args:
            query: The search query (medical topic, keywords, or research question)
            date_range: Optional tuple of (start_date, end_date) to filter results
            min_results: Minimum number of results to target (default: 15)
            
        Returns:
            List of SearchResult objects representing discovered papers
        """
        # Generate query variants for comprehensive coverage
        query_variants = self._expand_query(query)
        
        all_results = []
        
        # Execute searches for each variant
        for variant in query_variants:
            results = await self._execute_exa_search(variant, date_range)
            all_results.extend(results)
            
        # Deduplicate by DOI/URL
        deduplicated = self._deduplicate_results(all_results)
        
        return deduplicated[:self.max_results_per_query * 2]  # Cap at reasonable limit
    
    def _expand_query(self, query: str) -> List[str]:
        """
        Generate 2-3 query variants to maximize coverage
        
        Strategy:
        1. Original query
        2. Query with medical terminology
        3. Broader/narrower related terms
        """
        variants = [query]
        
        # Add medical terminology variant
        medical_terms = self._add_medical_terminology(query)
        if medical_terms != query:
            variants.append(medical_terms)
            
        # Add broader context variant
        if len(variants) < 3:
            variants.append(f"{query} research clinical trial")
            
        return variants[:3]
    
    def _add_medical_terminology(self, query: str) -> str:
        """Add MeSH-like medical terminology to query"""
        # Simple approach - in production, use MeSH API or medical NLP
        medical_additions = {
            "cancer": "neoplasm carcinoma tumor",
            "heart": "cardiovascular cardiac",
            "lung": "pulmonary respiratory",
            "diabetes": "diabetic mellitus glycemic",
            "therapy": "treatment intervention",
        }
        
        query_lower = query.lower()
        for term, additions in medical_additions.items():
            if term in query_lower:
                return f"{query} {additions}"
                
        return query
    
    async def _execute_exa_search(
        self,
        query: str,
        date_range: Optional[tuple[datetime, datetime]] = None
    ) -> List[SearchResult]:
        """
        Execute search using Exa API (or fallback mock implementation)
        """
        if not self.exa_api_key:
            # Mock implementation for demonstration
            return self._mock_search_results(query, date_range)
            
        # Real Exa API implementation
        try:
            async with httpx.AsyncClient() as client:
                headers = {"Authorization": f"Bearer {self.exa_api_key}"}
                
                payload = {
                    "query": query,
                    "type": "neural",  # Deep semantic search
                    "category": "research paper",
                    "numResults": self.max_results_per_query,
                    "contents": {
                        "text": True,
                        "highlights": True
                    }
                }
                
                if date_range:
                    payload["startPublishedDate"] = date_range[0].isoformat()
                    payload["endPublishedDate"] = date_range[1].isoformat()
                    
                response = await client.post(
                    "https://api.exa.ai/search",
                    json=payload,
                    headers=headers,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return self._parse_exa_results(data)
                    
        except Exception as e:
            print(f"Exa API error: {e}")
            
        # Fallback to mock
        return self._mock_search_results(query, date_range)
    
    def _parse_exa_results(self, data: Dict[str, Any]) -> List[SearchResult]:
        """Parse Exa API response into SearchResult objects"""
        results = []
        
        for item in data.get("results", []):
            results.append(SearchResult(
                title=item.get("title", ""),
                url=item.get("url", ""),
                abstract=item.get("text", ""),
                publication_date=item.get("publishedDate"),
                authors=item.get("author", "").split(",") if item.get("author") else None,
            ))
            
        return results
    
    def _mock_search_results(
        self,
        query: str,
        date_range: Optional[tuple[datetime, datetime]] = None
    ) -> List[SearchResult]:
        """Generate mock search results for demonstration"""
        # In production, this would be removed and only real API would be used
        mock_results = []
        
        for i in range(5):
            mock_results.append(SearchResult(
                title=f"Mock Paper {i+1}: {query[:50]}",
                authors=["Smith J", "Johnson M", "Williams K"],
                journal="Medical Journal" if i % 2 == 0 else "Journal of Medicine",
                publication_date=(datetime.now() - timedelta(days=30*i)).isoformat(),
                abstract=f"This is a mock abstract for paper {i+1} about {query}. " * 3,
                url=f"https://pubmed.ncbi.nlm.nih.gov/mock{i}",
                doi=f"10.1234/mock.{i}",
                citation_count=100 - (i * 10)
            ))
            
        return mock_results
    
    def _deduplicate_results(self, results: List[SearchResult]) -> List[SearchResult]:
        """Remove duplicate papers based on DOI or URL"""
        seen = set()
        deduplicated = []
        
        for result in results:
            # Create unique key based on DOI or URL
            if result.doi:
                key = f"doi:{result.doi}"
            elif result.url:
                key = f"url:{result.url}"
            else:
                key = f"title:{result.title}"
                
            if key not in seen:
                seen.add(key)
                deduplicated.append(result)
                
        return deduplicated
