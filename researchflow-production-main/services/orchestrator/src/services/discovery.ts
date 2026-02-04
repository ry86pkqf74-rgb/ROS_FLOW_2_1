import { CircuitBreakerRegistry } from '../utils/circuit-breaker.js';

export type ServiceHealth = 'UNKNOWN' | 'HEALTHY' | 'DEGRADED' | 'UNHEALTHY';

export interface ServiceInstance {
  id: string;
  baseUrl?: string; // reserved for future HTTP proxying
  version?: string;
  weight?: number;
  lastSeenAt?: number;
  health: ServiceHealth;
  metadata?: Record<string, any>;
}

export interface ServiceRecord {
  name: string;
  version?: string;
  instances: ServiceInstance[];
  lastUpdatedAt: number;
}

export interface DiscoveryConfig {
  unhealthyFailover: boolean;
  preferHealthy: boolean;
}

export class ServiceDiscovery {
  private registry = new Map<string, ServiceRecord>();
  private rrCursor = new Map<string, number>();

  constructor(
    private readonly circuits: CircuitBreakerRegistry,
    private readonly config: DiscoveryConfig = { unhealthyFailover: true, preferHealthy: true },
  ) {}

  public registerService(name: string, record: Partial<ServiceRecord> & { instances?: ServiceInstance[] } = {}) {
    const now = Date.now();
    const existing = this.registry.get(name);
    const merged: ServiceRecord = {
      name,
      version: record.version ?? existing?.version,
      instances: record.instances ?? existing?.instances ?? [{ id: `${name}-singleton`, health: 'UNKNOWN' }],
      lastUpdatedAt: now,
    };
    this.registry.set(name, merged);
  }

  public updateInstanceHealth(name: string, instanceId: string, health: ServiceHealth) {
    const rec = this.registry.get(name);
    if (!rec) return;
    const now = Date.now();
    const inst = rec.instances.find(i => i.id === instanceId);
    if (inst) {
      inst.health = health;
      inst.lastSeenAt = now;
    }
    rec.lastUpdatedAt = now;
  }

  public getServiceRecord(name: string): ServiceRecord | undefined {
    return this.registry.get(name);
  }

  public listServices(): ServiceRecord[] {
    return Array.from(this.registry.values());
  }

  public chooseInstance(name: string): ServiceInstance | undefined {
    const rec = this.registry.get(name);
    if (!rec || rec.instances.length === 0) return undefined;

    const breaker = this.circuits.get(name);
    const circuitOpen = breaker.getState() === 'OPEN';

    let candidates = rec.instances.slice();

    if (this.config.preferHealthy) {
      const healthy = candidates.filter(i => i.health === 'HEALTHY');
      const degraded = candidates.filter(i => i.health === 'DEGRADED');
      const unknown = candidates.filter(i => i.health === 'UNKNOWN');
      const unhealthy = candidates.filter(i => i.health === 'UNHEALTHY');

      candidates = healthy.length ? healthy
        : degraded.length ? degraded
          : unknown.length ? unknown
            : unhealthy;
    }

    if (this.config.unhealthyFailover) {
      candidates = candidates.filter(i => i.health !== 'UNHEALTHY');
      if (candidates.length === 0) candidates = rec.instances.slice();
    }

    // If circuit is OPEN, still return an instance (router will block), but prefer HEALTHY to aid recovery
    if (circuitOpen && this.config.preferHealthy) {
      const healthy = candidates.filter(i => i.health === 'HEALTHY');
      if (healthy.length) candidates = healthy;
    }

    const cursor = (this.rrCursor.get(name) ?? 0) % candidates.length;
    this.rrCursor.set(name, cursor + 1);
    return candidates[cursor];
  }

  public snapshot() {
    return {
      services: this.listServices(),
      circuits: this.circuits.snapshots(),
    };
  }
}
