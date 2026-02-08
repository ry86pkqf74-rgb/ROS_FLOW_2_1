# Results Interpretation Agent - Workflow Integration Guide

**Agent:** `agent-results-interpretation`  
**Version:** 1.0.0 (LangSmith Import)  
**Date:** 2026-02-08  
**Status:** ✅ Imported, 🚧 Integration Pending

> **Canonical wiring/deploy reference:**
> [`docs/agents/results-interpretation/wiring.md`](../../../docs/agents/results-interpretation/wiring.md)
>
> For deployment truth (compose, router, auth, health, validation), always
> consult the canonical doc above. This file contains aspirational
> integration designs that are **not yet implemented**.

---

## Overview

The Results Interpretation Agent provides comprehensive interpretation of research results across multiple domains (clinical, social science, behavioral, survey). It features a sophisticated multi-worker architecture with parallel processing for literature research, methodology audits, section drafting, and refinement.

---

## Integration Points

### 1. Worker Integration

The agent is **currently LangSmith-hosted** and will be integrated into ResearchFlow's workflow orchestration system.

#### 1.1 Agent Registration

Add to `services/worker/src/agents/__init__.py`:

```python
from typing import Dict, Any
from dataclasses import dataclass

@dataclass
class AgentRegistryEntry:
    name: str
    description: str
    stages: List[int]
    factory: Callable
    agent_class: Optional[type] = None
    langsmith_agent_id: Optional[str] = None

# Add to AGENT_REGISTRY
AGENT_REGISTRY = {
    # ... existing agents
    "results_interpretation": AgentRegistryEntry(
        name="ResultsInterpretationAgent",
        description="Multi-domain research results interpretation with worker delegation",
        stages=[7, 8, 9],  # Results stages
        factory=None,  # LangSmith-hosted, no local factory
        agent_class=None,
        langsmith_agent_id="results-interpretation",
    ),
}
```

---

### 2. Orchestrator Integration

#### 2.1 Service Configuration

Add to `services/worker/src/integrations/orchestration_router.py`:

```python
# In ai-orchestration.json or config
{
  "agents": {
    "langsmith": {
      "agents": {
        "results-interpretation": {
          "name": "Results Interpretation Agent",
          "description": "Multi-domain research results interpretation",
          "endpoint": "https://api.smith.langchain.com/v1/agents/invoke",
          "stages": [7, 8, 9],
          "task_types": ["RESULTS_INTERPRETATION", "STATISTICAL_ANALYSIS"],
          "capabilities": ["clinical", "social_science", "behavioral", "survey"],
          "workers": {
            "literature_research": {
              "name": "Literature_Research_Worker",
              "purpose": "Deep literature search and benchmarking"
            },
            "methodology_audit": {
              "name": "Methodology_Audit_Worker",
              "purpose": "Study design and methods evaluation"
            },
            "section_draft": {
              "name": "Section_Draft_Worker",
              "purpose": "Narrative section generation"
            },
            "draft_refinement": {
              "name": "Draft_Refinement_Worker",
              "purpose": "Quality assurance and refinement"
            }
          },
          "skills": {
            "clinical_trials": {
              "path": "skills/clinical-trials/SKILL.md",
              "triggered_by": ["RCT", "clinical trial", "Phase I-IV"]
            },
            "survey_analysis": {
              "path": "skills/survey-analysis/SKILL.md",
              "triggered_by": ["survey", "questionnaire", "poll"]
            }
          }
        }
      }
    }
  }
}
```

#### 2.2 LangSmith Bridge

Create LangSmith dispatcher in orchestrator:

**Location:** `services/orchestrator/src/dispatchers/langsmith-dispatcher.ts`

