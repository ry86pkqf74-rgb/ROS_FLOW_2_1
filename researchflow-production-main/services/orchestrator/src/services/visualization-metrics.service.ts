/**
 * Visualization Metrics and Monitoring Service
 * 
 * Comprehensive monitoring system for visualization performance, usage patterns,
 * system health, and operational metrics. Provides Prometheus-compatible metrics
 * and custom dashboard data for production monitoring.
 */

import { Registry, Counter, Histogram, Gauge, Summary } from 'prom-client';

import { visualizationConfig } from '../config/visualization.config';
import { pool } from '../db';
import { createLogger } from '../utils/logger';

import { visualizationCache } from './visualization-cache.service';

const logger = createLogger('visualization-metrics');

export interface DashboardMetrics {
  // Performance metrics
  chartsGenerated24h: number;
  averageGenerationTime: number;
  cacheHitRate: number;
  errorRate: number;
  
  // Usage metrics
  topChartTypes: Array<{ type: string; count: number; percentage: number }>;
  topJournalStyles: Array<{ style: string; count: number; percentage: number }>;
  
  // System health
  workerStatus: 'healthy' | 'degraded' | 'unavailable';
  databaseStatus: 'healthy' | 'degraded' | 'unavailable';
  cacheStatus: 'healthy' | 'degraded' | 'unavailable';
  
  // Resource usage
  queueDepth: number;
  activeJobs: number;
  memoryUsage: number;
  
  // Quality metrics
  averageImageSize: number;
  successRate: number;
  timeouts: number;
}

export interface AlertCondition {
  metric: string;
  threshold: number;
  operator: 'gt' | 'lt' | 'eq';
  severity: 'warning' | 'critical';
  description: string;
}

export class VisualizationMetricsService {
  private registry: Registry;
  private startTime: Date;
  
  // Prometheus metrics
  private chartsGenerated: Counter<string>;
  private generationDuration: Histogram<string>;
  private activeJobs: Gauge<string>;
  private errorCount: Counter<string>;
  private cacheOperations: Counter<string>;
  private databaseOperations: Histogram<string>;
  private requestSize: Histogram<string>;
  private responseSize: Histogram<string>;
  private workerRequests: Counter<string>;
  private queueDepth: Gauge<string>;
  private systemResources: Gauge<string>;
  
  // Internal tracking
  private recentMetrics: Map<string, any[]> = new Map();
  private alertHistory: Array<{ alert: AlertCondition; timestamp: Date; value: number }> = [];
  
  constructor() {
    this.registry = new Registry();
    this.startTime = new Date();
    this.initializeMetrics();
    this.startBackgroundTasks();
  }
  
