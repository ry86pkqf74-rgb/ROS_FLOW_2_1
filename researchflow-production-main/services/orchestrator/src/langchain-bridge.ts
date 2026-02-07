/**
 * LangChain Bridge - Node.js Integration with Python Worker's LangGraph Agents
 *
 * Connects the Node.js orchestrator to Python worker's LangGraph agents via HTTP and WebSocket.
 * Provides fault tolerance through circuit breaker pattern and exponential backoff retry logic.
 *
 * Features:
 * - HTTP client for calling Python worker agent endpoints
 * - WebSocket client for real-time progress tracking
 * - Type definitions for agent tasks and responses
 * - Retry logic with exponential backoff
 * - Circuit breaker pattern for fault tolerance
 * - Progress event streaming
 *
 * ROS-107: Track A - LangChain Integration
 * ROS-108: LangGraph Agent Orchestration
 */

import { EventEmitter } from 'events';

import WebSocket from 'ws';

/**
 * Configuration from environment
 */
const WORKER_URL = process.env.WORKER_CALLBACK_URL || 'http://worker:8000';
const WORKER_WS_URL = process.env.WORKER_WS_URL || 'ws://worker:8000';
const LANGCHAIN_API_TIMEOUT = parseInt(process.env.LANGCHAIN_API_TIMEOUT || '30000', 10);
const LANGCHAIN_RETRY_MAX_ATTEMPTS = parseInt(process.env.LANGCHAIN_RETRY_MAX_ATTEMPTS || '3', 10);
const LANGCHAIN_RETRY_INITIAL_DELAY = parseInt(process.env.LANGCHAIN_RETRY_INITIAL_DELAY || '1000', 10);
const LANGCHAIN_CIRCUIT_BREAKER_ENABLED = process.env.LANGCHAIN_CIRCUIT_BREAKER_ENABLED !== 'false';
const LANGCHAIN_CIRCUIT_FAILURE_THRESHOLD = parseInt(process.env.LANGCHAIN_CIRCUIT_FAILURE_THRESHOLD || '5', 10);
const LANGCHAIN_CIRCUIT_SUCCESS_THRESHOLD = parseInt(process.env.LANGCHAIN_CIRCUIT_SUCCESS_THRESHOLD || '2', 10);
const LANGCHAIN_CIRCUIT_RESET_TIMEOUT = parseInt(process.env.LANGCHAIN_CIRCUIT_RESET_TIMEOUT || '60000', 10);

// ============================================================================
// TYPE DEFINITIONS
// ============================================================================

/**
 * Supported LangGraph agent types
 */
export enum AgentType {
  ResearchAnalyzer = 'research_analyzer',
  LiteratureReviewer = 'literature_reviewer',
  DataProcessor = 'data_processor',
  ManuscriptGenerator = 'manuscript_generator',
  GuidelineExtractor = 'guideline_extractor',
  CustomAgent = 'custom_agent',
}

/**
 * Task status enumeration
 */
export enum TaskStatus {
  Pending = 'pending',
  Running = 'running',
  Paused = 'paused',
  Completed = 'completed',
  Failed = 'failed',
  Cancelled = 'cancelled',
}

/**
 * Task priority levels
 */
export enum TaskPriority {
  Low = 'low',
  Normal = 'normal',
  High = 'high',
  Critical = 'critical',
}

/**
 * Agent task input
 */
export interface AgentTaskInput {
  /** Unique task identifier */
  taskId?: string;

  /** Agent type to execute */
  agentType: AgentType | string;

  /** Input data for the agent */
  data: Record<string, unknown>;

  /** Optional parameters */
  params?: {
    timeout?: number;
    maxIterations?: number;
    temperature?: number;
    model?: string;
    streaming?: boolean;
  };

  /** Task metadata */
  metadata?: {
    userId?: string;
    projectId?: string;
    requestId?: string;
    tags?: string[];
  };

  /** Priority level */
  priority?: TaskPriority;

  /** Callback URL for status updates */
  callbackUrl?: string;
}

