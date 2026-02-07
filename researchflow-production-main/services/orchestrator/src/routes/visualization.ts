/**
 * Visualization Routes - Stage 8 Integration
 * 
 * Handles chart generation and figure management using Mercury backend.
 * Proxies requests to worker service's DataVisualizationAgent.
 * Stores generated figures in database with PHI scanning.
 * 
 * Routes:
 * - POST /api/visualization/generate - Generate chart via Mercury
 * - GET /api/visualization/figures/:researchId - List figures for research
 * - GET /api/visualization/figure/:id - Get specific figure
 * - DELETE /api/visualization/figure/:id - Delete figure
 * - GET /api/visualization/capabilities - Available chart types
 * - GET /api/visualization/health - Service health check
 */

import { Router, Request, Response } from 'express';
import rateLimit from 'express-rate-limit';
import { z } from 'zod';

import { config } from '../config/env';
import { visualizationConfig, getTimeoutForChartType, validateDataSize } from '../config/visualization.config';
import { pool } from '../db';
import { asyncHandler } from '../middleware/asyncHandler';
import { requirePermission } from '../middleware/rbac';
import { VisualizationErrorHandler, validateVisualizationRequest } from '../middleware/visualization-error-handler';
import { logAction } from '../services/audit-service';
import { createFiguresService, type FigureCreateInput } from '../services/figures.service';
import { visualizationCache } from '../services/visualization-cache.service';
import { visualizationMetrics } from '../services/visualization-metrics.service';
import { createLogger } from '../utils/logger';

const router = Router();
const logger = createLogger('visualization-route');

// Worker service URL
const WORKER_URL = config.workerUrl;

// Initialize figures service
const figuresService = pool ? createFiguresService(pool) : null;

// Rate limiting middleware
const createVisualizationRateLimit = () => {
  return rateLimit({
    windowMs: 60 * 1000, // 1 minute
    max: async (req) => {
      const userTier = req.user?.subscription_tier || 'free';
      const limits = {
        free: Math.floor(visualizationConfig.security.rateLimitPerMinute * 0.3),
        basic: Math.floor(visualizationConfig.security.rateLimitPerMinute * 0.6),
        premium: visualizationConfig.security.rateLimitPerMinute,
        enterprise: Math.floor(visualizationConfig.security.rateLimitPerMinute * 2),
      };
      return limits[userTier] || limits.free;
    },
    message: {
      error: 'RATE_LIMIT_EXCEEDED',
      message: `Too many visualization requests. Please wait before trying again. (Limit: ${visualizationConfig.security.rateLimitPerMinute}/minute)`,
      retryAfter: 60,
    },
    standardHeaders: true,
    legacyHeaders: false,
    skip: (req) => {
      return req.headers['x-system-request'] === 'true';
    },
  });
};

// Apply rate limiting to generation endpoints
const rateLimitMiddleware = visualizationConfig.security.enableRateLimit 
  ? createVisualizationRateLimit() 
  : (req: Request, res: Response, next: Function) => next();

// =============================================================================
// Request Schemas
// =============================================================================

/**
 * Chart generation request schema
 * Supports multiple chart types with flexible data structures
 */
const ChartGenerationRequestSchema = z.object({
  chart_type: z.enum([
    'bar_chart',
    'line_chart',
    'scatter_plot',
    'box_plot',
    'forest_plot',
    'flowchart',
    'kaplan_meier',
  ]),
  data: z.record(z.any()).describe('Chart data as key-value pairs'),
  config: z.object({
    title: z.string().optional(),
    x_label: z.string().optional(),
    y_label: z.string().optional(),
    show_error_bars: z.boolean().optional(),
    show_markers: z.boolean().optional(),
    show_trendline: z.boolean().optional(),
    show_confidence_bands: z.boolean().optional(),
    show_outliers: z.boolean().optional(),
    show_means: z.boolean().optional(),
    color_palette: z.string().optional(),
    journal_style: z.string().optional(),
    dpi: z.number().min(72).max(600).optional(),
    width: z.number().optional(),
    height: z.number().optional(),
  }).optional(),
  research_id: z.string().optional(),
  metadata: z.record(z.any()).optional(),
});

// =============================================================================
// Routes
// =============================================================================

/**
 * POST /api/visualization/generate
 * 
 * Generate a chart using Mercury backend and store in database.
 */
