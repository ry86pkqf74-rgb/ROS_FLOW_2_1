# Agent Stage 2 Screen - Literature Screening & Deduplication

This agent performs Stage 2 literature screening after initial retrieval. It handles:
1. **Deduplication** - Removes duplicate papers based on DOI, title, and author
2. **Inclusion/Exclusion Criteria** - Applies research-specific screening rules
3. **Study Type Tagging** - Classifies papers by study type (RCT, meta-analysis, cohort, etc.)

## Features

- ✅ **Deterministic Deduplication** - DOI-based and title normalization
- ✅ **Rule-based Screening** - Fast, deterministic criteria application
- ✅ **Study Type Classification** - Pattern-based with extensible rules
- ✅ **AI Bridge Integration** - Ready for LLM-enhanced decisions (optional)
- ✅ **Strict JSON Output** - Structured Pydantic models
- ✅ **Governance Mode Support** - DEMO vs LIVE modes
- ✅ **Contract Compliance** - Follows agent HTTP contract
- ✅ **PHI-Safe Logging** - Only logs IDs and metrics

## API Endpoints

### POST /agents/run/sync
Synchronous screening execution.

**Request:**
```json
{
  "request_id": "req-123",
  "task_type": "STAGE2_SCREEN",
  "mode": "DEMO",
  "domain_id": "clinical",
  "inputs": {
    "papers": [
      {
        "id": "12345",
        "title": "A randomized controlled trial...",
        "abstract": "This study evaluates...",
        "year": 2020,
        "authors": ["Smith J", "Doe J"],
        "doi": "10.1234/example"
      }
    ],
    "criteria": {
      "inclusion": ["diabetes", "metformin"],
      "exclusion": ["pediatric"],
      "required_keywords": [],
      "excluded_keywords": [],
      "study_types_required": [],
      "study_types_excluded": ["case_report"],
      "year_min": 2015,
      "year_max": 2024,
      "require_abstract": true
    },
    "domainId": "clinical",
    "governanceMode": "DEMO"
  }
}
```

**Response:**
```json
{
  "status": "ok",
  "request_id": "req-123",
  "outputs": {
    "included": [
      {
        "paper_id": "12345",
        "title": "A randomized controlled trial...",
        "verdict": "included",
        "reason": "Meets criteria: Inclusion: diabetes; Inclusion: metformin",
        "study_type": "randomized_controlled_trial",
        "confidence": 1.0,
        "matched_criteria": ["Inclusion: diabetes", "Inclusion: metformin"],
        "duplicate_of": null,
        "metadata": {
          "year": 2020,
          "authors": ["Smith J", "Doe J", null],
          "doi": "10.1234/example"
        }
      }
    ],
    "excluded": [],
    "duplicates": [],
    "total_processed": 1,
    "stats": {
      "total_input": 1,
      "duplicates_removed": 0,
      "unique_papers": 1,
      "included_count": 1,
      "excluded_count": 0,
      "study_type_distribution": {
        "randomized_controlled_trial": 1
      }
    }
  },
  "artifacts": [],
  "provenance": {
    "governance_mode": "DEMO",
    "domain_id": "clinical"
  },
  "usage": {
    "duration_ms": 42
  }
}
```

### POST /agents/run/stream
Streaming screening execution with Server-Sent Events (SSE).

Emits progress events:
- `started` - Screening initiated
- `progress` - Progress updates (normalizing, deduplicating, screening)
- `final` - Terminal event with complete outputs

### GET /health
Liveness probe - returns `{"status": "ok"}`

### GET /health/ready
Readiness probe - returns `{"status": "ready"}`

## Screening Criteria

### Inclusion Criteria
- **inclusion** (string[]): Text patterns that must be present in title/abstract
- **required_keywords** (string[]): Keywords that MUST be present

At least one inclusion criterion must match if any are specified.

### Exclusion Criteria
- **exclusion** (string[]): Text patterns that exclude the paper
- **excluded_keywords** (string[]): Keywords that exclude the paper

Any match results in exclusion (fail-fast).

### Study Type Filtering
- **study_types_required** (StudyType[]): Only include these study types
- **study_types_excluded** (StudyType[]): Exclude these study types

### Year Range
- **year_min** (int, optional): Minimum publication year
- **year_max** (int, optional): Maximum publication year

