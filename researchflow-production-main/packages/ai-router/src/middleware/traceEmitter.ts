/**
 * Trace Emitter for AI Router Insights
 *
 * Provides tracing and observability for AI operations.
 *
 * @module @researchflow/ai-router/middleware/traceEmitter
 */

/**
 * Configuration options for the trace emitter
 */
export interface TraceEmitterOptions {
  /** Whether tracing is enabled */
  enabled?: boolean;
  /** Endpoint for trace collection */
  endpoint?: string;
  /** Batch size for trace events */
  batchSize?: number;
  /** Flush interval in milliseconds */
  flushIntervalMs?: number;
  /** Whether to include prompt content in traces */
  includePrompts?: boolean;
  /** Maximum prompt length to include */
  maxPromptLength?: number;
}

/**
 * Context for trace events
 */
export interface TraceContext {
  /** Unique trace ID */
  traceId: string;
  /** Parent span ID if any */
  parentSpanId?: string;
  /** Current span ID */
  spanId: string;
  /** Operation name */
  operationName: string;
  /** Start timestamp */
  startTime: number;
  /** End timestamp */
  endTime?: number;
  /** Additional metadata */
  metadata?: Record<string, unknown>;
  /** Error if any */
  error?: Error;
}

/**
 * Response from AI Router operations
 */
export interface AIRouterResponse<T = unknown> {
  /** Response data */
  data: T;
  /** Model used */
  model: string;
  /** Token usage */
  usage: {
    promptTokens: number;
    completionTokens: number;
    totalTokens: number;
  };
  /** Cost in USD */
  cost: number;
  /** Latency in milliseconds */
  latencyMs: number;
  /** Trace context */
  trace?: TraceContext;
}

// In-memory trace buffer
let traceBuffer: TraceContext[] = [];
let traceConfig: TraceEmitterOptions = {
  enabled: true,
  batchSize: 100,
  flushIntervalMs: 5000,
  includePrompts: false,
  maxPromptLength: 1000,
};
let flushInterval: NodeJS.Timeout | null = null;

/**
 * Initialize the trace emitter with options
 */
export function initTraceEmitter(options?: TraceEmitterOptions): void {
  traceConfig = { ...traceConfig, ...options };

  if (traceConfig.enabled && !flushInterval) {
    flushInterval = setInterval(() => {
      flushTraces();
    }, traceConfig.flushIntervalMs);
  }
}

/**
 * Emit a trace event
 */
export function emitTraceEvent(context: Partial<TraceContext>): TraceContext {
  const fullContext: TraceContext = {
    traceId: context.traceId || generateId(),
    spanId: context.spanId || generateId(),
    operationName: context.operationName || 'unknown',
    startTime: context.startTime || Date.now(),
    ...context,
  };

  if (traceConfig.enabled) {
    traceBuffer.push(fullContext);

    if (traceBuffer.length >= (traceConfig.batchSize || 100)) {
      flushTraces();
    }
  }

  return fullContext;
}

/**
 * Wrapper to add tracing to async operations
 */
export async function withTraceEmitter<T>(
  operationName: string,
  operation: () => Promise<T>,
  metadata?: Record<string, unknown>
): Promise<{ result: T; trace: TraceContext }> {
  const trace = emitTraceEvent({
    operationName,
    startTime: Date.now(),
    metadata,
  });

  try {
    const result = await operation();
    trace.endTime = Date.now();
    return { result, trace };
  } catch (error) {
    trace.endTime = Date.now();
    trace.error = error instanceof Error ? error : new Error(String(error));
    throw error;
  }
}

/**
 * Check the health of the trace emitter
 */
export function checkTraceEmitterHealth(): {
  healthy: boolean;
  bufferSize: number;
  enabled: boolean;
} {
  return {
    healthy: true,
    bufferSize: traceBuffer.length,
    enabled: traceConfig.enabled ?? true,
  };
}

/**
 * Shutdown the trace emitter
 */
export async function shutdownTraceEmitter(): Promise<void> {
  if (flushInterval) {
    clearInterval(flushInterval);
    flushInterval = null;
  }

  await flushTraces();
  traceBuffer = [];
}

/**
 * Flush traces to the configured endpoint
 */
async function flushTraces(): Promise<void> {
  if (traceBuffer.length === 0) return;

  const traces = [...traceBuffer];
  traceBuffer = [];

  if (traceConfig.endpoint) {
    try {
      await fetch(traceConfig.endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ traces }),
      });
    } catch (error) {
      // Re-add traces to buffer on failure
      traceBuffer.push(...traces);
      console.error('Failed to flush traces:', error);
    }
  }
}

/**
 * Generate a unique ID for traces
 */
function generateId(): string {
  return `${Date.now().toString(36)}-${Math.random().toString(36).substring(2, 9)}`;
}

export default {
  initTraceEmitter,
  emitTraceEvent,
  withTraceEmitter,
  checkTraceEmitterHealth,
  shutdownTraceEmitter,
};
