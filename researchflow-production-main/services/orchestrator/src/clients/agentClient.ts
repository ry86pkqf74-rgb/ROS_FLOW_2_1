/**
 * Agent Client with Circuit Breaker and SSRF Protection
 *
 * HTTP client for communicating with specialist agent services.
 * Implements circuit breaker pattern to prevent cascade failures.
 *
 * Circuit Breaker States:
 * - CLOSED: Normal operation, requests pass through
 * - OPEN: Failures exceeded threshold, requests fail fast
 * - HALF_OPEN: Testing if service recovered
 *
 * Security:
 * - SSRF protection: validates URLs and blocks private networks
 * - PHI safety: never logs request/response bodies
 * - Timeout enforcement: prevents resource exhaustion
 */

import { logAction } from '../services/audit-service';

// Configuration from environment
const CIRCUIT_BREAKER_ENABLED = process.env.AGENT_CIRCUIT_BREAKER_ENABLED !== 'false';
const FAILURE_THRESHOLD = parseInt(process.env.AGENT_CIRCUIT_BREAKER_FAILURE_THRESHOLD || '5', 10);
const SUCCESS_THRESHOLD = parseInt(process.env.AGENT_CIRCUIT_BREAKER_SUCCESS_THRESHOLD || '2', 10);
const TIMEOUT_MS = parseInt(process.env.AGENT_REQUEST_TIMEOUT || '30000', 10);
const RESET_TIMEOUT_MS = parseInt(process.env.AGENT_CIRCUIT_BREAKER_RESET_TIMEOUT_MS || '60000', 10);
const ALLOWED_PRIVATE_NETWORKS = process.env.AGENT_ALLOWED_PRIVATE_NETWORKS?.split(',') || [];

/**
 * Circuit breaker states
 */
type CircuitState = 'CLOSED' | 'OPEN' | 'HALF_OPEN';

/**
 * Circuit breaker status
 */
export interface CircuitStatus {
  state: CircuitState;
  failures: number;
  successes: number;
  lastFailure?: Date;
  lastSuccess?: Date;
  openedAt?: Date;
  nextAttemptAt?: Date;
}

/**
 * Agent response type (matches WorkerResponse pattern)
 */
export interface AgentResponse<T = unknown> {
  success: boolean;
  data?: T;
  error?: string;
  statusCode: number;
  latencyMs: number;
}

/**
 * Request options
 */
export interface RequestOptions {
  headers?: Record<string, string>;
  timeout?: number;
}

/**
 * Agent client options
 */
export interface AgentClientOptions {
  timeout?: number;
  circuitBreakerThreshold?: number;
  circuitBreakerSuccessThreshold?: number;
  circuitBreakerResetTimeout?: number;
}

/**
 * Parsed SSE event from an agent stream
 */
export interface SSEStreamEvent {
  event?: string;
  data: unknown;
  id?: string;
  raw?: string;
  retry?: number;
}

/**
 * Stream event yielded by postStreamIterator (async iterator).
 * Includes raw, data, event, id, retry, and ts for each SSE frame.
 */
export interface StreamEvent {
  raw: string;
  data?: unknown;
  event?: string;
  id?: string;
  retry?: number;
  ts: string;
}

/**
 * Options for streaming requests
 */
export interface StreamOptions extends RequestOptions {
  /** Overall stream timeout in ms (default: 300 000 = 5 min) */
  streamTimeout?: number;
  /** Idle timeout between events in ms (default: 60 000 = 1 min) */
  idleTimeout?: number;
}

/**
 * Circuit Breaker implementation
 */
class CircuitBreaker {
  private state: CircuitState = 'CLOSED';
  private failures = 0;
  private successes = 0;
  private lastFailure?: Date;
  private lastSuccess?: Date;
  private openedAt?: Date;
  private nextAttemptAt?: Date;

  constructor(
    private name: string,
    private failureThreshold: number = FAILURE_THRESHOLD,
    private successThreshold: number = SUCCESS_THRESHOLD,
    private resetTimeout: number = RESET_TIMEOUT_MS
  ) {}

