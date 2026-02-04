"""
Search Strategies Module - PICO Framework & Query Building

This module provides structured search strategy tools for literature search:
- PICO (Population, Intervention, Comparison, Outcome) framework
- Boolean query builders with database-specific syntax
- MeSH term expansion for PubMed
- Search query optimization and refinement

Linear Issues: ROS-XXX
"""

import re
import logging
from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# =============================================================================
# PICO Framework
# =============================================================================

class PICOComponent(str, Enum):
    """PICO framework components."""
    POPULATION = "population"
    INTERVENTION = "intervention"
    COMPARISON = "comparison"
    OUTCOME = "outcome"


class PICOFramework(BaseModel):
    """
    PICO framework for structured research question decomposition.
    
    PICO helps construct effective literature searches by breaking down
    research questions into key components.
    """
    population: List[str] = Field(
        default_factory=list,
        description="Target population (e.g., 'adults with Type 2 diabetes')"
    )
    intervention: List[str] = Field(
        default_factory=list,
        description="Intervention being studied (e.g., 'metformin', 'lifestyle modification')"
    )
    comparison: List[str] = Field(
        default_factory=list,
        description="Comparison group or treatment (e.g., 'placebo', 'standard care')"
    )
    outcome: List[str] = Field(
        default_factory=list,
        description="Outcome measures (e.g., 'HbA1c reduction', 'mortality')"
    )
    
    def to_query_parts(self) -> Dict[str, List[str]]:
        """Convert PICO components to query parts."""
        return {
            "population": self.population,
            "intervention": self.intervention,
            "comparison": self.comparison,
            "outcome": self.outcome,
        }
    
    def to_boolean_query(self, operator: str = "AND") -> str:
        """
        Convert PICO to boolean search query.
        
        Args:
            operator: Boolean operator to join components (AND/OR)
        
        Returns:
            Boolean query string
        """
        parts = []
        
        if self.population:
            pop_query = " OR ".join(f'"{term}"' for term in self.population)
            parts.append(f"({pop_query})")
        
        if self.intervention:
            int_query = " OR ".join(f'"{term}"' for term in self.intervention)
            parts.append(f"({int_query})")
        
        if self.comparison:
            comp_query = " OR ".join(f'"{term}"' for term in self.comparison)
            parts.append(f"({comp_query})")
        
        if self.outcome:
            out_query = " OR ".join(f'"{term}"' for term in self.outcome)
            parts.append(f"({out_query})")
        
        return f" {operator} ".join(parts)
    
    @classmethod
    def from_research_question(cls, question: str) -> "PICOFramework":
        """
        Extract PICO components from a research question using pattern matching.
        
        Args:
            question: Natural language research question
        
        Returns:
            PICOFramework with extracted components
        
        Note: This is a simple heuristic approach. For production, consider
        using an NLP model trained on PICO extraction.
        """
        # Simple pattern-based extraction (can be enhanced with NLP)
        population_patterns = [
            r"in (\w+(?:\s+\w+){0,3})\s+(?:patients|subjects|individuals|adults|children)",
            r"among (\w+(?:\s+\w+){0,3})\s+(?:patients|population)",
        ]
        
        intervention_patterns = [
            r"(?:treated with|receiving|given)\s+(\w+(?:\s+\w+){0,2})",
            r"effect of\s+(\w+(?:\s+\w+){0,2})",
        ]
        
        outcome_patterns = [
            r"(?:reduce|improve|increase|decrease)\s+(\w+(?:\s+\w+){0,2})",
            r"on (\w+(?:\s+\w+){0,2})\s*(?:\?|$)",
        ]
        
        population = []
        for pattern in population_patterns:
            matches = re.findall(pattern, question, re.IGNORECASE)
            population.extend(matches)
        
        intervention = []
        for pattern in intervention_patterns:
            matches = re.findall(pattern, question, re.IGNORECASE)
            intervention.extend(matches)
        
        outcome = []
        for pattern in outcome_patterns:
            matches = re.findall(pattern, question, re.IGNORECASE)
            outcome.extend(matches)
        
        return cls(
            population=list(set(population)),
            intervention=list(set(intervention)),
            outcome=list(set(outcome)),
        )


# =============================================================================
# Query Builder
# =============================================================================

class DatabaseType(str, Enum):
    """Supported database types."""
    PUBMED = "pubmed"
    SEMANTIC_SCHOLAR = "semantic_scholar"
    WEB_OF_SCIENCE = "web_of_science"
    SCOPUS = "scopus"


@dataclass
class SearchQuery:
    """Structured search query."""
    query_string: str
    database: DatabaseType
    filters: Dict[str, any] = field(default_factory=dict)
    max_results: int = 50
    
    def to_api_params(self) -> Dict[str, any]:
        """Convert to database-specific API parameters."""
        params = {
            "query": self.query_string,
            "max_results": self.max_results,
        }
        params.update(self.filters)
        return params


