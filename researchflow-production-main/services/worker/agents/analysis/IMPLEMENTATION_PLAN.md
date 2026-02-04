# LitSearchAgent Implementation Plan

## Overview
Comprehensive literature search agent for ResearchFlow Stage 6 with PICO framework, multi-database search, and citation formatting.

## Files Created

### 1. search_strategies.py ✅ DONE
- PICOFramework class for structured search
- SearchQueryBuilder for boolean queries
- MeSHTermExpander for PubMed
- Query optimization utilities
- Paper deduplication

### 2. citation_formatters.py (IN PROGRESS)
- 5 citation styles: AMA, APA, MLA, Chicago, Vancouver
- Author name parsing utilities
- Abstract CitationFormatter base class
- Factory pattern for formatter selection

### 3. lit_search_agent.py (TODO)
- Enhanced LitSearchAgent with PICO integration
- Multi-database orchestration
- Relevance ranking with LLM
- Citation generation pipeline

### 4. API Routes: src/api/routes/literature.py (TODO)
Endpoints:
- POST /literature/search
- GET /literature/papers/{paper_id}
- POST /literature/rank
- POST /literature/citations
- GET /literature/search/{task_id}/status

### 5. Unit Tests: tests/test_lit_search_agent.py (TODO)
- PICO extraction tests
- Query builder tests
- Citation formatting tests
- API integration tests
- Database mock tests

## Integration Points
- Extends BaseAgent from src/agents/base_agent.py
- Registers in src/agents/__init__.py as stage 6 handler
- Exposes routes through src/api/routes/__init__.py
- Uses existing LangGraph patterns

## Next Steps
1. Create citation_formatters.py (split into chunks)
2. Create enhanced lit_search_agent.py
3. Create API routes
4. Create comprehensive tests
5. Update agent registry
6. Add to API router