  /**
   * Get current circuit status
   */
  getStatus(): CircuitStatus {
    return {
      state: this.state,
      failures: this.failures,
      successes: this.successes,
      lastFailure: this.lastFailure,
      lastSuccess: this.lastSuccess,
      openedAt: this.openedAt,
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
      // Check if reset timeout has passed
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
      // Reset failure count on success
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
      // Any failure in half-open goes back to open
      this.transitionTo('OPEN');
    } else if (this.state === 'CLOSED' && this.failures >= this.failureThreshold) {
      this.transitionTo('OPEN');
    }
  }

  /**
   * Transition to a new state
   */
  private transitionTo(newState: CircuitState): void {
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

    console.log(`[CircuitBreaker:${this.name}] State transition: ${oldState} -> ${newState}`);
  }

  /**
   * Force circuit open (for testing/admin)
   */
  forceOpen(): void {
    this.transitionTo('OPEN');
  }

  /**
   * Force circuit closed (for testing/admin)
   */
  forceClose(): void {
    this.transitionTo('CLOSED');
  }

  /**
   * Execute a function with circuit breaker protection
   */
  async execute<T>(fn: () => Promise<T>): Promise<T> {
    if (!this.canRequest()) {
      throw new CircuitOpenError(this.name, this.nextAttemptAt);
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

/**
 * Error thrown when circuit is open
 */
export class CircuitOpenError extends Error {
  constructor(
    public serviceName: string,
    public retryAfter?: Date
  ) {
    super(`Circuit breaker open for ${serviceName}`);
    this.name = 'CircuitOpenError';
  }
}

/**
 * Error thrown when URL validation fails (SSRF protection)
 */
export class URLValidationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'URLValidationError';
  }
}

/**
 * Validate URL for SSRF protection
 * - Must be http or https
 * - Blocks private networks unless explicitly allowed
 */
function validateAgentUrl(urlString: string): void {
  let url: URL;

  try {
    url = new URL(urlString);
  } catch (error) {
    throw new URLValidationError(`Invalid URL: ${error instanceof Error ? error.message : 'malformed URL'}`);
  }

  // Only allow http and https
  if (!['http:', 'https:'].includes(url.protocol)) {
    throw new URLValidationError(`Invalid protocol: ${url.protocol}. Only http and https are allowed.`);
  }

  const hostname = url.hostname;

  // Check if it's explicitly allowed
  if (ALLOWED_PRIVATE_NETWORKS.some(allowed => hostname === allowed || hostname.endsWith(`.${allowed}`))) {
    return; // Explicitly allowed
  }

  // Block localhost variations
  const localhostPatterns = ['localhost', '127.0.0.1', '::1', '0.0.0.0', '::'];
  if (localhostPatterns.some(pattern => hostname === pattern || hostname.startsWith(pattern + ':'))) {
    throw new URLValidationError(`Private network target blocked: ${hostname}`);
  }

  // Block private IP ranges (basic check)
  const privateIPPatterns = [
    /^10\./,                    // 10.0.0.0/8
    /^172\.(1[6-9]|2[0-9]|3[0-1])\./, // 172.16.0.0/12
    /^192\.168\./,              // 192.168.0.0/16
    /^169\.254\./,              // 169.254.0.0/16 (link-local)
    /^fc00:/,                   // IPv6 Unique Local
    /^fe80:/,                   // IPv6 Link-Local
  ];

  if (privateIPPatterns.some(pattern => pattern.test(hostname))) {
    throw new URLValidationError(`Private network target blocked: ${hostname}`);
  }

  // Block internal domain patterns (common internal DNS)
  const internalDomainPatterns = ['.local', '.internal', '.private', '.corp'];
  if (internalDomainPatterns.some(pattern => hostname.endsWith(pattern))) {
    throw new URLValidationError(`Internal domain blocked: ${hostname}`);
  }
}

/**
 * Parse SSE events from a text buffer.
 * Returns parsed events and any remaining incomplete text.
 */
function parseSSEBuffer(buffer: string): { events: SSEStreamEvent[]; remainder: string } {
  const normalized = buffer.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
  const blocks = normalized.split('\n\n');
  const remainder = blocks.pop() || '';
  const events: SSEStreamEvent[] = [];

  for (const block of blocks) {
    if (!block.trim()) continue;

    const evt: SSEStreamEvent = { data: null };
    const dataLines: string[] = [];

    for (const line of block.split('\n')) {
      if (line.startsWith('data:')) {
        dataLines.push(line.slice(5).trimStart());
      } else if (line.startsWith('event:')) {
        evt.event = line.slice(6).trimStart();
      } else if (line.startsWith('id:')) {
        evt.id = line.slice(3).trimStart();
      } else if (line.startsWith('retry:')) {
        const n = parseInt(line.slice(6).trim(), 10);
        if (!Number.isNaN(n)) evt.retry = n;
      }
      // Lines starting with ':' are SSE comments — ignored
    }

    if (dataLines.length > 0) {
      const rawData = dataLines.join('\n');
      evt.raw = rawData;
      try {
        evt.data = JSON.parse(rawData);
      } catch {
        evt.data = rawData;
      }
      events.push(evt);
    }
  }

  return { events, remainder };
}

/**
 * Agent Client
 */
class AgentClient {
  private circuitBreaker: CircuitBreaker;
  private timeout: number;