/**
 * Agent task response
 */
export interface AgentTaskResponse {
  /** Task ID */
  taskId: string;

  /** Current task status */
  status: TaskStatus;

  /** Agent type that executed */
  agentType: AgentType | string;

  /** Task result/output */
  result?: Record<string, unknown>;

  /** Error message if failed */
  error?: string;

  /** Error code if failed */
  errorCode?: string;

  /** Execution metadata */
  metadata?: {
    startTime?: string;
    endTime?: string;
    executionTimeMs?: number;
    iterationCount?: number;
    tokenCount?: number;
  };

  /** Progress information */
  progress?: {
    current: number;
    total: number;
    percentage: number;
    message: string;
  };

  /** Response timestamp */
  timestamp: string;
}

/**
 * Progress event for WebSocket streaming
 */
export interface ProgressEvent {
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

/**
 * Circuit breaker status
 */
export interface CircuitBreakerStatus {
  state: 'CLOSED' | 'OPEN' | 'HALF_OPEN';
  failures: number;
  successes: number;
  lastFailure?: Date;
  lastSuccess?: Date;
  nextAttemptAt?: Date;
}

/**
 * Retry options
 */
export interface RetryOptions {
  maxAttempts?: number;
  initialDelayMs?: number;
  maxDelayMs?: number;
  backoffMultiplier?: number;
  shouldRetry?: (error: Error, attempt: number) => boolean;
}

/**
 * Agent status response
 */
export interface AgentStatusResponse {
  taskId: string;
  status: TaskStatus;
  progress: {
    current: number;
    total: number;
    percentage: number;
  };
  result?: Record<string, unknown>;
  error?: string;
  executionTimeMs?: number;
}

// ============================================================================
// RETRY WITH EXPONENTIAL BACKOFF
// ============================================================================

/**
 * Implements retry logic with exponential backoff
 *
 * @param fn Function to retry
 * @param options Retry options
 * @returns Result of the function
 */
export async function withRetry<T>(
  fn: () => Promise<T>,
  options: RetryOptions = {}
): Promise<T> {
  const {
    maxAttempts = LANGCHAIN_RETRY_MAX_ATTEMPTS,
    initialDelayMs = LANGCHAIN_RETRY_INITIAL_DELAY,
    maxDelayMs = 32000,
    backoffMultiplier = 2,
    shouldRetry = (error) => {
      // Retry on network errors and 5xx status codes
      const retryableErrors = ['ECONNREFUSED', 'ECONNRESET', 'ETIMEDOUT', 'EHOSTUNREACH'];
      return retryableErrors.includes((error as NodeJS.ErrnoException).code || '');
    },
  } = options;

  let lastError: Error | null = null;
  let delay = initialDelayMs;

  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error instanceof Error ? error : new Error(String(error));

      // Check if we should retry this error
      if (attempt === maxAttempts || !shouldRetry(lastError, attempt)) {
        throw lastError;
      }

      // Calculate delay with exponential backoff
      const jitter = Math.random() * 0.1 * delay;
      const actualDelay = Math.min(delay + jitter, maxDelayMs);

      console.log(
        `[LangChainBridge] Retry attempt ${attempt}/${maxAttempts} after ${actualDelay}ms: ${lastError.message}`
      );

      await new Promise((resolve) => setTimeout(resolve, actualDelay));
      delay = Math.min(delay * backoffMultiplier, maxDelayMs);
    }
  }

  throw lastError || new Error('Max retry attempts exceeded');
}

// ============================================================================
// CIRCUIT BREAKER
// ============================================================================

/**
 * Circuit breaker implementation for LangChain bridge
 */
class LangChainCircuitBreaker {
  private state: 'CLOSED' | 'OPEN' | 'HALF_OPEN' = 'CLOSED';
  private failures = 0;
  private successes = 0;
  private lastFailure?: Date;
  private lastSuccess?: Date;
  private openedAt?: Date;
  private nextAttemptAt?: Date;

