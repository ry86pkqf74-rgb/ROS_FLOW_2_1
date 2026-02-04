import { EventEmitter } from 'events';

export type CircuitState = 'CLOSED' | 'OPEN' | 'HALF_OPEN';

export interface CircuitBreakerConfig {
  failureThreshold: number; // consecutive failures
  recoveryTimeoutMs: number; // time before moving OPEN -> HALF_OPEN
  halfOpenSuccessThreshold?: number; // successes required in HALF_OPEN to close
  rollingWindowMs?: number; // optional, for future extension
}

export interface CircuitBreakerSnapshot {
  state: CircuitState;
  failures: number;
  successesInHalfOpen: number;
  lastFailureAt?: number;
  openedAt?: number;
  nextAttemptAt?: number;
}

export class CircuitBreaker extends EventEmitter {
  private state: CircuitState = 'CLOSED';
  private failures = 0;
  private successesInHalfOpen = 0;
  private lastFailureAt?: number;
  private openedAt?: number;
  private nextAttemptAt?: number;

  constructor(
    public readonly name: string,
    private readonly config: CircuitBreakerConfig,
  ) {
    super();

    if (!config || config.failureThreshold < 1) {
      throw new Error('CircuitBreakerConfig.failureThreshold must be >= 1');
    }
    if (config.recoveryTimeoutMs < 1) {
      throw new Error('CircuitBreakerConfig.recoveryTimeoutMs must be >= 1');
    }
  }

  public getState(): CircuitState {
    return this.state;
  }

  public snapshot(): CircuitBreakerSnapshot {
    return {
      state: this.state,
      failures: this.failures,
      successesInHalfOpen: this.successesInHalfOpen,
      lastFailureAt: this.lastFailureAt,
      openedAt: this.openedAt,
      nextAttemptAt: this.nextAttemptAt,
    };
  }

  private setState(next: CircuitState) {
    if (next === this.state) return;
    const prev = this.state;
    this.state = next;
    this.emit('stateChange', { name: this.name, previous: prev, current: next, snapshot: this.snapshot() });
  }

  private now(): number {
    return Date.now();
  }

  public canRequest(): boolean {
    if (this.state === 'CLOSED') return true;
    if (this.state === 'HALF_OPEN') return true;

    // OPEN
    const n = this.now();
    if (!this.nextAttemptAt) {
      this.nextAttemptAt = n + this.config.recoveryTimeoutMs;
      return false;
    }
    if (n >= this.nextAttemptAt) {
      this.setState('HALF_OPEN');
      this.failures = 0;
      this.successesInHalfOpen = 0;
      this.nextAttemptAt = undefined;
      return true;
    }
    return false;
  }

  public recordSuccess() {
    if (this.state === 'HALF_OPEN') {
      this.successesInHalfOpen += 1;
      const needed = this.config.halfOpenSuccessThreshold ?? 1;
      if (this.successesInHalfOpen >= needed) {
        this.failures = 0;
        this.successesInHalfOpen = 0;
        this.openedAt = undefined;
        this.nextAttemptAt = undefined;
        this.setState('CLOSED');
      }
      return;
    }

    // CLOSED
    this.failures = 0;
  }

  public recordFailure(err?: unknown) {
    this.failures += 1;
    this.lastFailureAt = this.now();

    if (this.state === 'HALF_OPEN') {
      this.openedAt = this.now();
      this.nextAttemptAt = this.openedAt + this.config.recoveryTimeoutMs;
      this.setState('OPEN');
      this.emit('failure', { name: this.name, error: err, snapshot: this.snapshot() });
      return;
    }

    // CLOSED
    if (this.failures >= this.config.failureThreshold) {
      this.openedAt = this.now();
      this.nextAttemptAt = this.openedAt + this.config.recoveryTimeoutMs;
      this.setState('OPEN');
    }

    this.emit('failure', { name: this.name, error: err, snapshot: this.snapshot() });
  }

  public async execute<T>(fn: () => Promise<T>): Promise<T> {
    if (!this.canRequest()) {
      const e = new Error(`Circuit '${this.name}' is OPEN`);
      (e as any).code = 'CIRCUIT_OPEN';
      throw e;
    }

    try {
      const result = await fn();
      this.recordSuccess();
      return result;
    } catch (err) {
      this.recordFailure(err);
      throw err;
    }
  }
}

export class CircuitBreakerRegistry {
  private breakers = new Map<string, CircuitBreaker>();

  constructor(private readonly defaultConfig: CircuitBreakerConfig) {}

  public get(serviceName: string, override?: Partial<CircuitBreakerConfig>): CircuitBreaker {
    const existing = this.breakers.get(serviceName);
    if (existing) return existing;

    const breaker = new CircuitBreaker(serviceName, {
      ...this.defaultConfig,
      ...(override ?? {}),
    });
    this.breakers.set(serviceName, breaker);
    return breaker;
  }

  public snapshots(): Record<string, CircuitBreakerSnapshot> {
    const out: Record<string, CircuitBreakerSnapshot> = {};
    for (const [k, v] of this.breakers.entries()) out[k] = v.snapshot();
    return out;
  }
}
