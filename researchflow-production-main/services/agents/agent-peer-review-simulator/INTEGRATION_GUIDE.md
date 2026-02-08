# Peer Review Simulator - Integration Guide

**Date:** 2026-02-08  
**Status:** Files imported, integration pending  
**Priority:** Medium - Enhances manuscript quality validation

## Overview

This guide provides step-by-step instructions for integrating the LangSmith Peer Review Simulator agent into the ResearchFlow production workflow.

## Prerequisites

- [ ] LangSmith account with API access
- [ ] Agent deployed and accessible via LangSmith API
- [ ] Google Docs/Sheets API credentials (for full functionality)
- [ ] Orchestrator service running
- [ ] Worker service with stage_13_internal_review.py

## Integration Steps

### Step 1: Configure LangSmith Credentials

Add the following to your environment configuration:

**File:** `researchflow-production-main/.env`

```bash
# LangSmith Peer Review Simulator
LANGSMITH_PEER_REVIEW_URL=https://api.smith.langchain.com/v1/agents
LANGSMITH_PEER_REVIEW_AGENT_ID=<your-agent-id>
LANGSMITH_API_KEY=<your-api-key>

# Google API (for Google Docs/Sheets integration)
GOOGLE_DOCS_API_KEY=<your-google-api-key>
GOOGLE_SHEETS_API_KEY=<your-google-sheets-api-key>
```

**File:** `researchflow-production-main/services/orchestrator/.env`

```bash
LANGSMITH_PEER_REVIEW_URL=${LANGSMITH_PEER_REVIEW_URL}
LANGSMITH_PEER_REVIEW_AGENT_ID=${LANGSMITH_PEER_REVIEW_AGENT_ID}
LANGSMITH_API_KEY=${LANGSMITH_API_KEY}
```

### Step 2: Update AI Bridge Configuration

**File:** `services/orchestrator/src/config/ai-bridge.ts`

Add the LangSmith agent configuration:

```typescript
export interface LangSmithAgentConfig {
  url: string;
  apiKey: string;
  agentId: string;
  timeout?: number;
}

export const LANGSMITH_AGENTS: Record<string, LangSmithAgentConfig> = {
  'evidence-synthesis': {
    url: process.env.LANGSMITH_EVIDENCE_SYNTHESIS_URL || '',
    apiKey: process.env.LANGSMITH_API_KEY || '',
    agentId: process.env.LANGSMITH_EVIDENCE_SYNTHESIS_AGENT_ID || '',
    timeout: 300000, // 5 minutes
  },
  'peer-review-simulator': {
    url: process.env.LANGSMITH_PEER_REVIEW_URL || '',
    apiKey: process.env.LANGSMITH_API_KEY || '',
    agentId: process.env.LANGSMITH_PEER_REVIEW_AGENT_ID || '',
    timeout: 600000, // 10 minutes (reviews can be lengthy)
  },
  // ... other agents
};
```

### Step 3: Create LangSmith Client Service

**File:** `services/orchestrator/src/services/langsmith-client.ts`

```typescript
import axios, { AxiosInstance } from 'axios';
import { LANGSMITH_AGENTS } from '../config/ai-bridge';

export interface LangSmithInvokeRequest {
  input: Record<string, any>;
  config?: Record<string, any>;
  stream?: boolean;
}

export interface LangSmithInvokeResponse {
  output: Record<string, any>;
  metadata?: Record<string, any>;
}

class LangSmithClient {
  private clients: Map<string, AxiosInstance> = new Map();

  private getClient(agentName: string): AxiosInstance {
    if (!this.clients.has(agentName)) {
      const config = LANGSMITH_AGENTS[agentName];
      if (!config || !config.url || !config.apiKey) {
        throw new Error(`LangSmith agent "${agentName}" not configured`);
      }

      const client = axios.create({
        baseURL: config.url,
        timeout: config.timeout || 300000,
        headers: {
          'Authorization': `Bearer ${config.apiKey}`,
          'Content-Type': 'application/json',
        },
      });

      this.clients.set(agentName, client);
    }

    return this.clients.get(agentName)!;
  }

  async invoke(
    agentName: string,
    input: Record<string, any>,
    config?: Record<string, any>
  ): Promise<LangSmithInvokeResponse> {
    const client = this.getClient(agentName);
    const agentConfig = LANGSMITH_AGENTS[agentName];

    const response = await client.post(`/runs`, {
      agent_id: agentConfig.agentId,
      input,
      config: config || {},
      stream: false,
    });

    return response.data;
  }

  async stream(
    agentName: string,
    input: Record<string, any>,
    config?: Record<string, any>,
    onChunk?: (chunk: any) => void
  ): Promise<LangSmithInvokeResponse> {
    const client = this.getClient(agentName);
    const agentConfig = LANGSMITH_AGENTS[agentName];

    const response = await client.post(`/runs`, {
      agent_id: agentConfig.agentId,
      input,
      config: config || {},
      stream: true,
    }, {
      responseType: 'stream',
    });

    // Process streaming response
    let fullOutput = '';
    for await (const chunk of response.data) {
      if (onChunk) onChunk(chunk);
      fullOutput += chunk.toString();
    }

    return { output: { result: fullOutput } };
  }
}

export const langsmithClient = new LangSmithClient();
```

