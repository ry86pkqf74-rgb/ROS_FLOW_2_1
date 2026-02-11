/**
 * AI Bridge Enhanced Error Handler
 * 
 * Provides sophisticated error categorization, recovery strategies, and user guidance
 */

import { Request, Response, NextFunction } from 'express';

import { logAction } from '../services/audit-service';
import { createLogger } from '../utils/logger';

const logger = createLogger('ai-bridge-error-handler');

export enum ErrorCategory {
  AUTHENTICATION = 'AUTHENTICATION',
  AUTHORIZATION = 'AUTHORIZATION',
  VALIDATION = 'VALIDATION',
  RATE_LIMIT = 'RATE_LIMIT',
  BUDGET = 'BUDGET',
  SERVICE_UNAVAILABLE = 'SERVICE_UNAVAILABLE',
  MODEL_ERROR = 'MODEL_ERROR',
  NETWORK = 'NETWORK',
  TIMEOUT = 'TIMEOUT',
  INTERNAL = 'INTERNAL',
  UNKNOWN = 'UNKNOWN'
}

export enum ErrorSeverity {
  LOW = 'LOW',
  MEDIUM = 'MEDIUM',
  HIGH = 'HIGH',
  CRITICAL = 'CRITICAL'
}

export interface EnhancedError {
  category: ErrorCategory;
  severity: ErrorSeverity;
  code: string;
  message: string;
  details?: any;
  retryable: boolean;
  retryAfter?: number;
  suggestions: string[];
  technicalDetails?: string;
  correlationId?: string;
}