  constructor(
    private name: string,
    private failureThreshold: number = LANGCHAIN_CIRCUIT_FAILURE_THRESHOLD,
    private successThreshold: number = LANGCHAIN_CIRCUIT_SUCCESS_THRESHOLD,
    private resetTimeout: number = LANGCHAIN_CIRCUIT_RESET_TIMEOUT
  ) {}

  /**
   * Get circuit breaker status
   */
  getStatus(): CircuitBreakerStatus {
    return {
      state: this.state,
      failures: this.failures,
      successes: this.successes,
      lastFailure: this.lastFailure,
      lastSuccess: this.lastSuccess,
      nextAttemptAt: this.nextAttemptAt,
    };
  }

  /**
   * Check if request is allowed
   */
  canRequest(): boolean {
    if (this.state === 'CLOSED') {
      return true;
    }

    if (this.state === 'OPEN') {
      if (this.nextAttemptAt && Date.now() >= this.nextAttemptAt.getTime()) {
        this.transitionTo('HALF_OPEN');
        return true;
      }
      return false;
    }

    // HALF_OPEN: allow single request
    return true;
  }

  /**
   * Record a successful request
   */
  recordSuccess(): void {
    this.lastSuccess = new Date();

    if (this.state === 'HALF_OPEN') {
      this.successes++;
      if (this.successes >= this.successThreshold) {
        this.transitionTo('CLOSED');
      }
    } else if (this.state === 'CLOSED') {
      this.failures = 0;
    }
  }

  /**
   * Record a failed request
   */
  recordFailure(): void {
    this.failures++;
    this.lastFailure = new Date();

    if (this.state === 'HALF_OPEN') {
      this.transitionTo('OPEN');
    } else if (this.state === 'CLOSED' && this.failures >= this.failureThreshold) {
      this.transitionTo('OPEN');
    }
  }

  /**
   * Transition to a new state
   */
  private transitionTo(newState: 'CLOSED' | 'OPEN' | 'HALF_OPEN'): void {
    const oldState = this.state;
    this.state = newState;

    if (newState === 'OPEN') {
      this.openedAt = new Date();
      this.nextAttemptAt = new Date(Date.now() + this.resetTimeout);
      this.successes = 0;
    } else if (newState === 'CLOSED') {
      this.failures = 0;
      this.successes = 0;
      this.openedAt = undefined;
      this.nextAttemptAt = undefined;
    } else if (newState === 'HALF_OPEN') {
      this.successes = 0;
    }

    console.log(`[LangChainCircuitBreaker:${this.name}] ${oldState} -> ${newState}`);
  }

  /**
   * Execute function with circuit breaker protection
   */
  async execute<T>(fn: () => Promise<T>): Promise<T> {
    if (!this.canRequest()) {
      throw new Error(
        `Circuit breaker open for ${this.name}. Retry after ${this.nextAttemptAt?.toISOString()}`
      );
    }

    try {
      const result = await fn();
      this.recordSuccess();
      return result;
    } catch (error) {
      this.recordFailure();
      throw error;
    }
  }
}

// ============================================================================
// LANGCHAIN BRIDGE
// ============================================================================

/**
 * LangChain Bridge - Main service for orchestrating LangGraph agents
 *
 * @example
 * ```typescript
 * const bridge = new LangChainBridge();
 *
 * // Run an agent
 * const response = await bridge.runAgent(AgentType.ResearchAnalyzer, {
 *   title: 'COVID-19 vaccines',
 *   keywords: ['mRNA', 'vaccination']
 * });
 *
 * // Subscribe to progress
 * bridge.subscribeToProgress(response.taskId, (event) => {
 *   console.log(`Progress: ${event.data.progress?.percentage}%`);
 * });
 *
 * // Check status
 * const status = await bridge.getAgentStatus(response.taskId);
 * console.log(`Status: ${status.status}`);
 * ```
 */
export class LangChainBridge extends EventEmitter {
  private circuitBreaker: LangChainCircuitBreaker;
  private wsConnections: Map<string, WebSocket> = new Map();
  private taskSubscriptions: Map<string, Set<(event: ProgressEvent) => void>> = new Map();
  private baseUrl: string;
  private wsUrl: string;

