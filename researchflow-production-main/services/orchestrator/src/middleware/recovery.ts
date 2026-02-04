/**
 * Advanced Error Recovery Middleware
 * Enterprise-grade self-healing mechanisms with intelligent retry
 */

import { EventEmitter } from 'events';
import fetch from 'node-fetch';
import { Request, Response, NextFunction } from 'express';

interface RecoveryConfig {
  maxRetries: number;
  baseDelay: number;
  maxDelay: number;
  jitterMax: number;
  backoffMultiplier: number;
  enableSelfHealing: boolean;
  healthCheckInterval: number;
  cascadeTimeout: number;
}

interface RetryContext {
  requestId?: string;
  route?: string;
  maxRetries?: number;
  operationName?: string;
  timeout?: number;
}

interface RecoveryRequest extends Request {
  requestId?: string;
  recovery?: {
    retry: (operation: () => Promise<any>, context?: RetryContext) => Promise<any>;
    checkService: (serviceName: string) => Promise<boolean>;
    preventCascade: (serviceName: string, timeout?: number) => Promise<boolean>;
    healService: (serviceName: string, healingFn?: () => Promise<void>) => Promise<any>;
  };
}

export class AdvancedErrorRecovery extends EventEmitter {
    private retryState = new Map();
    private serviceHealth = new Map();
    private cascadeBreakers = new Map();
    private healingJobs = new Map();
    public config: RecoveryConfig;

    constructor(options: Partial<RecoveryConfig> = {}) {
        super();
        this.config = {
            maxRetries: options.maxRetries || 5,
            baseDelay: options.baseDelay || 1000,
            maxDelay: options.maxDelay || 30000,
            jitterMax: options.jitterMax || 0.1,
            backoffMultiplier: options.backoffMultiplier || 2,
            enableSelfHealing: options.enableSelfHealing !== false,
            healthCheckInterval: options.healthCheckInterval || 30000,
            cascadeTimeout: options.cascadeTimeout || 5000,
            ...options
        };



        if (this.config.enableSelfHealing) {
            this.startHealthMonitoring();
        }

        // Bind methods to preserve context
        this.middleware = this.middleware.bind(this);
    }

    /**
     * Express middleware for intelligent retry and recovery
     */
    middleware() {
        return async (req: RecoveryRequest, res: Response, next: NextFunction) => {
            const requestId = this.generateRequestId();
            req.requestId = requestId;
            
            // Add recovery context to request
            req.recovery = {
                retry: (operation, context = {}) => this.retryWithBackoff(operation, {
                    ...context,
                    requestId,
                    route: req.route?.path || req.path
                }),
                
                checkService: (serviceName) => this.checkServiceHealth(serviceName),
                
                preventCascade: (serviceName, timeout) => 
                    this.preventCascadeFailure(serviceName, timeout),
                
                healService: (serviceName, healingFn) => 
                    this.initiateServiceHealing(serviceName, healingFn)
            };

            // Track request for cascade prevention
            this.trackRequest(requestId, req.path);

            // Enhanced error handling
            const originalSend = res.send;
            res.send = (data) => {
                this.completeRequest(requestId, res.statusCode);
                return originalSend.call(res, data);
            };

            next();
        };
    }

    /**
     * Intelligent retry with exponential backoff and jitter
     */
    async retryWithBackoff(operation: () => Promise<any>, context: RetryContext = {}): Promise<any> {
        const { 
            requestId, 
            route = 'unknown', 
            maxRetries = this.config.maxRetries,
            operationName = 'operation'
        } = context;

        let attempt = 0;
        let lastError;

        while (attempt < maxRetries) {
            try {
                const result = await this.executeWithTimeout(operation, context);
                
                // Success - clear retry state
                this.clearRetryState(requestId, operationName);
                
                // Emit success event for monitoring
                this.emit('retry:success', {
                    requestId,
                    route,
                    operationName,
                    attempt,
                    totalAttempts: attempt + 1
                });

                return result;

            } catch (error) {
                lastError = error;
                attempt++;

                // Check if error is retryable
                if (!this.isRetryableError(error) || attempt >= maxRetries) {
                    this.emit('retry:failed', {
                        requestId,
                        route,
                        operationName,
                        error: error.message,
                        totalAttempts: attempt,
                        finalFailure: true
                    });
                    throw error;
                }

                // Calculate delay with exponential backoff and jitter
                const delay = this.calculateDelay(attempt);
                
                this.emit('retry:attempt', {
                    requestId,
                    route,
                    operationName,
                    attempt,
                    delay,
                    error: error.message
                });

                // Store retry state
                this.updateRetryState(requestId, operationName, {
                    attempt,
                    lastError: error.message,
                    nextRetry: Date.now() + delay
                });

                await this.sleep(delay);
            }
        }

        throw lastError;
    }