```typescript
import axios from 'axios';

interface LangSmithAgentRequest {
  agent_id: string;
  input: {
    results_data?: string;
    study_metadata?: {
      study_type: string;
      domain: string;
      data_types: string;
    };
    spreadsheet_id?: string;
    document_id?: string;
    url?: string;
  };
  config?: {
    use_workers?: string[];  // ['literature_research', 'methodology_audit']
    skip_refinement?: boolean;
  };
}

interface LangSmithAgentResponse {
  report: {
    study_overview: object;
    findings: string;
    statistical_assessment: string;
    bias_limitations: string;
    implications: string;
    literature_context?: string;
    methodology_audit?: string;
    quality_scores: object;
    confidence_rating: {
      level: 'High' | 'Moderate' | 'Low';
      rationale: string;
    };
  };
  google_doc_url: string;
  metadata: {
    workers_used: string[];
    processing_time_ms: number;
  };
}

export class LangSmithDispatcher {
  private apiKey: string;
  private endpoint: string;

  constructor() {
    this.apiKey = process.env.LANGSMITH_API_KEY!;
    this.endpoint = 'https://api.smith.langchain.com/v1/agents/invoke';
  }

  async invokeResultsInterpretation(
    request: LangSmithAgentRequest
  ): Promise<LangSmithAgentResponse> {
    try {
      const response = await axios.post(
        this.endpoint,
        {
          agent_id: 'results-interpretation',
          input: request.input,
          config: request.config || {},
        },
        {
          headers: {
            'Authorization': `Bearer ${this.apiKey}`,
            'Content-Type': 'application/json',
          },
          timeout: 300000,  // 5 min timeout for full pipeline
        }
      );

      return response.data;
    } catch (error) {
      console.error('LangSmith Results Interpretation failed:', error);
      throw new Error(`Results interpretation failed: ${error.message}`);
    }
  }
}
```

---

### 3. API Endpoints

#### 3.1 Create Results Interpretation Route

**Location:** `services/orchestrator/src/routes/results-interpretation.ts`

```typescript
import { Router } from 'express';
import { LangSmithDispatcher } from '../dispatchers/langsmith-dispatcher';

const router = Router();
const dispatcher = new LangSmithDispatcher();

/**
 * POST /api/results/interpret
 * 
 * Interpret research results via Results Interpretation Agent
 */
router.post('/interpret', async (req, res) => {
  try {
    const {
      results_data,
      study_type,
      domain,
      data_types,
      spreadsheet_id,
      document_id,
      url,
      use_workers,
      skip_refinement
    } = req.body;

    // Validate input
    if (!results_data && !spreadsheet_id && !document_id && !url) {
      return res.status(400).json({
        error: 'Must provide one of: results_data, spreadsheet_id, document_id, or url'
      });
    }

    // Dispatch to LangSmith agent
    const result = await dispatcher.invokeResultsInterpretation({
      agent_id: 'results-interpretation',
      input: {
        results_data,
        study_metadata: {
          study_type: study_type || 'unknown',
          domain: domain || 'general',
          data_types: data_types || 'quantitative'
        },
        spreadsheet_id,
        document_id,
        url
      },
      config: {
        use_workers: use_workers || [],
        skip_refinement: skip_refinement || false
      }
    });

    res.json({
      success: true,
      report: result.report,
      google_doc_url: result.google_doc_url,
      metadata: result.metadata
    });
  } catch (error) {
    console.error('Results interpretation error:', error);
    res.status(500).json({
      error: 'Results interpretation failed',
      message: error.message
    });
  }
});

/**
 * GET /api/results/interpret/health
 * 
 * Health check for Results Interpretation Agent
 */
router.get('/health', async (req, res) => {
  try {
    // Ping LangSmith agent
    const response = await axios.get(
      'https://api.smith.langchain.com/v1/agents/health',
      {
        headers: {
          'Authorization': `Bearer ${process.env.LANGSMITH_API_KEY}`
        }
      }
    );

    res.json({
      status: 'healthy',
      agent: 'results-interpretation',
      langsmith_status: response.data.status
    });
  } catch (error) {
    res.status(503).json({
      status: 'unhealthy',
      error: error.message
    });
  }
});

export default router;
```

#### 3.2 Register Route in Main App

**Location:** `services/orchestrator/src/app.ts`