  /**
   * Initialize all Prometheus metrics
   */
  private initializeMetrics(): void {
    // Chart generation metrics
    this.chartsGenerated = new Counter({
      name: 'viz_charts_generated_total',
      help: 'Total number of charts generated',
      labelNames: ['chart_type', 'journal_style', 'status', 'quality_profile'],
      registers: [this.registry],
    });
    
    this.generationDuration = new Histogram({
      name: 'viz_generation_duration_seconds',
      help: 'Time taken to generate charts',
      labelNames: ['chart_type', 'chart_complexity'],
      buckets: [0.1, 0.5, 1, 2, 5, 10, 20, 30, 60, 120],
      registers: [this.registry],
    });
    
    this.activeJobs = new Gauge({
      name: 'viz_active_jobs',
      help: 'Number of active chart generation jobs',
      labelNames: ['job_type'],
      registers: [this.registry],
    });
    
    // Error tracking
    this.errorCount = new Counter({
      name: 'viz_errors_total',
      help: 'Total number of errors by type',
      labelNames: ['error_type', 'error_severity', 'component'],
      registers: [this.registry],
    });
    
    // Cache metrics
    this.cacheOperations = new Counter({
      name: 'viz_cache_operations_total',
      help: 'Cache operations (hits, misses, sets)',
      labelNames: ['operation', 'result'],
      registers: [this.registry],
    });
    
    // Database operations
    this.databaseOperations = new Histogram({
      name: 'viz_database_operation_duration_seconds',
      help: 'Database operation duration',
      labelNames: ['operation', 'table'],
      buckets: [0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
      registers: [this.registry],
    });
    
    // Request/Response size tracking
    this.requestSize = new Histogram({
      name: 'viz_request_size_bytes',
      help: 'Size of chart generation requests',
      buckets: [1024, 10240, 51200, 102400, 512000, 1048576, 5242880], // 1KB to 5MB
      registers: [this.registry],
    });
    
    this.responseSize = new Histogram({
      name: 'viz_response_size_bytes',
      help: 'Size of generated chart responses',
      buckets: [10240, 51200, 102400, 512000, 1048576, 5242880, 10485760], // 10KB to 10MB
      registers: [this.registry],
    });
    
    // Worker communication
    this.workerRequests = new Counter({
      name: 'viz_worker_requests_total',
      help: 'Requests sent to worker service',
      labelNames: ['endpoint', 'status'],
      registers: [this.registry],
    });
    
    // Queue metrics
    this.queueDepth = new Gauge({
      name: 'viz_queue_depth',
      help: 'Number of jobs waiting in queue',
      labelNames: ['priority'],
      registers: [this.registry],
    });
    
    // System resource usage
    this.systemResources = new Gauge({
      name: 'viz_system_resources',
      help: 'System resource usage',
      labelNames: ['resource_type'],
      registers: [this.registry],
    });
    
    logger.info('Visualization metrics initialized', { 
      metricsCount: this.registry.getMetricsAsArray().length,
    });
  }
  
  /**
   * Record chart generation event
   */
  recordChartGeneration(params: {
    chartType: string;
    journalStyle?: string;
    status: 'success' | 'error' | 'timeout';
    duration: number;
    qualityProfile?: string;
    dataPoints?: number;
    imageSize?: number;
    errorType?: string;
  }): void {
    const {
      chartType,
      journalStyle = 'default',
      status,
      duration,
      qualityProfile = 'standard',
      dataPoints = 0,
      imageSize = 0,
      errorType,
    } = params;
    
    // Update counters
    this.chartsGenerated.inc({
      chart_type: chartType,
      journal_style: journalStyle,
      status,
      quality_profile: qualityProfile,
    });
    
    // Record duration
    const complexity = this.classifyComplexity(chartType, dataPoints);
    this.generationDuration.observe(
      { chart_type: chartType, chart_complexity: complexity },
      duration / 1000 // Convert to seconds
    );
    
    // Record response size if available
    if (imageSize > 0) {
      this.responseSize.observe(imageSize);
    }
    
    // Record error if failed
    if (status === 'error' && errorType) {
      this.errorCount.inc({
        error_type: errorType,
        error_severity: this.classifyErrorSeverity(errorType),
        component: 'chart_generation',
      });
    }
    
    // Store in recent metrics for dashboard
    this.storeRecentMetric('chart_generation', {
      chartType,
      journalStyle,
      status,
      duration,
      timestamp: new Date(),
      dataPoints,
      imageSize,
    });
  }
  
  /**
   * Record cache operation
   */
  recordCacheOperation(operation: 'hit' | 'miss' | 'set' | 'delete', success: boolean = true): void {
    this.cacheOperations.inc({
      operation,
      result: success ? 'success' : 'error',
    });
  }
  
  /**
   * Record database operation
   */
  recordDatabaseOperation(operation: string, table: string, duration: number): void {
    this.databaseOperations.observe(
      { operation, table },
      duration / 1000 // Convert to seconds
    );
  }
  
  /**
   * Record worker request
   */
  recordWorkerRequest(endpoint: string, status: number): void {
    const statusCategory = Math.floor(status / 100) * 100; // 200, 400, 500, etc.
    this.workerRequests.inc({
      endpoint,
      status: statusCategory.toString(),
    });
  }
  
  /**
   * Update active job count
   */
  updateActiveJobs(jobType: string, count: number): void {
    this.activeJobs.set({ job_type: jobType }, count);
  }
  
  /**
   * Update queue depth
   */
  updateQueueDepth(priority: string, depth: number): void {
    this.queueDepth.set({ priority }, depth);
  }
  
  /**
   * Update system resource usage
   */
  updateSystemResources(resourceType: string, value: number): void {
    this.systemResources.set({ resource_type: resourceType }, value);
  }
  
  /**
   * Get Prometheus metrics as text
   */
  async getPrometheusMetrics(): Promise<string> {
    // Update real-time metrics before export
    await this.updateRealTimeMetrics();
    
    return this.registry.metrics();
  }
  
  /**
   * Get dashboard metrics for UI
   */
  async getDashboardMetrics(): Promise<DashboardMetrics> {
    try {
      const [
        charts24h,
        avgGenTime,
        cacheStats,
        errorStats,
        topChartTypes,
        topJournalStyles,
        systemHealth,
        qualityMetrics,
      ] = await Promise.all([
        this.getChartsGenerated24h(),
        this.getAverageGenerationTime(),
        this.getCacheStats(),
        this.getErrorRate(),
        this.getTopChartTypes(),
        this.getTopJournalStyles(),
        this.getSystemHealth(),
        this.getQualityMetrics(),
      ]);
      
      return {
        chartsGenerated24h: charts24h,
        averageGenerationTime: avgGenTime,
        cacheHitRate: cacheStats.hitRate,
        errorRate: errorStats.rate,
        topChartTypes,
        topJournalStyles,
        workerStatus: systemHealth.worker,
        databaseStatus: systemHealth.database,
        cacheStatus: systemHealth.cache,
        queueDepth: await this.getQueueDepth(),
        activeJobs: await this.getActiveJobsCount(),
        memoryUsage: await this.getMemoryUsage(),
        averageImageSize: qualityMetrics.avgImageSize,
        successRate: qualityMetrics.successRate,
        timeouts: qualityMetrics.timeouts,
      };
    } catch (error) {
      logger.error('Failed to get dashboard metrics', { error: error.message });
      throw error;
    }
  }
  
  /**
   * Check alert conditions and return triggered alerts
   */
  async checkAlerts(): Promise<Array<{ alert: AlertCondition; value: number; severity: string }>> {
    const triggeredAlerts = [];
    
    const alertConditions: AlertCondition[] = [
      {
        metric: 'error_rate',
        threshold: visualizationConfig.monitoring.alertThresholds.errorRate,
        operator: 'gt',
        severity: 'warning',
        description: 'High error rate detected',
      },
      {
        metric: 'avg_response_time',
        threshold: visualizationConfig.monitoring.alertThresholds.avgResponseTime,
        operator: 'gt',
        severity: 'warning',
        description: 'Average response time too high',
      },
      {
        metric: 'queue_depth',
        threshold: visualizationConfig.monitoring.alertThresholds.queueDepth,
        operator: 'gt',
        severity: 'critical',
        description: 'Queue depth critical',
      },
      {
        metric: 'memory_usage',
        threshold: visualizationConfig.monitoring.alertThresholds.memoryUsage,
        operator: 'gt',
        severity: 'critical',
        description: 'Memory usage critical',
      },
    ];
    
    for (const alert of alertConditions) {
      const value = await this.getMetricValue(alert.metric);
      const triggered = this.evaluateAlertCondition(value, alert.threshold, alert.operator);
      
      if (triggered) {
        triggeredAlerts.push({ alert, value, severity: alert.severity });
        
        // Store in alert history
        this.alertHistory.push({
          alert,
          timestamp: new Date(),
          value,
        });
        
        // Keep only recent alerts (last 24 hours)
        const cutoff = new Date(Date.now() - 24 * 60 * 60 * 1000);
        this.alertHistory = this.alertHistory.filter(entry => entry.timestamp > cutoff);
      }
    }
    
    return triggeredAlerts;
  }
  
  /**
   * Get health status for all components
   */
  async getHealthStatus(): Promise<{
    overall: 'healthy' | 'degraded' | 'unhealthy';
    components: Record<string, any>;
  }> {
    const components = {
      metrics: { healthy: true, latency: 0 },
      cache: await this.checkCacheHealth(),
      database: await this.checkDatabaseHealth(),
      worker: await this.checkWorkerHealth(),
    };
    
    const healthyCount = Object.values(components).filter(c => c.healthy).length;
    const totalCount = Object.values(components).length;
    
    let overall: 'healthy' | 'degraded' | 'unhealthy';
    if (healthyCount === totalCount) {
      overall = 'healthy';
    } else if (healthyCount >= totalCount / 2) {
      overall = 'degraded';
    } else {
      overall = 'unhealthy';
    }
    
    return { overall, components };
  }
  
  // Private helper methods
  
  private classifyComplexity(chartType: string, dataPoints: number): string {
    const complexTypes = ['forest_plot', 'kaplan_meier', 'consort_diagram'];
    
    if (complexTypes.includes(chartType)) return 'complex';
    if (dataPoints > 10000) return 'large';
    if (dataPoints > 1000) return 'medium';
    return 'simple';
  }
  
  private classifyErrorSeverity(errorType: string): string {
    const criticalErrors = ['CONFIGURATION_ERROR', 'UNKNOWN_ERROR', 'DATABASE_ERROR'];
    const warningErrors = ['TIMEOUT', 'WORKER_UNAVAILABLE', 'MEMORY_LIMIT'];
    
    if (criticalErrors.some(e => errorType.includes(e))) return 'critical';
    if (warningErrors.some(e => errorType.includes(e))) return 'warning';
    return 'info';
  }
  
  private storeRecentMetric(type: string, data: any): void {
    if (!this.recentMetrics.has(type)) {
      this.recentMetrics.set(type, []);
    }
    
    const metrics = this.recentMetrics.get(type)!;
    metrics.push(data);
    
    // Keep only last 1000 entries per type
    if (metrics.length > 1000) {
      metrics.splice(0, metrics.length - 1000);
    }
  }
  
  private async updateRealTimeMetrics(): Promise<void> {
    try {
      // Update queue depth
      // This would be implemented based on your queue system
      
      // Update memory usage
      const memoryUsage = process.memoryUsage();
      this.systemResources.set(
        { resource_type: 'heap_used' },
        memoryUsage.heapUsed / 1024 / 1024 // MB
      );
      this.systemResources.set(
        { resource_type: 'heap_total' },
        memoryUsage.heapTotal / 1024 / 1024 // MB
      );
    } catch (error) {
      logger.error('Failed to update real-time metrics', { error: error.message });
    }
  }
  
  private async getChartsGenerated24h(): Promise<number> {
    const metrics = this.recentMetrics.get('chart_generation') || [];
    const cutoff = new Date(Date.now() - 24 * 60 * 60 * 1000);
    
    return metrics.filter(m => m.timestamp > cutoff).length;
  }
  
  private async getAverageGenerationTime(): Promise<number> {
    const metrics = this.recentMetrics.get('chart_generation') || [];
    const cutoff = new Date(Date.now() - 60 * 60 * 1000); // Last hour
    
    const recentMetrics = metrics.filter(m => m.timestamp > cutoff);
    if (recentMetrics.length === 0) return 0;
    
    const totalTime = recentMetrics.reduce((sum, m) => sum + m.duration, 0);
    return totalTime / recentMetrics.length;
  }
  
  private async getCacheStats(): Promise<{ hitRate: number; missRate: number }> {
    try {
      const cacheMetrics = await visualizationCache.getCacheMetrics();
      return {
        hitRate: cacheMetrics.hitRate,
        missRate: cacheMetrics.missRate,
      };
    } catch (error) {
      return { hitRate: 0, missRate: 0 };
    }
  }
  
  private async getErrorRate(): Promise<{ rate: number; total: number }> {
    const metrics = this.recentMetrics.get('chart_generation') || [];
    const cutoff = new Date(Date.now() - 60 * 60 * 1000); // Last hour
    
    const recentMetrics = metrics.filter(m => m.timestamp > cutoff);
    if (recentMetrics.length === 0) return { rate: 0, total: 0 };
    
    const errors = recentMetrics.filter(m => m.status === 'error').length;
    return {
      rate: errors / recentMetrics.length,
      total: errors,
    };
  }
  
  private async getTopChartTypes(): Promise<Array<{ type: string; count: number; percentage: number }>> {
    const metrics = this.recentMetrics.get('chart_generation') || [];
    const cutoff = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000); // Last week
    
    const recentMetrics = metrics.filter(m => m.timestamp > cutoff);
    const typeCounts = new Map<string, number>();
    
    recentMetrics.forEach(m => {
      const count = typeCounts.get(m.chartType) || 0;
      typeCounts.set(m.chartType, count + 1);
    });
    
    const total = recentMetrics.length;
    return Array.from(typeCounts.entries())
      .sort(([,a], [,b]) => b - a)
      .slice(0, 5)
      .map(([type, count]) => ({
        type,
        count,
        percentage: total > 0 ? Math.round((count / total) * 10000) / 100 : 0,
      }));
  }
  
