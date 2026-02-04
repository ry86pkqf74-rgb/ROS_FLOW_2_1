/**
 * AI Bridge Metrics Middleware
 * 
 * Tracks performance, usage, and cost metrics for the AI Bridge.
 * Essential for production monitoring and optimization.
 */

import { Request, Response, NextFunction } from 'express';
import { createLogger } from '../utils/logger';
import { register, Counter, Histogram, Gauge } from 'prom-client';

const logger = createLogger('ai-bridge-metrics');

// Metrics definitions
const bridgeRequestsTotal = new Counter({
  name: 'ai_bridge_requests_total',
  help: 'Total number of AI Bridge requests',
  labelNames: ['endpoint', 'status', 'model_tier', 'task_type']
});

const bridgeRequestDuration = new Histogram({
  name: 'ai_bridge_request_duration_seconds',
  help: 'AI Bridge request duration in seconds',
  labelNames: ['endpoint', 'model_tier'],
  buckets: [0.1, 0.5, 1, 2, 5, 10, 30]
});

const bridgeCostTotal = new Counter({
  name: 'ai_bridge_cost_total_dollars',
  help: 'Total cost incurred through AI Bridge',
  labelNames: ['model_tier', 'task_type', 'agent_id']
});

const bridgeTokensTotal = new Counter({
  name: 'ai_bridge_tokens_total',
  help: 'Total tokens processed through AI Bridge',
  labelNames: ['type', 'model_tier'] // type: 'input' | 'output'
});

const bridgeActiveRequests = new Gauge({
  name: 'ai_bridge_active_requests',
  help: 'Current number of active AI Bridge requests'
});

export const aiBridgeMetricsMiddleware = (req: Request, res: Response, next: NextFunction) => {
  const startTime = Date.now();
  const endpoint = req.path.replace('/api/ai-bridge/', '');
  
  bridgeActiveRequests.inc();
  
  // Capture original response methods
  const originalJson = res.json;
  const originalStatus = res.status;
  
  let statusCode = 200;
  let responseData: any = null;
  
  // Override res.status to capture status code
  res.status = function(code: number) {
    statusCode = code;
    return originalStatus.call(this, code);
  };
  
  // Override res.json to capture response data and metrics
  res.json = function(data: any) {
    responseData = data;
    
    // Record metrics
    const duration = (Date.now() - startTime) / 1000;
    const modelTier = req.body?.options?.modelTier || 'unknown';
    const taskType = req.body?.options?.taskType || 'unknown';
    const agentId = req.body?.metadata?.agentId || 'unknown';
    
    bridgeRequestsTotal
      .labels(endpoint, statusCode.toString(), modelTier, taskType)
      .inc();
      
    bridgeRequestDuration
      .labels(endpoint, modelTier)
      .observe(duration);
    
    // Track cost and token usage from successful responses
    if (statusCode === 200 && data) {
      if (data.cost) {
        bridgeCostTotal
          .labels(modelTier, taskType, agentId)
          .inc(data.cost.total || 0);
      }
      
      if (data.usage) {
        bridgeTokensTotal
          .labels('input', modelTier)
          .inc(data.usage.promptTokens || 0);
        bridgeTokensTotal
          .labels('output', modelTier)
          .inc(data.usage.completionTokens || 0);
      }
      
      // For batch responses
      if (data.responses && Array.isArray(data.responses)) {
        let totalCost = 0;
        let totalInputTokens = 0;
        let totalOutputTokens = 0;
        
        data.responses.forEach((response: any) => {
          if (response.cost) totalCost += response.cost.total || 0;
          if (response.usage) {
            totalInputTokens += response.usage.promptTokens || 0;
            totalOutputTokens += response.usage.completionTokens || 0;
          }
        });
        
        bridgeCostTotal.labels(modelTier, taskType, agentId).inc(totalCost);
        bridgeTokensTotal.labels('input', modelTier).inc(totalInputTokens);
        bridgeTokensTotal.labels('output', modelTier).inc(totalOutputTokens);
      }
    }
    
    bridgeActiveRequests.dec();
    
    // Log high-level metrics
    logger.info('AI Bridge Request', {
      endpoint,
      statusCode,
      duration,
      modelTier,
      taskType,
      agentId,
      cost: responseData?.cost?.total || responseData?.totalCost || 0,
      tokens: responseData?.usage?.totalTokens || 0
    });
    
    return originalJson.call(this, data);
  };
  
  next();
};

export { register as metricsRegistry };