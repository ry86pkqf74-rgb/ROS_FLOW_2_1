/*
 * Feature Flags Implementation
 *
 * Provides a lightweight feature flag system with:
 * - Percentage-based rollouts
 * - A/B testing support
 * - User segment targeting
 * - Consistent hashing for stable assignments
 */

export enum FeatureFlagKey {
  CUSTOM_AGENT_ENABLED = 'custom_agent_enabled',
  CUSTOM_AGENT_V2 = 'custom_agent_v2',
  CUSTOM_AGENT_ADVANCED_ROUTING = 'custom_agent_advanced_routing',
  CUSTOM_AGENT_MEMORY_MANAGEMENT = 'custom_agent_memory_management',
  CUSTOM_AGENT_TIERED_ROUTING = 'custom_agent_tiered_routing',
  CUSTOM_AGENT_COST_OPTIMIZATION = 'custom_agent_cost_optimization',
  CUSTOM_AGENT_QUALITY_GATING = 'custom_agent_quality_gating',
  CUSTOM_AGENT_PHI_ENFORCEMENT = 'custom_agent_phi_enforcement',
  CUSTOM_AGENT_WORKFLOW_STAGES = 'custom_agent_workflow_stages',
  CUSTOM_AGENT_CACHE_ENABLED = 'custom_agent_cache_enabled',
  CUSTOM_AGENT_PERFORMANCE_MONITORING = 'custom_agent_performance_monitoring',
}

export interface FeatureFlagConfig {
  key: FeatureFlagKey;
  enabled: boolean;
  rolloutPercentage: number;
  variant?: string;
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
    rolloutPercentage: 100,
    metadata: {
      description: 'Enable the custom agent routing system',
      testName: 'custom_agent_enabled_test',
    },
  },
  [FeatureFlagKey.CUSTOM_AGENT_V2]: {
    key: FeatureFlagKey.CUSTOM_AGENT_V2,
    enabled: false,
    rolloutPercentage: 0,
    metadata: {
      description: 'Enable custom agent v2 implementation',
      testName: 'custom_agent_v2_test',
    },
  },
  [FeatureFlagKey.CUSTOM_AGENT_ADVANCED_ROUTING]: {
    key: FeatureFlagKey.CUSTOM_AGENT_ADVANCED_ROUTING,
    enabled: false,
    rolloutPercentage: 0,
    metadata: {
      description: 'Enable advanced routing algorithms for custom agents',
      testName: 'advanced_routing_test',
    },
  },
  [FeatureFlagKey.CUSTOM_AGENT_MEMORY_MANAGEMENT]: {
    key: FeatureFlagKey.CUSTOM_AGENT_MEMORY_MANAGEMENT,
    enabled: false,
    rolloutPercentage: 0,
    metadata: {
      description: 'Enable memory management features for custom agents',
      testName: 'memory_management_test',
    },
  },
  [FeatureFlagKey.CUSTOM_AGENT_TIERED_ROUTING]: {
    key: FeatureFlagKey.CUSTOM_AGENT_TIERED_ROUTING,
    enabled: true,
    rolloutPercentage: 100,
    metadata: {
      description: 'Enable tiered routing (LOCAL/NANO/MINI/FRONTIER/CUSTOM) for agents',
    },
  },
  [FeatureFlagKey.CUSTOM_AGENT_COST_OPTIMIZATION]: {
    key: FeatureFlagKey.CUSTOM_AGENT_COST_OPTIMIZATION,
    enabled: true,
    rolloutPercentage: 100,
    metadata: {
      description: 'Enable cost-based model selection and escalation logic',
    },
  },
  [FeatureFlagKey.CUSTOM_AGENT_QUALITY_GATING]: {
    key: FeatureFlagKey.CUSTOM_AGENT_QUALITY_GATING,
    enabled: false,
    rolloutPercentage: 0,
    metadata: {
      description: 'Enable quality gating checks and potential re-run/escalation',
    },
  },
  [FeatureFlagKey.CUSTOM_AGENT_PHI_ENFORCEMENT]: {
    key: FeatureFlagKey.CUSTOM_AGENT_PHI_ENFORCEMENT,
    enabled: true,
    rolloutPercentage: 100,
    metadata: {
      description: 'Enforce PHI scanning requirements for certain workflows',
    },
  },
  [FeatureFlagKey.CUSTOM_AGENT_WORKFLOW_STAGES]: {
    key: FeatureFlagKey.CUSTOM_AGENT_WORKFLOW_STAGES,
    enabled: true,
    rolloutPercentage: 100,
    metadata: {
      description: 'Enable workflow stage tracking in agent inputs/outputs',
    },
  },
  [FeatureFlagKey.CUSTOM_AGENT_CACHE_ENABLED]: {
    key: FeatureFlagKey.CUSTOM_AGENT_CACHE_ENABLED,
    enabled: true,
    rolloutPercentage: 100,
    metadata: {
      description: 'Enable caching of custom agent dispatch decisions',
    },
  },
  [FeatureFlagKey.CUSTOM_AGENT_PERFORMANCE_MONITORING]: {
    key: FeatureFlagKey.CUSTOM_AGENT_PERFORMANCE_MONITORING,
    enabled: true,
    rolloutPercentage: 100,
    metadata: {
      description: 'Enable performance monitoring and metrics for agent dispatch',
    },
  },
};

