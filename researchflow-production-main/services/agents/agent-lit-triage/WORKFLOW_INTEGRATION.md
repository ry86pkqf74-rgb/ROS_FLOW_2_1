# Literature Triage Agent - Workflow Integration Guide

**Agent:** `agent-lit-triage`  
**Version:** 1.0.0 (LangSmith Import)  
**Date:** 2026-02-07  
**Status:** ✅ Production Ready

## Integration Points

### 1. Stage 2 Literature Pipeline

The Literature Triage Agent integrates into the Stage 2 Literature Pipeline as an upstream discovery and prioritization layer:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Stage 2 Literature Pipeline                  │
└─────────────────────────────────────────────────────────────────┘

  1. Literature Discovery
     └─> agent-lit-triage (NEW)
         ├─> Search: Multi-query semantic search across medical databases
         ├─> Rank: Multi-criteria scoring (recency, relevance, impact)
         └─> Output: Tiered list of prioritized papers
  
  2. Literature Screening
     └─> agent-stage2-screen
         ├─> Input: Prioritized papers from triage
         ├─> Process: Deduplication, inclusion/exclusion criteria
         └─> Output: Screened papers for extraction
  
  3. Data Extraction
     └─> agent-stage2-extract
         ├─> Input: Screened papers
         ├─> Process: PICO extraction
         └─> Output: Structured evidence data
  
  4. Evidence Synthesis
     └─> agent-evidence-synthesis
         ├─> Input: Extracted evidence
         ├─> Process: GRADE assessment, conflict analysis
         └─> Output: Synthesis report
```

### 2. Orchestrator Integration

#### 2.1 Service Registration

Add to [`docker-compose.yml`](../../docker-compose.yml):

```yaml
services:
  agent-lit-triage:
    build:
      context: .
      dockerfile: services/agents/agent-lit-triage/Dockerfile
    ports:
      - "8012:8000"
    environment:
      - EXA_API_KEY=${EXA_API_KEY}
      - LANGCHAIN_API_KEY=${LANGCHAIN_API_KEY}
      - LANGCHAIN_PROJECT=researchflow-lit-triage
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - researchflow
```

#### 2.2 Orchestrator Configuration

Update `services/orchestrator/config/agent_endpoints.json`:

```json
{
  "agents": {
    "lit-triage": {
      "url": "http://agent-lit-triage:8000",
      "timeout": 60,
      "retry": 3,
      "enabled": true
    }
  }
}
```

### 3. Workflow Engine Integration

#### 3.1 Stage 2 Literature Agent Enhancement

Update [`services/worker/src/workflow_engine/stages/stage_02_literature.py`](../../services/worker/src/workflow_engine/stages/stage_02_literature.py):

```python
from typing import Dict, Any
import httpx