class SearchQueryBuilder:
    """
    Build optimized search queries for different databases.
    
    Features:
    - Boolean operators (AND, OR, NOT)
    - Field-specific searching (title, abstract, author)
    - Date range filtering
    - Study type filtering
    - Database-specific syntax translation
    """
    
    def __init__(self, database: DatabaseType = DatabaseType.PUBMED):
        self.database = database
        self.terms: List[str] = []
        self.filters: Dict[str, any] = {}
        self.field_terms: Dict[str, List[str]] = {}
    
    def add_term(self, term: str, operator: str = "AND") -> "SearchQueryBuilder":
        """Add a search term with operator."""
        if self.terms:
            self.terms.append(operator)
        self.terms.append(f'"{term}"' if " " in term else term)
        return self
    
    def add_terms(self, terms: List[str], operator: str = "OR") -> "SearchQueryBuilder":
        """Add multiple terms with specified operator."""
        if not terms:
            return self
        
        group = f"({' {} '.format(operator).join(terms)})"
        if self.terms:
            self.terms.append("AND")
        self.terms.append(group)
        return self
    
    def add_field_term(self, field: str, term: str) -> "SearchQueryBuilder":
        """Add term for specific field (title, abstract, author)."""
        if field not in self.field_terms:
            self.field_terms[field] = []
        self.field_terms[field].append(term)
        return self
    
    def add_date_filter(self, year_from: Optional[int] = None, year_to: Optional[int] = None) -> "SearchQueryBuilder":
        """Add date range filter."""
        if year_from:
            self.filters["year_from"] = year_from
        if year_to:
            self.filters["year_to"] = year_to
        return self
    
    def add_study_type_filter(self, study_types: List[str]) -> "SearchQueryBuilder":
        """Add study type filter (RCT, meta-analysis, etc.)."""
        self.filters["study_types"] = study_types
        return self
    
    def exclude_term(self, term: str) -> "SearchQueryBuilder":
        """Exclude a term from search."""
        if self.terms:
            self.terms.append("AND")
        self.terms.append(f'NOT "{term}"' if " " in term else f"NOT {term}")
        return self
    
    def build(self) -> SearchQuery:
        """Build the final search query."""
        # Combine regular terms
        query_parts = [" ".join(self.terms)] if self.terms else []
        
        # Add field-specific terms
        if self.database == DatabaseType.PUBMED:
            for field, terms in self.field_terms.items():
                field_suffix = self._get_pubmed_field_suffix(field)
                field_query = " OR ".join(f"{term}{field_suffix}" for term in terms)
                if field_query:
                    query_parts.append(f"({field_query})")
        
        query_string = " AND ".join(query_parts)
        
        return SearchQuery(
            query_string=query_string,
            database=self.database,
            filters=self.filters.copy(),
        )
    
    def _get_pubmed_field_suffix(self, field: str) -> str:
        """Get PubMed field suffix."""
        field_map = {
            "title": "[Title]",
            "abstract": "[Abstract]",
            "author": "[Author]",
            "mesh": "[MeSH Terms]",
            "journal": "[Journal]",
        }
        return field_map.get(field, "")
    
    @classmethod
    def from_pico(cls, pico: PICOFramework, database: DatabaseType = DatabaseType.PUBMED) -> "SearchQueryBuilder":
        """Create query builder from PICO framework."""
        builder = cls(database=database)
        
        # Add PICO components as term groups
        if pico.population:
            builder.add_terms(pico.population, operator="OR")
        
        if pico.intervention:
            builder.add_terms(pico.intervention, operator="OR")
        
        if pico.comparison:
            builder.add_terms(pico.comparison, operator="OR")
        
        if pico.outcome:
            builder.add_terms(pico.outcome, operator="OR")
        
        return builder


# =============================================================================
# MeSH Term Expander
# =============================================================================

