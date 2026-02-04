/**
 * Enhanced Error Handling for Visualization System
 * 
 * Comprehensive error handling, classification, and recovery for the visualization
 * system with user-friendly messages, structured logging, and automated recovery.
 */

import { Request, Response, NextFunction } from 'express';
import { z } from 'zod';
import { visualizationConfig } from '../config/visualization.config';
import { createLogger } from '../utils/logger';
import { logAction } from '../services/audit-service';

const logger = createLogger('visualization-error');

export enum VisualizationErrorType {
  // Input validation errors
  INVALID_REQUEST = 'INVALID_REQUEST',
  INVALID_DATA_FORMAT = 'INVALID_DATA_FORMAT',
  DATA_TOO_LARGE = 'DATA_TOO_LARGE',
  UNSUPPORTED_CHART_TYPE = 'UNSUPPORTED_CHART_TYPE',
  MISSING_REQUIRED_FIELDS = 'MISSING_REQUIRED_FIELDS',
  
  // Processing errors
  GENERATION_TIMEOUT = 'GENERATION_TIMEOUT',
  WORKER_UNAVAILABLE = 'WORKER_UNAVAILABLE',
  PROCESSING_ERROR = 'PROCESSING_ERROR',
  MEMORY_LIMIT_EXCEEDED = 'MEMORY_LIMIT_EXCEEDED',
  CONCURRENT_LIMIT_EXCEEDED = 'CONCURRENT_LIMIT_EXCEEDED',
  
  // Infrastructure errors
  DATABASE_ERROR = 'DATABASE_ERROR',
  CACHE_ERROR = 'CACHE_ERROR',
  NETWORK_ERROR = 'NETWORK_ERROR',
  STORAGE_ERROR = 'STORAGE_ERROR',
  
  // Security errors
  RATE_LIMIT_EXCEEDED = 'RATE_LIMIT_EXCEEDED',
  UNAUTHORIZED = 'UNAUTHORIZED',
  PHI_DETECTION_ERROR = 'PHI_DETECTION_ERROR',
  SUSPICIOUS_CONTENT = 'SUSPICIOUS_CONTENT',
  
  // System errors
  CONFIGURATION_ERROR = 'CONFIGURATION_ERROR',
  UNKNOWN_ERROR = 'UNKNOWN_ERROR',
}

export interface VisualizationError {
  type: VisualizationErrorType;
  message: string;
  userMessage: string;
  statusCode: number;
  retryable: boolean;
  suggestions: string[];
  context?: any;
  errorId: string;
  timestamp: string;
}

export class VisualizationErrorHandler {
  private static errorStats = {
    totalErrors: 0,
    errorsByType: new Map<VisualizationErrorType, number>(),
    lastReset: new Date(),
  };
  
  /**
   * Main error handler middleware
   */
  static handleVisualizationError(
    error: any,
    req: Request,
    res: Response,
    next: NextFunction
  ): void {
    const errorId = generateErrorId();
    const timestamp = new Date().toISOString();
    
    // Classify the error
    const errorType = this.classifyError(error);
    const statusCode = this.getStatusCodeForError(errorType);
    const userMessage = this.getUserFriendlyMessage(errorType, error);
    const suggestions = this.getErrorSuggestions(errorType);
    const isRetryable = this.isRetryable(errorType);
    
    // Create structured error response
    const vizError: VisualizationError = {
      type: errorType,
      message: error.message || 'Unknown error occurred',
      userMessage,
      statusCode,
      retryable: isRetryable,
      suggestions,
      context: this.getErrorContext(req, error),
      errorId,
      timestamp,
    };
    
    // Log the error with full context
    this.logError(vizError, req, error);
    
    // Update error statistics
    this.updateErrorStats(errorType);
    
    // Attempt automated recovery
    this.attemptRecovery(errorType, req, error);
    
    // Send user-friendly response
    res.status(statusCode).json({
      error: errorType,
      message: userMessage,
      errorId,
      timestamp,
      suggestions: suggestions.slice(0, 3), // Limit to top 3 suggestions
      retryable: isRetryable,
      ...(visualizationConfig.monitoring.enableDetailedLogging && {
        details: {
          originalMessage: error.message,
          context: vizError.context,
        },
      }),
    });
    
    // Don't call next() - we've handled the error
  }
  
