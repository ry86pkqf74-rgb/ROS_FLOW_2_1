/**
 * AI Bridge API Routes
 *
 * Bridge endpoints for Python LangGraph agents to access the TypeScript AI Router.
 * These endpoints wrap the existing AI Router functionality and provide a clean
 * interface for Python workers to make LLM calls.
 *
 * Architecture: Python Worker → AI Bridge → AI Router → LLM Provider
 */

import { Router, type Request, type Response } from 'express';
import { z } from 'zod';
import axios from 'axios';
import { asyncHandler } from '../middleware/asyncHandler';
import { requirePermission } from '../middleware/rbac';
import { createLogger } from '../utils/logger';
import { logAction } from '../services/audit-service';
import { getAIBridgeConfig } from '../config/ai-bridge.config';
import { 
  aiBridgeMetricsMiddleware, 
  metricsRegistry 
} from '../middleware/ai-bridge-metrics';
import { 
  rateLimitMiddleware,
  costProtectionMiddleware,
  circuitBreakerMiddleware,
  recordCircuitBreakerOutcome,
  updateCostTracking
} from '../middleware/ai-bridge-protection';
import { getConnectionPool } from '../middleware/ai-bridge-connection-pool';
import { getBatchOptimizer } from '../middleware/ai-bridge-batch-optimizer';
import { 
  enhancedErrorHandlerMiddleware,
  getAIBridgeErrorHandler 
} from '../middleware/ai-bridge-error-handler';

const router = Router();
const logger = createLogger('ai-bridge');
const bridgeConfig = getAIBridgeConfig();
const connectionPool = getConnectionPool();
const batchOptimizer = getBatchOptimizer();
const errorHandler = getAIBridgeErrorHandler();

// Apply middleware to all routes
router.use(aiBridgeMetricsMiddleware);
router.use(rateLimitMiddleware);
router.use(costProtectionMiddleware);
router.use(circuitBreakerMiddleware);

// ============================
// Validation Schemas
// ============================

const ModelOptionsSchema = z.object({
  taskType: z.string(),
  stageId: z.number().int().positive().optional(),
  modelTier: z.enum(['ECONOMY', 'STANDARD', 'PREMIUM']).optional(),
  governanceMode: z.enum(['DEMO', 'LIVE']).optional(),
  requirePhiCompliance: z.boolean().optional(),
  budgetLimit: z.number().positive().optional(),
  maxTokens: z.number().positive().optional(),
  temperature: z.number().min(0).max(2).optional(),
  streamResponse: z.boolean().optional(),
});

const AgentMetadataSchema = z.object({
  agentId: z.string(),
  projectId: z.string(),
  runId: z.string(),
  threadId: z.string(),
  stageRange: z.tuple([z.number(), z.number()]),
  currentStage: z.number(),
});

const InvokeRequestSchema = z.object({
  prompt: z.string().min(1),
  options: ModelOptionsSchema,
  metadata: AgentMetadataSchema.optional(),
});

const BatchRequestSchema = z.object({
  prompts: z.array(z.string().min(1)),
  options: ModelOptionsSchema,
  metadata: AgentMetadataSchema.optional(),
});

const StreamRequestSchema = z.object({
  prompt: z.string().min(1),
  options: ModelOptionsSchema,
  metadata: AgentMetadataSchema.optional(),
});

// ============================
// Helper Functions
// ============================

/**
 * Convert bridge model tier to router tier format
 */
function convertModelTier(bridgeTier?: string): string {
  return bridgeConfig.tierMappings[bridgeTier as keyof typeof bridgeConfig.tierMappings] || bridgeConfig.tierMappings.STANDARD;
}

/**
 * Get internal AI Router routing with connection pooling
 */
async function getAIRouting(prompt: string, options: any, priority: number = 0): Promise<{
  selectedTier: string;
  model: string;
  costEstimate: any;
}> {
  const estimatedInputTokens = Math.ceil(prompt.length / 4);
  const estimatedOutputTokens = Math.ceil(estimatedInputTokens * 0.5);

  try {
    const response = await connectionPool.request(
      'http://localhost:3001/api/ai/router/route',
      {
        taskType: options.taskType,
        estimatedInputTokens,
        estimatedOutputTokens,
        governanceMode: options.governanceMode || 'DEMO',
        preferredTier: convertModelTier(options.modelTier),
        budgetLimit: options.budgetLimit,
        requirePhiCompliance: options.requirePhiCompliance ?? true,
        stageId: options.stageId,
      },
      priority
    );

    return {
      selectedTier: response.data.selectedTier,
      model: response.data.model,
      costEstimate: response.data.costEstimate,
    };
  } catch (error) {
    logger.warn('AI Router routing failed, using defaults', { error });
    return {
      selectedTier: 'standard',
      model: 'claude-3-5-sonnet-20241022',
      costEstimate: { total: 0.01, input: 0.005, output: 0.005 },
    };
  }
}