class MeSHTermExpander:
    """
    Expand search terms with MeSH (Medical Subject Headings) terms.
    
    MeSH is a controlled vocabulary for indexing biomedical literature.
    Using MeSH terms improves recall in PubMed searches.
    """
    
    # Common medical term -> MeSH mapping (subset for demo)
    MESH_MAPPINGS = {
        "diabetes": ["Diabetes Mellitus", "Diabetes Mellitus, Type 2", "Diabetes Mellitus, Type 1"],
        "hypertension": ["Hypertension", "Hypertension, Pulmonary", "Hypertension, Pregnancy-Induced"],
        "cancer": ["Neoplasms", "Carcinoma", "Adenocarcinoma"],
        "heart attack": ["Myocardial Infarction", "Acute Coronary Syndrome"],
        "stroke": ["Stroke", "Cerebrovascular Accident", "Brain Ischemia"],
        "obesity": ["Obesity", "Obesity, Morbid", "Overweight"],
    }
    
    def __init__(self):
        self.cache: Dict[str, List[str]] = {}
    
    def expand_term(self, term: str) -> List[str]:
        """
        Expand a term with related MeSH terms.
        
        Args:
            term: Search term to expand
        
        Returns:
            List of expanded terms including original and MeSH terms
        
        TODO: Integrate with NCBI E-utilities MeSH API for dynamic lookup
        """
        term_lower = term.lower()
        
        # Check cache
        if term_lower in self.cache:
            return self.cache[term_lower]
        
        # Check static mappings
        mesh_terms = self.MESH_MAPPINGS.get(term_lower, [])
        
        # Combine original with MeSH terms
        expanded = [term] + mesh_terms
        
        # Cache result
        self.cache[term_lower] = expanded
        
        return expanded
    
    def expand_query(self, query: str) -> str:
        """
        Expand all terms in a query with MeSH terms.
        
        Args:
            query: Original search query
        
        Returns:
            Expanded query with MeSH terms
        """
        # Extract terms from query (simple tokenization)
        terms = re.findall(r'\b[a-zA-Z]+\b', query)
        
        expanded_parts = []
        for term in set(terms):
            mesh_terms = self.expand_term(term)
            if len(mesh_terms) > 1:
                mesh_group = " OR ".join(f'"{t}"[MeSH Terms]' for t in mesh_terms[1:])
                expanded_parts.append(f"({term} OR {mesh_group})")
            else:
                expanded_parts.append(term)
        
        return " AND ".join(expanded_parts)


# =============================================================================
# Query Optimizer
# =============================================================================

class QueryOptimizer:
    """Optimize search queries for better recall and precision."""
    
    @staticmethod
    def remove_duplicates(query: str) -> str:
        """Remove duplicate terms from query."""
        # Split by boolean operators
        parts = re.split(r'\s+(AND|OR|NOT)\s+', query)
        
        seen = set()
        optimized = []
        
        for i, part in enumerate(parts):
            if part in ("AND", "OR", "NOT"):
                optimized.append(part)
            elif part not in seen:
                seen.add(part)
                optimized.append(part)
        
        return " ".join(optimized)
    
    @staticmethod
    def simplify_nested_operators(query: str) -> str:
        """Simplify nested boolean operators."""
        # Remove double ANDs/ORs
        query = re.sub(r'\s+AND\s+AND\s+', ' AND ', query)
        query = re.sub(r'\s+OR\s+OR\s+', ' OR ', query)
        
        # Remove redundant parentheses
        while True:
            simplified = re.sub(r'\(\(([^()]+)\)\)', r'(\1)', query)
            if simplified == query:
                break
            query = simplified
        
        return query
    
    @staticmethod
    def estimate_result_count(query: str) -> Tuple[int, int]:
        """
        Estimate min/max result count based on query complexity.
        
        Returns:
            Tuple of (estimated_min, estimated_max)
        """
        # Count terms and operators
        and_count = query.count(" AND ")
        or_count = query.count(" OR ")
        not_count = query.count(" NOT ")
        
        # Heuristic: more ANDs = fewer results, more ORs = more results
        if and_count > or_count:
            return (10, 100)
        elif or_count > and_count:
            return (100, 10000)
        else:
            return (50, 1000)


# =============================================================================
# Deduplication
# =============================================================================

class PaperDeduplicator:
    """Deduplicate papers from multiple database sources."""
    
    @staticmethod
    def get_paper_signature(paper: Dict[str, any]) -> str:
        """
        Generate unique signature for a paper.
        
        Uses DOI if available, otherwise title + first author + year.
        """
        # Prefer DOI
        if paper.get("doi"):
            return f"doi:{paper['doi'].lower()}"
        
        # Fallback to title + author + year
        title = paper.get("title", "").lower().strip()
        authors = paper.get("authors", [])
        first_author = authors[0].lower() if authors else "unknown"
        year = paper.get("year", "")
        
        return f"title:{title[:50]}|author:{first_author}|year:{year}"
    
    @staticmethod
    def deduplicate(papers: List[Dict[str, any]]) -> List[Dict[str, any]]:
        """
        Remove duplicate papers from list.
        
        Args:
            papers: List of paper dictionaries
        
        Returns:
            Deduplicated list of papers
        """
        seen_signatures: Set[str] = set()
        unique_papers = []
        
        for paper in papers:
            signature = PaperDeduplicator.get_paper_signature(paper)
            
            if signature not in seen_signatures:
                seen_signatures.add(signature)
                unique_papers.append(paper)
            else:
                logger.debug(f"Duplicate paper removed: {paper.get('title', 'Unknown')[:50]}")
        
        return unique_papers