class LiteratureScoutAgent(BaseStageAgent):
    """Enhanced with AI-powered triage"""
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute literature discovery with intelligent triage"""
        
        # 1. Get research query from context
        query = context.get("research_question", "")
        
        # 2. Call lit-triage agent for prioritized papers
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://agent-lit-triage:8000/agents/run/sync",
                json={
                    "request_id": context.get("request_id"),
                    "task_type": "LIT_TRIAGE",
                    "inputs": {
                        "query": query,
                        "date_range_days": 730,  # 2 years
                        "min_results": 20,
                        "use_ai": True
                    }
                },
                timeout=60.0
            )
            
            triage_result = response.json()
        
        # 3. Extract prioritized papers
        papers = triage_result["outputs"]["papers"]
        tier1 = [p for p in papers if p["tier"] == "Must Read"]
        tier2 = [p for p in papers if p["tier"] == "Should Read"]
        
        # 4. Focus on Tier 1 & 2 for downstream processing
        priority_papers = tier1 + tier2
        
        # 5. Update context with prioritized papers
        context["papers"] = priority_papers
        context["triage_summary"] = triage_result["outputs"]["executive_summary"]
        context["triage_stats"] = triage_result["outputs"]["stats"]
        
        return {
            "status": "success",
            "papers_found": len(priority_papers),
            "tier1_count": len(tier1),
            "tier2_count": len(tier2),
            "next_stage": "stage_02_screen"
        }
```

### 4. API Usage Examples

#### 4.1 Direct API Call (Sync)

```bash
curl -X POST http://localhost:8012/agents/run/sync \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "req-123",
    "task_type": "LIT_TRIAGE",
    "inputs": {
      "query": "CAR-T therapy efficacy in lymphoma",
      "date_range_days": 730,
      "min_results": 15,
      "use_ai": true
    }
  }'
```

**Response:**

```json
{
  "ok": true,
  "request_id": "req-123",
  "task_type": "LIT_TRIAGE",
  "outputs": {
    "query": "CAR-T therapy efficacy in lymphoma",
    "executive_summary": "This literature triage identified 23 relevant papers...",
    "papers": [...],
    "tier1_count": 6,
    "tier2_count": 11,
    "tier3_count": 6,
    "stats": {
      "found": 28,
      "ranked": 23
    },
    "markdown_report": "# 📋 Literature Triage Report\n..."
  }
}
```

#### 4.2 Streaming API Call

```python
import httpx
import json

async def stream_triage():
    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST",
            "http://localhost:8012/agents/run/stream",
            json={
                "request_id": "req-456",
                "task_type": "LIT_TRIAGE",
                "inputs": {
                    "query": "diabetes treatment metformin",
                    "use_ai": true
                }
            }
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    event = json.loads(line[6:])
                    print(f"Event: {event['event']}")
                    if event["event"] == "progress":
                        print(f"Progress: {event['pct']}%")
                    elif event["event"] == "final":
                        print(f"Complete! Stats: {event['outputs']['stats']}")
```

#### 4.3 Python SDK Integration

```python
from typing import List, Dict, Any
import httpx

class LitTriageClient:
    """Client for Literature Triage Agent"""
    
    def __init__(self, base_url: str = "http://agent-lit-triage:8000"):
        self.base_url = base_url
    
    async def triage(
        self,
        query: str,
        date_range_days: int = 730,
        min_results: int = 15
    ) -> Dict[str, Any]:
        """Execute literature triage"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/agents/run/sync",
                json={
                    "request_id": f"triage-{query[:20]}",
                    "task_type": "LIT_TRIAGE",
                    "inputs": {
                        "query": query,
                        "date_range_days": date_range_days,
                        "min_results": min_results,
                        "use_ai": True
                    }
                },
                timeout=60.0
            )
            return response.json()
    
    def get_tier1_papers(self, result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract Tier 1 (Must Read) papers"""
        return [
            p for p in result["outputs"]["papers"]
            if p["tier"] == "Must Read"
        ]

# Usage
client = LitTriageClient()
result = await client.triage("immunotherapy lung cancer")
must_read = client.get_tier1_papers(result)
print(f"Found {len(must_read)} must-read papers")
```

### 5. Environment Configuration

#### 5.1 Required Environment Variables

Add to [`.env`](../../.env) or deployment config:

```bash
# Literature Triage Agent
EXA_API_KEY=your_exa_api_key_here
LANGCHAIN_API_KEY=your_langsmith_key_here
LANGCHAIN_PROJECT=researchflow-lit-triage

# Optional: Enable tracing
LANGCHAIN_TRACING_V2=true
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
```

#### 5.2 Development Mode (Mock Search)

For development without Exa API:

```bash
# .env.development
EXA_API_KEY=  # Empty = use mock results
```

The agent will automatically fallback to mock search results for testing.

### 6. Monitoring & Observability

#### 6.1 Health Checks

```bash
# Basic health
curl http://localhost:8012/health

# Readiness check
curl http://localhost:8012/health/ready
```

#### 6.2 LangSmith Tracing

When `LANGCHAIN_TRACING_V2=true`, all agent executions are traced in LangSmith:

- View traces at: https://smith.langchain.com
- Project: `researchflow-lit-triage`
- Traces include:
  - Search queries and results
  - Ranking scores and rationale
  - Execution timing
  - Error details

#### 6.3 Logging

Agent logs structured output for each phase:

```
[Phase 1] Searching for papers on query: CAR-T therapy efficacy
[Phase 1] Found 28 candidate papers
[Phase 2] Ranking papers using multi-criteria scoring
[Phase 2] Ranked 23 papers
[Phase 3] Organizing into priority tiers
[Phase 3] Tier 1: 6, Tier 2: 11, Tier 3: 6
```

### 7. Testing

#### 7.1 Unit Tests

```bash
cd services/agents/agent-lit-triage
pytest tests/
```

#### 7.2 Integration Tests

```bash
# Start service
docker-compose up agent-lit-triage

# Run integration test
pytest tests/integration/test_lit_triage_integration.py
```

#### 7.3 End-to-End Test

```python
import httpx
import asyncio

async def test_e2e():
    async with httpx.AsyncClient() as client:
        # Test health
        health = await client.get("http://localhost:8012/health")
        assert health.status_code == 200
        
        # Test triage
        result = await client.post(
            "http://localhost:8012/agents/run/sync",
            json={
                "request_id": "test-e2e",
                "task_type": "LIT_TRIAGE",
                "inputs": {
                    "query": "test query",
                    "use_ai": True
                }
            }
        )
        assert result.status_code == 200
        data = result.json()
        assert data["ok"] == True
        assert "papers" in data["outputs"]

asyncio.run(test_e2e())
```

### 8. Performance Considerations

#### 8.1 Timeouts

- Typical triage execution: 10-30 seconds
- Exa API calls: 5-10 seconds per query
- Ranking: 1-2 seconds for 20-50 papers
- Total budget: 60 seconds timeout recommended

#### 8.2 Rate Limits

- Exa API: 100 requests/minute (free tier)
- Consider caching frequent queries
- Use `date_range_days` to limit search scope

#### 8.3 Concurrency

Agent is async-capable and can handle concurrent requests:

```python
# Multiple concurrent triages
import asyncio
queries = ["query1", "query2", "query3"]
results = await asyncio.gather(*[
    client.triage(q) for q in queries
])
```

### 9. Troubleshooting

#### 9.1 Common Issues

**Issue:** Agent returns mock results instead of real papers

**Solution:** Verify `EXA_API_KEY` is set correctly:
```bash
docker-compose exec agent-lit-triage env | grep EXA_API_KEY
```

**Issue:** Timeouts on large queries

**Solution:** Reduce search scope:
```json
{
  "inputs": {
    "query": "your query",
    "date_range_days": 365,  // Reduce from 730
    "min_results": 10  // Reduce from 15
  }
}
```

**Issue:** Low relevance scores

**Solution:** Refine query with medical terminology:
- ❌ "heart failure drugs"
- ✅ "heart failure pharmacological treatment ACE inhibitors beta blockers"

### 10. Future Enhancements

Planned improvements for the Literature Triage Agent:

- [ ] PubMed API direct integration (no API key required)
- [ ] Custom scoring weight configuration per domain
- [ ] Citation network analysis for related paper discovery
- [ ] Automated alerts for new papers matching saved queries
- [ ] Export to Zotero/Mendeley/EndNote
- [ ] Multi-language support (currently English only)
- [ ] Fine-tuned medical embeddings for better relevance
- [ ] Incremental search mode (add to existing results)

---

## Summary

The Literature Triage Agent successfully integrates into the ResearchFlow workflow as:

1. **Upstream Discovery Layer**: Feeds Stage 2 Literature Pipeline
2. **Intelligent Prioritization**: Reduces information overload with tiered ranking
3. **Evidence Quality Gate**: Ensures downstream agents work with high-quality sources
4. **Modular Service**: Can be called independently or as part of workflow
5. **Observable & Traceable**: Full LangSmith integration for monitoring

**Next Steps:**
1. Deploy to production environment
2. Update orchestrator configuration
3. Integrate with Stage 2 Literature Agent
4. Configure monitoring dashboards
5. Train users on API usage