export class FeatureFlagManager {
  private flags: Map<FeatureFlagKey, FeatureFlagConfig>;

  constructor(customFlags?: Partial<Record<FeatureFlagKey, FeatureFlagConfig>>) {
    const merged: Record<FeatureFlagKey, FeatureFlagConfig> = {
      ...FEATURE_FLAGS,
      ...(customFlags ?? {}),
    };

    this.flags = new Map(
      Object.entries(merged) as Array<[FeatureFlagKey, FeatureFlagConfig]>
    );
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

  private isUserExcluded(userContext: UserContext, config: FeatureFlagConfig): boolean {
    if (config.metadata?.internalOnly && !userContext.isInternalUser) {
      return true;
    }

    if (config.metadata?.excludedTiers && userContext.tier) {
      const excludedTiers = config.metadata.excludedTiers as string[];
      if (excludedTiers.includes(userContext.tier)) {
        return true;
      }
    }

    if (config.metadata?.excludedSegments && userContext.segment) {
      const excludedSegments = config.metadata.excludedSegments as string[];
      if (excludedSegments.includes(userContext.segment)) {
        return true;
      }
    }

    return false;
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
      return {
        flagKey,
        enabled: false,
        variant: config.variant,
        rolloutPercentage: config.rolloutPercentage,
        reason: 'user_excluded',
      };
    }

    const userHash = this.getConsistentHash(userContext.userId, flagKey);
    const isEnabledByRollout = userHash < config.rolloutPercentage;

    return {
      flagKey,
      enabled: isEnabledByRollout,
      variant: config.variant,
      rolloutPercentage: config.rolloutPercentage,
      reason: isEnabledByRollout ? 'enabled' : 'rollout_percentage',
    };
  }

  evaluateFlags(
    flagKeys: FeatureFlagKey[],
    userContext: UserContext
  ): Partial<Record<FeatureFlagKey, FeatureFlagEvaluationResult>> {
    const results: Partial<Record<FeatureFlagKey, FeatureFlagEvaluationResult>> = {};
    for (const flagKey of flagKeys) {
      results[flagKey] = this.evaluateFlag(flagKey, userContext);
    }
    return results;
  }

  getABTestVariant(testName: string, userId: string): 'a' | 'b' | 'control' | null {
    for (const [, config] of this.flags) {
      const configTestName = config.metadata?.testName as string | undefined;
      if (configTestName === testName && config.variant) {
        return this.getConsistentHash(userId, config.key) < config.rolloutPercentage
          ? (config.variant as 'a' | 'b')
          : 'control';
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
        tests.get(testName)!.push({
          variant: config.variant,
          rolloutPercentage: config.rolloutPercentage,
        });
      }
    }

    return Array.from(tests.entries()).map(([testName, variants]) => ({ testName, variants }));
  }

  setFlag(flagKey: FeatureFlagKey, config: FeatureFlagConfig): void {
    this.flags.set(flagKey, config);
  }

  getFlagConfig(flagKey: FeatureFlagKey): FeatureFlagConfig | undefined {
    return this.flags.get(flagKey);
  }

  getAllFlags(): FeatureFlagConfig[] {
    return Array.from(this.flags.values());
  }
}