/**
 * Process batch chunk with different strategies
 */
async function processBatchChunk(
  requests: any[],
  strategy: 'sequential' | 'parallel' | 'adaptive'
): Promise<any[]> {
  const results: any[] = [];
  
  switch (strategy) {
    case 'parallel':
      // Process all requests in parallel
      const parallelPromises = requests.map(async (request, index) => {
        try {
          const routing = await getAIRouting(request.prompt, request.options, 1);
          const llmResponse = await callLLMProvider(request.prompt, routing.model, request.options);
          return {
            content: llmResponse.content,
            usage: llmResponse.usage,
            cost: llmResponse.cost,
            model: routing.model,
            tier: routing.selectedTier,
            finishReason: llmResponse.finishReason,
          };
        } catch (error) {
          return {
            error: 'LLM_CALL_FAILED',
            message: error instanceof Error ? error.message : 'Unknown error',
          };
        }
      });
      return await Promise.all(parallelPromises);
      
    case 'sequential':
      // Process requests one by one
      for (const request of requests) {
        try {
          const routing = await getAIRouting(request.prompt, request.options, 2);
          const llmResponse = await callLLMProvider(request.prompt, routing.model, request.options);
          results.push({
            content: llmResponse.content,
            usage: llmResponse.usage,
            cost: llmResponse.cost,
            model: routing.model,
            tier: routing.selectedTier,
            finishReason: llmResponse.finishReason,
          });
        } catch (error) {
          results.push({
            error: 'LLM_CALL_FAILED',
            message: error instanceof Error ? error.message : 'Unknown error',
          });
        }
      }
      return results;
      
    case 'adaptive':
      // Process in small parallel groups
      const chunkSize = 3;
      for (let i = 0; i < requests.length; i += chunkSize) {
        const chunk = requests.slice(i, i + chunkSize);
        const chunkResults = await processBatchChunk(chunk, 'parallel');
        results.push(...chunkResults);
        
        // Small delay between chunks to avoid overwhelming
        if (i + chunkSize < requests.length) {
          await new Promise(resolve => setTimeout(resolve, 500));
        }
      }
      return results;
      
    default:
      throw new Error(`Unknown processing strategy: ${strategy}`);
  }
}

/**
 * Mock LLM call (until actual AI provider integration)
 */
async function callLLMProvider(
  prompt: string,
  model: string,
  options: any
): Promise<{
  content: string;
  usage: { totalTokens: number; promptTokens: number; completionTokens: number };
  cost: { total: number; input: number; output: number };
  finishReason: string;
}> {
  // Simulate processing time
  await new Promise(resolve => setTimeout(resolve, 1000 + Math.random() * 2000));

  // Mock response based on prompt
  const promptTokens = Math.ceil(prompt.length / 4);
  const completionTokens = Math.ceil(promptTokens * 0.7 + Math.random() * 200);
  const totalTokens = promptTokens + completionTokens;

  // Calculate mock costs based on tier
  const tierCosts = {
    economy: { input: 0.0001, output: 0.00015 },
    standard: { input: 0.001, output: 0.0015 },
    premium: { input: 0.01, output: 0.015 },
  };

  const costs = tierCosts.standard; // Default
  const inputCost = promptTokens * costs.input;
  const outputCost = completionTokens * costs.output;

  return {
    content: `[AI Bridge Mock Response for ${options.taskType}]\n\nThis is a simulated response for the prompt: "${prompt.substring(0, 100)}..."\n\nModel: ${model}\nTokens: ${totalTokens}\nTask: ${options.taskType}`,
    usage: {
      totalTokens,
      promptTokens,
      completionTokens,
    },
    cost: {
      total: inputCost + outputCost,
      input: inputCost,
      output: outputCost,
    },
    finishReason: 'stop',
  };
}

// ============================
// Bridge Endpoints
// ============================

/**
 * POST /api/ai-bridge/invoke
 * Single LLM invocation
 */