  constructor(options: AgentClientOptions = {}) {
    this.timeout = options.timeout || TIMEOUT_MS;
    this.circuitBreaker = new CircuitBreaker(
      'agent',
      options.circuitBreakerThreshold || FAILURE_THRESHOLD,
      options.circuitBreakerSuccessThreshold || SUCCESS_THRESHOLD,
      options.circuitBreakerResetTimeout || RESET_TIMEOUT_MS
    );
  }

  /**
   * Make a request to an agent service
   * PHI Safety: Never logs request or response bodies
   */
  private async makeRequest<T>(
    agentBaseUrl: string,
    path: string,
    body: unknown,
    options: RequestOptions = {}
  ): Promise<AgentResponse<T>> {
    const { headers = {}, timeout = this.timeout } = options;
    const startTime = Date.now();

    // Validate URL for SSRF protection
    const fullUrl = `${agentBaseUrl}${path}`;
    try {
      validateAgentUrl(fullUrl);
    } catch (error) {
      // PHI-safe logging: only log error type, not URL details that might contain sensitive info
      console.error(`[AgentClient] URL validation failed: ${error instanceof Error ? error.message : 'Invalid URL'}`);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'URL validation failed',
        statusCode: 400,
        latencyMs: Date.now() - startTime,
      };
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    try {
      const response = await fetch(fullUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...headers,
        },
        body: JSON.stringify(body),
        signal: controller.signal,
      });

      const latencyMs = Date.now() - startTime;
      const data = response.headers.get('content-type')?.includes('application/json')
        ? await response.json()
        : await response.text();

      // PHI-safe logging: only log path, status, and latency
      console.log(`[AgentClient] POST ${path} -> ${response.status} (${latencyMs}ms)`);

