/**
 * Visualization Configuration Management
 * 
 * Centralized configuration for visualization system with environment-specific settings,
 * performance limits, security controls, and operational parameters.
 */

import { z } from 'zod';
import { createLogger } from '../utils/logger';

const logger = createLogger('visualization-config');

// Configuration schema with validation
const VisualizationConfigSchema = z.object({
  // Performance limits
  performance: z.object({
    maxDataPoints: z.number().min(100).max(1000000).default(50000),
    maxConcurrentJobs: z.number().min(1).max(50).default(10),
    generationTimeoutMs: z.number().min(5000).max(300000).default(60000),
    maxImageSizeBytes: z.number().min(1024).max(52428800).default(10485760), // 10MB
    workerTimeoutMs: z.number().min(5000).max(120000).default(30000),
  }),
  
  // Quality settings
  quality: z.object({
    defaultDPI: z.number().min(72).max(600).default(300),
    compressionLevel: z.number().min(1).max(9).default(6),
    enableImageOptimization: z.boolean().default(true),
    thumbnailSize: z.object({
      width: z.number().min(50).max(500).default(200),
      height: z.number().min(50).max(500).default(150),
    }),
    qualityProfiles: z.object({
      draft: z.object({ dpi: z.number().default(72), compression: z.number().default(3) }),
      presentation: z.object({ dpi: z.number().default(150), compression: z.number().default(5) }),
      publication: z.object({ dpi: z.number().default(300), compression: z.number().default(7) }),
    }),
  }),
  
  // Cache settings
  cache: z.object({
    enabled: z.boolean().default(true),
    expiryHours: z.number().min(1).max(168).default(24), // 1 week max
    maxCacheSizeMB: z.number().min(100).max(10240).default(1024), // 1GB
    keyPrefix: z.string().default('viz'),
    warmupEnabled: z.boolean().default(false),
    compressionEnabled: z.boolean().default(true),
  }),
  
  // Security and rate limiting
  security: z.object({
    enableRateLimit: z.boolean().default(true),
    rateLimitPerMinute: z.number().min(1).max(1000).default(30),
    allowedFileTypes: z.array(z.string()).default(['png', 'svg', 'pdf']),
    maxUploadSizeMB: z.number().min(1).max(100).default(50),
    enableInputSanitization: z.boolean().default(true),
    enablePhiScanning: z.boolean().default(true),
    blockSuspiciousPatterns: z.boolean().default(true),
  }),
  
  // Database settings
  database: z.object({
    enableFigureStorage: z.boolean().default(true),
    enableMetricsCollection: z.boolean().default(true),
    cleanupOldFiguresDays: z.number().min(7).max(365).default(90),
    enableAuditTrail: z.boolean().default(true),
    batchSize: z.number().min(10).max(1000).default(100),
  }),
  
  // Monitoring and observability
  monitoring: z.object({
    enableMetrics: z.boolean().default(true),
    enableDetailedLogging: z.boolean().default(false),
    enablePerformanceTracking: z.boolean().default(true),
    alertThresholds: z.object({
      errorRate: z.number().min(0).max(1).default(0.05), // 5%
      avgResponseTime: z.number().min(1000).max(60000).default(10000), // 10s
      queueDepth: z.number().min(1).max(1000).default(100),
      memoryUsage: z.number().min(0.5).max(0.95).default(0.85), // 85%
    }),
  }),
  
  // External integrations
  integrations: z.object({
    enableWebhooks: z.boolean().default(false),
    webhookTimeout: z.number().min(1000).max(30000).default(5000),
    enableExportFormats: z.array(z.string()).default(['png', 'svg', 'pdf']),
    aiCaptionProvider: z.enum(['anthropic', 'openai', 'disabled']).default('anthropic'),
  }),
});

export type VisualizationConfig = z.infer<typeof VisualizationConfigSchema>;

/**
 * Load and validate visualization configuration from environment
 */