```typescript
import resultsInterpretationRouter from './routes/results-interpretation';

// ... other imports

app.use('/api/results', resultsInterpretationRouter);
```

---

### 4. Workflow Stage Mapping

The Results Interpretation Agent aligns with **Stages 7-9** of the ResearchFlow pipeline:

| Stage | Name | Agent Role |
|-------|------|-----------|
| **7** | Results Analysis | Primary: Analyze quantitative/qualitative results |
| **8** | Results Synthesis | Secondary: Interpret synthesized findings |
| **9** | Results Refinement | Validation: Review and refine interpretations |

#### Integration with Stage Agents

**Location:** `services/worker/src/workflow_engine/stages/`

```python
# In stage_07_results_analysis.py
from src.integrations.orchestration_router import OrchestrationRouter

class Stage07ResultsAnalysisAgent(LangGraphBaseAgent):
    def __init__(self, llm_bridge: Any, checkpointer: Optional[Any] = None):
        super().__init__(
            llm_bridge=llm_bridge,
            stages=[7],
            agent_id='results_analysis',
            checkpointer=checkpointer,
        )
        self.orchestration = OrchestrationRouter()

    async def analyze_results_node(self, state: AgentState) -> AgentState:
        """Analyze results using Results Interpretation Agent."""
        
        # Extract results data from state
        results_data = state.get('results_data', '')
        
        # Get LangSmith agent config
        agent_config = self.orchestration.get_langsmith_agent('results-interpretation')
        
        if agent_config:
            # Dispatch to Results Interpretation Agent
            response = await self._call_langsmith_agent(
                agent_config,
                {
                    'results_data': results_data,
                    'study_metadata': {
                        'study_type': state.get('study_type', 'unknown'),
                        'domain': state.get('domain', 'general')
                    },
                    'use_workers': ['literature_research', 'methodology_audit'],
                    'skip_refinement': False
                }
            )
            
            # Update state with interpretation
            state['interpretation_report'] = response['report']
            state['google_doc_url'] = response['google_doc_url']
            state['current_output'] = response['report']['findings']
        
        return state
```

---

### 5. Environment Configuration

#### 5.1 Required Environment Variables

Add to `.env` or deployment config:

```bash
# Results Interpretation Agent
LANGSMITH_API_KEY=your_langsmith_api_key_here
LANGCHAIN_PROJECT=researchflow-results-interpretation
LANGCHAIN_TRACING_V2=true
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com

# Google Workspace (required for report generation)
GOOGLE_DOCS_API_KEY=your_google_docs_api_key
GOOGLE_SHEETS_API_KEY=your_google_sheets_api_key

# Tavily Search (for Literature_Research_Worker)
TAVILY_API_KEY=your_tavily_api_key
```

#### 5.2 Development Mode (Mock Interpretation)

For development without LangSmith API:

```bash
# .env.development
LANGSMITH_API_KEY=  # Empty = use mock results
USE_MOCK_INTERPRETATION=true
```

The orchestrator will automatically fallback to mock interpretation results for testing.

---

### 6. Testing

#### 6.1 Integration Test

**Location:** `tests/integration/test_results_interpretation.py`

```python
import pytest
from services.orchestrator.src.dispatchers.langsmith_dispatcher import LangSmithDispatcher

@pytest.mark.integration
async def test_results_interpretation_clinical():
    """Test clinical trial results interpretation."""
    dispatcher = LangSmithDispatcher()
    
    result = await dispatcher.invokeResultsInterpretation({
        'agent_id': 'results-interpretation',
        'input': {
            'results_data': 'RCT with 500 participants, primary endpoint: 30% relative risk reduction (p=0.023, 95% CI: 10-45%)',
            'study_metadata': {
                'study_type': 'RCT',
                'domain': 'clinical',
                'data_types': 'quantitative'
            }
        },
        'config': {
            'use_workers': ['literature_research', 'methodology_audit'],
            'skip_refinement': False
        }
    })
    
    assert result['report']['findings']
    assert result['report']['confidence_rating']['level'] in ['High', 'Moderate', 'Low']
    assert result['google_doc_url'].startswith('https://docs.google.com')
    assert 'literature_research' in result['metadata']['workers_used']
```