router.post(
  '/invoke',
  requirePermission('ANALYZE'),
  asyncHandler(async (req: Request, res: Response) => {
    const user = req.user;
    if (!user) {
      return res.status(401).json({
        error: 'AUTHENTICATION_REQUIRED',
        message: 'Authentication required for AI Bridge access',
      });
    }

    // Validate request
    const validation = InvokeRequestSchema.safeParse(req.body);
    if (!validation.success) {
      return res.status(400).json({
        error: 'VALIDATION_ERROR',
        message: 'Invalid request body',
        details: validation.error.flatten(),
      });
    }

    const { prompt, options, metadata } = validation.data;

    try {
      // Step 1: Get AI Router routing
      const routing = await getAIRouting(prompt, options);

      // Step 2: Make LLM call
      const llmResponse = await callLLMProvider(prompt, routing.model, options);

      // Step 3: Audit log the request
      await logAction({
        eventType: 'AI_BRIDGE_INVOKE',
        action: 'LLM_CALL_COMPLETED',
        userId: user.id,
        resourceType: 'ai_bridge',
        resourceId: metadata?.runId || `invoke_${Date.now()}`,
        details: {
          taskType: options.taskType,
          selectedTier: routing.selectedTier,
          model: routing.model,
          tokenUsage: llmResponse.usage,
          cost: llmResponse.cost,
          stageId: options.stageId,
          agentId: metadata?.agentId,
          projectId: metadata?.projectId,
          governanceMode: options.governanceMode,
        },
      });

      // Step 4: Record success and update cost tracking
      recordCircuitBreakerOutcome(true);
      updateCostTracking(user.id, llmResponse.cost.total);

      // Step 5: Return bridge response format
      res.json({
        content: llmResponse.content,
        usage: llmResponse.usage,
        cost: llmResponse.cost,
        model: routing.model,
        tier: routing.selectedTier,
        finishReason: llmResponse.finishReason,
        metadata: {
          requestId: `bridge_${Date.now()}`,
          routingMethod: 'ai_router',
          bridgeVersion: '1.0.0',
        },
      });
    } catch (error) {
      recordCircuitBreakerOutcome(false);
      
      logger.logError('AI Bridge invoke failed', error as Error, {
        userId: user.id,
        taskType: options.taskType,
        agentId: metadata?.agentId,
      });

      res.status(500).json({
        error: 'LLM_CALL_FAILED',
        message: 'Failed to complete LLM invocation',
        details: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  })
);

/**
 * POST /api/ai-bridge/batch
 * Batch LLM processing
 */
router.post(
  '/batch',
  requirePermission('ANALYZE'),
  asyncHandler(async (req: Request, res: Response) => {
    const user = req.user;
    if (!user) {
      return res.status(401).json({
        error: 'AUTHENTICATION_REQUIRED',
        message: 'Authentication required for AI Bridge access',
      });
    }

    // Validate request
    const validation = BatchRequestSchema.safeParse(req.body);
    if (!validation.success) {
      return res.status(400).json({
        error: 'VALIDATION_ERROR',
        message: 'Invalid batch request body',
        details: validation.error.flatten(),
      });
    }

    const { prompts, options, metadata } = validation.data;

    // Create batch requests for optimization
    const batchRequests = prompts.map(prompt => ({ prompt, options, metadata }));
    
    // Validate batch
    const validation_result = batchOptimizer.validateBatch(batchRequests);
    if (!validation_result.valid) {
      return res.status(400).json({
        error: 'BATCH_VALIDATION_FAILED',
        message: 'Batch validation failed',
        errors: validation_result.errors,
      });
    }

    // Optimize batch processing
    const optimizedBatches = batchOptimizer.optimizeBatch(batchRequests);
    const recommendations = batchOptimizer.getProcessingRecommendations(optimizedBatches);
    
    // Log optimization results
    logger.info('Batch optimization completed', {
      originalSize: prompts.length,
      optimizedBatches: optimizedBatches.length,
      estimatedCost: recommendations.totalEstimatedCost,
      estimatedDuration: recommendations.estimatedDuration,
      strategies: optimizedBatches.map(batch => batch.processingStrategy)
    });

    try {
      const startTime = Date.now();
      const responses: any[] = [];
      let totalCost = 0;
      let successCount = 0;
      let errorCount = 0;

      // Process optimized batches
      for (const batch of optimizedBatches) {
        const batchResponses = await processBatchChunk(
          batch.requests,
          batch.processingStrategy
        );
        
        batchResponses.forEach((response, localIndex) => {
          const globalIndex = responses.length;
          
          if (response.error) {
            responses.push({
              error: response.error,
              message: response.message,
              index: globalIndex,
            });
            errorCount++;
          } else {
            responses.push({
              content: response.content,
              usage: response.usage,
              cost: response.cost,
              model: response.model,
              tier: response.tier,
              finishReason: response.finishReason,
              index: globalIndex,
            });
            totalCost += response.cost.total;
            successCount++;
          }
        });
      }

      const processingTime = Date.now() - startTime;

      // Audit log the batch request
      await logAction({
        eventType: 'AI_BRIDGE_BATCH',
        action: 'BATCH_COMPLETED',
        userId: user.id,
        resourceType: 'ai_bridge',
        resourceId: metadata?.runId || `batch_${Date.now()}`,
        details: {
          taskType: options.taskType,
          batchSize: prompts.length,
          successCount,
          errorCount,
          totalCost,
          processingTimeMs: processingTime,
          agentId: metadata?.agentId,
          projectId: metadata?.projectId,
        },
      });

      // Update cost tracking
      updateCostTracking(user.id, totalCost);
      recordCircuitBreakerOutcome(errorCount < prompts.length / 2); // Success if less than 50% failures

      res.json({
        responses,
        totalCost,
        averageLatency: processingTime / prompts.length,
        successCount,
        errorCount,
        metadata: {
          requestId: `bridge_batch_${Date.now()}`,
          processingTimeMs: processingTime,
          bridgeVersion: '1.0.0',
        },
      });
    } catch (error) {
      recordCircuitBreakerOutcome(false);
      
      logger.logError('AI Bridge batch processing failed', error as Error, {
        userId: user.id,
        batchSize: prompts.length,
        taskType: options.taskType,
      });

      res.status(500).json({
        error: 'BATCH_PROCESSING_FAILED',
        message: 'Failed to process batch request',
        details: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  })
);

/**
 * POST /api/ai-bridge/stream
 * Streaming LLM responses (Server-Sent Events)
 */
router.post(
  '/stream',
  requirePermission('ANALYZE'),
  asyncHandler(async (req: Request, res: Response) => {
    const user = req.user;
    if (!user) {
      return res.status(401).json({
        error: 'AUTHENTICATION_REQUIRED',
        message: 'Authentication required for AI Bridge access',
      });
    }

    // Validate request
    const validation = StreamRequestSchema.safeParse(req.body);
    if (!validation.success) {
      return res.status(400).json({
        error: 'VALIDATION_ERROR',
        message: 'Invalid stream request body',
        details: validation.error.flatten(),
      });
    }

    const { prompt, options, metadata } = validation.data;

    try {
      // Setup SSE headers
      res.writeHead(200, {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Cache-Control',
      });

      // Get routing
      const routing = await getAIRouting(prompt, options);

      // Send initial status
      res.write(`data: ${JSON.stringify({
        type: 'status',
        status: 'starting',
        tier: routing.selectedTier,
        model: routing.model,
      })}\n\n`);

      // Simulate streaming response
      const fullResponse = await callLLMProvider(prompt, routing.model, options);
      const words = fullResponse.content.split(' ');

      // Stream words with delays
      let streamedContent = '';
      for (let i = 0; i < words.length; i++) {
        const word = words[i] + ' ';
        streamedContent += word;

        res.write(`data: ${JSON.stringify({
          type: 'content',
          content: word,
          index: i,
        })}\n\n`);

        // Add realistic delay
        await new Promise(resolve => setTimeout(resolve, 50 + Math.random() * 100));
      }

      // Send completion
      res.write(`data: ${JSON.stringify({
        type: 'complete',
        finalContent: streamedContent.trim(),
        usage: fullResponse.usage,
        cost: fullResponse.cost,
        model: routing.model,
        tier: routing.selectedTier,
        finishReason: fullResponse.finishReason,
      })}\n\n`);

      res.write('data: [DONE]\n\n');
      res.end();

      // Record success and update cost tracking
      recordCircuitBreakerOutcome(true);
      updateCostTracking(user.id, fullResponse.cost.total);

      // Audit log
      await logAction({
        eventType: 'AI_BRIDGE_STREAM',
        action: 'STREAM_COMPLETED',
        userId: user.id,
        resourceType: 'ai_bridge',
        resourceId: metadata?.runId || `stream_${Date.now()}`,
        details: {
          taskType: options.taskType,
          selectedTier: routing.selectedTier,
          model: routing.model,
          usage: fullResponse.usage,
          cost: fullResponse.cost,
          agentId: metadata?.agentId,
        },
      });
    } catch (error) {
      recordCircuitBreakerOutcome(false);
      
      logger.logError('AI Bridge streaming failed', error as Error, {
        userId: user.id,
        taskType: options.taskType,
      });

      res.write(`data: ${JSON.stringify({
        type: 'error',
        error: 'STREAM_FAILED',
        message: error instanceof Error ? error.message : 'Unknown error',
      })}\n\n`);

      res.end();
    }
  })
);

/**
 * GET /api/ai-bridge/health
 * Bridge health check
 */
router.get(
  '/health',
  asyncHandler(async (req: Request, res: Response) => {
    const startTime = Date.now();

    try {
      // Check AI Router availability
      let aiRouterHealthy = false;
      let aiRouterLatency = 0;

      try {
        const aiRouterStart = Date.now();
        const routerResponse = await axios.get('http://localhost:3001/api/ai/router/tiers', {
          timeout: 5000,
        });
        aiRouterLatency = Date.now() - aiRouterStart;
        aiRouterHealthy = routerResponse.status === 200;
      } catch (error) {
        logger.warn('AI Router health check failed', { error });
      }

      const totalLatency = Date.now() - startTime;

      const healthStatus = {
        status: aiRouterHealthy ? 'healthy' : 'degraded',
        timestamp: new Date().toISOString(),
        bridge: {
          version: '1.0.0',
          uptime: process.uptime(),
          healthy: true,
        },
        dependencies: {
          aiRouter: {
            healthy: aiRouterHealthy,
            latencyMs: aiRouterLatency,
          },
        },
        performance: {
          totalLatencyMs: totalLatency,
          memoryUsage: process.memoryUsage(),
        },
              features: bridgeConfig.features,
      };

      res.status(aiRouterHealthy ? 200 : 503).json(healthStatus);
    } catch (error) {
      logger.logError('Bridge health check failed', error as Error);

      res.status(503).json({
        status: 'unhealthy',
        timestamp: new Date().toISOString(),
        error: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  })
);

/**
 * GET /api/ai-bridge/capabilities
 * Get bridge capabilities and supported features
 */
router.get(
  '/capabilities',
  asyncHandler(async (req: Request, res: Response) => {
    res.json({
      version: bridgeConfig.version,
      endpoints: [
        { path: '/invoke', method: 'POST', description: 'Single LLM invocation' },
        { path: '/batch', method: 'POST', description: 'Batch LLM processing' },
        { path: '/stream', method: 'POST', description: 'Streaming LLM responses' },
        { path: '/health', method: 'GET', description: 'Health check' },
        { path: '/capabilities', method: 'GET', description: 'Capabilities info' },
        { path: '/metrics', method: 'GET', description: 'Prometheus metrics' },
      ],
      features: {
        modelTiers: Object.keys(bridgeConfig.tierMappings),
        governanceModes: ['DEMO', 'LIVE'],
        ...bridgeConfig.features,
      },
      limits: bridgeConfig.limits,
      supportedTaskTypes: Object.entries(bridgeConfig.taskTypes).map(([taskType, config]) => ({
        type: taskType,
        description: config.description,
        recommendedTier: config.recommendedTier,
        requiresPhiCompliance: config.requiresPhiCompliance,
      })),
    });
  })
);

/**
 * GET /api/ai-bridge/metrics
 * Prometheus metrics endpoint
 */
router.get(
  '/metrics',
  asyncHandler(async (req: Request, res: Response) => {
    try {
      res.set('Content-Type', metricsRegistry.contentType);
      const metrics = await metricsRegistry.metrics();
      res.send(metrics);
    } catch (error) {
      logger.logError('Failed to generate metrics', error as Error);
      res.status(500).json({
        error: 'METRICS_FAILED',
        message: 'Failed to generate Prometheus metrics',
      });
    }
  })
);

/**
 * GET /api/ai-bridge/pool-stats
 * Get connection pool statistics
 */
router.get(
  '/pool-stats',
  asyncHandler(async (req: Request, res: Response) => {
    const stats = connectionPool.getStats();
    
    res.json({
      timestamp: new Date().toISOString(),
      connectionPool: stats,
      bridgeVersion: bridgeConfig.version,
    });
  })
);

// Enhanced error handler as final middleware
router.use(enhancedErrorHandlerMiddleware);

export default router;