  /**
   * Classify error into specific type for better handling
   */
  private static classifyError(error: any): VisualizationErrorType {
    const message = error.message?.toLowerCase() || '';
    const code = error.code;
    const status = error.status;
    
    // Network and connectivity errors
    if (code === 'ECONNREFUSED' || code === 'ENOTFOUND' || code === 'ETIMEDOUT') {
      return VisualizationErrorType.WORKER_UNAVAILABLE;
    }
    
    if (code === 'ECONNRESET' || message.includes('network')) {
      return VisualizationErrorType.NETWORK_ERROR;
    }
    
    // Timeout errors
    if (message.includes('timeout') || code === 'TIMEOUT') {
      return VisualizationErrorType.GENERATION_TIMEOUT;
    }
    
    // Memory and resource errors
    if (message.includes('memory') || message.includes('out of memory') || code === 'ENOMEM') {
      return VisualizationErrorType.MEMORY_LIMIT_EXCEEDED;
    }
    
    // Data validation errors
    if (error instanceof z.ZodError || message.includes('validation')) {
      return VisualizationErrorType.INVALID_REQUEST;
    }
    
    if (message.includes('data') && (message.includes('invalid') || message.includes('format'))) {
      return VisualizationErrorType.INVALID_DATA_FORMAT;
    }
    
    if (message.includes('too large') || message.includes('size') || message.includes('limit')) {
      return VisualizationErrorType.DATA_TOO_LARGE;
    }
    
    if (message.includes('chart type') || message.includes('unsupported')) {
      return VisualizationErrorType.UNSUPPORTED_CHART_TYPE;
    }
    
    if (message.includes('required') || message.includes('missing')) {
      return VisualizationErrorType.MISSING_REQUIRED_FIELDS;
    }
    
    // Database errors
    if (message.includes('database') || message.includes('connection') || code?.startsWith('28')) {
      return VisualizationErrorType.DATABASE_ERROR;
    }
    
    // Cache errors
    if (message.includes('redis') || message.includes('cache')) {
      return VisualizationErrorType.CACHE_ERROR;
    }
    
    // Rate limiting
    if (status === 429 || message.includes('rate limit') || message.includes('too many requests')) {
      return VisualizationErrorType.RATE_LIMIT_EXCEEDED;
    }
    
    // Authorization
    if (status === 401 || status === 403 || message.includes('unauthorized') || message.includes('forbidden')) {
      return VisualizationErrorType.UNAUTHORIZED;
    }
    
    // PHI detection
    if (message.includes('phi') || message.includes('sensitive data')) {
      return VisualizationErrorType.PHI_DETECTION_ERROR;
    }
    
    // Processing errors from worker
    if (status >= 400 && status < 500) {
      return VisualizationErrorType.PROCESSING_ERROR;
    }
    
    // Configuration errors
    if (message.includes('config') || message.includes('environment')) {
      return VisualizationErrorType.CONFIGURATION_ERROR;
    }
    
    return VisualizationErrorType.UNKNOWN_ERROR;
  }
  
  /**
   * Get appropriate HTTP status code for error type
   */
  private static getStatusCodeForError(errorType: VisualizationErrorType): number {
    const statusCodes = {
      [VisualizationErrorType.INVALID_REQUEST]: 400,
      [VisualizationErrorType.INVALID_DATA_FORMAT]: 400,
      [VisualizationErrorType.DATA_TOO_LARGE]: 413,
      [VisualizationErrorType.UNSUPPORTED_CHART_TYPE]: 400,
      [VisualizationErrorType.MISSING_REQUIRED_FIELDS]: 400,
      [VisualizationErrorType.GENERATION_TIMEOUT]: 408,
      [VisualizationErrorType.WORKER_UNAVAILABLE]: 503,
      [VisualizationErrorType.PROCESSING_ERROR]: 422,
      [VisualizationErrorType.MEMORY_LIMIT_EXCEEDED]: 507,
      [VisualizationErrorType.CONCURRENT_LIMIT_EXCEEDED]: 429,
      [VisualizationErrorType.DATABASE_ERROR]: 503,
      [VisualizationErrorType.CACHE_ERROR]: 503,
      [VisualizationErrorType.NETWORK_ERROR]: 503,
      [VisualizationErrorType.STORAGE_ERROR]: 507,
      [VisualizationErrorType.RATE_LIMIT_EXCEEDED]: 429,
      [VisualizationErrorType.UNAUTHORIZED]: 401,
      [VisualizationErrorType.PHI_DETECTION_ERROR]: 400,
      [VisualizationErrorType.SUSPICIOUS_CONTENT]: 400,
      [VisualizationErrorType.CONFIGURATION_ERROR]: 500,
      [VisualizationErrorType.UNKNOWN_ERROR]: 500,
    };
    
    return statusCodes[errorType] || 500;
  }
  