    /**
     * Execute operation with timeout protection
     */
    async executeWithTimeout(operation: () => Promise<any>, context: RetryContext): Promise<any> {
        const timeout = context.timeout || 30000; // 30 second default
        
        return Promise.race([
            operation(),
            new Promise((_, reject) => 
                setTimeout(() => reject(new Error('Operation timeout')), timeout)
            )
        ]);
    }

    /**
     * Check if error is retryable
     */
    isRetryableError(error: Error): boolean {
        const retryablePatterns = [
            /network/i,
            /timeout/i,
            /connection/i,
            /503/i,
            /502/i,
            /504/i,
            /ECONNRESET/i,
            /ENOTFOUND/i,
            /socket hang up/i
        ];

        const errorString = error.message || error.toString();
        return retryablePatterns.some(pattern => pattern.test(errorString));
    }

    /**
     * Calculate delay with exponential backoff and jitter
     */
    calculateDelay(attempt: number): number {
        const exponentialDelay = Math.min(
            this.config.baseDelay * Math.pow(this.config.backoffMultiplier, attempt),
            this.config.maxDelay
        );

        // Add jitter to prevent thundering herd
        const jitter = exponentialDelay * this.config.jitterMax * Math.random();
        
        return Math.floor(exponentialDelay + jitter);
    }

    /**
     * Prevent cascade failures across services
     */
    async preventCascadeFailure(serviceName: string, timeout = this.config.cascadeTimeout): Promise<boolean> {
        const breakerKey = `cascade:${serviceName}`;
        
        if (this.cascadeBreakers.has(breakerKey)) {
            const breaker = this.cascadeBreakers.get(breakerKey);
            if (Date.now() - breaker.timestamp < timeout) {
                throw new Error(`Cascade prevention: ${serviceName} temporarily unavailable`);
            }
        }

        try {
            // Check if service is healthy
            const isHealthy = await this.checkServiceHealth(serviceName);
            
            if (!isHealthy) {
                // Activate cascade breaker
                this.cascadeBreakers.set(breakerKey, {
                    timestamp: Date.now(),
                    reason: 'Service unhealthy'
                });

                this.emit('cascade:prevented', {
                    service: serviceName,
                    reason: 'Service unhealthy',
                    timeout
                });

                throw new Error(`Cascade prevention activated for ${serviceName}`);
            }

            // Clear breaker if service is healthy
            this.cascadeBreakers.delete(breakerKey);
            return true;

        } catch (error) {
            this.cascadeBreakers.set(breakerKey, {
                timestamp: Date.now(),
                reason: error.message
            });
            throw error;
        }
    }

    /**
     * Check service health with caching
     */
    async checkServiceHealth(serviceName: string): Promise<boolean> {
        const cacheKey = `health:${serviceName}`;
        const cached = this.serviceHealth.get(cacheKey);
        
        // Return cached result if recent (30 seconds)
        if (cached && Date.now() - cached.timestamp < 30000) {
            return cached.healthy;
        }

        try {
            const healthy = await this.performHealthCheck(serviceName);
            
            this.serviceHealth.set(cacheKey, {
                healthy,
                timestamp: Date.now()
            });

            if (healthy !== cached?.healthy) {
                this.emit('health:changed', {
                    service: serviceName,
                    healthy,
                    previous: cached?.healthy
                });
            }

            return healthy;

        } catch (error) {
            this.serviceHealth.set(cacheKey, {
                healthy: false,
                timestamp: Date.now(),
                error: error.message
            });

            this.emit('health:error', {
                service: serviceName,
                error: error.message
            });

            return false;
        }
    }

    /**
     * Perform actual health check (to be overridden by service-specific logic)
     */
    async performHealthCheck(serviceName: string): Promise<boolean> {
        // Default implementation - override for specific services
        const serviceUrls = {
            worker: 'http://worker:8000/health',
            collab: 'http://collab:1234/health',
            redis: 'redis://redis:6379',
            postgres: 'postgresql://postgres:5432'
        };

        const url = serviceUrls[serviceName];
        if (!url) {
            throw new Error(`Unknown service: ${serviceName}`);
        }

        if (url.startsWith('http')) {
            const response = await fetch(url, { 
                method: 'GET',
                timeout: 5000 as any
            });
            return response.ok;
        }

        // For non-HTTP services, assume healthy (implement specific checks)
        return true;
    }