### Step 4: Add Peer Review Endpoint to Orchestrator

**File:** `services/orchestrator/src/routes/manuscripts.ts`

```typescript
import { langsmithClient } from '../services/langsmith-client';

/**
 * POST /api/manuscripts/:id/peer-review-comprehensive
 * Invoke LangSmith Peer Review Simulator
 */
manuscriptRouter.post('/:id/peer-review-comprehensive', async (req, res) => {
  try {
    const { id } = req.params;
    const {
      personas = ['methodologist', 'statistician', 'ethics_reviewer', 'domain_expert'],
      study_type,
      enable_iteration = true,
      max_cycles = 3,
    } = req.body;

    // Fetch manuscript
    const manuscript = await fetchManuscriptById(id);

    // Invoke LangSmith agent
    const result = await langsmithClient.invoke('peer-review-simulator', {
      manuscript: manuscript.content,
      personas,
      study_type: study_type || manuscript.metadata?.study_type,
      enable_iteration,
      max_cycles,
    });

    res.json({
      success: true,
      manuscript_id: id,
      review: result.output,
      metadata: result.metadata,
    });
  } catch (error) {
    console.error('Peer review comprehensive failed:', error);
    res.status(500).json({
      success: false,
      error: error.message,
    });
  }
});
```

### Step 5: Update Stage 13 Internal Review

**File:** `services/worker/src/workflow_engine/stages/stage_13_internal_review.py`

Add LangSmith integration option:

```python
async def execute(self, context: StageContext) -> StageResult:
    # ... existing code ...
    
    use_langsmith = context.config.get("use_langsmith_peer_review", False)
    
    if use_langsmith:
        # Call LangSmith Peer Review Simulator
        logger.info("Using LangSmith Peer Review Simulator")
        
        personas = context.config.get("personas", [
            "methodologist", 
            "statistician", 
            "ethics_reviewer", 
            "domain_expert"
        ])
        
        langsmith_result = await self.call_langsmith_peer_review(
            context=context,
            manuscript_payload=manuscript_payload,
            personas=personas,
            study_type=context.config.get("study_type", "observational"),
            max_cycles=context.config.get("max_review_cycles", 1)
        )
        
        output["langsmith_peer_review"] = langsmith_result
        output["review_type"] = "comprehensive_langsmith"
    else:
        # Use existing peer-review.service.ts
        logger.info("Using standard peer review service")
        peer_review_result = await self.call_manuscript_service(
            "peer-review",
            "simulateReview",
            {"manuscriptId": context.job_id, ...}
        )
        output["peer_review"] = peer_review_result
        output["review_type"] = "standard"
    
    # ... rest of existing code ...
```

Add method to call LangSmith:

