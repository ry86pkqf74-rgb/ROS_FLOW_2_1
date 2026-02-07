/**
 * AI Bridge Configuration
 *
 * Configuration settings for the Python ↔ TypeScript AI Bridge.
 * These settings control routing, limits, and behavior.
 */

export const AI_BRIDGE_CONFIG = {
  // Bridge metadata
  version: '1.0.0',
  name: 'ResearchFlow AI Bridge',
  
  // Request limits
  limits: {
    maxBatchSize: 10,
    maxTokens: 200000,
    timeoutMs: 60000,
    maxConcurrentRequests: 5,
    rateLimitPerMinute: 100,
  },
  
  // Default model configuration
  defaults: {
    modelTier: 'STANDARD',
    governanceMode: 'DEMO',
    temperature: 0.7,
    requirePhiCompliance: true,
    costTrackingEnabled: true,
    // Provider mode: 'mock' | 'shadow' | 'real'
    // mock   – deterministic stubs, zero cost (default)
    // shadow – real call fires but mock response returned (for comparison)
    // real   – real provider response returned to caller
    providerMode: (process.env.AI_BRIDGE_PROVIDER_MODE || 'mock') as 'mock' | 'shadow' | 'real',
  },
  
  // Supported task types and their configurations
  taskTypes: {
    hypothesis_generation: {
      recommendedTier: 'STANDARD',
      minimumTier: 'ECONOMY',
      requiresPhiCompliance: false,
      description: 'Generate and refine research hypotheses',
    },
    literature_search: {
      recommendedTier: 'ECONOMY',
      minimumTier: 'ECONOMY',
      requiresPhiCompliance: false,
      description: 'Search and analyze academic literature',
    },
    data_analysis: {
      recommendedTier: 'STANDARD',
      minimumTier: 'STANDARD',
      requiresPhiCompliance: false,
      description: 'Analyze research data and datasets',
    },
    statistical_analysis: {
      recommendedTier: 'PREMIUM',
      minimumTier: 'STANDARD',
      requiresPhiCompliance: false,
      description: 'Perform statistical tests and analysis',
    },
    manuscript_drafting: {
      recommendedTier: 'STANDARD',
      minimumTier: 'STANDARD',
      requiresPhiCompliance: false,
      description: 'Draft manuscript sections',
    },
    manuscript_revision: {
      recommendedTier: 'STANDARD',
      minimumTier: 'ECONOMY',
      requiresPhiCompliance: false,
      description: 'Revise and improve manuscript content',
    },
    citation_formatting: {
      recommendedTier: 'ECONOMY',
      minimumTier: 'ECONOMY',
      requiresPhiCompliance: false,
      description: 'Format and validate citations',
    },
    phi_redaction: {
      recommendedTier: 'PREMIUM',
      minimumTier: 'PREMIUM',
      requiresPhiCompliance: true,
      description: 'Detect and redact protected health information',
    },
    ethical_review: {
      recommendedTier: 'PREMIUM',
      minimumTier: 'STANDARD',
      requiresPhiCompliance: true,
      description: 'Review content for ethical compliance',
    },
    claim_verification: {
      recommendedTier: 'STANDARD',
      minimumTier: 'STANDARD',
      requiresPhiCompliance: false,
      description: 'Verify research claims and statements',
    },
    summarization: {
      recommendedTier: 'ECONOMY',
      minimumTier: 'ECONOMY',
      requiresPhiCompliance: false,
      description: 'Summarize documents and content',
    },
    code_generation: {
      recommendedTier: 'STANDARD',
      minimumTier: 'ECONOMY',
      requiresPhiCompliance: false,
      description: 'Generate analysis code and scripts',
    },
    figure_generation: {
      recommendedTier: 'STANDARD',
      minimumTier: 'STANDARD',
      requiresPhiCompliance: false,
      description: 'Generate data visualizations',
    },
  },
  
  // Model tier mappings (Bridge tier → Router tier)
  tierMappings: {
    'ECONOMY': 'economy',
    'STANDARD': 'standard',
    'PREMIUM': 'premium',
  },
  
  // Feature flags
  features: {
    streamingEnabled: true,
    batchProcessingEnabled: true,
    costTrackingEnabled: true,
    auditLoggingEnabled: true,
    phiComplianceEnabled: true,
    rateLimitingEnabled: true,
  },
  
  // Health check configuration
  healthCheck: {
    timeoutMs: 5000,
    requiredServices: ['aiRouter'],
    criticalEndpoints: ['/api/ai/router/tiers'],
  },
  
  // Monitoring and observability
  monitoring: {
    logLevel: 'info',
    metricsEnabled: true,
    tracingEnabled: false,
    errorReportingEnabled: true,
  },
  
  // Cost thresholds and warnings
  costManagement: {
    warnAtDollars: 10.0,
    blockAtDollars: 100.0,
    dailyBudgetDollars: 50.0,
    costTrackingRetentionDays: 30,
  },
  
  // Integration-specific settings
  integration: {
    orchestratorUrl: process.env.AI_BRIDGE_ORCHESTRATOR_URL || 'http://localhost:3001',
    workerUrl: process.env.AI_BRIDGE_WORKER_URL || 'http://localhost:8000',
    authenticationRequired: true,
    rbacEnabled: true,
  },
};

// Environment-based overrides
export function getAIBridgeConfig() {
  const config = { ...AI_BRIDGE_CONFIG };
  
  // Override from environment variables
  if (process.env.AI_BRIDGE_MAX_BATCH_SIZE) {
    config.limits = {
      ...config.limits,
      maxBatchSize: parseInt(process.env.AI_BRIDGE_MAX_BATCH_SIZE)
    };
  }
  
  if (process.env.AI_BRIDGE_DEFAULT_TIER) {
    config.defaults = {
      ...config.defaults,
      modelTier: process.env.AI_BRIDGE_DEFAULT_TIER as any
    };
  }
  
  if (process.env.AI_BRIDGE_PHI_COMPLIANCE) {
    config.defaults = {
      ...config.defaults,
      requirePhiCompliance: process.env.AI_BRIDGE_PHI_COMPLIANCE === 'true'
    };
  }
  
  if (process.env.AI_BRIDGE_STREAMING_ENABLED) {
    config.features = {
      ...config.features,
      streamingEnabled: process.env.AI_BRIDGE_STREAMING_ENABLED === 'true'
    };
  }
  
  if (process.env.AI_BRIDGE_COST_LIMIT) {
    config.costManagement = {
      ...config.costManagement,
      blockAtDollars: parseFloat(process.env.AI_BRIDGE_COST_LIMIT)
    };
  }

  if (process.env.AI_BRIDGE_PROVIDER_MODE) {
    const mode = process.env.AI_BRIDGE_PROVIDER_MODE as ProviderMode;
    if (['mock', 'shadow', 'real'].includes(mode)) {
      config.defaults = {
        ...config.defaults,
        providerMode: mode,
      };
    }
  }
  
  return config;
}

// Type exports for use in other modules
export type TaskType = keyof typeof AI_BRIDGE_CONFIG.taskTypes;
export type ModelTier = keyof typeof AI_BRIDGE_CONFIG.tierMappings;
export type GovernanceMode = 'DEMO' | 'LIVE';
export type ProviderMode = 'mock' | 'shadow' | 'real';

export default AI_BRIDGE_CONFIG;