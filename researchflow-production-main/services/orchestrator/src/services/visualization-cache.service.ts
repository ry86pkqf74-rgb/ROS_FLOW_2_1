/**
 * Visualization Cache Service
 * 
 * Redis-based caching for generated charts to improve performance and reduce
 * redundant chart generation. Provides intelligent cache management with
 * compression, TTL, and cache warming capabilities.
 */

import crypto from 'crypto';
import { promisify } from 'util';
import { gzip, gunzip } from 'zlib';

import Redis from 'ioredis';

import { visualizationConfig } from '../config/visualization.config';
import { createLogger } from '../utils/logger';

const logger = createLogger('visualization-cache');
const gzipAsync = promisify(gzip);
const gunzipAsync = promisify(gunzip);

export interface CacheStats {
  totalKeys: number;
  memoryUsageMB: number;
  hitRate: number;
  missRate: number;
  avgResponseTime: number;
  cacheSize: string;
  oldestEntry: string;
  newestEntry: string;
}

export interface CacheMetrics {
  hits: number;
  misses: number;
  sets: number;
  deletes: number;
  errors: number;
  totalRequests: number;
}

export class VisualizationCacheService {
  private redis: Redis;
  private keyPrefix: string;
  private metrics: CacheMetrics;
  
  constructor() {
    // Initialize Redis connection
    this.redis = new Redis(process.env.REDIS_URL || 'redis://localhost:6379', {
      retryDelayOnFailover: 100,
      maxRetriesPerRequest: 3,
      lazyConnect: true,
      keyPrefix: visualizationConfig.cache.keyPrefix + ':',
    });
    
    this.keyPrefix = visualizationConfig.cache.keyPrefix;
    this.metrics = {
      hits: 0,
      misses: 0,
      sets: 0,
      deletes: 0,
      errors: 0,
      totalRequests: 0,
    };
    
    this.setupEventHandlers();
  }
  
  /**
   * Setup Redis event handlers and monitoring
   */
  private setupEventHandlers() {
    this.redis.on('connect', () => {
      logger.info('Connected to Redis cache');
    });
    
    this.redis.on('error', (error) => {
      logger.error('Redis cache error', { error: error.message });
      this.metrics.errors++;
    });
    
    this.redis.on('reconnecting', (delay) => {
      logger.warn('Redis reconnecting', { delay });
    });
  }
  
  /**
   * Generate deterministic cache key from chart request
   */
  private getCacheKey(chartRequest: any): string {
    // Normalize request to ensure consistent caching
    const normalized = this.normalizeRequest(chartRequest);
    const hash = crypto
      .createHash('sha256')
      .update(JSON.stringify(normalized))
      .digest('hex');
    
    return `chart:${normalized.chart_type}:${hash}`;
  }
  
  /**
   * Normalize chart request for consistent cache keys
   */
  private normalizeRequest(request: any): any {
    const {
      chart_type,
      data,
      config = {},
      research_id, // Include but don't affect cache key unless privacy mode
      ...otherFields
    } = request;
    
    // Sort data arrays for consistency
    const normalizedData = this.sortDataArrays(data);
    
    // Remove non-deterministic fields
    const normalizedConfig = this.cleanConfig(config);
    
    return {
      chart_type,
      data: normalizedData,
      config: normalizedConfig,
      // Add version for cache invalidation when chart generation changes
      agent_version: '1.0.0',
    };
  }
  
  /**
   * Sort data arrays to ensure consistent ordering
   */
  private sortDataArrays(data: any): any {
    if (!data || typeof data !== 'object') return data;
    
    const sorted = { ...data };
    
    // For consistent caching, sort arrays by their first element if numeric
    Object.keys(sorted).forEach(key => {
      if (Array.isArray(sorted[key]) && sorted[key].length > 1) {
        if (typeof sorted[key][0] === 'number') {
          // Create index mapping to maintain relationships
          const indices = sorted[key].map((_, i) => i).sort((a, b) => sorted[key][a] - sorted[key][b]);
          
          // Sort all related arrays using the same index mapping
          Object.keys(sorted).forEach(relatedKey => {
            if (Array.isArray(sorted[relatedKey]) && sorted[relatedKey].length === sorted[key].length) {
              sorted[relatedKey] = indices.map(i => sorted[relatedKey][i]);
            }
          });
        }
      }
    });
    
    return sorted;
  }
  
  /**
   * Clean config object removing non-cacheable fields
   */
  private cleanConfig(config: any): any {
    const {
      // Remove time-specific or request-specific fields
      timestamp,
      request_id,
      user_id,
      session_id,
      ...cleanConfig
    } = config;
    
    // Sort keys for consistent serialization
    const sortedConfig = {};
    Object.keys(cleanConfig).sort().forEach(key => {
      sortedConfig[key] = cleanConfig[key];
    });
    
    return sortedConfig;
  }
  