  constructor(baseUrl: string = WORKER_URL, wsUrl: string = WORKER_WS_URL) {
    super();
    this.baseUrl = baseUrl;
    this.wsUrl = wsUrl;
    this.circuitBreaker = new LangChainCircuitBreaker(
      'langchain-agent',
      LANGCHAIN_CIRCUIT_FAILURE_THRESHOLD,
      LANGCHAIN_CIRCUIT_SUCCESS_THRESHOLD,
      LANGCHAIN_CIRCUIT_RESET_TIMEOUT
    );
  }

  /**
   * Make HTTP request to worker API
   *
   * @param endpoint API endpoint path
   * @param options Request options
   * @returns Response data
   */
  private async makeRequest<T>(
    endpoint: string,
    options: {
      method?: string;
      body?: unknown;
      headers?: Record<string, string>;
      timeout?: number;
    } = {}
  ): Promise<T> {
    const {
      method = 'GET',
      body,
      headers = {},
      timeout = LANGCHAIN_API_TIMEOUT,
    } = options;

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    try {
      const response = await fetch(`${this.baseUrl}${endpoint}`, {
        method,
        headers: {
          'Content-Type': 'application/json',
          ...headers,
        },
        body: body ? JSON.stringify(body) : undefined,
        signal: controller.signal,
      });

      const data = await response.json();

      if (!response.ok) {
        const errorMsg = (data as any).error || (data as any).detail || 'Unknown error';
        const error = new Error(errorMsg);
        (error as any).statusCode = response.status;
        throw error;
      }

      return data as T;
    } finally {
      clearTimeout(timeoutId);
    }
  }

  /**
   * Call worker API with circuit breaker and retry logic
   *
   * @param endpoint API endpoint
   * @param options Request options
   * @returns Response data
   */
  private async callWithProtection<T>(
    endpoint: string,
    options: {
      method?: string;
      body?: unknown;
      headers?: Record<string, string>;
      timeout?: number;
    } = {}
  ): Promise<T> {
    if (!LANGCHAIN_CIRCUIT_BREAKER_ENABLED) {
      return withRetry(() => this.makeRequest<T>(endpoint, options));
    }

    return withRetry(
      () => this.circuitBreaker.execute(() => this.makeRequest<T>(endpoint, options)),
      {
        maxAttempts: LANGCHAIN_RETRY_MAX_ATTEMPTS,
        initialDelayMs: LANGCHAIN_RETRY_INITIAL_DELAY,
        shouldRetry: (error: Error) => {
          const code = (error as any).code;
          const statusCode = (error as any).statusCode;
          const retryableStatusCodes = [408, 429, 500, 502, 503, 504];
          return ['ECONNREFUSED', 'ECONNRESET', 'ETIMEDOUT'].includes(code) ||
                 retryableStatusCodes.includes(statusCode);
        },
      }
    );
  }

  /**
   * Run a LangGraph agent
   *
   * @param agentType Type of agent to run
   * @param input Task input data
   * @param options Additional options
   * @returns Agent task response with taskId
   *
   * @example
   * ```typescript
   * const response = await bridge.runAgent(
   *   AgentType.ResearchAnalyzer,
   *   { title: 'COVID-19', keywords: ['vaccine'] },
   *   { timeout: 60000 }
   * );
   * ```
   */
  async runAgent(
    agentType: AgentType | string,
    input: Record<string, unknown>,
    options?: {
      timeout?: number;
      priority?: TaskPriority;
      metadata?: AgentTaskInput['metadata'];
    }
  ): Promise<AgentTaskResponse> {
    try {
      const taskInput: AgentTaskInput = {
        agentType,
        data: input,
        priority: options?.priority || TaskPriority.Normal,
        metadata: options?.metadata,
        params: {
          timeout: options?.timeout,
        },
      };

      const response = await this.callWithProtection<AgentTaskResponse>(
        '/api/langchain/agents/run',
        {
          method: 'POST',
          body: taskInput,
          timeout: options?.timeout,
        }
      );

      // Subscribe to progress automatically
      if (response.taskId) {
        this.connectToProgressStream(response.taskId);
      }

      this.emit('agent:started', { taskId: response.taskId, agentType });
      return response;
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : 'Unknown error';
      this.emit('agent:error', { agentType, error: errorMsg });
      throw new Error(`Failed to run agent ${agentType}: ${errorMsg}`);
    }
  }

