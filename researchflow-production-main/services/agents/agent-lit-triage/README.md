# Literature Triage Agent

An AI-powered literature triage agent that searches for academic papers across the medical domain, ranks them using multi-criteria scoring, and delivers a prioritized list of the most important papers.

## Overview

This agent implements an intelligent three-phase pipeline for medical literature discovery and prioritization:

1. **SEARCH**: Comprehensive literature discovery using AI-powered semantic search
2. **RANK**: Multi-criteria scoring based on recency, relevance, journal impact, author reputation, and citations
3. **PRIORITIZE & DELIVER**: Structured output with tiered recommendations (Must Read / Should Read / Optional)

## Architecture

### Components

- **LiteratureTriageAgent** (`agent/__init__.py`): Main orchestrator coordinating the full pipeline
- **LiteratureSearchWorker** (`workers/search_worker.py`): Performs comprehensive literature searches with query expansion
- **LiteratureRankingWorker** (`workers/ranking_worker.py`): Applies multi-criteria scoring and prioritization
- **FastAPI Service** (`app/main.py`): REST API wrapper for agent invocation

### LangSmith Configuration

The agent is based on a LangSmith agent design stored in `langsmith_export/`:

- `config.json`: Agent metadata and configuration
- `tools.json`: Tool definitions (exa_web_search, read_url_content)
- `AGENTS.md`: Complete agent instructions and workflow specification
- `subagents/`: Worker agent configurations

## Scoring Methodology

Papers are scored on five dimensions (1-10 scale):

1. **Recency (20%)**: Publication date
   - 10 = Last month
   - 8 = Last 3 months
   - 6 = Last 6 months
   - 4 = Last year
   - 2 = Last 2 years
   - 1 = Older

2. **Keyword Relevance (30%)**: Match to user query
   - 10 = Directly addresses exact question
   - 7 = Highly related
   - 4 = Tangentially related
   - 1 = Weak connection

3. **Journal Impact (20%)**: Publication venue reputation
   - 10 = Top-tier (NEJM, Lancet, JAMA, Nature, Science, BMJ)
   - 8 = High-impact specialty journals
   - 6 = Solid peer-reviewed journals
   - 4 = Regional/niche journals
   - 2 = Preprint servers
   - 1 = Unknown

4. **Author Reputation (15%)**: Author credentials and affiliations
   - 10 = Leading experts / major institutions
   - 7 = Well-established researchers
   - 4 = Mid-career
   - 1 = Cannot determine

5. **Citation Count (15%)**: Citation impact (adjusted for recency)
   - 10 = Highly cited relative to age
   - 7 = Above average
   - 4 = Average
   - 1 = Few citations

**Composite Score** = (Recency × 0.20) + (Relevance × 0.30) + (Journal × 0.20) + (Author × 0.15) + (Citations × 0.15)

### Priority Tiers

- **Tier 1 — Must Read 🔴**: Composite score ≥ 75
- **Tier 2 — Should Read 🟡**: Composite score 50-74
- **Tier 3 — Optional 🟢**: Composite score < 50

## API Endpoints

### Health Check

```bash
GET /health
GET /health/ready
```

### Run Triage (Sync)

```bash
POST /agents/run/sync
Content-Type: application/json

{
  "request_id": "unique-id",
  "task_type": "LIT_TRIAGE",
  "inputs": {
    "query": "recent advances in immunotherapy for lung cancer",
    "date_range_days": 730,
    "min_results": 15,
    "use_ai": true
  }
}
```

**Response:**

```json
{
  "ok": true,
  "request_id": "unique-id",
  "task_type": "LIT_TRIAGE",
  "outputs": {
    "query": "recent advances in immunotherapy for lung cancer",
    "executive_summary": "...",
    "papers": [...],
    "tier1_count": 5,
    "tier2_count": 8,
    "tier3_count": 2,
    "stats": {
      "found": 25,
      "ranked": 15
    },
    "markdown_report": "..."
  },
  "warnings": []
}
```

### Run Triage (Stream)

```bash
POST /agents/run/stream
Content-Type: application/json

{
  "request_id": "unique-id",
  "task_type": "LIT_TRIAGE",
  "inputs": {
    "query": "diabetes treatment guidelines",
    "use_ai": true
  }
}
```

Returns Server-Sent Events stream with progress updates.

## Input Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | string | required | Research question or topic |
| `date_range_days` | int | 730 | Number of days to look back (default: 2 years) |
| `min_results` | int | 15 | Minimum papers to discover |
| `use_ai` | bool | true | Use AI-powered triage (vs legacy rule-based) |

## Legacy Mode

The agent maintains backward compatibility with the original rule-based triage:

```json
{
  "inputs": {
    "papers": [...],
    "require_abstract": true,
    "dedupe": true,
    "include_keywords": ["immunotherapy"],
    "exclude_keywords": ["retracted"],
    "use_ai": false
  }
}
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `EXA_API_KEY` | API key for Exa semantic search | Optional* |
| `LANGCHAIN_API_KEY` | LangSmith tracing API key | Optional |
| `LANGCHAIN_PROJECT` | LangSmith project name | Optional |

*If `EXA_API_KEY` is not provided, the agent will use mock search results for demonstration.

## Development

### Local Setup

```bash
cd services/agents/agent-lit-triage

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export EXA_API_KEY=your_api_key_here

# Run service
uvicorn app.main:app --reload --port 8000
```

### Docker Build

```bash
# From repository root
docker build -f services/agents/agent-lit-triage/Dockerfile -t agent-lit-triage .

# Run container
docker run -p 8000:8000 \
  -e EXA_API_KEY=your_api_key \
  agent-lit-triage
```

### Testing

```bash
# Test health endpoint
curl http://localhost:8000/health

# Test triage endpoint
curl -X POST http://localhost:8000/agents/run/sync \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "test-1",
    "task_type": "LIT_TRIAGE",
    "inputs": {
      "query": "COVID-19 vaccine efficacy",
      "date_range_days": 365
    }
  }'
```

## Integration with ResearchFlow

This agent integrates into the ResearchFlow pipeline as follows:

1. **Stage 1**: Literature discovery and initial triage
2. **Stage 2**: Evidence synthesis and quality assessment
3. **Stage 3**: Report generation and narrative synthesis

The agent outputs are designed to feed directly into downstream evidence synthesis agents.

## Future Enhancements

- [ ] Integration with PubMed API for authoritative medical literature
- [ ] Support for custom scoring weights per user/domain
- [ ] Citation network analysis for related paper discovery
- [ ] Automated alerts for new papers matching saved queries
- [ ] Export to reference managers (EndNote, Zotero, Mendeley)
- [ ] Multi-language support beyond English
- [ ] Fine-tuned medical domain embeddings

## References

- [LangSmith Agent Builder](https://smith.langchain.com)
- [Exa AI Search](https://exa.ai)
- [PubMed API](https://www.ncbi.nlm.nih.gov/home/develop/api/)
- [MeSH Terms](https://www.ncbi.nlm.nih.gov/mesh)

## License

Part of the ResearchFlow platform. See main repository LICENSE for details.