function loadConfig(): VisualizationConfig {
  const config = {
    performance: {
      maxDataPoints: parseInt(process.env.VIZ_MAX_DATA_POINTS || '50000'),
      maxConcurrentJobs: parseInt(process.env.VIZ_MAX_CONCURRENT || '10'),
      generationTimeoutMs: parseInt(process.env.VIZ_TIMEOUT_MS || '60000'),
      maxImageSizeBytes: parseInt(process.env.VIZ_MAX_IMAGE_SIZE || '10485760'),
      workerTimeoutMs: parseInt(process.env.VIZ_WORKER_TIMEOUT || '30000'),
    },
    
    quality: {
      defaultDPI: parseInt(process.env.VIZ_DEFAULT_DPI || '300'),
      compressionLevel: parseInt(process.env.VIZ_COMPRESSION || '6'),
      enableImageOptimization: process.env.VIZ_OPTIMIZE_IMAGES !== 'false',
      thumbnailSize: {
        width: parseInt(process.env.VIZ_THUMB_WIDTH || '200'),
        height: parseInt(process.env.VIZ_THUMB_HEIGHT || '150'),
      },
      qualityProfiles: {
        draft: { 
          dpi: parseInt(process.env.VIZ_DRAFT_DPI || '72'), 
          compression: parseInt(process.env.VIZ_DRAFT_COMPRESSION || '3') 
        },
        presentation: { 
          dpi: parseInt(process.env.VIZ_PRES_DPI || '150'), 
          compression: parseInt(process.env.VIZ_PRES_COMPRESSION || '5') 
        },
        publication: { 
          dpi: parseInt(process.env.VIZ_PUB_DPI || '300'), 
          compression: parseInt(process.env.VIZ_PUB_COMPRESSION || '7') 
        },
      },
    },
    
    cache: {
      enabled: process.env.VIZ_ENABLE_CACHE !== 'false',
      expiryHours: parseInt(process.env.VIZ_CACHE_EXPIRY || '24'),
      maxCacheSizeMB: parseInt(process.env.VIZ_MAX_CACHE_SIZE || '1024'),
      keyPrefix: process.env.VIZ_CACHE_PREFIX || 'viz',
      warmupEnabled: process.env.VIZ_CACHE_WARMUP === 'true',
      compressionEnabled: process.env.VIZ_CACHE_COMPRESSION !== 'false',
    },
    
    security: {
      enableRateLimit: process.env.VIZ_RATE_LIMIT !== 'false',
      rateLimitPerMinute: parseInt(process.env.VIZ_RATE_LIMIT_PER_MIN || '30'),
      allowedFileTypes: (process.env.VIZ_ALLOWED_TYPES || 'png,svg,pdf').split(','),
      maxUploadSizeMB: parseInt(process.env.VIZ_MAX_UPLOAD_MB || '50'),
      enableInputSanitization: process.env.VIZ_INPUT_SANITIZATION !== 'false',
      enablePhiScanning: process.env.VIZ_PHI_SCANNING !== 'false',
      blockSuspiciousPatterns: process.env.VIZ_BLOCK_SUSPICIOUS !== 'false',
    },
    
    database: {
      enableFigureStorage: process.env.VIZ_DB_STORAGE !== 'false',
      enableMetricsCollection: process.env.VIZ_DB_METRICS !== 'false',
      cleanupOldFiguresDays: parseInt(process.env.VIZ_CLEANUP_DAYS || '90'),
      enableAuditTrail: process.env.VIZ_AUDIT_TRAIL !== 'false',
      batchSize: parseInt(process.env.VIZ_DB_BATCH_SIZE || '100'),
    },
    
    monitoring: {
      enableMetrics: process.env.VIZ_ENABLE_METRICS !== 'false',
      enableDetailedLogging: process.env.VIZ_DETAILED_LOGGING === 'true',
      enablePerformanceTracking: process.env.VIZ_PERF_TRACKING !== 'false',
      alertThresholds: {
        errorRate: parseFloat(process.env.VIZ_ERROR_THRESHOLD || '0.05'),
        avgResponseTime: parseInt(process.env.VIZ_RESPONSE_THRESHOLD || '10000'),
        queueDepth: parseInt(process.env.VIZ_QUEUE_THRESHOLD || '100'),
        memoryUsage: parseFloat(process.env.VIZ_MEMORY_THRESHOLD || '0.85'),
      },
    },
    
    integrations: {
      enableWebhooks: process.env.VIZ_ENABLE_WEBHOOKS === 'true',
      webhookTimeout: parseInt(process.env.VIZ_WEBHOOK_TIMEOUT || '5000'),
      enableExportFormats: (process.env.VIZ_EXPORT_FORMATS || 'png,svg,pdf').split(','),
      aiCaptionProvider: (process.env.VIZ_AI_PROVIDER || 'anthropic') as 'anthropic' | 'openai' | 'disabled',
    },
  };
  
  try {
    const validatedConfig = VisualizationConfigSchema.parse(config);
    logger.info('Visualization configuration loaded successfully', {
      cacheEnabled: validatedConfig.cache.enabled,
      rateLimitEnabled: validatedConfig.security.enableRateLimit,
      maxDataPoints: validatedConfig.performance.maxDataPoints,
      defaultDPI: validatedConfig.quality.defaultDPI,
    });
    return validatedConfig;
  } catch (error) {
    logger.error('Invalid visualization configuration', { error });
    throw new Error(`Configuration validation failed: ${error.message}`);
  }
}