  /**
   * Get status of a running or completed agent task
   *
   * @param taskId Task identifier
   * @returns Current task status
   *
   * @example
   * ```typescript
   * const status = await bridge.getAgentStatus('task-123');
   * console.log(status.status); // 'completed' | 'running' | 'failed'
   * console.log(status.progress.percentage); // 0-100
   * ```
   */
  async getAgentStatus(taskId: string): Promise<AgentStatusResponse> {
    try {
      return await this.callWithProtection<AgentStatusResponse>(
        `/api/langchain/agents/${taskId}/status`
      );
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : 'Unknown error';
      throw new Error(`Failed to get agent status for task ${taskId}: ${errorMsg}`);
    }
  }

  /**
   * Subscribe to real-time progress updates via WebSocket
   *
   * @param taskId Task identifier
   * @param callback Callback function for progress events
   * @returns Unsubscribe function
   *
   * @example
   * ```typescript
   * const unsubscribe = bridge.subscribeToProgress(taskId, (event) => {
   *   if (event.type === 'progress') {
   *     console.log(`${event.data.progress?.percentage}%`);
   *   }
   *   if (event.type === 'error') {
   *     console.error(event.data.error?.message);
   *   }
   * });
   *
   * // Later: unsubscribe();
   * ```
   */
  subscribeToProgress(
    taskId: string,
    callback: (event: ProgressEvent) => void
  ): () => void {
    // Add callback to subscription set
    if (!this.taskSubscriptions.has(taskId)) {
      this.taskSubscriptions.set(taskId, new Set());
      this.connectToProgressStream(taskId);
    }

    const callbacks = this.taskSubscriptions.get(taskId)!;
    callbacks.add(callback);

    // Return unsubscribe function
    return () => {
      callbacks.delete(callback);
      if (callbacks.size === 0) {
        this.taskSubscriptions.delete(taskId);
        this.disconnectProgressStream(taskId);
      }
    };
  }

  /**
   * Connect to WebSocket progress stream for a task
   *
   * @param taskId Task identifier
   */
  private connectToProgressStream(taskId: string): void {
    if (this.wsConnections.has(taskId)) {
      return; // Already connected
    }

    try {
      const ws = new WebSocket(`${this.wsUrl}/api/langchain/agents/${taskId}/progress`);

      ws.on('open', () => {
        console.log(`[LangChainBridge] Connected to progress stream for task ${taskId}`);
        this.emit('progress:connected', { taskId });
      });

      ws.on('message', (data: WebSocket.Data) => {
        try {
          const event: ProgressEvent = JSON.parse(data.toString());

          // Emit to all subscribers
          const callbacks = this.taskSubscriptions.get(taskId);
          if (callbacks) {
            callbacks.forEach((callback) => {
              try {
                callback(event);
              } catch (err) {
                console.error(`[LangChainBridge] Error in progress callback: ${err}`);
              }
            });
          }

          // Emit global event
          this.emit('progress:update', { taskId, event });

          // Handle completion
          if (event.type === 'completed') {
            this.emit('agent:completed', { taskId });
            this.disconnectProgressStream(taskId);
          }
        } catch (err) {
          console.error(`[LangChainBridge] Failed to parse progress message: ${err}`);
        }
      });

      ws.on('error', (error: Error) => {
        console.error(`[LangChainBridge] WebSocket error for task ${taskId}: ${error.message}`);
        this.emit('progress:error', { taskId, error: error.message });
      });

      ws.on('close', () => {
        console.log(`[LangChainBridge] Disconnected from progress stream for task ${taskId}`);
        this.wsConnections.delete(taskId);
        this.emit('progress:disconnected', { taskId });
      });

      this.wsConnections.set(taskId, ws);
    } catch (error) {
      console.error(`[LangChainBridge] Failed to connect to progress stream: ${error}`);
      this.emit('progress:connection-failed', { taskId, error: String(error) });
    }
  }