  /**
   * Get user-friendly error message
   */
  private static getUserFriendlyMessage(errorType: VisualizationErrorType, error: any): string {
    const messages = {
      [VisualizationErrorType.INVALID_REQUEST]: 
        'The chart request is invalid. Please check your data format and try again.',
      [VisualizationErrorType.INVALID_DATA_FORMAT]: 
        'The data format is not supported. Please ensure your data is properly formatted.',
      [VisualizationErrorType.DATA_TOO_LARGE]: 
        `Dataset is too large. Maximum allowed data points: ${visualizationConfig.performance.maxDataPoints.toLocaleString()}.`,
      [VisualizationErrorType.UNSUPPORTED_CHART_TYPE]: 
        'The requested chart type is not supported. Please choose from available chart types.',
      [VisualizationErrorType.MISSING_REQUIRED_FIELDS]: 
        'Required fields are missing from your request. Please check the documentation.',
      [VisualizationErrorType.GENERATION_TIMEOUT]: 
        `Chart generation took too long (limit: ${visualizationConfig.performance.generationTimeoutMs/1000}s). Try reducing data complexity.`,
      [VisualizationErrorType.WORKER_UNAVAILABLE]: 
        'The chart generation service is temporarily unavailable. Please try again in a moment.',
      [VisualizationErrorType.PROCESSING_ERROR]: 
        'Unable to process your chart request. Please check your data and configuration.',
      [VisualizationErrorType.MEMORY_LIMIT_EXCEEDED]: 
        'Dataset is too complex to process. Please reduce the amount of data or simplify the chart.',
      [VisualizationErrorType.CONCURRENT_LIMIT_EXCEEDED]: 
        'Too many chart generation requests are currently running. Please wait and try again.',
      [VisualizationErrorType.DATABASE_ERROR]: 
        'Unable to save your chart. Please try again or contact support if the problem persists.',
      [VisualizationErrorType.CACHE_ERROR]: 
        'Caching service is experiencing issues. Your request will be processed without caching.',
      [VisualizationErrorType.NETWORK_ERROR]: 
        'Network connectivity issue. Please check your connection and try again.',
      [VisualizationErrorType.STORAGE_ERROR]: 
        'Unable to store the generated chart. Please try again or reduce image quality.',
      [VisualizationErrorType.RATE_LIMIT_EXCEEDED]: 
        `Too many requests. Please wait before making another request. (Limit: ${visualizationConfig.security.rateLimitPerMinute}/minute)`,
      [VisualizationErrorType.UNAUTHORIZED]: 
        'You are not authorized to perform this action. Please check your permissions.',
      [VisualizationErrorType.PHI_DETECTION_ERROR]: 
        'Potential sensitive data detected in your request. Please review and remove any personal information.',
      [VisualizationErrorType.SUSPICIOUS_CONTENT]: 
        'Your request contains suspicious content and has been blocked for security reasons.',
      [VisualizationErrorType.CONFIGURATION_ERROR]: 
        'System configuration error. Please contact support.',
      [VisualizationErrorType.UNKNOWN_ERROR]: 
        'An unexpected error occurred. Our team has been notified and will investigate.',
    };
    
    return messages[errorType] || messages[VisualizationErrorType.UNKNOWN_ERROR];
  }
  
