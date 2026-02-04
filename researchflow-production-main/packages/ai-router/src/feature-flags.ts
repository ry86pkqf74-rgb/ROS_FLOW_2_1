/**
 * Feature Flags Implementation - Phase 6 (ROS-83)
 * Custom Agent Rollout with A/B Testing and Gradual Rollout Support
 */

export enum FeatureFlagKey {
  CUSTOM_AGENT_ENABLED = 'custom_agent_enabled',
  CUSTOM_AGENT_V2 = 'custom_agent_v2',
  CUSTOM_AGENT_ADVANCED_ROUTING = 'custom_agent_advanced_routing',
  CUSTOM_AGENT_MEMORY_MANAGEMENT = 'custom_agent_memory_management',
  CUSTOM_AGENT_PERFORMANCE_MONITORING = 'custom_agent_performance_monitoring',
  CUSTOM_AGENT_AB_TEST_VARIANT_A = 'custom_agent_ab_test_variant_a',
  CUSTOM_AGENT_AB_TEST_VARIANT_B = 'custom_agent_ab_test_variant_b',
  CUSTOM_AGENT_AB_TEST_CONTROL = 'custom_agent_ab_test_control',
  CUSTOM_AGENT_EXPERIMENTAL_INFERENCE = 'custom_agent_experimental_inference',
  CUSTOM_AGENT_EXPERIMENTAL_CACHING = 'custom_agent_experimental_caching',
  CUSTOM_AGENT_EXPERIMENTAL_BATCH_PROCESSING = 'custom_agent_experimental_batch_processing',
}

export interface FeatureFlagConfig {
  key: FeatureFlagKey;
  enabled: boolean;
  rolloutPercentage: number;
  variant?: 'a' | 'b' | 'control';
  metadata?: Record<string, unknown>;
}

export interface UserContext {
  userId: string;
  email: string;
  organizationId: string;
  tier?: 'free' | 'pro' | 'enterprise';
  segment?: string;
  isInternalUser?: boolean;
}

export interface FeatureFlagEvaluationResult {
  flagKey: FeatureFlagKey;
  enabled: boolean;
  variant?: string;
  rolloutPercentage: number;
  reason: 'enabled' | 'disabled' | 'rollout_percentage' | 'user_excluded' | 'not_found';
}