  /**
   * Check if chart exists in cache
   */
  async getCachedChart(chartRequest: any): Promise<any | null> {
    if (!visualizationConfig.cache.enabled) {
      return null;
    }
    
    const startTime = Date.now();
    this.metrics.totalRequests++;
    
    try {
      const key = this.getCacheKey(chartRequest);
      logger.debug('Checking cache for chart', { key });
      
      const cachedData = await this.redis.getBuffer(key);
      
      if (!cachedData) {
        this.metrics.misses++;
        logger.debug('Cache miss', { key });
        return null;
      }
      
      // Decompress if enabled
      const data = visualizationConfig.cache.compressionEnabled
        ? await gunzipAsync(cachedData)
        : cachedData;
      
      const result = JSON.parse(data.toString());
      
      // Add cache metadata
      result.cache_hit = true;
      result.cached_at = result.cached_at;
      result.cache_age_ms = Date.now() - new Date(result.cached_at).getTime();
      
      this.metrics.hits++;
      
      const responseTime = Date.now() - startTime;
      logger.info('Cache hit', { 
        key, 
        responseTime,
        ageMs: result.cache_age_ms,
      });
      
      return result;
    } catch (error) {
      this.metrics.errors++;
      this.metrics.misses++;
      logger.error('Cache retrieval error', { error: error.message });
      return null;
    }
  }
  
  /**
   * Store generated chart in cache
   */
  async cacheChart(chartRequest: any, result: any): Promise<void> {
    if (!visualizationConfig.cache.enabled) {
      return;
    }
    
    const startTime = Date.now();
    
    try {
      const key = this.getCacheKey(chartRequest);
      
      // Add cache metadata to result
      const cacheableResult = {
        ...result,
        cached_at: new Date().toISOString(),
        cache_key: key,
      };
      
      // Serialize result
      const serialized = Buffer.from(JSON.stringify(cacheableResult));
      
      // Compress if enabled
      const data = visualizationConfig.cache.compressionEnabled
        ? await gzipAsync(serialized)
        : serialized;
      
      // Calculate TTL
      const expirySeconds = visualizationConfig.cache.expiryHours * 3600;
      
      // Store in cache
      await this.redis.setex(key, expirySeconds, data);
      
      this.metrics.sets++;
      
      const responseTime = Date.now() - startTime;
      logger.info('Chart cached', { 
        key, 
        responseTime,
        sizeBytes: data.length,
        compressed: visualizationConfig.cache.compressionEnabled,
        expiryHours: visualizationConfig.cache.expiryHours,
      });
      
      // Update cache size tracking
      await this.updateCacheSize(data.length);
      
    } catch (error) {
      this.metrics.errors++;
      logger.error('Cache storage error', { error: error.message });
    }
  }
  
  /**
   * Invalidate cache entries by pattern
   */
  async invalidateByPattern(pattern: string): Promise<number> {
    try {
      const keys = await this.redis.keys(`${this.keyPrefix}:${pattern}`);
      
      if (keys.length === 0) {
        return 0;
      }
      
      const deleted = await this.redis.del(...keys);
      this.metrics.deletes += deleted;
      
      logger.info('Cache invalidated by pattern', { 
        pattern, 
        keysDeleted: deleted,
      });
      
      return deleted;
    } catch (error) {
      logger.error('Cache invalidation error', { error: error.message });
      return 0;
    }
  }
  
  /**
   * Invalidate specific chart from cache
   */
  async invalidateChart(chartRequest: any): Promise<boolean> {
    try {
      const key = this.getCacheKey(chartRequest);
      const deleted = await this.redis.del(key);
      
      if (deleted > 0) {
        this.metrics.deletes++;
        logger.info('Chart invalidated', { key });
      }
      
      return deleted > 0;
    } catch (error) {
      logger.error('Chart invalidation error', { error: error.message });
      return false;
    }
  }
  
  /**
   * Get comprehensive cache statistics
   */
  async getCacheStats(): Promise<CacheStats> {
    try {
      const info = await this.redis.info('memory');
      const keyspace = await this.redis.info('keyspace');
      
      // Parse Redis info
      const memoryUsed = this.parseRedisInfo(info, 'used_memory');
      const totalKeys = await this.redis.dbsize();
      
      // Calculate hit rate
      const hitRate = this.metrics.totalRequests > 0 
        ? this.metrics.hits / this.metrics.totalRequests 
        : 0;
      
      const missRate = 1 - hitRate;
      
      // Get oldest/newest entries
      const { oldest, newest } = await this.getEntryTimestamps();
      
      return {
        totalKeys,
        memoryUsageMB: Math.round(memoryUsed / 1024 / 1024 * 100) / 100,
        hitRate: Math.round(hitRate * 10000) / 100, // Percentage with 2 decimal places
        missRate: Math.round(missRate * 10000) / 100,
        avgResponseTime: this.calculateAvgResponseTime(),
        cacheSize: this.formatBytes(memoryUsed),
        oldestEntry: oldest || 'N/A',
        newestEntry: newest || 'N/A',
      };
    } catch (error) {
      logger.error('Failed to get cache stats', { error: error.message });
      throw error;
    }
  }
  