```python
async def call_langsmith_peer_review(
    self,
    context: StageContext,
    manuscript_payload: Dict[str, Any],
    personas: List[str],
    study_type: str,
    max_cycles: int = 1
) -> Dict[str, Any]:
    """Call LangSmith Peer Review Simulator via bridge."""
    bridge_url = self.config.get("bridge_url", "http://localhost:3001")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{bridge_url}/api/langsmith/peer-review-simulator",
                json={
                    "manuscript": manuscript_payload,
                    "personas": personas,
                    "study_type": study_type,
                    "max_cycles": max_cycles,
                },
                timeout=aiohttp.ClientTimeout(total=600)
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"LangSmith call failed: {response.status}")
                    return {"error": f"HTTP {response.status}"}
    except Exception as e:
        logger.error(f"LangSmith peer review failed: {e}")
        return {"error": str(e)}
```

### Step 6: Update Configuration Schema

**File:** `services/worker/src/workflow_engine/config_schema.json`

Add new configuration options:

```json
{
  "stage_13_config": {
    "type": "object",
    "properties": {
      "use_langsmith_peer_review": {
        "type": "boolean",
        "default": false,
        "description": "Use LangSmith Peer Review Simulator instead of standard service"
      },
      "personas": {
        "type": "array",
        "items": {"type": "string"},
        "default": ["methodologist", "statistician", "ethics_reviewer", "domain_expert"],
        "description": "Reviewer personas to simulate"
      },
      "max_review_cycles": {
        "type": "integer",
        "default": 1,
        "minimum": 1,
        "maximum": 3,
        "description": "Maximum number of review-revision cycles"
      },
      "enable_google_docs_output": {
        "type": "boolean",
        "default": false,
        "description": "Generate Google Docs report for comprehensive review"
      }
    }
  }
}
```

### Step 7: Testing

Create integration test:

**File:** `tests/integration/langsmith/test_peer_review_simulator.py`

```python
import pytest
from src.workflow_engine.stages.stage_13_internal_review import InternalReviewAgent

@pytest.mark.integration
async def test_langsmith_peer_review_integration():
    """Test LangSmith Peer Review Simulator integration."""
    
    agent = InternalReviewAgent({
        "bridge_url": "http://localhost:3001",
        "use_langsmith_peer_review": True
    })
    
    context = StageContext(
        job_id="test-job",
        config={
            "use_langsmith_peer_review": True,
            "study_type": "RCT",
            "personas": ["methodologist", "statistician"]
        },
        previous_results={
            10: {  # Stage 10 output
                "manuscript": {
                    "title": "Test Manuscript",
                    "abstract": "Sample abstract...",
                    # ... other sections
                }
            }
        }
    )
    
    result = await agent.execute(context)
    
    assert result.status == "completed"
    assert "langsmith_peer_review" in result.output
    assert result.output["review_type"] == "comprehensive_langsmith"
```

## Verification Checklist

- [ ] Environment variables configured
- [ ] AI Bridge updated with LangSmith configuration
- [ ] LangSmith client service created
- [ ] Orchestrator endpoint added
- [ ] Stage 13 updated with LangSmith option
- [ ] Configuration schema updated
- [ ] Integration tests written and passing
- [ ] Documentation updated
- [ ] Monitoring/logging configured

## Feature Flags

Consider using feature flags for gradual rollout:

```typescript
// In feature-flags.ts
export const FEATURES = {
  LANGSMITH_PEER_REVIEW: process.env.FEATURE_LANGSMITH_PEER_REVIEW === 'true',
  // ... other features
};
```

## Monitoring

Add monitoring for LangSmith calls:

```typescript
import { metrics } from '../monitoring';

// Before LangSmith call
const startTime = Date.now();

// After LangSmith call
metrics.histogram('langsmith.peer_review.duration', Date.now() - startTime);
metrics.increment('langsmith.peer_review.calls');
```

## Rollback Plan

If issues arise:

1. Set `use_langsmith_peer_review: false` in stage configurations
2. Remove or comment out LangSmith endpoint
3. Revert to standard peer-review.service.ts
4. Monitor for errors in logs

## Next Steps

1. Deploy to development environment
2. Test with sample manuscripts
3. Validate output quality
4. Compare with standard peer review
5. Gradual rollout to production
6. Monitor performance and costs
7. Gather user feedback

## Support

- **Issues:** Report in GitHub Issues with `peer-review-simulator` label
- **Documentation:** See [README.md](./README.md)
- **Contact:** Agent fleet coordination team