export const FEATURE_FLAGS: Record<FeatureFlagKey, FeatureFlagConfig> = {
  [FeatureFlagKey.CUSTOM_AGENT_ENABLED]: {
    key: FeatureFlagKey.CUSTOM_AGENT_ENABLED,
    enabled: true,
    rolloutPercentage: 50,
    metadata: {
      description: 'Enable custom agent functionality for users',
      launchDate: '2024-Q1',
      phase: 6,
    },
  },
  [FeatureFlagKey.CUSTOM_AGENT_V2]: {
    key: FeatureFlagKey.CUSTOM_AGENT_V2,
    enabled: true,
    rolloutPercentage: 30,
    metadata: {
      description: 'Custom Agent V2 with improved architecture',
      launchDate: '2024-Q1',
      previousVersion: 'custom_agent_v1',
    },
  },
  [FeatureFlagKey.CUSTOM_AGENT_ADVANCED_ROUTING]: {
    key: FeatureFlagKey.CUSTOM_AGENT_ADVANCED_ROUTING,
    enabled: true,
    rolloutPercentage: 25,
    metadata: {
      description: 'Advanced routing logic for custom agents',
      dependencies: ['custom_agent_enabled'],
      riskLevel: 'medium',
    },
  },
  [FeatureFlagKey.CUSTOM_AGENT_MEMORY_MANAGEMENT]: {
    key: FeatureFlagKey.CUSTOM_AGENT_MEMORY_MANAGEMENT,
    enabled: true,
    rolloutPercentage: 40,
    metadata: {
      description: 'Enhanced memory management for custom agents',
      performanceImprovement: '35%',
    },
  },
  [FeatureFlagKey.CUSTOM_AGENT_PERFORMANCE_MONITORING]: {
    key: FeatureFlagKey.CUSTOM_AGENT_PERFORMANCE_MONITORING,
    enabled: true,
    rolloutPercentage: 60,
    metadata: {
      description: 'Real-time performance monitoring for custom agents',
      metricsTracked: ['latency', 'throughput', 'error_rate'],
    },
  },
  [FeatureFlagKey.CUSTOM_AGENT_AB_TEST_VARIANT_A]: {
    key: FeatureFlagKey.CUSTOM_AGENT_AB_TEST_VARIANT_A,
    enabled: true,
    rolloutPercentage: 33,
    variant: 'a',
    metadata: {
      description: 'A/B Test Variant A: Original algorithm',
      testName: 'custom_agent_routing_ab_test',
      testStartDate: '2024-01-15',
    },
  },
  [FeatureFlagKey.CUSTOM_AGENT_AB_TEST_VARIANT_B]: {
    key: FeatureFlagKey.CUSTOM_AGENT_AB_TEST_VARIANT_B,
    enabled: true,
    rolloutPercentage: 33,
    variant: 'b',
    metadata: {
      description: 'A/B Test Variant B: Optimized algorithm',
      testName: 'custom_agent_routing_ab_test',
      expectedImprovement: '15-20%',
    },
  },
  [FeatureFlagKey.CUSTOM_AGENT_AB_TEST_CONTROL]: {
    key: FeatureFlagKey.CUSTOM_AGENT_AB_TEST_CONTROL,
    enabled: true,
    rolloutPercentage: 34,
    variant: 'control',
    metadata: {
      description: 'A/B Test Control Group: Baseline behavior',
      testName: 'custom_agent_routing_ab_test',
    },
  },
  [FeatureFlagKey.CUSTOM_AGENT_EXPERIMENTAL_INFERENCE]: {
    key: FeatureFlagKey.CUSTOM_AGENT_EXPERIMENTAL_INFERENCE,
    enabled: true,
    rolloutPercentage: 10,
    metadata: {
      description: 'Experimental inference optimizations',
      status: 'alpha',
      requiresOptIn: true,
    },
  },
  [FeatureFlagKey.CUSTOM_AGENT_EXPERIMENTAL_CACHING]: {
    key: FeatureFlagKey.CUSTOM_AGENT_EXPERIMENTAL_CACHING,
    enabled: true,
    rolloutPercentage: 15,
    metadata: {
      description: 'Experimental caching layer',
      status: 'beta',
      expectedBenefit: 'Reduced latency',
    },
  },
  [FeatureFlagKey.CUSTOM_AGENT_EXPERIMENTAL_BATCH_PROCESSING]: {
    key: FeatureFlagKey.CUSTOM_AGENT_EXPERIMENTAL_BATCH_PROCESSING,
    enabled: true,
    rolloutPercentage: 5,
    metadata: {
      description: 'Experimental batch processing for agents',
      status: 'experimental',
      internalTestingOnly: true,
    },
  },
};

export class FeatureFlagManager {
  private flags: Map<FeatureFlagKey, FeatureFlagConfig>;

  constructor(customFlags?: Record<FeatureFlagKey, FeatureFlagConfig>) {
    this.flags = new Map(Object.entries(customFlags || FEATURE_FLAGS));
  }

  private getConsistentHash(userId: string, flagKey: FeatureFlagKey): number {
    const combined = `${userId}:${flagKey}`;
    let hash = 0;
    for (let i = 0; i < combined.length; i++) {
      const char = combined.charCodeAt(i);
      hash = (hash << 5) - hash + char;
      hash = hash & hash;
    }
    return Math.abs(hash) % 100;
  }

  evaluateFlag(flagKey: FeatureFlagKey, userContext: UserContext): FeatureFlagEvaluationResult {
    const config = this.flags.get(flagKey);
    if (!config) {
      return { flagKey, enabled: false, rolloutPercentage: 0, reason: 'not_found' };
    }
    if (!config.enabled) {
      return { flagKey, enabled: false, rolloutPercentage: config.rolloutPercentage, reason: 'disabled' };
    }
    if (this.isUserExcluded(userContext, config)) {
      return { flagKey, enabled: false, variant: config.variant, rolloutPercentage: config.rolloutPercentage, reason: 'user_excluded' };
    }
    const userHash = this.getConsistentHash(userContext.userId, flagKey);
    const isEnabledByRollout = userHash < config.rolloutPercentage;
    return { flagKey, enabled: isEnabledByRollout, variant: config.variant, rolloutPercentage: config.rolloutPercentage, reason: isEnabledByRollout ? 'enabled' : 'rollout_percentage' };
  }

  evaluateFlags(flagKeys: FeatureFlagKey[], userContext: UserContext): Record<FeatureFlagKey, FeatureFlagEvaluationResult> {
    const results: Record<FeatureFlagKey, FeatureFlagEvaluationResult> = {};
    for (const flagKey of flagKeys) {
      results[flagKey] = this.evaluateFlag(flagKey, userContext);
    }
    return results;
  }