// Export singleton configuration
export const visualizationConfig = loadConfig();

/**
 * Get user-specific rate limit based on subscription tier
 */
export function getUserRateLimit(tier: string): number {
  const baseLimits = {
    free: Math.floor(visualizationConfig.security.rateLimitPerMinute * 0.3),      // 30%
    basic: Math.floor(visualizationConfig.security.rateLimitPerMinute * 0.6),     // 60%
    premium: visualizationConfig.security.rateLimitPerMinute,                      // 100%
    enterprise: Math.floor(visualizationConfig.security.rateLimitPerMinute * 2),  // 200%
  };
  
  return baseLimits[tier as keyof typeof baseLimits] || baseLimits.free;
}

/**
 * Get quality profile settings
 */
export function getQualityProfile(profile: 'draft' | 'presentation' | 'publication') {
  return visualizationConfig.quality.qualityProfiles[profile];
}

/**
 * Check if data size is within limits
 */
export function validateDataSize(dataPoints: number): { valid: boolean; message?: string } {
  if (dataPoints > visualizationConfig.performance.maxDataPoints) {
    return {
      valid: false,
      message: `Data size ${dataPoints} exceeds maximum allowed ${visualizationConfig.performance.maxDataPoints} points`,
    };
  }
  return { valid: true };
}

/**
 * Get timeout for chart type
 */
export function getTimeoutForChartType(chartType: string): number {
  const complexCharts = ['forest_plot', 'kaplan_meier', 'consort_diagram'];
  const isComplex = complexCharts.includes(chartType);
  
  return isComplex 
    ? visualizationConfig.performance.generationTimeoutMs * 1.5
    : visualizationConfig.performance.generationTimeoutMs;
}

/**
 * Export configuration for Docker environment
 */
export function generateDockerEnv(): string {
  return `
# Visualization Configuration
VIZ_MAX_DATA_POINTS=${visualizationConfig.performance.maxDataPoints}
VIZ_MAX_CONCURRENT=${visualizationConfig.performance.maxConcurrentJobs}
VIZ_TIMEOUT_MS=${visualizationConfig.performance.generationTimeoutMs}
VIZ_DEFAULT_DPI=${visualizationConfig.quality.defaultDPI}
VIZ_ENABLE_CACHE=${visualizationConfig.cache.enabled}
VIZ_CACHE_EXPIRY=${visualizationConfig.cache.expiryHours}
VIZ_RATE_LIMIT_PER_MIN=${visualizationConfig.security.rateLimitPerMinute}
VIZ_OPTIMIZE_IMAGES=${visualizationConfig.quality.enableImageOptimization}
VIZ_ENABLE_METRICS=${visualizationConfig.monitoring.enableMetrics}
VIZ_PHI_SCANNING=${visualizationConfig.security.enablePhiScanning}
`.trim();
}

// Export types and utilities
export type QualityProfile = 'draft' | 'presentation' | 'publication';
export type ChartType = 'bar_chart' | 'line_chart' | 'scatter_plot' | 'box_plot' | 'forest_plot' | 'kaplan_meier' | 'consort_diagram';