router.post(
  '/visualization/generate',
  rateLimitMiddleware,
  requirePermission('ANALYZE'),
  validateVisualizationRequest,
  asyncHandler(async (req: Request, res: Response) => {
    const startTime = Date.now();
    const requestId = `viz_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

    logger.info('Chart generation requested', { requestId, chartType: req.body.chart_type });
    
    // Update active jobs metric
    visualizationMetrics.updateActiveJobs('chart_generation', 1);
    
    try {

      // Validate request
      const parseResult = ChartGenerationRequestSchema.safeParse(req.body);
      if (!parseResult.success) {
        visualizationMetrics.recordChartGeneration({
          chartType: req.body.chart_type || 'unknown',
          status: 'error',
          duration: Date.now() - startTime,
          errorType: 'INVALID_REQUEST',
        });
        
        throw new Error('Invalid chart generation request');
      }

      const { chart_type, data, config, research_id, metadata } = parseResult.data;
      
      // Validate data size
      const dataArrays = Object.values(data).filter(Array.isArray);
      if (dataArrays.length > 0) {
        const maxLength = Math.max(...dataArrays.map((arr: any) => arr.length));
        const sizeValidation = validateDataSize(maxLength);
        if (!sizeValidation.valid) {
          visualizationMetrics.recordChartGeneration({
            chartType: chart_type,
            status: 'error',
            duration: Date.now() - startTime,
            errorType: 'DATA_TOO_LARGE',
            dataPoints: maxLength,
          });
          
          throw new Error(sizeValidation.message);
        }
      }
      
      // Check cache first
      const cacheKey = { chart_type, data, config: config || {} };
      const cachedResult = await visualizationCache.getCachedChart(cacheKey);
      
      if (cachedResult) {
        logger.info('Chart served from cache', { requestId, chartType: chart_type });
        
        visualizationMetrics.recordCacheOperation('hit');
        visualizationMetrics.recordChartGeneration({
          chartType: chart_type,
          journalStyle: config?.journal_style,
          status: 'success',
          duration: Date.now() - startTime,
          qualityProfile: config?.quality || 'standard',
        });
        
        return res.json({
          request_id: requestId,
          research_id: research_id || null,
          status: 'completed',
          result: {
            ...cachedResult,
            request_id: requestId,
          },
          duration_ms: Date.now() - startTime,
          cached: true,
        });
      }
      
      visualizationMetrics.recordCacheOperation('miss');
      // Determine endpoint based on chart type
      const endpoint = chart_type.replace('_', '-');
      const workerUrl = `${WORKER_URL}/api/visualization/${endpoint}`;
      
      // Get timeout based on chart complexity
      const timeout = getTimeoutForChartType(chart_type);

      logger.info('Calling worker visualization service', { 
        requestId,
        workerUrl,
        chartType: chart_type,
        timeout,
      });
      
      // Record request size
      const requestSize = JSON.stringify({ data, ...(config || {}) }).length;
      visualizationMetrics.recordChartGeneration({
        chartType: chart_type,
        status: 'success',
        duration: 0, // Will update after completion
        dataPoints: Object.values(data).reduce((max, val) => 
          Array.isArray(val) ? Math.max(max, val.length) : max, 0
        ),
      });

      // Call worker service
      const workerResponse = await fetch(workerUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Request-ID': requestId,
          'X-Research-ID': research_id || 'unknown',
        },
        body: JSON.stringify({
          data,
          ...(config || {}),
        }),
        signal: AbortSignal.timeout(timeout),
      });
      
      // Record worker request
      visualizationMetrics.recordWorkerRequest(endpoint, workerResponse.status);

      if (!workerResponse.ok) {
        const errorText = await workerResponse.text();
        logger.error('Worker visualization failed', {
          requestId,
          status: workerResponse.status,
          error: errorText,
        });

        return res.status(workerResponse.status).json({
          error: 'VISUALIZATION_FAILED',
          message: `Worker returned ${workerResponse.status}`,
          details: errorText,
          request_id: requestId,
        });
      }

      const visualizationResult = await workerResponse.json();

      // Store figure in database
      if (figuresService && visualizationResult.image_base64) {
        try {
          const imageBuffer = Buffer.from(visualizationResult.image_base64, 'base64');
          
          const figureInput: FigureCreateInput = {
            research_id: research_id || 'unknown',
            figure_type: chart_type as any,
            title: config?.title || `${chart_type.replace('_', ' ')} chart`,
            caption: visualizationResult.caption,
            alt_text: visualizationResult.alt_text,
            image_data: imageBuffer,
            image_format: visualizationResult.format || 'png',
            width: visualizationResult.width,
            height: visualizationResult.height,
            dpi: config?.dpi || 300,
            chart_config: config || {},
            journal_style: config?.journal_style,
            color_palette: config?.color_palette,
            source_data_hash: visualizationResult.data_hash,
            generated_by: 'DataVisualizationAgent',
            generation_duration_ms: Date.now() - startTime,
            agent_version: '1.0.0',
            metadata: {
              ...metadata,
              worker_response: {
                request_id: requestId,
                worker_figure_id: visualizationResult.figure_id,
              },
            },
          };

          const storedFigure = await figuresService.createFigure(figureInput);
          
          logger.info('Figure stored in database', {
            requestId,
            figureId: storedFigure.id,
            sizeBytes: storedFigure.size_bytes,
          });

          // Add database info to response
          visualizationResult.database_id = storedFigure.id;
          visualizationResult.stored_at = storedFigure.created_at;
        } catch (dbError) {
          logger.error('Failed to store figure in database', {
            requestId,
            error: dbError instanceof Error ? dbError.message : 'Unknown error',
          });
          // Continue without failing the request
        }
      }

      // Log successful generation
      await logAction({
        userId: req.user?.id || 'anonymous',
        action: 'CHART_GENERATED',
        resourceType: 'visualization',
        resourceId: visualizationResult.figure_id || requestId,
        metadata: {
          chart_type,
          research_id: research_id || null,
          duration_ms: Date.now() - startTime,
          size_bytes: visualizationResult.image_base64?.length || 0,
        },
      });

      logger.info('Chart generation completed', {
        requestId,
        chartType: chart_type,
        durationMs: Date.now() - startTime,
      });

      return res.json({
        request_id: requestId,
        research_id: research_id || null,
        status: 'completed',
        result: visualizationResult,
        duration_ms: Date.now() - startTime,
      });

    } catch (error) {
      const duration = Date.now() - startTime;
      
      // Record error metrics
      visualizationMetrics.recordChartGeneration({
        chartType: req.body.chart_type || 'unknown',
        status: 'error',
        duration,
        errorType: error instanceof Error ? error.message.includes('timeout') ? 'TIMEOUT' : 'PROCESSING_ERROR' : 'UNKNOWN_ERROR',
      });
      
      // Use enhanced error handler
      VisualizationErrorHandler.handleVisualizationError(error, req, res, () => {});
    } finally {
      // Update active jobs metric
      visualizationMetrics.updateActiveJobs('chart_generation', -1);
    }
  })
);

/**
 * GET /api/visualization/metrics
 * 
 * Get Prometheus metrics for monitoring
 */
router.get('/visualization/metrics', async (_req: Request, res: Response) => {
  try {
    const metrics = await visualizationMetrics.getPrometheusMetrics();
    res.set('Content-Type', 'text/plain');
    res.send(metrics);
  } catch (error) {
    logger.error('Failed to get metrics', { error: error.message });
    res.status(500).send('Error retrieving metrics');
  }
});

/**
 * GET /api/visualization/dashboard
 * 
 * Get dashboard metrics for UI
 */
router.get(
  '/visualization/dashboard',
  requirePermission('VIEW'),
  asyncHandler(async (_req: Request, res: Response) => {
    try {
      const dashboardData = await visualizationMetrics.getDashboardMetrics();
      const cacheStats = await visualizationCache.getCacheStats();
      const healthStatus = await visualizationMetrics.getHealthStatus();
      
      res.json({
        metrics: dashboardData,
        cache: cacheStats,
        health: healthStatus,
        timestamp: new Date().toISOString(),
      });
    } catch (error) {
      logger.error('Failed to get dashboard data', { error: error.message });
      res.status(500).json({
        error: 'Failed to retrieve dashboard data',
        message: error.message,
      });
    }
  })
);

/**
 * POST /api/visualization/cache/clear
 * 
 * Clear visualization cache (admin only)
 */
router.post(
  '/visualization/cache/clear',
  requirePermission('ADMIN'),
  asyncHandler(async (_req: Request, res: Response) => {
    try {
      const cleared = await visualizationCache.clearCache();
      
      logger.info('Visualization cache cleared', { clearedEntries: cleared });
      
      res.json({
        success: true,
        cleared_entries: cleared,
        timestamp: new Date().toISOString(),
      });
    } catch (error) {
      logger.error('Failed to clear cache', { error: error.message });
      res.status(500).json({
        error: 'Failed to clear cache',
        message: error.message,
      });
    }
  })
);

/**
 * GET /api/visualization/capabilities
 * 
 * Get available chart types, styles, and palettes.
 */
router.get(
  '/visualization/capabilities',
  asyncHandler(async (_req: Request, res: Response) => {
    try {
      const workerResponse = await fetch(`${WORKER_URL}/api/visualization/capabilities`, {
        method: 'GET',
        signal: AbortSignal.timeout(5000),
      });

      if (!workerResponse.ok) {
        throw new Error(`Worker returned ${workerResponse.status}`);
      }

      const capabilities = await workerResponse.json();
      return res.json(capabilities);

    } catch (error) {
      logger.error('Failed to fetch capabilities', {
        error: error instanceof Error ? error.message : 'Unknown error',
      });

      // Return static capabilities as fallback
      return res.json({
        chart_types: [
          'bar_chart',
          'line_chart',
          'scatter_plot',
          'box_plot',
          'forest_plot',
          'flowchart',
          'kaplan_meier',
        ],
        journal_styles: [
          'nature',
          'jama',
          'nejm',
          'lancet',
          'bmj',
          'plos',
          'apa',
        ],
        color_palettes: [
          'colorblind_safe',
          'grayscale',
          'viridis',
          'pastel',
          'bold',
        ],
        export_formats: ['png', 'svg', 'pdf'],
        dpi_options: [72, 150, 300, 600],
      });
    }
  })
);

/**
 * GET /api/visualization/health
 * 
 * Health check for visualization service.
 */
router.get('/visualization/health', async (_req: Request, res: Response) => {
  let workerStatus = 'unknown';

  try {
    const workerResponse = await fetch(`${WORKER_URL}/api/visualization/health`, {
      method: 'GET',
      signal: AbortSignal.timeout(5000),
    });
    workerStatus = workerResponse.ok ? 'healthy' : 'unhealthy';
  } catch {
    workerStatus = 'unreachable';
  }

  res.json({
    status: workerStatus === 'healthy' ? 'healthy' : 'degraded',
    service: 'visualization',
    stage: 8,
    worker_url: WORKER_URL,
    worker_status: workerStatus,
    timestamp: new Date().toISOString(),
  });
});

/**
 * GET /api/visualization/figures/:researchId
 * 
 * List all figures for a research project.
 */
router.get(
  '/visualization/figures/:researchId',
  requirePermission('VIEW'),
  asyncHandler(async (req: Request, res: Response) => {
    const { researchId } = req.params;
    const { 
      figure_type, 
      phi_scan_status, 
      limit = '50', 
      offset = '0' 
    } = req.query;

    logger.info('Listing figures', { researchId });

    if (!figuresService) {
      return res.status(503).json({
        error: 'DATABASE_UNAVAILABLE',
        message: 'Database service not available',
      });
    }

    try {
      const result = await figuresService.listFigures({
        research_id: researchId,
        figure_type: figure_type as any,
        phi_scan_status: phi_scan_status as any,
        limit: parseInt(limit as string),
        offset: parseInt(offset as string),
      });

      // Remove image data from list response for performance
      const figuresWithoutImageData = result.figures.map(figure => ({
        ...figure,
        image_data: undefined,
        has_image_data: true,
      }));

      return res.json({
        research_id: researchId,
        figures: figuresWithoutImageData,
        total: result.total,
        pagination: {
          limit: parseInt(limit as string),
          offset: parseInt(offset as string),
        },
      });
    } catch (error) {
      logger.error('Failed to list figures', {
        researchId,
        error: error instanceof Error ? error.message : 'Unknown error',
      });

      return res.status(500).json({
        error: 'DATABASE_ERROR',
        message: 'Failed to retrieve figures',
      });
    }
  })
);

/**
 * GET /api/visualization/figure/:id
 * 
 * Get a specific figure by ID.
 */
router.get(
  '/visualization/figure/:id',
  requirePermission('VIEW'),
  asyncHandler(async (req: Request, res: Response) => {
    const { id } = req.params;
    const { include_image = 'false' } = req.query;

    logger.info('Fetching figure', { figureId: id });

    if (!figuresService) {
      return res.status(503).json({
        error: 'DATABASE_UNAVAILABLE',
        message: 'Database service not available',
      });
    }

    try {
      const figure = await figuresService.getFigureById(id);

      if (!figure) {
        return res.status(404).json({
          error: 'NOT_FOUND',
          message: 'Figure not found',
          figure_id: id,
        });
      }

      // Optionally exclude image data for metadata-only requests
      const response = {
        ...figure,
        image_data: include_image === 'true' 
          ? figure.image_data.toString('base64')
          : undefined,
        has_image_data: true,
      };

      return res.json(response);
    } catch (error) {
      logger.error('Failed to fetch figure', {
        figureId: id,
        error: error instanceof Error ? error.message : 'Unknown error',
      });

      return res.status(500).json({
        error: 'DATABASE_ERROR',
        message: 'Failed to retrieve figure',
      });
    }
  })
);

/**
 * DELETE /api/visualization/figure/:id
 * 
 * Delete a figure.
 */
router.delete(
  '/visualization/figure/:id',
  requirePermission('DELETE'),
  asyncHandler(async (req: Request, res: Response) => {
    const { id } = req.params;

    logger.info('Deleting figure', { figureId: id });

    if (!figuresService) {
      return res.status(503).json({
        error: 'DATABASE_UNAVAILABLE',
        message: 'Database service not available',
      });
    }

    try {
      const deleted = await figuresService.deleteFigure(id);

      if (!deleted) {
        return res.status(404).json({
          error: 'NOT_FOUND',
          message: 'Figure not found',
          figure_id: id,
        });
      }

      // Log deletion
      await logAction({
        userId: req.user?.id || 'anonymous',
        action: 'FIGURE_DELETED',
        resourceType: 'figure',
        resourceId: id,
        metadata: { deleted_at: new Date().toISOString() },
      });

      return res.json({
        success: true,
        figure_id: id,
        deleted_at: new Date().toISOString(),
      });
    } catch (error) {
      logger.error('Failed to delete figure', {
        figureId: id,
        error: error instanceof Error ? error.message : 'Unknown error',
      });

      return res.status(500).json({
        error: 'DATABASE_ERROR',
        message: 'Failed to delete figure',
      });
    }
  })
);

/**
 * GET /api/visualization/stats/:researchId
 * 
 * Get figure statistics for a research project.
 */
router.get(
  '/visualization/stats/:researchId',
  requirePermission('VIEW'),
  asyncHandler(async (req: Request, res: Response) => {
    const { researchId } = req.params;

    logger.info('Fetching figure statistics', { researchId });

    if (!figuresService) {
      return res.status(503).json({
        error: 'DATABASE_UNAVAILABLE',
        message: 'Database service not available',
      });
    }

    try {
      const stats = await figuresService.getFigureStats(researchId);

      return res.json({
        research_id: researchId,
        statistics: {
          ...stats,
          size_mb: (stats.total_size_bytes / (1024 * 1024)).toFixed(2),
        },
        timestamp: new Date().toISOString(),
      });
    } catch (error) {
      logger.error('Failed to fetch figure statistics', {
        researchId,
        error: error instanceof Error ? error.message : 'Unknown error',
      });

      return res.status(500).json({
        error: 'DATABASE_ERROR',
        message: 'Failed to retrieve statistics',
      });
    }
  })
);

/**
 * PATCH /api/visualization/figure/:id/phi-scan
 * 
 * Update PHI scan results for a figure.
 */
router.patch(
  '/visualization/figure/:id/phi-scan',
  requirePermission('MODERATE'),
  asyncHandler(async (req: Request, res: Response) => {
    const { id } = req.params;
    const { phi_scan_status, phi_risk_level, phi_findings } = req.body;

    logger.info('Updating PHI scan results', { 
      figureId: id,
      phiScanStatus: phi_scan_status,
    });

    if (!figuresService) {
      return res.status(503).json({
        error: 'DATABASE_UNAVAILABLE',
        message: 'Database service not available',
      });
    }

    if (!phi_scan_status || !['PENDING', 'PASS', 'FAIL', 'OVERRIDE'].includes(phi_scan_status)) {
      return res.status(400).json({
        error: 'INVALID_REQUEST',
        message: 'Valid phi_scan_status is required',
      });
    }

    try {
      const updatedFigure = await figuresService.updatePhiScanResult(
        id,
        phi_scan_status,
        phi_risk_level,
        phi_findings
      );

      if (!updatedFigure) {
        return res.status(404).json({
          error: 'NOT_FOUND',
          message: 'Figure not found',
          figure_id: id,
        });
      }

      // Log PHI scan update
      await logAction({
        userId: req.user?.id || 'anonymous',
        action: 'PHI_SCAN_UPDATED',
        resourceType: 'figure',
        resourceId: id,
        metadata: {
          phi_scan_status,
          phi_risk_level: phi_risk_level || null,
          findings_count: phi_findings ? phi_findings.length : 0,
        },
      });

      return res.json({
        success: true,
        figure_id: id,
        phi_scan_status: updatedFigure.phi_scan_status,
        phi_risk_level: updatedFigure.phi_risk_level,
        updated_at: updatedFigure.updated_at,
      });
    } catch (error) {
      logger.error('Failed to update PHI scan results', {
        figureId: id,
        error: error instanceof Error ? error.message : 'Unknown error',
      });

      return res.status(500).json({
        error: 'DATABASE_ERROR',
        message: 'Failed to update PHI scan results',
      });
    }
  })
);

export default router;