  getABTestVariant(testName: string, userId: string): 'a' | 'b' | 'control' | null {
    for (const [, config] of this.flags) {
      if (config.metadata?.testName === testName && config.variant) {
        const userHash = this.getConsistentHash(userId, config.key);
        const baseRollout = Math.floor(config.rolloutPercentage / 3);
        if (userHash < baseRollout) {
          return config.variant;
        }
      }
    }
    return null;
  }

  getActiveABTests(): Array<{ testName: string; variants: Array<{ variant: string; rolloutPercentage: number }> }> {
    const tests = new Map<string, Array<{ variant: string; rolloutPercentage: number }>>();
    for (const [, config] of this.flags) {
      const testName = config.metadata?.testName as string | undefined;
      if (testName && config.variant) {
        if (!tests.has(testName)) {
          tests.set(testName, []);
        }
        tests.get(testName)!.push({ variant: config.variant, rolloutPercentage: config.rolloutPercentage });
      }
    }
    return Array.from(tests, ([testName, variants]) => ({ testName, variants }));
  }

  updateFlag(flagKey: FeatureFlagKey, config: Partial<FeatureFlagConfig>): void {
    const existing = this.flags.get(flagKey);
    if (existing) {
      this.flags.set(flagKey, { ...existing, ...config });
    }
  }

  setRolloutPercentage(flagKey: FeatureFlagKey, percentage: number): void {
    if (percentage < 0 || percentage > 100) {
      throw new Error('Rollout percentage must be between 0 and 100');
    }
    const config = this.flags.get(flagKey);
    if (config) {
      config.rolloutPercentage = percentage;
    }
  }

  private isUserExcluded(userContext: UserContext, config: FeatureFlagConfig): boolean {
    const internalTestingOnly = config.metadata?.internalTestingOnly as boolean | undefined;
    if (internalTestingOnly && !userContext.isInternalUser) {
      return true;
    }
    const requiresOptIn = config.metadata?.requiresOptIn as boolean | undefined;
    if (requiresOptIn) {
      return !userContext.isInternalUser;
    }
    return false;
  }

  getAllFlags(): FeatureFlagConfig[] {
    return Array.from(this.flags.values());
  }

  getFlagStatistics(): Record<string, { totalEnabled: number; totalDisabled: number; averageRolloutPercentage: number; flags: FeatureFlagConfig[] }> {
    const stats = {
      phase6: { totalEnabled: 0, totalDisabled: 0, averageRolloutPercentage: 0, flags: [] as FeatureFlagConfig[] },
      abTests: { totalEnabled: 0, totalDisabled: 0, averageRolloutPercentage: 0, flags: [] as FeatureFlagConfig[] },
      experimental: { totalEnabled: 0, totalDisabled: 0, averageRolloutPercentage: 0, flags: [] as FeatureFlagConfig[] },
    };
    for (const [, config] of this.flags) {
      let category: keyof typeof stats;
      if (config.metadata?.testName) {
        category = 'abTests';
      } else if (config.metadata?.status === 'experimental' || config.metadata?.status === 'alpha' || config.metadata?.status === 'beta') {
        category = 'experimental';
      } else {
        category = 'phase6';
      }
      if (config.enabled) {
        stats[category].totalEnabled++;
      } else {
        stats[category].totalDisabled++;
      }
      stats[category].flags.push(config);
    }
    for (const category of Object.keys(stats) as Array<keyof typeof stats>) {
      const flags = stats[category].flags;
      if (flags.length > 0) {
        stats[category].averageRolloutPercentage = flags.reduce((sum, flag) => sum + flag.rolloutPercentage, 0) / flags.length;
      }
    }
    return stats;
  }
}

export const featureFlagManager = new FeatureFlagManager();

export function isFeatureEnabled(flagKey: FeatureFlagKey, userContext: UserContext): boolean {
  const result = featureFlagManager.evaluateFlag(flagKey, userContext);
  return result.enabled;
}

export function getFeatureVariant(flagKey: FeatureFlagKey, userContext: UserContext): string | undefined {
  const result = featureFlagManager.evaluateFlag(flagKey, userContext);
  return result.variant;
}

export function getABTestVariant(testName: string, userId: string): string | null {
  return featureFlagManager.getABTestVariant(testName, userId) || null;
}