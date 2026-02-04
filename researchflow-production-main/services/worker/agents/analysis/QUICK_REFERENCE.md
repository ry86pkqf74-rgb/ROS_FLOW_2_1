# LitSearchAgent Quick Reference Card

## 🚀 Quick Start

```python
from agents.analysis import LitSearchAgent, StudyContext

# Initialize
agent = LitSearchAgent()

# Define study
study = StudyContext(
    title="Your Study Title",
    keywords=["keyword1", "keyword2"],
    research_question="Your research question?",
    study_type="RCT"
)

# Execute
result = await agent.execute(study_context=study, max_results=50)
```

## 📁 File Structure

```
services/worker/agents/analysis/
├── lit_search_agent.py        # Main agent
├── search_strategies.py       # PICO & queries
├── citation_formatters.py     # Citations
├── __init__.py                # Exports
└── docs/                      # Documentation
```

## 🔧 Key Classes

| Class | Purpose | Location |
|-------|---------|----------|
| `LitSearchAgent` | Main agent orchestration | lit_search_agent.py |
| `PICOFramework` | Structured search | search_strategies.py |
| `SearchQueryBuilder` | Query building | search_strategies.py |
| `MeSHTermExpander` | MeSH terms | search_strategies.py |
| `AMAFormatter` | AMA citations | citation_formatters.py |
| `StudyContext` | Study metadata | lit_search_agent.py |
| `Paper` | Paper model | lit_search_agent.py |
| `RankedPaper` | Scored paper | lit_search_agent.py |

## 🌐 API Endpoints

```bash
# Async search
POST /literature/search
Body: {"study_context": {...}, "max_results": 50}

# Check status  
GET /literature/search/{task_id}/status

# Rank papers
POST /literature/rank
Body: {"papers": [...], "study_context": {...}}

# Generate citations
POST /literature/citations
Body: {"papers": [...], "style": "AMA"}
```

## 🧪 Testing

```bash
# Run all tests
cd services/worker
python3 -m pytest tests/test_lit_search_agent.py -v

# Run specific test
pytest tests/test_lit_search_agent.py::TestPICOFramework -v

# With coverage
pytest tests/test_lit_search_agent.py --cov=agents.analysis
```

## 🔑 Environment Variables

```bash
# Optional - improves PubMed rate limits
export NCBI_API_KEY=your_key

# Optional - for Semantic Scholar
export SEMANTIC_SCHOLAR_API_KEY=your_key

# Required for LLM (inherited from BaseAgent)
export ANTHROPIC_API_KEY=your_key
```

## 📊 Quality Criteria

| Criterion | Target | Weight |
|-----------|--------|--------|
| Paper Count | 10+ | 25% |
| Avg Relevance | 0.6+ | 25% |
| DB Coverage | 2+ | 25% |
| Year Diversity | Recent | 25% |

## 🎨 PICO Example

```python
pico = PICOFramework(
    population=["adults with Type 2 diabetes"],
    intervention=["metformin"],
    comparison=["placebo"],
    outcome=["HbA1c reduction"]
)

query = pico.to_boolean_query()
# Output: (adults with Type 2 diabetes) AND (metformin) AND ...
```

## 🔍 Query Building

```python
builder = SearchQueryBuilder(database=DatabaseType.PUBMED)
builder.add_terms(["diabetes", "hyperglycemia"], operator="OR")
builder.add_field_term("title", "metformin")
builder.add_date_filter(year_from=2020)
builder.exclude_term("retracted")

query = builder.build()
```

## 📚 Citation Styles

| Style | Status | Code |
|-------|--------|------|
| AMA | ✅ Complete | `CitationFormatterFactory.get_formatter("AMA")` |
| APA | 📋 Ready | Architecture in place |
| MLA | 📋 Ready | Architecture in place |
| Chicago | 📋 Ready | Architecture in place |
| Vancouver | 📋 Ready | Architecture in place |

## 🐛 Common Issues

**No papers found**
- Broaden search terms
- Reduce date filters
- Try alternative databases

**Low relevance scores**
- Refine PICO components
- Add MeSH terms
- Use field-specific searches

**Duplicates**
- PaperDeduplicator handles automatically
- Based on DOI or title+author+year

## 📖 Documentation

- **README.md** - Full usage guide
- **COMPLETION_SUMMARY.md** - Implementation details
- **IMPLEMENTATION_PLAN.md** - Development roadmap
- **QUICK_REFERENCE.md** - This file

## 🔗 Integration

### Register Agent
```python
# In src/agents/__init__.py
from agents.analysis import create_lit_search_agent

AGENT_REGISTRY["lit_search"] = AgentRegistryEntry(...)
```

### Add API Router
```python
# In src/main.py
from src.api.routes import literature
app.include_router(literature.router, prefix="/api")
```

## 💡 Tips

1. **Use PICO** for structured searches
2. **Add MeSH terms** for better recall on PubMed
3. **Filter by date** to focus on recent research
4. **Rank with AI** for relevance scoring
5. **Cache results** for repeated searches

## 📞 Support

- GitHub Issues: [Project Repo]
- Linear: ROS-XXX
- Docs: See README.md

---

**Version**: 1.0.0  
**Last Updated**: 2025-02-03  
**Status**: ✅ Production Ready (pending external APIs)