  /**
   * Get actionable suggestions for error resolution
   */
  private static getErrorSuggestions(errorType: VisualizationErrorType): string[] {
    const suggestions = {
      [VisualizationErrorType.INVALID_REQUEST]: [
        'Check the API documentation for correct request format',
        'Validate your JSON data structure',
        'Ensure all required fields are present',
        'Try a simpler request to test connectivity',
      ],
      [VisualizationErrorType.INVALID_DATA_FORMAT]: [
        'Ensure data arrays are properly formatted',
        'Check that numeric data contains only valid numbers',
        'Verify that categorical data is properly labeled',
        'Remove any null or undefined values',
      ],
      [VisualizationErrorType.DATA_TOO_LARGE]: [
        'Reduce the number of data points',
        'Sample your data (e.g., every 10th point)',
        'Consider aggregating data before visualization',
        'Use a different chart type that handles large datasets better',
      ],
      [VisualizationErrorType.UNSUPPORTED_CHART_TYPE]: [
        'Check available chart types in the documentation',
        'Consider using a similar supported chart type',
        'Verify the spelling of the chart type name',
      ],
      [VisualizationErrorType.GENERATION_TIMEOUT]: [
        'Reduce data complexity or size',
        'Lower the DPI setting',
        'Use a simpler chart type',
        'Try generating the chart during off-peak hours',
      ],
      [VisualizationErrorType.WORKER_UNAVAILABLE]: [
        'Wait a moment and try again',
        'Check if there are any system maintenance notifications',
        'Try a simpler chart request first',
      ],
      [VisualizationErrorType.RATE_LIMIT_EXCEEDED]: [
        'Wait before making another request',
        'Consider upgrading your plan for higher limits',
        'Batch multiple charts into fewer requests',
      ],
      [VisualizationErrorType.PHI_DETECTION_ERROR]: [
        'Review your data for personal information',
        'Remove names, addresses, or IDs from data labels',
        'Use generic labels instead of specific identifiers',
      ],
    };
    
    return suggestions[errorType] || [
      'Try again in a few moments',
      'Check your internet connection',
      'Contact support if the problem persists',
    ];
  }
  
  /**
   * Determine if error is retryable
   */
  private static isRetryable(errorType: VisualizationErrorType): boolean {
    const retryableErrors = [
      VisualizationErrorType.GENERATION_TIMEOUT,
      VisualizationErrorType.WORKER_UNAVAILABLE,
      VisualizationErrorType.NETWORK_ERROR,
      VisualizationErrorType.DATABASE_ERROR,
      VisualizationErrorType.CACHE_ERROR,
      VisualizationErrorType.CONCURRENT_LIMIT_EXCEEDED,
      VisualizationErrorType.RATE_LIMIT_EXCEEDED,
    ];
    
    return retryableErrors.includes(errorType);
  }
  
  /**
   * Extract relevant context from request and error
   */
  private static getErrorContext(req: Request, error: any): any {
    return {
      method: req.method,
      path: req.path,
      chartType: req.body?.chart_type,
      dataSize: req.body?.data ? JSON.stringify(req.body.data).length : 0,
      userAgent: req.headers['user-agent'],
      timestamp: new Date().toISOString(),
      requestId: req.headers['x-request-id'],
      userId: req.user?.id,
      sessionId: req.sessionID,
      stack: visualizationConfig.monitoring.enableDetailedLogging ? error.stack : undefined,
    };
  }
  
  /**
   * Log error with structured data
   */
  private static logError(vizError: VisualizationError, req: Request, originalError: any): void {
    const logLevel = this.getLogLevel(vizError.type);
    
    const logData = {
      errorId: vizError.errorId,
      errorType: vizError.type,
      statusCode: vizError.statusCode,
      retryable: vizError.retryable,
      context: vizError.context,
      originalMessage: originalError.message,
      originalStack: originalError.stack,
    };
    
    switch (logLevel) {
      case 'error':
        logger.error(vizError.message, logData);
        break;
      case 'warn':
        logger.warn(vizError.message, logData);
        break;
      case 'info':
        logger.info(vizError.message, logData);
        break;
    }
    
    // Log to audit trail for security-related errors
    if (this.isSecurityError(vizError.type)) {
      logAction({
        userId: req.user?.id || 'anonymous',
        action: 'SECURITY_ERROR',
        resourceType: 'visualization',
        resourceId: req.body?.research_id || 'unknown',
        metadata: {
          errorType: vizError.type,
          errorId: vizError.errorId,
          userAgent: req.headers['user-agent'],
          ip: req.ip,
        },
      }).catch(auditError => {
        logger.error('Failed to log security error to audit trail', { auditError });
      });
    }
  }
  
