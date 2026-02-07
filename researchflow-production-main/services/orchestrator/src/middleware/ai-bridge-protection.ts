/**
 * AI Bridge Protection Middleware
 * 
 * Implements rate limiting, circuit breaker, and cost protection
 * to prevent abuse and system overload.
 */

import { Request, Response, NextFunction } from 'express';

import { getAIBridgeConfig } from '../config/ai-bridge.config';
import { createLogger } from '../utils/logger';

const logger = createLogger('ai-bridge-protection');
const config = getAIBridgeConfig();

// In-memory rate limiting store (use Redis in production)
const rateLimitStore = new Map<string, { count: number; resetTime: number; cost: number }>();

// Circuit breaker state
interface CircuitBreakerState {
  failures: number;
  lastFailureTime: number;
  state: 'CLOSED' | 'OPEN' | 'HALF_OPEN';
}

const circuitBreakerState: CircuitBreakerState = {
  failures: 0,
  lastFailureTime: 0,
  state: 'CLOSED'
};

/**
 * Rate limiting middleware
 */
export const rateLimitMiddleware = (req: Request, res: Response, next: NextFunction) => {
  if (!config.features.rateLimitingEnabled) {
    return next();
  }
  
  const userId = req.user?.id || 'anonymous';
  const now = Date.now();
  const windowMs = 60 * 1000; // 1 minute window
  
  const userKey = `rate_limit:${userId}`;
  const userLimit = rateLimitStore.get(userKey);
  
  if (!userLimit || userLimit.resetTime < now) {
    // Reset window
    rateLimitStore.set(userKey, {
      count: 1,
      resetTime: now + windowMs,
      cost: 0
    });
    return next();
  }
  
  if (userLimit.count >= config.limits.rateLimitPerMinute) {
    logger.warn('Rate limit exceeded', { userId, count: userLimit.count });
    return res.status(429).json({
      error: 'RATE_LIMIT_EXCEEDED',
      message: 'Too many requests. Please wait before retrying.',
      retryAfter: Math.ceil((userLimit.resetTime - now) / 1000)
    });
  }
  
  userLimit.count++;
  next();
};

/**
 * Cost protection middleware
 */
export const costProtectionMiddleware = (req: Request, res: Response, next: NextFunction) => {
  const userId = req.user?.id || 'anonymous';
  const userKey = `rate_limit:${userId}`;
  const userLimit = rateLimitStore.get(userKey);
  
  if (userLimit && userLimit.cost > config.costManagement.dailyBudgetDollars) {
    logger.warn('Daily budget exceeded', { userId, cost: userLimit.cost });
    return res.status(402).json({
      error: 'BUDGET_EXCEEDED',
      message: 'Daily budget limit exceeded. Please contact support.',
      currentCost: userLimit.cost,
      budgetLimit: config.costManagement.dailyBudgetDollars
    });
  }
  
  next();
};

/**
 * Circuit breaker middleware
 */
export const circuitBreakerMiddleware = (req: Request, res: Response, next: NextFunction) => {
  const now = Date.now();
  const timeoutMs = 60000; // 1 minute timeout
  const failureThreshold = 5;
  
  switch (circuitBreakerState.state) {
    case 'OPEN':
      if (now - circuitBreakerState.lastFailureTime > timeoutMs) {
        circuitBreakerState.state = 'HALF_OPEN';
        logger.info('Circuit breaker transitioning to HALF_OPEN');
        next();
      } else {
        logger.warn('Circuit breaker OPEN - rejecting request');
        return res.status(503).json({
          error: 'SERVICE_UNAVAILABLE',
          message: 'Service temporarily unavailable. Please retry later.',
          retryAfter: Math.ceil((timeoutMs - (now - circuitBreakerState.lastFailureTime)) / 1000)
        });
      }
      break;
      
    case 'HALF_OPEN':
      // Allow one request through to test
      next();
      break;
      
    case 'CLOSED':
    default:
      next();
      break;
  }
};

/**
 * Record circuit breaker success/failure
 */
export const recordCircuitBreakerOutcome = (success: boolean) => {
  if (success) {
    if (circuitBreakerState.state === 'HALF_OPEN') {
      circuitBreakerState.state = 'CLOSED';
      circuitBreakerState.failures = 0;
      logger.info('Circuit breaker reset to CLOSED');
    }
  } else {
    circuitBreakerState.failures++;
    circuitBreakerState.lastFailureTime = Date.now();
    
    if (circuitBreakerState.failures >= 5) {
      circuitBreakerState.state = 'OPEN';
      logger.warn('Circuit breaker OPEN due to failures', { failures: circuitBreakerState.failures });
    }
  }
};

/**
 * Update cost tracking
 */
export const updateCostTracking = (userId: string, cost: number) => {
  const userKey = `rate_limit:${userId}`;
  const userLimit = rateLimitStore.get(userKey);
  
  if (userLimit) {
    userLimit.cost += cost;
  }
};