  /**
   * Disconnect from WebSocket progress stream
   *
   * @param taskId Task identifier
   */
  private disconnectProgressStream(taskId: string): void {
    const ws = this.wsConnections.get(taskId);
    if (ws) {
      ws.close();
      this.wsConnections.delete(taskId);
    }
  }

  /**
   * Cancel a running task
   *
   * @param taskId Task identifier
   * @returns Cancellation response
   *
   * @example
   * ```typescript
   * await bridge.cancelTask(taskId);
   * // Task will transition to 'cancelled' status
   * ```
   */
  async cancelTask(taskId: string): Promise<{ taskId: string; status: TaskStatus }> {
    try {
      const response = await this.callWithProtection<{ taskId: string; status: TaskStatus }>(
        `/api/langchain/agents/${taskId}/cancel`,
        {
          method: 'POST',
          body: {},
        }
      );

      this.emit('agent:cancelled', { taskId });
      this.disconnectProgressStream(taskId);
      return response;
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : 'Unknown error';
      throw new Error(`Failed to cancel task ${taskId}: ${errorMsg}`);
    }
  }

  /**
   * Health check for LangChain bridge and worker connection
   *
   * @returns Health status
   */
  async healthCheck(): Promise<{
    healthy: boolean;
    agentServiceConnected: boolean;
    circuitBreaker: CircuitBreakerStatus;
    latencyMs: number;
    error?: string;
  }> {
    try {
      const startTime = Date.now();
      await this.callWithProtection<{ status: string }>('/api/langchain/health');
      const latencyMs = Date.now() - startTime;

      return {
        healthy: true,
        agentServiceConnected: true,
        circuitBreaker: this.circuitBreaker.getStatus(),
        latencyMs,
      };
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : 'Unknown error';
      return {
        healthy: false,
        agentServiceConnected: false,
        circuitBreaker: this.circuitBreaker.getStatus(),
        latencyMs: 0,
        error: errorMsg,
      };
    }
  }

  /**
   * Get circuit breaker status
   *
   * @returns Circuit breaker status
   */
  getCircuitBreakerStatus(): CircuitBreakerStatus {
    return this.circuitBreaker.getStatus();
  }

  /**
   * Close all WebSocket connections and cleanup resources
   */
  close(): void {
    this.wsConnections.forEach((ws) => ws.close());
    this.wsConnections.clear();
    this.taskSubscriptions.clear();
    this.removeAllListeners();
  }
}

// ============================================================================
// SINGLETON INSTANCE
// ============================================================================

/** Global LangChain bridge instance */
let defaultBridge: LangChainBridge | null = null;

/**
 * Get or create the default LangChain bridge instance
 *
 * @param baseUrl Optional base URL for worker service
 * @param wsUrl Optional WebSocket URL for worker service
 * @returns LangChain bridge instance
 *
 * @example
 * ```typescript
 * const bridge = getLangChainBridge();
 * const response = await bridge.runAgent(AgentType.ResearchAnalyzer, data);
 * ```
 */
export function getLangChainBridge(
  baseUrl?: string,
  wsUrl?: string
): LangChainBridge {
  if (!defaultBridge) {
    defaultBridge = new LangChainBridge(baseUrl, wsUrl);
  }
  return defaultBridge;
}

/**
 * Reset the default bridge instance (useful for testing)
 */
export function resetLangChainBridge(): void {
  if (defaultBridge) {
    defaultBridge.close();
    defaultBridge = null;
  }
}

// ============================================================================
// EXPORTS
// ============================================================================

export {
  LangChainBridge,
  LangChainCircuitBreaker,
  RetryOptions,
};