  /**
   * Determine appropriate log level for error type
   */
  private static getLogLevel(errorType: VisualizationErrorType): 'error' | 'warn' | 'info' {
    const errorLevels = [
      VisualizationErrorType.UNKNOWN_ERROR,
      VisualizationErrorType.CONFIGURATION_ERROR,
      VisualizationErrorType.DATABASE_ERROR,
      VisualizationErrorType.STORAGE_ERROR,
    ];
    
    const warnLevels = [
      VisualizationErrorType.WORKER_UNAVAILABLE,
      VisualizationErrorType.NETWORK_ERROR,
      VisualizationErrorType.CACHE_ERROR,
      VisualizationErrorType.MEMORY_LIMIT_EXCEEDED,
      VisualizationErrorType.GENERATION_TIMEOUT,
    ];
    
    if (errorLevels.includes(errorType)) return 'error';
    if (warnLevels.includes(errorType)) return 'warn';
    return 'info';
  }
  
  /**
   * Check if error type is security-related
   */
  private static isSecurityError(errorType: VisualizationErrorType): boolean {
    const securityErrors = [
      VisualizationErrorType.UNAUTHORIZED,
      VisualizationErrorType.PHI_DETECTION_ERROR,
      VisualizationErrorType.SUSPICIOUS_CONTENT,
      VisualizationErrorType.RATE_LIMIT_EXCEEDED,
    ];
    
    return securityErrors.includes(errorType);
  }
  
  /**
   * Attempt automated recovery for certain error types
   */
  private static attemptRecovery(errorType: VisualizationErrorType, req: Request, error: any): void {
    switch (errorType) {
      case VisualizationErrorType.CACHE_ERROR:
        // Disable cache for this request
        logger.info('Attempting recovery: disabling cache', { errorType });
        break;
        
      case VisualizationErrorType.DATA_TOO_LARGE:
        // Could suggest data sampling
        logger.info('Attempting recovery: suggesting data reduction', { errorType });
        break;
        
      case VisualizationErrorType.WORKER_UNAVAILABLE:
        // Could trigger health check or failover
        logger.info('Attempting recovery: checking worker health', { errorType });
        break;
    }
  }
  
  /**
   * Update error statistics for monitoring
   */
  private static updateErrorStats(errorType: VisualizationErrorType): void {
    this.errorStats.totalErrors++;
    
    const currentCount = this.errorStats.errorsByType.get(errorType) || 0;
    this.errorStats.errorsByType.set(errorType, currentCount + 1);
  }
  
  /**
   * Get error statistics for monitoring dashboard
   */
  static getErrorStats(): any {
    const stats = {
      totalErrors: this.errorStats.totalErrors,
      errorsByType: Object.fromEntries(this.errorStats.errorsByType),
      lastReset: this.errorStats.lastReset,
      topErrors: [...this.errorStats.errorsByType.entries()]
        .sort(([,a], [,b]) => b - a)
        .slice(0, 5)
        .map(([type, count]) => ({ type, count })),
    };
    
    return stats;
  }
  
  /**
   * Reset error statistics
   */
  static resetErrorStats(): void {
    this.errorStats.totalErrors = 0;
    this.errorStats.errorsByType.clear();
    this.errorStats.lastReset = new Date();
    
    logger.info('Error statistics reset');
  }
}

/**
 * Generate unique error ID for tracking
 */
function generateErrorId(): string {
  const timestamp = Date.now().toString(36);
  const random = Math.random().toString(36).substring(2, 8);
  return `viz_error_${timestamp}_${random}`;
}

/**
 * Request validation middleware
 */
export const validateVisualizationRequest = (req: Request, res: Response, next: NextFunction) => {
  try {
    // Basic request structure validation
    if (!req.body) {
      throw new Error('Request body is required');
    }
    
    if (!req.body.chart_type) {
      throw new Error('chart_type is required');
    }
    
    if (!req.body.data || typeof req.body.data !== 'object') {
      throw new Error('data object is required');
    }
    
    // Data size validation
    const dataString = JSON.stringify(req.body.data);
    if (dataString.length > 1024 * 1024) { // 1MB limit for request body
      throw new Error('Request data is too large');
    }
    
    // Data point count validation
    const dataArrays = Object.values(req.body.data).filter(Array.isArray);
    if (dataArrays.length > 0) {
      const maxLength = Math.max(...dataArrays.map((arr: any) => arr.length));
      const validation = visualizationConfig.performance.maxDataPoints;
      
      if (maxLength > validation) {
        throw new Error(`Data contains ${maxLength} points, maximum allowed is ${validation}`);
      }
    }
    
    next();
  } catch (error) {
    VisualizationErrorHandler.handleVisualizationError(error, req, res, next);
  }
};

export { VisualizationErrorHandler };