      return {
        success: response.ok,
        data: response.ok ? data : undefined,
        error: response.ok ? undefined : (typeof data === 'string' ? data : data.error || data.detail),
        statusCode: response.status,
        latencyMs,
      };
    } catch (error) {
      const latencyMs = Date.now() - startTime;

      if (error instanceof Error && error.name === 'AbortError') {
        console.error(`[AgentClient] POST ${path} -> TIMEOUT (${latencyMs}ms)`);
        return {
          success: false,
          error: `Request timeout after ${timeout}ms`,
          statusCode: 408,
          latencyMs,
        };
      }

      // PHI-safe logging: only log error type, not details that might contain PHI
      console.error(`[AgentClient] POST ${path} -> ERROR: ${error instanceof Error ? error.name : 'Unknown error'} (${latencyMs}ms)`);

      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
        statusCode: 0,
        latencyMs,
      };
    } finally {
      clearTimeout(timeoutId);
    }
  }

  /**
   * Internal: async generator that yields StreamEvent for each SSE frame.
   * Uses same timeouts and Accept: text/event-stream as makeStreamRequest.
   * PHI Safety: Never logs request or response bodies.
   */
  private async * _streamEvents(
    agentBaseUrl: string,
    path: string,
    body: unknown,
    options: StreamOptions = {}
  ): AsyncGenerator<StreamEvent, void, unknown> {
    const {
      headers = {},
      streamTimeout = parseInt(process.env.AGENT_STREAM_TIMEOUT || '300000', 10),
      idleTimeout = 60000,
    } = options;

    const fullUrl = `${agentBaseUrl}${path}`;
    try {
      validateAgentUrl(fullUrl);
    } catch (error) {
      console.error(`[AgentClient] URL validation failed: ${error instanceof Error ? error.message : 'Invalid URL'}`);
      throw error;
    }

    const controller = new AbortController();
    const overallTimer = setTimeout(() => controller.abort(), streamTimeout);
    let idleTimer: ReturnType<typeof setTimeout> | null = null;

    const resetIdleTimer = (): void => {
      if (idleTimer) clearTimeout(idleTimer);
      idleTimer = setTimeout(() => controller.abort(), idleTimeout);
    };

    try {
      const response = await fetch(fullUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'text/event-stream',
          ...headers,
        },
        body: JSON.stringify(body),
        signal: controller.signal,
      });

      if (!response.ok) {
        console.log(`[AgentClient] STREAM ${path} -> ${response.status}`);
        throw new Error(`Agent returned ${response.status}`);
      }

      if (!response.body) {
        throw new Error('No response body for SSE stream');
      }

       
      const reader = (response.body as any).getReader() as { read(): Promise<{ done: boolean; value?: Uint8Array }> };
      const decoder = new TextDecoder();
      let buffer = '';

      resetIdleTimer();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        resetIdleTimer();
        buffer += decoder.decode(value, { stream: true });

        const { events, remainder } = parseSSEBuffer(buffer);
        buffer = remainder;

        for (const evt of events) {
          const raw = evt.raw ?? (typeof evt.data === 'string' ? evt.data : JSON.stringify(evt.data));
          yield {
            raw,
            data: evt.data,
            event: evt.event,
            id: evt.id,
            retry: evt.retry,
            ts: new Date().toISOString(),
          };
        }
      }

      if (buffer.trim()) {
        const { events } = parseSSEBuffer(buffer + '\n\n');
        for (const evt of events) {
          const raw = evt.raw ?? (typeof evt.data === 'string' ? evt.data : JSON.stringify(evt.data));
          yield {
            raw,
            data: evt.data,
            event: evt.event,
            id: evt.id,
            retry: evt.retry,
            ts: new Date().toISOString(),
          };
        }
      }
    } finally {
      clearTimeout(overallTimer);
      if (idleTimer) clearTimeout(idleTimer);
    }
  }

  /**
   * Internal: streaming request to agent SSE endpoint.
   * PHI Safety: Never logs request or response bodies.
   */
  private async makeStreamRequest(
    agentBaseUrl: string,
    path: string,
    body: unknown,
    onEvent: (event: SSEStreamEvent) => void | Promise<void>,
    options: StreamOptions = {}
  ): Promise<AgentResponse<unknown>> {
    const {
      headers = {},
      streamTimeout = parseInt(process.env.AGENT_STREAM_TIMEOUT || '300000', 10),
      idleTimeout = 60000,
    } = options;
    const startTime = Date.now();
    let eventCount = 0;
    let finalData: unknown = undefined;

    const fullUrl = `${agentBaseUrl}${path}`;
    try {
      validateAgentUrl(fullUrl);
    } catch (error) {
      console.error(`[AgentClient] URL validation failed: ${error instanceof Error ? error.message : 'Invalid URL'}`);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'URL validation failed',
        statusCode: 400,
        latencyMs: Date.now() - startTime,
      };
    }

    const controller = new AbortController();
    const overallTimer = setTimeout(() => controller.abort(), streamTimeout);
    let idleTimer: ReturnType<typeof setTimeout> | null = null;

    function resetIdleTimer(): void {
      if (idleTimer) clearTimeout(idleTimer);
      idleTimer = setTimeout(() => controller.abort(), idleTimeout);
    }

    try {
      const response = await fetch(fullUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'text/event-stream',
          ...headers,
        },
        body: JSON.stringify(body),
        signal: controller.signal,
      });

      if (!response.ok) {
        const latencyMs = Date.now() - startTime;
        console.log(`[AgentClient] STREAM ${path} -> ${response.status} (${latencyMs}ms)`);
        return {
          success: false,
          error: `Agent returned ${response.status}`,
          statusCode: response.status,
          latencyMs,
        };
      }

      if (!response.body) {
        return {
          success: false,
          error: 'No response body for SSE stream',
          statusCode: response.status,
          latencyMs: Date.now() - startTime,
        };
      }

       
      const reader = (response.body as any).getReader() as { read(): Promise<{ done: boolean; value?: Uint8Array }> };
      const decoder = new TextDecoder();
      let buffer = '';

      resetIdleTimer();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        resetIdleTimer();
        buffer += decoder.decode(value, { stream: true });

        const { events, remainder } = parseSSEBuffer(buffer);
        buffer = remainder;

        for (const evt of events) {
          eventCount++;
          if (evt.event === 'done' || evt.event === 'complete') {
            finalData = evt.data;
          }
          await onEvent(evt);
        }
      }

      // Flush any remaining buffer content
      if (buffer.trim()) {
        const { events } = parseSSEBuffer(buffer + '\n\n');
        for (const evt of events) {
          eventCount++;
          if (evt.event === 'done' || evt.event === 'complete') {
            finalData = evt.data;
          }
          await onEvent(evt);
        }
      }

      const latencyMs = Date.now() - startTime;
      console.log(`[AgentClient] STREAM ${path} -> 200 (${latencyMs}ms, ${eventCount} events)`);

      return {
        success: true,
        data: finalData,
        statusCode: response.status,
        latencyMs,
      };
    } catch (error) {
      const latencyMs = Date.now() - startTime;

      if (error instanceof Error && error.name === 'AbortError') {
        console.error(`[AgentClient] STREAM ${path} -> TIMEOUT (${latencyMs}ms, ${eventCount} events)`);
        return {
          success: false,
          error: `Stream timeout after ${latencyMs}ms`,
          statusCode: 408,
          latencyMs,
        };
      }

      console.error(`[AgentClient] STREAM ${path} -> ERROR: ${error instanceof Error ? error.name : 'Unknown'} (${latencyMs}ms)`);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
        statusCode: 0,
        latencyMs,
      };
    } finally {
      clearTimeout(overallTimer);
      if (idleTimer) clearTimeout(idleTimer);
    }
  }

  /**
   * POST request to agent with circuit breaker protection
   * Named "postSync" to distinguish from future streaming operations
   *
   * @param agentBaseUrl - Base URL of the agent service
   * @param path - Path to the endpoint (e.g., '/api/execute')
   * @param body - Request body (will be JSON stringified)
   * @param options - Optional headers and timeout
   * @returns Promise<AgentResponse<T>> - Response with success, data, error, statusCode, latencyMs
   */
  async postSync<T = unknown>(
    agentBaseUrl: string,
    path: string,
    body: unknown,
    options: RequestOptions = {}
  ): Promise<AgentResponse<T>> {
    if (!CIRCUIT_BREAKER_ENABLED) {
      return this.makeRequest<T>(agentBaseUrl, path, body, options);
    }

    try {
      return await this.circuitBreaker.execute(() => this.makeRequest<T>(agentBaseUrl, path, body, options));
    } catch (error) {
      if (error instanceof CircuitOpenError) {
        await logAction({
          eventType: 'CIRCUIT_BREAKER',
          action: 'REQUEST_BLOCKED',
          resourceType: 'agent',
          resourceId: path,
          details: {
            service: error.serviceName,
            retryAfter: error.retryAfter?.toISOString(),
          },
        });

        // PHI-safe: no request/response details in error
        console.warn(`[AgentClient] Circuit open for agent, blocked request to ${path}`);

        return {
          success: false,
          error: `Service temporarily unavailable (circuit open). Retry after ${error.retryAfter?.toISOString() || 'unknown'}`,
          statusCode: 503,
          latencyMs: 0,
        };
      }
      throw error;
    }
  }

  /**
   * POST to agent SSE endpoint with circuit breaker protection.
   * Parses SSE events and calls onEvent for each one.
   * PHI Safety: Never logs request or response bodies.
   *
   * @param agentBaseUrl - Base URL of the agent service
   * @param path - Endpoint path (e.g., '/agents/run/stream')
   * @param body - Request body (JSON stringified)
   * @param onEvent - Callback for each parsed SSE event
   * @param options - Stream timeout and header options
   */
  async postStream(
    agentBaseUrl: string,
    path: string,
    body: unknown,
    onEvent: (event: SSEStreamEvent) => void | Promise<void>,
    options: StreamOptions = {}
  ): Promise<AgentResponse<unknown>> {
    const streamFn = () => this.makeStreamRequest(agentBaseUrl, path, body, onEvent, options);

    if (!CIRCUIT_BREAKER_ENABLED) {
      return streamFn();
    }

    try {
      return await this.circuitBreaker.execute(streamFn);
    } catch (error) {
      if (error instanceof CircuitOpenError) {
        await logAction({
          eventType: 'CIRCUIT_BREAKER',
          action: 'STREAM_REQUEST_BLOCKED',
          resourceType: 'agent',
          resourceId: path,
          details: {
            service: error.serviceName,
            retryAfter: error.retryAfter?.toISOString(),
          },
        });

        console.warn(`[AgentClient] Circuit open for agent, blocked stream to ${path}`);

        return {
          success: false,
          error: `Service temporarily unavailable (circuit open). Retry after ${error.retryAfter?.toISOString() || 'unknown'}`,
          statusCode: 503,
          latencyMs: 0,
        };
      }
      throw error;
    }
  }

  /**
   * POST to agent SSE endpoint; yields an async iterator of StreamEvent.
   * Uses same timeouts and circuit breaker behavior as postSync/postStream.
   * PHI Safety: Never logs request or response bodies.
   *
   * @param agentBaseUrl - Base URL of the agent service
   * @param path - Endpoint path (e.g., '/agents/run/stream')
   * @param body - Request body (JSON stringified)
   * @param options - Stream timeout and header options
   * @returns AsyncIterableIterator of StreamEvent
   */
  postStreamIterator(
    agentBaseUrl: string,
    path: string,
    body: unknown,
    options: StreamOptions = {}
  ): AsyncIterableIterator<StreamEvent> {
    const self = this;
    let innerGen: AsyncGenerator<StreamEvent, void, unknown> | null = null;

    async function* wrap(): AsyncGenerator<StreamEvent, void, unknown> {
      innerGen = self._streamEvents(agentBaseUrl, path, body, options);
      if (!CIRCUIT_BREAKER_ENABLED) {
        yield* innerGen;
        return;
      }
      const first = await self.circuitBreaker.execute(() => innerGen!.next());
      if (first.done) return;
      yield first.value as StreamEvent;
      try {
        while (true) {
          const next = await innerGen!.next();
          if (next.done) break;
          yield next.value as StreamEvent;
        }
      } catch (err) {
        self.circuitBreaker.recordFailure();
        throw err;
      }
    }

    return wrap();
  }

  /**
   * Get circuit breaker status
   */
  getCircuitStatus(): CircuitStatus {
    return this.circuitBreaker.getStatus();
  }

  /**
   * Force circuit open (admin/testing)
   */
  forceCircuitOpen(): void {
    this.circuitBreaker.forceOpen();
  }

  /**
   * Force circuit closed (admin/testing)
   */
  forceCircuitClose(): void {
    this.circuitBreaker.forceClose();
  }
}

// Singleton instance
let defaultAgentClient: AgentClient | null = null;

/**
 * Get the agent client instance (singleton)
 * Safe for concurrent async operations
 *
 * @param options - Optional configuration (creates new instance if provided)
 * @returns AgentClient instance
 */
export function getAgentClient(options?: AgentClientOptions): AgentClient {
  if (!defaultAgentClient || options) {
    defaultAgentClient = new AgentClient(options);
  }
  return defaultAgentClient;
}

/**
 * Get circuit breaker status for agent services
 */
export function getAgentCircuitStatus(): CircuitStatus {
  const client = getAgentClient();
  return client.getCircuitStatus();
}

export { AgentClient, CircuitBreaker };
export default getAgentClient;