export class AIBridgeErrorHandler {
  /**
   * Categorize and enhance error information
   */
  categorizeError(error: any, req: Request): EnhancedError {
    const correlationId = `err_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    // HTTP status-based categorization
    if (error.response?.status) {
      return this.handleHttpError(error, correlationId, req);
    }
    
    // Network/connection errors
    if (error.code === 'ECONNREFUSED' || error.code === 'ENOTFOUND' || error.code === 'ETIMEDOUT') {
      return this.handleNetworkError(error, correlationId);
    }
    
    // Application-specific errors
    if (error.code) {
      return this.handleApplicationError(error, correlationId);
    }
    
    // Default unknown error
    return {
      category: ErrorCategory.UNKNOWN,
      severity: ErrorSeverity.HIGH,
      code: 'UNKNOWN_ERROR',
      message: 'An unexpected error occurred',
      details: error.message || 'Unknown error',
      retryable: false,
      suggestions: [
        'Check the request format and try again',
        'Contact support if the problem persists',
        'Review the API documentation for correct usage'
      ],
      technicalDetails: error.stack,
      correlationId
    };
  }
  
  /**
   * Handle HTTP status-based errors
   */
  private handleHttpError(error: any, correlationId: string, req: Request): EnhancedError {
    const status = error.response.status;
    const responseData = error.response.data;
    
    switch (status) {
      case 400:
        return {
          category: ErrorCategory.VALIDATION,
          severity: ErrorSeverity.MEDIUM,
          code: responseData?.error || 'VALIDATION_ERROR',
          message: responseData?.message || 'Request validation failed',
          details: responseData?.details,
          retryable: false,
          suggestions: [
            'Check the request body format and required fields',
            'Validate that all enum values are correct',
            'Ensure prompt is not empty and options are properly formatted',
            'Review the API documentation for correct parameter types'
          ],
          correlationId
        };
        
      case 401:
        return {
          category: ErrorCategory.AUTHENTICATION,
          severity: ErrorSeverity.HIGH,
          code: 'AUTHENTICATION_FAILED',
          message: 'Authentication required or invalid',
          retryable: false,
          suggestions: [
            'Verify your JWT token is valid and not expired',
            'Check that the Authorization header is properly formatted',
            'Ensure you have an active user session',
            'Contact an administrator if you believe this is an error'
          ],
          correlationId
        };
        
      case 403:
        return {
          category: ErrorCategory.AUTHORIZATION,
          severity: ErrorSeverity.HIGH,
          code: 'INSUFFICIENT_PERMISSIONS',
          message: 'Insufficient permissions for this operation',
          retryable: false,
          suggestions: [
            'Check that your user role has ANALYZE permissions',
            'Contact an administrator to review your permissions',
            'Verify you are accessing the correct resource',
            'Review RBAC documentation for permission requirements'
          ],
          correlationId
        };
        
      case 429:
        const retryAfter = parseInt(error.response.headers['retry-after'] || '60');
        return {
          category: ErrorCategory.RATE_LIMIT,
          severity: ErrorSeverity.MEDIUM,
          code: 'RATE_LIMIT_EXCEEDED',
          message: 'Request rate limit exceeded',
          retryable: true,
          retryAfter,
          suggestions: [
            `Wait ${retryAfter} seconds before retrying`,
            'Implement exponential backoff in your client',
            'Use batch processing to reduce request frequency',
            'Consider upgrading your rate limit if available'
          ],
          details: { retryAfter },
          correlationId
        };
        
      case 402:
        return {
          category: ErrorCategory.BUDGET,
          severity: ErrorSeverity.HIGH,
          code: 'BUDGET_EXCEEDED',
          message: 'Budget limit exceeded',
          retryable: false,
          suggestions: [
            'Monitor your daily usage with the metrics endpoint',
            'Use lower-cost model tiers (ECONOMY vs PREMIUM)',
            'Optimize prompts to reduce token usage',
            'Contact support to request a budget increase'
          ],
          details: responseData,
          correlationId
        };
        
      case 503:
        return {
          category: ErrorCategory.SERVICE_UNAVAILABLE,
          severity: ErrorSeverity.HIGH,
          code: 'SERVICE_UNAVAILABLE',
          message: 'AI Bridge service temporarily unavailable',
          retryable: true,
          retryAfter: parseInt(error.response.headers['retry-after'] || '30'),
          suggestions: [
            'Check the health endpoint for service status',
            'Wait for the circuit breaker to reset (usually 1 minute)',
            'Implement retry logic with exponential backoff',
            'Monitor service status for updates'
          ],
          correlationId
        };
        
      case 504:
        return {
          category: ErrorCategory.TIMEOUT,
          severity: ErrorSeverity.MEDIUM,
          code: 'GATEWAY_TIMEOUT',
          message: 'Request timed out',
          retryable: true,
          suggestions: [
            'Reduce prompt length to decrease processing time',
            'Use streaming for long-running requests',
            'Break large requests into smaller batches',
            'Check network connectivity and try again'
          ],
          correlationId
        };
        
      default:
        return {
          category: status >= 500 ? ErrorCategory.INTERNAL : ErrorCategory.UNKNOWN,
          severity: ErrorSeverity.HIGH,
          code: `HTTP_${status}`,
          message: responseData?.message || `HTTP ${status} error`,
          details: responseData,
          retryable: status >= 500,
          suggestions: [
            status >= 500 ? 'This is a server error - please try again later' : 'Check your request and try again',
            'Contact support if the problem persists',
            'Include the correlation ID when reporting issues'
          ],
          correlationId
        };
    }
  }
  
  /**
   * Handle network/connection errors
   */
  private handleNetworkError(error: any, correlationId: string): EnhancedError {
    const errorCodeMappings: Record<string, { category: ErrorCategory; message: string; suggestions: string[] }> = {
      'ECONNREFUSED': {
        category: ErrorCategory.NETWORK,
        message: 'Connection refused - service may be down',
        suggestions: [
          'Check that the AI Bridge service is running',
          'Verify the service URL configuration',
          'Check network connectivity',
          'Try again in a few moments'
        ]
      },
      'ENOTFOUND': {
        category: ErrorCategory.NETWORK,
        message: 'DNS resolution failed - hostname not found',
        suggestions: [
          'Verify the service URL is correct',
          'Check DNS configuration',
          'Ensure network connectivity',
          'Contact your network administrator if using internal services'
        ]
      },
      'ETIMEDOUT': {
        category: ErrorCategory.TIMEOUT,
        message: 'Connection timed out',
        suggestions: [
          'Check network connectivity',
          'Increase timeout values if possible',
          'Try the request again',
          'Use streaming for long-running operations'
        ]
      }
    };
    
    const errorInfo = errorCodeMappings[error.code] || {
      category: ErrorCategory.NETWORK,
      message: 'Network error occurred',
      suggestions: ['Check network connectivity and try again']
    };
    
    return {
      category: errorInfo.category,
      severity: ErrorSeverity.HIGH,
      code: error.code,
      message: errorInfo.message,
      details: error.message,
      retryable: true,
      suggestions: errorInfo.suggestions,
      technicalDetails: `${error.code}: ${error.message}`,
      correlationId
    };
  }
  
  /**
   * Handle application-specific errors
   */
  private handleApplicationError(error: any, correlationId: string): EnhancedError {
    // Add custom application error handling here
    const appErrorMappings: Record<string, Partial<EnhancedError>> = {
      'MODEL_OVERLOADED': {
        category: ErrorCategory.MODEL_ERROR,
        severity: ErrorSeverity.MEDIUM,
        message: 'AI model is overloaded',
        retryable: true,
        retryAfter: 30,
        suggestions: [
          'Try again in 30 seconds',
          'Use a different model tier',
          'Break large requests into smaller pieces'
        ]
      },
      'INVALID_TASK_TYPE': {
        category: ErrorCategory.VALIDATION,
        severity: ErrorSeverity.MEDIUM,
        message: 'Invalid task type specified',
        retryable: false,
        suggestions: [
          'Check the supported task types in /capabilities endpoint',
          'Verify task type spelling and case',
          'Review the API documentation for valid task types'
        ]
      }
    };
    
    const errorInfo = appErrorMappings[error.code];
    if (errorInfo) {
      return {
        category: ErrorCategory.UNKNOWN,
        severity: ErrorSeverity.MEDIUM,
        code: error.code,
        message: error.message,
        retryable: false,
        suggestions: ['Contact support for assistance'],
        ...errorInfo,
        correlationId
      };
    }
    
    return {
      category: ErrorCategory.UNKNOWN,
      severity: ErrorSeverity.MEDIUM,
      code: error.code,
      message: error.message || 'Application error',
      details: error.details,
      retryable: false,
      suggestions: [
        'Check the error details for specific guidance',
        'Contact support if the issue persists',
        'Include the correlation ID when reporting issues'
      ],
      correlationId
    };
  }
  
  /**
   * Generate user-friendly error response
   */
  generateErrorResponse(enhancedError: EnhancedError, req: Request): any {
    // Log for monitoring
    logger.warn('AI Bridge error', {
      correlationId: enhancedError.correlationId,
      category: enhancedError.category,
      severity: enhancedError.severity,
      code: enhancedError.code,
      userId: req.user?.id,
      endpoint: req.path,
      userAgent: req.headers['user-agent']
    });
    
    // Base response
    const response: any = {
      error: enhancedError.code,
      message: enhancedError.message,
      category: enhancedError.category,
      severity: enhancedError.severity,
      correlationId: enhancedError.correlationId,
      timestamp: new Date().toISOString()
    };
    
    // Add retry information
    if (enhancedError.retryable) {
      response.retryable = true;
      if (enhancedError.retryAfter) {
        response.retryAfter = enhancedError.retryAfter;
      }
    }
    
    // Add details if available
    if (enhancedError.details) {
      response.details = enhancedError.details;
    }
    
    // Add suggestions for resolution
    if (enhancedError.suggestions.length > 0) {
      response.suggestions = enhancedError.suggestions;
    }
    
    // Add technical details in development
    if (process.env.NODE_ENV === 'development' && enhancedError.technicalDetails) {
      response.technicalDetails = enhancedError.technicalDetails;
    }
    
    return response;
  }
  
  /**
   * Get HTTP status code for error category
   */
  getHttpStatusCode(enhancedError: EnhancedError): number {
    const statusMappings: Record<ErrorCategory, number> = {
      [ErrorCategory.AUTHENTICATION]: 401,
      [ErrorCategory.AUTHORIZATION]: 403,
      [ErrorCategory.VALIDATION]: 400,
      [ErrorCategory.RATE_LIMIT]: 429,
      [ErrorCategory.BUDGET]: 402,
      [ErrorCategory.SERVICE_UNAVAILABLE]: 503,
      [ErrorCategory.MODEL_ERROR]: 502,
      [ErrorCategory.NETWORK]: 503,
      [ErrorCategory.TIMEOUT]: 504,
      [ErrorCategory.INTERNAL]: 500,
      [ErrorCategory.UNKNOWN]: 500
    };
    
    return statusMappings[enhancedError.category] || 500;
  }
  
  /**
   * Audit log critical errors
   */
  async auditCriticalError(enhancedError: EnhancedError, req: Request) {
    if (enhancedError.severity === ErrorSeverity.CRITICAL || enhancedError.severity === ErrorSeverity.HIGH) {
      try {
        await logAction({
          eventType: 'AI_BRIDGE_ERROR',
          action: 'CRITICAL_ERROR_OCCURRED',
          userId: req.user?.id || 'anonymous',
          resourceType: 'ai_bridge',
          resourceId: enhancedError.correlationId || 'unknown',
          details: {
            category: enhancedError.category,
            severity: enhancedError.severity,
            code: enhancedError.code,
            message: enhancedError.message,
            endpoint: req.path,
            userAgent: req.headers['user-agent']
          }
        });
      } catch (auditError) {
        logger.error('Failed to audit critical error', { 
          error: auditError instanceof Error ? auditError.message : String(auditError),
          stack: auditError instanceof Error ? auditError.stack : undefined 
        });
      }
    }
  }
}

// Singleton instance
let errorHandler: AIBridgeErrorHandler | null = null;

export function getAIBridgeErrorHandler(): AIBridgeErrorHandler {
  if (!errorHandler) {
    errorHandler = new AIBridgeErrorHandler();
  }
  return errorHandler;
}

/**
 * Express middleware for enhanced error handling
 */
export const enhancedErrorHandlerMiddleware = async (
  error: any,
  req: Request,
  res: Response,
  next: NextFunction
) => {
  const handler = getAIBridgeErrorHandler();
  
  // Categorize and enhance the error
  const enhancedError = handler.categorizeError(error, req);
  
  // Audit critical errors
  await handler.auditCriticalError(enhancedError, req);
  
  // Generate response
  const errorResponse = handler.generateErrorResponse(enhancedError, req);
  const statusCode = handler.getHttpStatusCode(enhancedError);
  
  // Send response
  res.status(statusCode).json(errorResponse);
};

export default AIBridgeErrorHandler;