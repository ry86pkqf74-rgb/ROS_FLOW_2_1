# [ROS-96] Custom Agent Dispatcher Implementation - Phase 5.2

## Task Assignment: Cursor/GPT-4

## Overview
Implement CustomAgentDispatcher class for routing requests to LangGraph agents via CUSTOM tier.

## Deliverables

### Create `packages/ai-router/src/dispatchers/custom.ts`:

```typescript
import { Dispatcher, DispatchResult } from '../types';
import { Counter, Histogram } from 'prom-client';

const AGENT_ENDPOINTS = {
  manuscript: 'http://worker:8000/agents/manuscript',
  analysis: 'http://worker:8000/agents/analysis',
  dataprep: 'http://worker:8000/agents/dataprep',
  irb: 'http://worker:8000/agents/irb',
  quality: 'http://worker:8000/agents/quality'
};

export class CustomAgentDispatcher implements Dispatcher {
  private requestCounter: Counter;
  private latencyHistogram: Histogram;

  async dispatch(request: DispatchRequest): Promise<DispatchResult> {
    const agentName = this.mapTaskToAgent(request.taskType);
    const endpoint = AGENT_ENDPOINTS[agentName];
    
    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request)
      });
      
      this.requestCounter.inc({ agent: agentName, status: 'success' });
      return { success: true, data: await response.json() };
    } catch (error) {
      // Fallback to FRONTIER tier
      return this.fallbackToFrontier(request);
    }
  }
  
  private mapTaskToAgent(taskType: string): string {
    // Map task types to agent names
  }
  
  private async fallbackToFrontier(request: DispatchRequest): Promise<DispatchResult> {
    // Implement fallback logic
  }
}
```

## Success Criteria
- [ ] CustomAgentDispatcher class created
- [ ] Task-to-agent mapping implemented
- [ ] Prometheus metrics added
- [ ] Fallback to FRONTIER tier works
- [ ] Unit tests pass

## Commit Instructions
After completing, run:
```bash
git add packages/ai-router/src/dispatchers/custom.ts
git commit -m "feat(ai-router): Add CustomAgentDispatcher for CUSTOM tier [ROS-96]

Co-Authored-By: Cursor <noreply@cursor.com>"
git push origin main
```
