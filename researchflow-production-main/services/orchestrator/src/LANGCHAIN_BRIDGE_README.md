# LangChain Node.js Integration Bridge

## Overview

The LangChain Bridge (`langchain-bridge.ts`) is a production-ready TypeScript module that connects the Node.js orchestrator service to Python worker's LangGraph agents. It provides a comprehensive abstraction layer for:

- HTTP-based agent execution
- Real-time progress tracking via WebSocket
- Automatic retry with exponential backoff
- Circuit breaker pattern for fault tolerance
- Event-driven progress monitoring
- Type-safe agent definitions and responses

**Status**: ROS-107, ROS-108 - Track A LangChain Integration

---

## Table of Contents

1. [Architecture](#architecture)
2. [Installation & Setup](#installation--setup)
3. [Quick Start](#quick-start)
4. [API Reference](#api-reference)
5. [Core Features](#core-features)
6. [Configuration](#configuration)
7. [Error Handling](#error-handling)
8. [Examples](#examples)
9. [Testing](#testing)
10. [Production Checklist](#production-checklist)

---

## Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                   Node.js Orchestrator                       │
├─────────────────────────────────────────────────────────────┤
│  Express Routes / API Handlers                               │
│         │                                                     │
│         ▼                                                     │
│  LangChainBridge (langchain-bridge.ts)                       │
│  ├─ HTTP Client (runAgent, getStatus, cancelTask)           │
│  ├─ WebSocket Client (subscribeToProgress)                  │
│  ├─ Circuit Breaker (fault tolerance)                       │
│  ├─ Retry Logic (exponential backoff)                       │
│  └─ Event Emitter (progress events)                         │
│         │                                                     │
│         ├────────────────────┬─────────────────────┐        │
│         ▼                    ▼                     ▼        │
│      HTTP/REST        WebSocket Stream      Event Stream   │
│         │                    │                     │        │
│         ├────────────────────┼─────────────────────┤        │
│         │                    │                     │        │
│         ▼                    ▼                     ▼        │
└─────────────────────────────────────────────────────────────┘
          │                    │                     │
          │                    │                     │
          ▼                    ▼                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Python Worker Service                           │
├─────────────────────────────────────────────────────────────┤
│  FastAPI Server                                              │
│  ├─ /api/langchain/agents/run (POST)                        │
│  ├─ /api/langchain/agents/{id}/status (GET)                 │
│  ├─ /api/langchain/agents/{id}/cancel (POST)                │
│  ├─ /api/langchain/agents/{id}/progress (WebSocket)         │
│  └─ /api/langchain/health (GET)                             │
│         │                                                     │
│         ▼                                                     │
│  LangGraph Agent Orchestrator                               │
│  ├─ Research Analyzer Agent                                 │
│  ├─ Literature Reviewer Agent                               │
│  ├─ Data Processor Agent                                    │
│  ├─ Manuscript Generator Agent                              │
│  ├─ Guideline Extractor Agent                               │
│  └─ Custom Agents                                           │
│         │                                                     │
│         ▼                                                     │
│  LLM Integration Layer                                      │
│  ├─ OpenAI (GPT-4, GPT-3.5)                                 │
│  ├─ Anthropic (Claude)                                      │
│  ├─ LangSmith Monitoring                                    │
│  └─ Composio Tool Integration                               │
│         │                                                     │
│         ▼                                                     │
│  Vector Store (ChromaDB)                                    │
│  Knowledge Base & Embeddings                                │
└─────────────────────────────────────────────────────────────┘
```

### Key Classes

#### `LangChainBridge`
Main service class that orchestrates agent execution.

**Responsibilities**:
- HTTP communication with worker API
- WebSocket connection management
- Circuit breaker state management
- Event emission for monitoring
- Task lifecycle management

#### `LangChainCircuitBreaker`
Implements Circuit Breaker pattern with states: CLOSED, OPEN, HALF_OPEN.

**Features**:
- Automatic failure detection
- Configurable failure/success thresholds
- Exponential timeout resets
- State transition logging

#### `withRetry`
Utility function for automatic retry with exponential backoff.

**Features**:
- Configurable max attempts
- Exponential backoff with jitter
- Custom retry logic
- Timeout handling

---

## Installation & Setup

### 1. Prerequisites

The following are already included in the orchestrator's `package.json`:

```json
{
  "dependencies": {
    "ws": "^8.16.0"
  }
}
```

### 2. Update Worker Dependencies

The Python worker service requires LangChain and related packages. These have been added to `requirements.txt`:

```bash
# LangGraph Agent Dependencies
langchain>=0.3.0
langchain-anthropic>=0.2.0
langchain-openai>=0.2.0
langgraph>=0.2.0
langgraph-checkpoint>=0.2.0
anthropic>=0.34.0

# Composio + LangSmith Integration
composio-core>=0.4.3
composio-langchain>=0.4.3
langsmith>=0.1.0
langchain-community>=0.2.1

# Vector Database
chromadb>=0.4.0
```

### 3. Environment Variables

Configure these environment variables in your `.env` files:

```bash
# Worker Service URLs
WORKER_CALLBACK_URL=http://worker:8000
WORKER_WS_URL=ws://worker:8000

# API Timeout (milliseconds)
LANGCHAIN_API_TIMEOUT=30000

# Retry Configuration
LANGCHAIN_RETRY_MAX_ATTEMPTS=3
LANGCHAIN_RETRY_INITIAL_DELAY=1000

# Circuit Breaker Configuration
LANGCHAIN_CIRCUIT_BREAKER_ENABLED=true
LANGCHAIN_CIRCUIT_FAILURE_THRESHOLD=5
LANGCHAIN_CIRCUIT_SUCCESS_THRESHOLD=2
LANGCHAIN_CIRCUIT_RESET_TIMEOUT=60000
```

### 4. Import and Initialize

```typescript
import { getLangChainBridge, AgentType } from './langchain-bridge';

// Get singleton instance
const bridge = getLangChainBridge();

// Or create with custom URLs
const customBridge = getLangChainBridge(
  'http://custom-worker:8000',
  'ws://custom-worker:8000'
);
```

---

## Quick Start

### Basic Agent Execution

```typescript
import { getLangChainBridge, AgentType } from './langchain-bridge';

const bridge = getLangChainBridge();

// Run an agent
const response = await bridge.runAgent(
  AgentType.ResearchAnalyzer,
  {
    title: 'COVID-19 vaccines',
    keywords: ['mRNA', 'vaccination'],
    maxResults: 50
  }
);

console.log(`Task started: ${response.taskId}`);
console.log(`Status: ${response.status}`);
```

### Real-time Progress Monitoring

```typescript
// Subscribe to progress updates
const unsubscribe = bridge.subscribeToProgress(taskId, (event) => {
  if (event.type === 'progress') {
    console.log(`${event.data.progress?.percentage}%`);
  }
  if (event.type === 'error') {
    console.error(event.data.error?.message);
  }
  if (event.type === 'completed') {
    console.log('Task completed!');
    unsubscribe(); // Stop listening
  }
});
```

### Task Status Polling

```typescript
const status = await bridge.getAgentStatus(taskId);

console.log({
  taskId: status.taskId,
  status: status.status,
  progress: status.progress.percentage,
  executionTime: status.executionTimeMs,
  result: status.result,
  error: status.error
});
```

### Task Cancellation

```typescript
const result = await bridge.cancelTask(taskId);
console.log(`Task ${result.taskId} cancelled`);
```

---

## API Reference

### Enums

#### `AgentType`

Supported agent types:

```typescript
enum AgentType {
  ResearchAnalyzer = 'research_analyzer',
  LiteratureReviewer = 'literature_reviewer',
  DataProcessor = 'data_processor',
  ManuscriptGenerator = 'manuscript_generator',
  GuidelineExtractor = 'guideline_extractor',
  CustomAgent = 'custom_agent'
}
```

#### `TaskStatus`

Task lifecycle states:

```typescript
enum TaskStatus {
  Pending = 'pending',
  Running = 'running',
  Paused = 'paused',
  Completed = 'completed',
  Failed = 'failed',
  Cancelled = 'cancelled'
}
```

#### `TaskPriority`

Execution priority levels:

```typescript
enum TaskPriority {
  Low = 'low',
  Normal = 'normal',
  High = 'high',
  Critical = 'critical'
}
```

### Interfaces

#### `AgentTaskInput`

Input for agent execution:

```typescript
interface AgentTaskInput {
  taskId?: string;
  agentType: AgentType | string;
  data: Record<string, unknown>;
  params?: {
    timeout?: number;
    maxIterations?: number;
    temperature?: number;
    model?: string;
    streaming?: boolean;
  };
  metadata?: {
    userId?: string;
    projectId?: string;
    requestId?: string;
    tags?: string[];
  };
  priority?: TaskPriority;
  callbackUrl?: string;
}
```

#### `AgentTaskResponse`

Response from agent execution:

```typescript
interface AgentTaskResponse {
  taskId: string;
  status: TaskStatus;
  agentType: AgentType | string;
  result?: Record<string, unknown>;
  error?: string;
  errorCode?: string;
  metadata?: {
    startTime?: string;
    endTime?: string;
    executionTimeMs?: number;
    iterationCount?: number;
    tokenCount?: number;
  };
  progress?: {
    current: number;
    total: number;
    percentage: number;
    message: string;
  };
  timestamp: string;
}
```

#### `ProgressEvent`

WebSocket progress event:

```typescript
interface ProgressEvent {
  taskId: string;
  type: 'progress' | 'log' | 'checkpoint' | 'error' | 'completed';
  data: {
    message?: string;
    progress?: {
      current: number;
      total: number;
      percentage: number;
    };
    log?: string;
    checkpoint?: Record<string, unknown>;
    error?: {
      message: string;
      code: string;
    };
  };
  timestamp: string;
}
```

### Methods

#### `runAgent(agentType, input, options?)`

Run a LangGraph agent.

**Parameters**:
- `agentType`: Type of agent to run
- `input`: Input data for the agent
- `options.timeout`: Request timeout in milliseconds
- `options.priority`: Task priority level
- `options.metadata`: Task metadata

**Returns**: `Promise<AgentTaskResponse>`

**Example**:
```typescript
const response = await bridge.runAgent(
  AgentType.ResearchAnalyzer,
  { title: 'Topic', keywords: [] },
  { timeout: 60000, priority: TaskPriority.High }
);
```

---

#### `getAgentStatus(taskId)`

Get current status of a task.

**Parameters**:
- `taskId`: Task identifier

**Returns**: `Promise<AgentStatusResponse>`

**Example**:
```typescript
const status = await bridge.getAgentStatus(taskId);
console.log(status.progress.percentage);
```

---

#### `subscribeToProgress(taskId, callback)`

Subscribe to real-time progress updates.

**Parameters**:
- `taskId`: Task identifier
- `callback`: Function called for each progress event

**Returns**: Unsubscribe function

**Example**:
```typescript
const unsubscribe = bridge.subscribeToProgress(taskId, (event) => {
  console.log(`Progress: ${event.data.progress?.percentage}%`);
});

// Later
unsubscribe();
```

---

#### `cancelTask(taskId)`

Cancel a running task.

**Parameters**:
- `taskId`: Task identifier

**Returns**: `Promise<{ taskId: string; status: TaskStatus }>`

**Example**:
```typescript
const result = await bridge.cancelTask(taskId);
```

---

#### `healthCheck()`

Check bridge and worker health.

**Returns**: `Promise<HealthCheckResponse>`

**Example**:
```typescript
const health = await bridge.healthCheck();
if (health.healthy) {
  console.log(`Latency: ${health.latencyMs}ms`);
}
```

---

#### `getCircuitBreakerStatus()`

Get circuit breaker status.

**Returns**: `CircuitBreakerStatus`

**Example**:
```typescript
const status = bridge.getCircuitBreakerStatus();
console.log(`State: ${status.state}`);
console.log(`Failures: ${status.failures}`);
```

---

#### `close()`

Close all connections and cleanup resources.

**Example**:
```typescript
bridge.close();
```

---

## Core Features

### 1. Retry Logic with Exponential Backoff

Automatic retry with exponential backoff for transient failures:

```typescript
import { withRetry } from './langchain-bridge';

const result = await withRetry(
  async () => {
    // Your async operation
    return await someOperation();
  },
  {
    maxAttempts: 3,
    initialDelayMs: 1000,
    maxDelayMs: 32000,
    backoffMultiplier: 2,
    shouldRetry: (error) => {
      // Custom retry logic
      return error.code === 'ECONNREFUSED';
    }
  }
);
```

### 2. Circuit Breaker Pattern

Prevents cascading failures with automatic state transitions:

```
┌──────────┐     failures >= threshold     ┌──────────┐
│          │ ──────────────────────────────► │          │
│ CLOSED   │                               │   OPEN    │
│          │ ◄────────────────────────────── │          │
└──────────┘     successes >= threshold    └──────────┘
      │                                          │
      │ after reset timeout                      │
      └─────────────────────────────────────────►
                                            ┌──────────┐
                                            │          │
                                            │HALF_OPEN │
                                            │          │
                                            └──────────┘
```

**Configuration**:
- `FAILURE_THRESHOLD`: 5 failures trigger OPEN
- `SUCCESS_THRESHOLD`: 2 successes move CLOSED
- `RESET_TIMEOUT`: 60 seconds before attempting recovery

### 3. WebSocket Progress Streaming

Real-time progress updates with automatic reconnection:

```typescript
bridge.subscribeToProgress(taskId, (event) => {
  switch (event.type) {
    case 'progress':
      // Update progress bar
      console.log(`${event.data.progress?.percentage}%`);
      break;
    case 'checkpoint':
      // Save checkpoint
      console.log('Checkpoint:', event.data.checkpoint);
      break;
    case 'error':
      // Handle error
      console.error(event.data.error?.message);
      break;
    case 'completed':
      // Task finished
      console.log('Done!');
      break;
  }
});
```

### 4. Event-Driven Monitoring

Listen to bridge events for system-wide monitoring:

```typescript
bridge.on('agent:started', ({ taskId, agentType }) => {
  console.log(`Started ${agentType}`);
});

bridge.on('agent:completed', ({ taskId }) => {
  console.log(`Completed ${taskId}`);
});

bridge.on('agent:error', ({ agentType, error }) => {
  console.error(`Error in ${agentType}: ${error}`);
});

bridge.on('progress:connected', ({ taskId }) => {
  console.log(`WebSocket connected for ${taskId}`);
});

bridge.on('progress:disconnected', ({ taskId }) => {
  console.log(`WebSocket disconnected for ${taskId}`);
});
```

### 5. Type-Safe Agent Definitions

Full TypeScript support with auto-completion:

```typescript
// IDE provides auto-completion for agent types
const response = await bridge.runAgent(
  AgentType.ResearchAnalyzer, // Type-safe enum
  {
    title: 'Topic',
    keywords: ['key1', 'key2'] // Typed input
  }
);

// Result is also typed
const status: AgentStatusResponse = await bridge.getAgentStatus(
  response.taskId
);
```

---

## Configuration

### Environment Variables

```bash
# Worker Service Connection
WORKER_CALLBACK_URL=http://worker:8000
WORKER_WS_URL=ws://worker:8000

# API Timeout (ms)
LANGCHAIN_API_TIMEOUT=30000

# Retry Configuration
LANGCHAIN_RETRY_MAX_ATTEMPTS=3
LANGCHAIN_RETRY_INITIAL_DELAY=1000

# Circuit Breaker
LANGCHAIN_CIRCUIT_BREAKER_ENABLED=true
LANGCHAIN_CIRCUIT_FAILURE_THRESHOLD=5
LANGCHAIN_CIRCUIT_SUCCESS_THRESHOLD=2
LANGCHAIN_CIRCUIT_RESET_TIMEOUT=60000
```

### Runtime Configuration

```typescript
// Custom initialization
const bridge = new LangChainBridge(
  'http://custom-worker:8000',
  'ws://custom-worker:8000'
);

// Or use singleton with environment defaults
const bridge = getLangChainBridge();
```

---

## Error Handling

### Common Error Scenarios

#### 1. Network Errors (Auto-Retry)

```typescript
try {
  const response = await bridge.runAgent(agentType, data);
} catch (error) {
  if (error.message.includes('ECONNREFUSED')) {
    // Connection refused, will be retried automatically
    console.log('Service temporarily unavailable');
  }
}
```

#### 2. Circuit Breaker Open

```typescript
try {
  const response = await bridge.runAgent(agentType, data);
} catch (error) {
  if (error.message.includes('Circuit breaker open')) {
    // Service is in a bad state
    const cbStatus = bridge.getCircuitBreakerStatus();
    console.log(`Retry after ${cbStatus.nextAttemptAt}`);
  }
}
```

#### 3. Timeout Errors

```typescript
try {
  const response = await bridge.runAgent(agentType, data, {
    timeout: 120000 // 2 minutes
  });
} catch (error) {
  if (error.statusCode === 408) {
    // Request timeout
    console.log('Agent execution took too long');
  }
}
```

#### 4. Progress Event Errors

```typescript
bridge.subscribeToProgress(taskId, (event) => {
  if (event.type === 'error') {
    const { message, code } = event.data.error!;
    console.error(`Agent error: ${message} (${code})`);

    // Handle specific error codes
    switch (code) {
      case 'INVALID_INPUT':
        // Fix input data
        break;
      case 'RATE_LIMIT':
        // Implement backoff
        break;
      case 'MODEL_ERROR':
        // Try different model
        break;
    }
  }
});
```

---

## Examples

See `/langchain-bridge.example.ts` for 10 comprehensive examples:

1. **Basic Agent Execution** - Simple agent run with polling
2. **Real-time Progress Monitoring** - WebSocket streaming
3. **Multiple Agents in Parallel** - Concurrent execution
4. **Error Handling and Retries** - Fault tolerance
5. **Task Cancellation** - Timeout-based cancellation
6. **Health Checks and Circuit Breaker** - Monitoring
7. **Event Listener Pattern** - EventEmitter usage
8. **Express Integration** - REST API handlers
9. **Advanced Progress Handling** - Metrics and estimation
10. **Cleanup and Resource Management** - Proper shutdown

### Run Examples

```bash
# Import specific example
import { example1_basicAgentExecution } from './langchain-bridge.example';

// Execute
await example1_basicAgentExecution();
```

---

## Testing

### Unit Tests

```typescript
import { describe, it, expect, beforeEach, afterEach } from '@jest/globals';
import { getLangChainBridge, resetLangChainBridge, AgentType, TaskStatus } from './langchain-bridge';

describe('LangChainBridge', () => {
  let bridge: any;

  beforeEach(() => {
    resetLangChainBridge();
    bridge = getLangChainBridge();
  });

  afterEach(() => {
    bridge.close();
    resetLangChainBridge();
  });

  it('should run an agent successfully', async () => {
    const response = await bridge.runAgent(AgentType.ResearchAnalyzer, {
      title: 'Test',
      keywords: ['test']
    });

    expect(response.taskId).toBeDefined();
    expect(response.status).toBe(TaskStatus.Pending);
  });

  it('should get agent status', async () => {
    const response = await bridge.runAgent(AgentType.DataProcessor, {
      datasetId: 'test'
    });

    const status = await bridge.getAgentStatus(response.taskId);
    expect(status.taskId).toBe(response.taskId);
    expect(status.status).toBeDefined();
    expect(status.progress.percentage).toBeDefined();
  });

  it('should handle errors gracefully', async () => {
    expect(
      bridge.runAgent('invalid-agent', {})
    ).rejects.toThrow();
  });

  it('should subscribe to progress', (done) => {
    bridge.runAgent(AgentType.ResearchAnalyzer, { title: 'Test' })
      .then((response: any) => {
        const unsubscribe = bridge.subscribeToProgress(
          response.taskId,
          (event: any) => {
            expect(event.type).toBeDefined();
            expect(event.taskId).toBe(response.taskId);
            unsubscribe();
            done();
          }
        );
      });
  });

  it('should cancel a task', async () => {
    const response = await bridge.runAgent(AgentType.LiteratureReviewer, {
      topic: 'Test'
    });

    const result = await bridge.cancelTask(response.taskId);
    expect(result.taskId).toBe(response.taskId);
    expect(result.status).toBe(TaskStatus.Cancelled);
  });

  it('should perform health check', async () => {
    const health = await bridge.healthCheck();
    expect(health.healthy).toBeDefined();
    expect(health.latencyMs).toBeDefined();
  });

  it('should maintain circuit breaker status', () => {
    const status = bridge.getCircuitBreakerStatus();
    expect(status.state).toBeDefined();
    expect(['CLOSED', 'OPEN', 'HALF_OPEN']).toContain(status.state);
  });
});
```

### Integration Tests

```typescript
// Test with actual worker service
describe('LangChainBridge Integration', () => {
  it('should execute full agent workflow', async () => {
    const bridge = getLangChainBridge();

    try {
      // Start agent
      const response = await bridge.runAgent(
        AgentType.ManuscriptGenerator,
        { title: 'Test Manuscript' }
      );

      // Monitor progress
      let completed = false;
      const unsubscribe = bridge.subscribeToProgress(
        response.taskId,
        (event) => {
          if (event.type === 'completed') {
            completed = true;
          }
        }
      );

      // Wait for completion
      await new Promise(resolve => {
        const checkInterval = setInterval(() => {
          if (completed) {
            clearInterval(checkInterval);
            unsubscribe();
            resolve(null);
          }
        }, 100);
      });

      // Verify final status
      const finalStatus = await bridge.getAgentStatus(response.taskId);
      expect(finalStatus.status).toBe(TaskStatus.Completed);
      expect(finalStatus.result).toBeDefined();
    } finally {
      bridge.close();
    }
  });
});
```

---

## Production Checklist

- [ ] Environment variables configured correctly
- [ ] Worker service health checked and running
- [ ] Circuit breaker thresholds tuned for your workload
- [ ] Retry settings appropriate for network conditions
- [ ] WebSocket URL accessible from Node.js service
- [ ] Error handling implemented for all error scenarios
- [ ] Progress event listeners properly unsubscribed
- [ ] Resource cleanup on process shutdown
- [ ] Logging configured for monitoring
- [ ] Health check endpoint monitored
- [ ] Circuit breaker status monitored
- [ ] Database connections persistent across retries
- [ ] Rate limiting configured on worker service
- [ ] Timeout values appropriate for agent execution time
- [ ] Security: API endpoints authenticated if needed
- [ ] Load testing completed
- [ ] Documentation updated for operations team
- [ ] Alerting configured for circuit breaker OPEN state
- [ ] Metrics exported for observability
- [ ] Graceful shutdown procedures tested

---

## Support and Troubleshooting

### High Latency

```typescript
const health = await bridge.healthCheck();
if (health.latencyMs > 5000) {
  console.warn('High latency detected', health.latencyMs);
  // Consider queue or retry strategy
}
```

### Circuit Breaker Open

```typescript
const cbStatus = bridge.getCircuitBreakerStatus();
if (cbStatus.state === 'OPEN') {
  console.error('Circuit breaker is open');
  console.log('Last failure:', cbStatus.lastFailure);
  console.log('Retry after:', cbStatus.nextAttemptAt);
}
```

### WebSocket Connection Issues

```typescript
bridge.on('progress:connection-failed', ({ taskId, error }) => {
  console.error(`Failed to connect for task ${taskId}: ${error}`);
  // Fall back to polling instead
});
```

### Memory Leaks

Always unsubscribe from progress:

```typescript
const unsubscribe = bridge.subscribeToProgress(taskId, callback);
// Later
unsubscribe();

// Or on shutdown
bridge.close();
resetLangChainBridge();
```

---

## Version History

- **v1.0.0** (2026-01-30)
  - Initial implementation
  - HTTP and WebSocket clients
  - Circuit breaker pattern
  - Retry with exponential backoff
  - Full TypeScript support
  - 10+ comprehensive examples
  - Production-ready error handling

---

## License

ResearchFlow - Internal Project