### Abstract Requirement
- **require_abstract** (bool, default: true): Exclude papers without abstracts

## Study Types

Supported study type classifications:
- `randomized_controlled_trial`
- `systematic_review`
- `meta_analysis`
- `cohort_study`
- `case_control_study`
- `cross_sectional_study`
- `case_report`
- `observational_study`
- `review`
- `clinical_trial`
- `unknown`

## Deduplication Logic

Papers are deduplicated using:
1. **DOI** (preferred) - Exact match on DOI
2. **Title + Author + Year** (fallback) - Normalized comparison

Normalization:
- Lowercase conversion
- Punctuation removal
- Whitespace collapse
- First 100 chars of title
- First author name (first 50 chars)

## Development

### Local Testing

```bash
# Navigate to agent directory
cd researchflow-production-main/services/agents/agent-stage2-screen

# Install dependencies
pip install -r requirements.txt

# Run the service
uvicorn app.main:app --port 8000 --reload

# Test sync endpoint
curl -X POST http://localhost:8000/agents/run/sync \
  -H "Content-Type: application/json" \
  -d @test_request.json
```

### Docker Build

```bash
# Build from repo root
docker build -t agent-stage2-screen:latest \
  -f services/agents/agent-stage2-screen/Dockerfile .

# Run container
docker run -p 8000:8000 \
  -e GOVERNANCE_MODE=DEMO \
  -e AI_BRIDGE_URL=http://orchestrator:3001 \
  agent-stage2-screen:latest
```

### Contract Compliance Check

```bash
# From repo root
export AGENT_CONTRACT_TARGETS="http://localhost:8000=STAGE2_SCREEN"
python3 scripts/check-agent-contract.py
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AI_BRIDGE_URL` | `http://localhost:3001` | AI Bridge URL for LLM calls |
| `ORCHESTRATOR_INTERNAL_URL` | `http://localhost:3001` | Orchestrator internal URL |
| `AI_BRIDGE_TOKEN` | - | Authentication token for AI Bridge |
| `WORKER_SERVICE_TOKEN` | - | Worker service token |
| `GOVERNANCE_MODE` | `DEMO` | Governance mode (DEMO/LIVE) |

## Integration

### Docker Compose
The agent is registered in `docker-compose.yml` as `agent-stage2-screen` on port 8000.

### Orchestrator Registration
Added to `AGENT_ENDPOINTS_JSON`:
```json
{
  "agent-stage2-screen": "http://agent-stage2-screen:8000"
}
```

### Task Type Mapping
Map in orchestrator's `ai-router.ts`:
```typescript
const TASK_TYPE_TO_AGENT: Record<string, string> = {
  STAGE2_SCREEN: 'agent-stage2-screen',
  // ...
};
```

## AI Bridge Integration

The agent supports optional AI-enhanced screening via AI Bridge:
- **Provider Mode**: Respects `AI_BRIDGE_PROVIDER_MODE` (mock/shadow/real)
- **Deterministic**: Uses `temperature: 0.0` for consistent decisions
- **Fail-Safe**: Falls back to rule-based screening if AI Bridge unavailable
- **Disabled by Default**: Set `inputs.use_ai: true` to enable

## Logging

PHI-safe structured logging:
- ✅ Request IDs, task types, durations
- ✅ Paper counts, verdict statistics
- ❌ No paper content, titles, or abstracts
- ❌ No full request/response bodies

Log levels:
- `INFO`: Request lifecycle, screening stats
- `DEBUG`: Duplicate detection details
- `WARNING`: Invalid study types, bridge failures
- `ERROR`: Exception handling

## Performance

- **Deduplication**: O(n) with hash-based signature matching
- **Screening**: O(n) with regex pattern matching
- **Typical throughput**: 100-500 papers/second (rule-based)
- **Memory**: ~512MB for 1000 papers

## Future Enhancements

- [ ] AI-enhanced borderline case review
- [ ] Confidence scoring for screening decisions
- [ ] Inter-rater agreement simulation
- [ ] PRISMA flow diagram generation
- [ ] Export to screening management tools (Covidence, Rayyan)
- [ ] Advanced deduplication (fuzzy matching, author disambiguation)

## License

Part of ResearchFlow Production System