  private async getTopJournalStyles(): Promise<Array<{ style: string; count: number; percentage: number }>> {
    const metrics = this.recentMetrics.get('chart_generation') || [];
    const cutoff = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000); // Last week
    
    const recentMetrics = metrics.filter(m => m.timestamp > cutoff);
    const styleCounts = new Map<string, number>();
    
    recentMetrics.forEach(m => {
      const style = m.journalStyle || 'default';
      const count = styleCounts.get(style) || 0;
      styleCounts.set(style, count + 1);
    });
    
    const total = recentMetrics.length;
    return Array.from(styleCounts.entries())
      .sort(([,a], [,b]) => b - a)
      .slice(0, 5)
      .map(([style, count]) => ({
        style,
        count,
        percentage: total > 0 ? Math.round((count / total) * 10000) / 100 : 0,
      }));
  }
  
  private async getSystemHealth(): Promise<{
    worker: 'healthy' | 'degraded' | 'unavailable';
    database: 'healthy' | 'degraded' | 'unavailable';
    cache: 'healthy' | 'degraded' | 'unavailable';
  }> {
    const [workerHealth, dbHealth, cacheHealth] = await Promise.all([
      this.checkWorkerHealth(),
      this.checkDatabaseHealth(),
      this.checkCacheHealth(),
    ]);
    
    return {
      worker: workerHealth.healthy ? 'healthy' : 'unavailable',
      database: dbHealth.healthy ? 'healthy' : 'unavailable',
      cache: cacheHealth.healthy ? 'healthy' : 'unavailable',
    };
  }
  
  private async getQualityMetrics(): Promise<{
    avgImageSize: number;
    successRate: number;
    timeouts: number;
  }> {
    const metrics = this.recentMetrics.get('chart_generation') || [];
    const cutoff = new Date(Date.now() - 24 * 60 * 60 * 1000); // Last 24 hours
    
    const recentMetrics = metrics.filter(m => m.timestamp > cutoff);
    
    if (recentMetrics.length === 0) {
      return { avgImageSize: 0, successRate: 0, timeouts: 0 };
    }
    
    const imageSizes = recentMetrics.filter(m => m.imageSize > 0).map(m => m.imageSize);
    const avgImageSize = imageSizes.length > 0 
      ? imageSizes.reduce((sum, size) => sum + size, 0) / imageSizes.length 
      : 0;
    
    const successes = recentMetrics.filter(m => m.status === 'success').length;
    const timeouts = recentMetrics.filter(m => m.status === 'timeout').length;
    const successRate = successes / recentMetrics.length;
    
    return {
      avgImageSize: Math.round(avgImageSize),
      successRate: Math.round(successRate * 10000) / 100, // Percentage
      timeouts,
    };
  }
  
  private async checkWorkerHealth(): Promise<{ healthy: boolean; latency?: number }> {
    // This would be implemented based on your worker health check
    return { healthy: true, latency: 0 };
  }
  
  private async checkDatabaseHealth(): Promise<{ healthy: boolean; latency?: number }> {
    if (!pool) return { healthy: false };
    
    const startTime = Date.now();
    try {
      await pool.query('SELECT 1');
      return { healthy: true, latency: Date.now() - startTime };
    } catch {
      return { healthy: false };
    }
  }
  
  private async checkCacheHealth(): Promise<{ healthy: boolean; latency?: number }> {
    try {
      return await visualizationCache.healthCheck();
    } catch {
      return { healthy: false };
    }
  }
  
  private async getQueueDepth(): Promise<number> {
    // Implement based on your queue system
    return 0;
  }
  
  private async getActiveJobsCount(): Promise<number> {
    // Implement based on your job tracking system
    return 0;
  }
  
  private async getMemoryUsage(): Promise<number> {
    const usage = process.memoryUsage();
    return usage.heapUsed / usage.heapTotal; // Percentage
  }
  
  private async getMetricValue(metricName: string): Promise<number> {
    switch (metricName) {
      case 'error_rate':
        return (await this.getErrorRate()).rate;
      case 'avg_response_time':
        return await this.getAverageGenerationTime();
      case 'queue_depth':
        return await this.getQueueDepth();
      case 'memory_usage':
        return await this.getMemoryUsage();
      default:
        return 0;
    }
  }
  
  private evaluateAlertCondition(value: number, threshold: number, operator: string): boolean {
    switch (operator) {
      case 'gt': return value > threshold;
      case 'lt': return value < threshold;
      case 'eq': return value === threshold;
      default: return false;
    }
  }
  
  private startBackgroundTasks(): void {
    // Update metrics every 30 seconds
    setInterval(async () => {
      await this.updateRealTimeMetrics();
    }, 30000);
    
    // Check alerts every 5 minutes
    setInterval(async () => {
      const alerts = await this.checkAlerts();
      if (alerts.length > 0) {
        logger.warn('Alert conditions triggered', { alerts });
      }
    }, 5 * 60 * 1000);
  }
}

// Singleton instance
export const visualizationMetrics = new VisualizationMetricsService();