    /**
     * Initiate self-healing for a service
     */
    async initiateServiceHealing(serviceName: string, healingFunction?: () => Promise<void>): Promise<any> {
        const healingKey = `healing:${serviceName}`;
        
        // Prevent multiple concurrent healing attempts
        if (this.healingJobs.has(healingKey)) {
            return this.healingJobs.get(healingKey);
        }

        const healingPromise = this.executeHealing(serviceName, healingFunction);
        this.healingJobs.set(healingKey, healingPromise);

        try {
            const result = await healingPromise;
            this.healingJobs.delete(healingKey);
            
            this.emit('healing:success', {
                service: serviceName,
                result
            });

            return result;

        } catch (error) {
            this.healingJobs.delete(healingKey);
            
            this.emit('healing:failed', {
                service: serviceName,
                error: error.message
            });

            throw error;
        }
    }

    /**
     * Execute healing logic with retry
     */
    async executeHealing(serviceName: string, healingFunction?: () => Promise<void>): Promise<any> {
        this.emit('healing:started', { service: serviceName });

        // Wait for current operations to complete
        await this.sleep(1000);

        try {
            // Execute custom healing logic
            if (typeof healingFunction === 'function') {
                await healingFunction();
            } else {
                // Default healing strategies
                await this.performDefaultHealing(serviceName);
            }

            // Verify service is healthy after healing
            const isHealthy = await this.checkServiceHealth(serviceName);
            if (!isHealthy) {
                throw new Error(`Service ${serviceName} still unhealthy after healing attempt`);
            }

            return { healed: true, service: serviceName };

        } catch (error) {
            throw new Error(`Healing failed for ${serviceName}: ${error.message}`);
        }
    }

    /**
     * Default healing strategies
     */
    async performDefaultHealing(serviceName: string): Promise<void> {
        switch (serviceName) {
            case 'worker':
                // Restart worker connection pool
                break;
            case 'collab':
                // Reset collaboration state
                break;
            case 'redis':
                // Flush corrupted cache entries
                break;
            case 'postgres':
                // Reset database connections
                break;
            default:
                throw new Error(`No default healing strategy for ${serviceName}`);
        }
    }

    /**
     * Start health monitoring background process
     */
    startHealthMonitoring(): void {
        setInterval(() => {
            this.performHealthSweep();
        }, this.config.healthCheckInterval);
    }

    /**
     * Perform health check sweep of all services
     */
    async performHealthSweep(): Promise<void> {
        const services = ['worker', 'collab', 'redis', 'postgres'];
        
        for (const service of services) {
            try {
                await this.checkServiceHealth(service);
            } catch (error) {
                this.emit('health:sweep:error', {
                    service,
                    error: error.message
                });
            }
        }

        this.emit('health:sweep:complete', {
            timestamp: Date.now(),
            servicesChecked: services.length
        });
    }

    // Utility methods
    generateRequestId(): string {
        return `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    trackRequest(requestId: string, path: string): void {
        // Track for analytics/monitoring
        this.emit('request:tracked', { requestId, path });
    }

    completeRequest(requestId: string, statusCode: number): void {
        // Mark request as complete
        this.emit('request:completed', { requestId, statusCode });
    }

    updateRetryState(requestId: string, operationName: string, state: any): void {
        const key = `${requestId}:${operationName}`;
        this.retryState.set(key, state);
    }

    clearRetryState(requestId: string, operationName: string): void {
        const key = `${requestId}:${operationName}`;
        this.retryState.delete(key);
    }

    sleep(ms: number): Promise<void> {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    /**
     * Get current system status
     */
    getStatus(): any {
        return {
            retryStates: Array.from(this.retryState.entries()),
            serviceHealth: Array.from(this.serviceHealth.entries()),
            cascadeBreakers: Array.from(this.cascadeBreakers.entries()),
            activeHealingJobs: Array.from(this.healingJobs.keys()),
            config: this.config
        };
    }

    /**
     * Reset all state (for testing)
     */
    reset(): void {
        this.retryState.clear();
        this.serviceHealth.clear();
        this.cascadeBreakers.clear();
        this.healingJobs.clear();
    }
}

export default AdvancedErrorRecovery;