#### 6.2 E2E Workflow Test

```bash
# Test full pipeline: Evidence → Interpretation → Manuscript
pytest tests/e2e/test_evidence_to_manuscript.py -v
```

---

### 7. Monitoring & Observability

#### 7.1 LangSmith Tracing

All agent invocations are automatically traced in LangSmith:

- **Project**: `researchflow-results-interpretation`
- **Traces**: View at https://smith.langchain.com
- **Metrics**: Token usage, latency, worker delegation patterns

#### 7.2 Performance Metrics

Expected performance benchmarks:

| Scenario | Processing Time | Workers Used |
|----------|----------------|--------------|
| Simple interpretation (direct data) | 30-60s | Section_Draft, Draft_Refinement |
| Clinical trial (full pipeline) | 120-180s | All 4 workers |
| Survey data with literature context | 90-150s | Literature_Research, Section_Draft, Draft_Refinement |

---

## Usage Examples

### Example 1: Clinical Trial Results

```typescript
const result = await fetch('http://localhost:3000/api/results/interpret', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    results_data: 'Phase III RCT, N=850, primary endpoint HR=0.72 (95% CI 0.58-0.89, p=0.003)',
    study_type: 'RCT',
    domain: 'clinical',
    use_workers: ['literature_research', 'methodology_audit']
  })
});

const interpretation = await result.json();
console.log(interpretation.report.findings);
console.log(interpretation.google_doc_url);
```

### Example 2: Survey Data from Google Sheets

```typescript
const result = await fetch('http://localhost:3000/api/results/interpret', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    spreadsheet_id: '1abc123...',
    study_type: 'survey',
    domain: 'social_science',
    use_workers: []  // No deep workers needed for simple survey
  })
});
```

### Example 3: Observational Study from URL

```typescript
const result = await fetch('http://localhost:3000/api/results/interpret', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    url: 'https://example.com/cohort-study-results.pdf',
    study_type: 'cohort',
    domain: 'clinical',
    use_workers: ['methodology_audit']
  })
});
```

---

## Roadmap

### Phase 1: LangSmith Integration (Current)
- [x] Import agent and workers
- [x] Create briefing documentation
- [ ] Configure orchestration router
- [ ] Add API endpoints
- [ ] Integration tests

### Phase 2: Workflow Alignment
- [ ] Map to Stages 7-9
- [ ] Connect to `agent-evidence-synthesis` output
- [ ] Feed into `agent-clinical-manuscript`
- [ ] E2E workflow testing

### Phase 3: Containerization (Future)
- [ ] Create Dockerfile
- [ ] Add to docker-compose.yml
- [ ] Local deployment option
- [ ] Health check endpoints

### Phase 4: Optimization
- [ ] Cache literature searches
- [ ] Optimize worker delegation logic
- [ ] Parallel section processing improvements
- [ ] Performance benchmarking

---

## Troubleshooting

### Issue: LangSmith API timeout
**Solution:** Increase timeout in dispatcher (currently 5 min), or enable `skip_refinement: true` for faster processing

### Issue: Google Docs creation fails
**Solution:** Verify Google Workspace API credentials and scopes

### Issue: Worker delegation not working
**Solution:** Check worker names in `use_workers` array match exact worker IDs

### Issue: Low-quality interpretation
**Solution:** Ensure `skip_refinement: false` and provide sufficient `results_data` detail

---

## Support

- **Documentation**: [AGENT_RESULTS_INTERPRETATION_BRIEFING.md](../AGENT_RESULTS_INTERPRETATION_BRIEFING.md)
- **Agent Files**: `services/agents/agent-results-interpretation/`
- **Issues**: GitHub Issues with label `agent:results-interpretation`

---

**STATUS**: ✅ Documentation Complete | 🚧 Integration Pending  
**Last Updated**: 2026-02-08
