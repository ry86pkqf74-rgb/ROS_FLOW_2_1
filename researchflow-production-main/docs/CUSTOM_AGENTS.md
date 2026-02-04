# ResearchFlow: Custom Agents Architecture Guide
## Phase 10: Orchestration & Agent Customization

**Last Updated**: 2026-01-30
**Version**: 1.0

---

## Overview

ResearchFlow's custom agents system provides a pluggable orchestration layer for task decomposition, execution, and synthesis. The CustomDispatcher acts as the central hub coordinating multiple specialized agents based on task type and execution context.

### Key Capabilities

- **Multi-agent orchestration**: Coordinate specialized agents for complex workflows
- **Dynamic task routing**: Route tasks to optimal agents based on capability matching
- **Context preservation**: Maintain execution context across agent boundaries
- **Failure recovery**: Automatic fallback and error handling
- **Monitoring & observability**: Built-in performance tracking and logging

---

## CustomDispatcher Architecture

### Core Components

The CustomDispatcher implements a hub-and-spoke architecture for agent coordination.

**Core Interfaces**:

```typescript
export interface CustomAgent {
  id: string;
  name: string;
  description: string;
  capabilities: AgentCapability[];
  execute(context: ExecutionContext): Promise<ExecutionResult>;
  isAvailable(): boolean;
  requires?: string[];
}

export interface ICustomDispatcher {
  register(agent: CustomAgent): void;
  dispatch(task: Task, context: ExecutionContext): Promise<Result>;
  getMetrics(): DispatcherMetrics;
}
```

**Execution Flow**:

1. Task arrives with requirements
2. Dispatcher analyzes and selects optimal agents
3. Agents execute in configured order (sequence/parallel)
4. Results synthesized and returned

---

## Agent Types & Responsibilities

### 1. Data Extraction Agent

Extracts structured information from documents and papers.

**Capabilities**:
- Document parsing and chunking
- Entity extraction (authors, affiliations, citations)
- Metadata enrichment
- Quality validation

**Configuration**:
```typescript
const dataExtractionAgent = {
  id: 'data-extraction',
  capabilities: [
    { type: 'pdf-parsing', minConfidence: 0.85 },
    { type: 'entity-extraction', languages: ['en'] },
    { type: 'metadata-enrichment', sources: ['arxiv', 'pubmed'] }
  ],
  models: {
    primary: 'claude-opus-4-5-20251101',
    fallback: 'gpt-4o'
  },
  parallelizationFactor: 4,
  taskTimeout: 30000
};
```

### 2. Statistical Analysis Agent

Performs quantitative analysis on research data.

**Capabilities**:
- Statistical test selection
- Hypothesis validation
- Trend analysis
- Uncertainty quantification

**Configuration**:
```typescript
const statsAgent = {
  id: 'statistical-analysis',
  capabilities: [
    { type: 'hypothesis-testing', methods: ['t-test', 'anova', 'kruskal-wallis'] },
    { type: 'correlation-analysis', modes: ['pearson', 'spearman'] },
    { type: 'regression-modeling', types: ['linear', 'logistic'] }
  ],
  models: {
    primary: 'gpt-4o',
    fallback: 'claude-sonnet-4-5-20250929'
  },
  taskTimeout: 60000
};
```

### 3. Manuscript Drafting Agent

Generates draft sections and full manuscript scaffolds.

**Capabilities**:
- Section template generation
- Content synthesis from extractions
- Citation formatting
- Style consistency enforcement

**Configuration**:
```typescript
const draftingAgent = {
  id: 'manuscript-drafting',
  capabilities: [
    { type: 'abstract-generation', maxWords: 250 },
    { type: 'introduction-drafting', style: 'academic' },
    { type: 'methods-section', template: 'standard' },
    { type: 'results-narration', dataSource: 'statistical-analysis' },
    { type: 'discussion-synthesis', citations: true }
  ],
  models: {
    primary: 'claude-opus-4-5-20251101'
  },
  temperature: 0.7,
  maxTokens: 8000
};
```

### 4. Conference Scout Agent

Identifies relevant conferences and submission opportunities.

**Capabilities**:
- Conference database search
- Deadline tracking
- Fit analysis
- Recommendation ranking

---

## Configuration Options

### Global Dispatcher Configuration

```typescript
const dispatcherConfig = {
  execution: {
    parallelismFactor: 4,
    defaultTimeout: 30000,
    retryPolicy: {
      maxAttempts: 3,
      exponentialBackoff: true
    }
  },
  routing: {
    algorithm: 'capability-match',
    fallbackBehavior: 'cascade'
  },
  monitoring: {
    enabled: true,
    metricsInterval: 5000,
    logLevel: 'info'
  },
  cost: {
    trackingEnabled: true,
    maxCostPerTask: 0.50
  }
};
```

### Per-Agent Configuration

```typescript
const agentConfig = {
  models: {
    primary: 'claude-opus-4-5-20251101',
    fallback: 'gpt-4o',
    temperature: 0.3,
    maxTokens: 4000
  },
  timeout: 30000,
  maxRetries: 2,
  priority: 'high',
  minConfidence: 0.85,
  cacheResults: true,
  cacheTTL: 3600000
};
```

---

## Integration Examples

### Example 1: End-to-End Paper Analysis Pipeline

```typescript
import { CustomDispatcher } from '@researchflow/ai-agents';

const dispatcher = new CustomDispatcher({
  execution: { parallelismFactor: 4 }
});

async function analyzePaper(paperId: string) {
  // Extract paper data
  const extraction = await dispatcher.dispatch(
    { type: 'extraction', payload: { paperId } },
    { agentId: 'data-extraction' }
  );
  
  // Run statistical analysis
  const analysis = await dispatcher.dispatch(
    { 
      type: 'statistical_analysis',
      payload: {
        data: extraction.data.dataset,
        hypothesis: extraction.data.hypothesis
      }
    },
    { agentId: 'statistical-analysis' }
  );
  
  // Generate manuscript draft
  const draft = await dispatcher.dispatch(
    {
      type: 'manuscript_drafting',
      payload: {
        extractedData: extraction.data,
        analysisResults: analysis.data
      }
    },
    { agentId: 'manuscript-drafting' }
  );
  
  return { extraction, analysis, draft };
}
```

### Example 2: Parallel Agent Execution

```typescript
async function parallelAnalysis(paperId: string) {
  const [extraction, conferences] = await Promise.all([
    dispatcher.dispatch(
      { type: 'extraction', payload: { paperId } },
      { agentId: 'data-extraction' }
    ),
    dispatcher.dispatch(
      { type: 'conference_scouting', payload: { paperId } },
      { agentId: 'conference-scout' }
    )
  ]);
  
  return { extraction, conferences };
}
```

---

## Best Practices

1. Always check agent availability before dispatching critical tasks
2. Use appropriate timeouts based on task complexity
3. Enable monitoring in production for cost tracking
4. Test custom agents thoroughly before deployment
5. Implement fallback chains for high-criticality tasks
6. Cache results when applicable to reduce costs
7. Monitor token usage for LLM-based agents

---

*Documentation Version: 1.0 | Phase 10 Deliverable*