  /**
   * Get cache metrics for monitoring
   */
  getCacheMetrics(): CacheMetrics & { hitRate: number; missRate: number } {
    const hitRate = this.metrics.totalRequests > 0 
      ? this.metrics.hits / this.metrics.totalRequests 
      : 0;
    
    return {
      ...this.metrics,
      hitRate: Math.round(hitRate * 10000) / 100,
      missRate: Math.round((1 - hitRate) * 10000) / 100,
    };
  }
  
  /**
   * Warm up cache with common chart types
   */
  async warmUpCache(commonRequests: any[]): Promise<number> {
    if (!visualizationConfig.cache.warmupEnabled) {
      return 0;
    }
    
    logger.info('Starting cache warmup', { requests: commonRequests.length });
    let warmedUp = 0;
    
    for (const request of commonRequests) {
      try {
        const cached = await this.getCachedChart(request);
        if (!cached) {
          // Chart not in cache - could trigger generation
          // For now, just log the miss
          logger.debug('Cache warmup miss', { 
            chartType: request.chart_type,
            key: this.getCacheKey(request),
          });
        } else {
          warmedUp++;
        }
      } catch (error) {
        logger.warn('Cache warmup error for request', { 
          request: request.chart_type,
          error: error.message,
        });
      }
    }
    
    logger.info('Cache warmup completed', { warmedUp, total: commonRequests.length });
    return warmedUp;
  }
  
  /**
   * Clear all visualization cache entries
   */
  async clearCache(): Promise<number> {
    try {
      const pattern = `${this.keyPrefix}:*`;
      return await this.invalidateByPattern('*');
    } catch (error) {
      logger.error('Failed to clear cache', { error: error.message });
      return 0;
    }
  }
  
  /**
   * Health check for cache service
   */
  async healthCheck(): Promise<{ healthy: boolean; latency?: number; error?: string }> {
    const startTime = Date.now();
    
    try {
      await this.redis.ping();
      const latency = Date.now() - startTime;
      
      return {
        healthy: true,
        latency,
      };
    } catch (error) {
      return {
        healthy: false,
        error: error.message,
      };
    }
  }
  
  /**
   * Close cache connections
   */
  async close(): Promise<void> {
    try {
      await this.redis.quit();
      logger.info('Cache service closed');
    } catch (error) {
      logger.error('Error closing cache service', { error: error.message });
    }
  }
  
  // Private utility methods
  
  private parseRedisInfo(info: string, key: string): number {
    const match = info.match(new RegExp(`${key}:(\\d+)`));
    return match ? parseInt(match[1], 10) : 0;
  }
  
  private calculateAvgResponseTime(): number {
    // This would be implemented with actual response time tracking
    return 0; // Placeholder
  }
  
  private formatBytes(bytes: number): string {
    const sizes = ['B', 'KB', 'MB', 'GB'];
    if (bytes === 0) return '0 B';
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return `${Math.round(bytes / Math.pow(1024, i) * 100) / 100} ${sizes[i]}`;
  }
  
  private async getEntryTimestamps(): Promise<{ oldest?: string; newest?: string }> {
    try {
      const keys = await this.redis.keys(`${this.keyPrefix}:*`);
      if (keys.length === 0) return {};
      
      // Get TTLs to estimate ages (simplified approach)
      const ttls = await Promise.all(keys.map(key => this.redis.ttl(key)));
      
      const maxTTL = visualizationConfig.cache.expiryHours * 3600;
      const ages = ttls.map(ttl => maxTTL - ttl);
      
      const oldestAge = Math.max(...ages);
      const newestAge = Math.min(...ages);
      
      const now = new Date();
      
      return {
        oldest: new Date(now.getTime() - oldestAge * 1000).toISOString(),
        newest: new Date(now.getTime() - newestAge * 1000).toISOString(),
      };
    } catch (error) {
      logger.error('Failed to get entry timestamps', { error: error.message });
      return {};
    }
  }
  
  private async updateCacheSize(addedBytes: number): Promise<void> {
    // Track cache size and implement eviction if needed
    // This could be enhanced with LRU eviction policies
    try {
      const maxSizeBytes = visualizationConfig.cache.maxCacheSizeMB * 1024 * 1024;
      const currentMemory = await this.redis.memory('usage');
      
      if (currentMemory && currentMemory > maxSizeBytes) {
        logger.warn('Cache size exceeding limit', { 
          currentMB: Math.round(currentMemory / 1024 / 1024),
          maxMB: visualizationConfig.cache.maxCacheSizeMB,
        });
        
        // Could implement LRU eviction here
        // For now, just log the warning
      }
    } catch (error) {
      logger.error('Failed to update cache size tracking', { error: error.message });
    }
  }
}

/**
 * Singleton cache service instance
 */
export const visualizationCache = new VisualizationCacheService();