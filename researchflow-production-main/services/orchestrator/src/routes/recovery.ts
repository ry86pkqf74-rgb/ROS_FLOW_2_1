/**
 * Advanced Error Recovery Routes
 * Management endpoints for monitoring and controlling recovery systems
 */

import express from 'express';

import { AdvancedErrorRecovery } from '../middleware/recovery';
const router = express.Router();

// Recovery endpoints
router.get('/status', (req, res) => {
    try {
        const recovery = req.app.locals.recoverySystem;
        const status = recovery.getStatus();
        
        res.json({
            success: true,
            timestamp: Date.now(),
            recovery_status: {
                active_retries: status.retryStates.length,
                service_health: Object.fromEntries(
                    status.serviceHealth.map(([service, health]) => [
                        service.replace('health:', ''), 
                        {
                            healthy: health.healthy,
                            last_check: health.timestamp,
                            age_seconds: Math.floor((Date.now() - health.timestamp) / 1000)
                        }
                    ])
                ),
                cascade_breakers: Object.fromEntries(
                    status.cascadeBreakers.map(([service, breaker]) => [
                        service.replace('cascade:', ''),
                        {
                            active: Date.now() - breaker.timestamp < recovery.config.cascadeTimeout,
                            reason: breaker.reason,
                            activated: breaker.timestamp,
                            age_seconds: Math.floor((Date.now() - breaker.timestamp) / 1000)
                        }
                    ])
                ),
                active_healing: status.activeHealingJobs,
                configuration: {
                    max_retries: status.config.maxRetries,
                    base_delay_ms: status.config.baseDelay,
                    max_delay_ms: status.config.maxDelay,
                    backoff_multiplier: status.config.backoffMultiplier,
                    health_check_interval_ms: status.config.healthCheckInterval,
                    self_healing_enabled: status.config.enableSelfHealing
                }
            }
        });
    } catch (error) {
        res.status(500).json({
            success: false,
            error: 'Failed to get recovery status',
            details: error.message
        });
    }
});

router.get('/health/:service', async (req, res) => {
    try {
        const { service } = req.params;
        const recovery = req.app.locals.recoverySystem;
        
        const isHealthy = await recovery.checkServiceHealth(service);
        
        res.json({
            success: true,
            service,
            healthy: isHealthy,
            checked_at: Date.now()
        });
    } catch (error) {
        res.status(500).json({
            success: false,
            service: req.params.service,
            error: 'Health check failed',
            details: error.message
        });
    }
});

router.post('/heal/:service', async (req, res) => {
    try {
        const { service } = req.params;
        const { strategy } = req.body;
        const recovery = req.app.locals.recoverySystem;
        
        // Define healing strategies
        const strategies = {
            restart: async () => {
                // Implement service restart logic
                console.log(`Restarting service: ${service}`);
                await new Promise(resolve => setTimeout(resolve, 2000)); // Simulate restart
            },
            reset_connections: async () => {
                // Reset connection pools
                console.log(`Resetting connections for service: ${service}`);
                await new Promise(resolve => setTimeout(resolve, 1000));
            },
            clear_cache: async () => {
                // Clear service cache
                console.log(`Clearing cache for service: ${service}`);
                await new Promise(resolve => setTimeout(resolve, 500));
            }
        };
        
        const healingFunction = strategies[strategy];
        if (!healingFunction) {
            return res.status(400).json({
                success: false,
                error: 'Invalid healing strategy',
                valid_strategies: Object.keys(strategies)
            });
        }
        
        const result = await recovery.initiateServiceHealing(service, healingFunction);
        
        res.json({
            success: true,
            service,
            strategy,
            result,
            healed_at: Date.now()
        });
    } catch (error) {
        res.status(500).json({
            success: false,
            service: req.params.service,
            strategy: req.body.strategy,
            error: 'Healing failed',
            details: error.message
        });
    }
});

router.post('/circuit-breaker/:service/reset', (req, res) => {
    try {
        const { service } = req.params;
        const recovery = req.app.locals.recoverySystem;
        
        // Reset cascade breaker for service
        const breakerKey = `cascade:${service}`;
        recovery.cascadeBreakers.delete(breakerKey);
        
        res.json({
            success: true,
            service,
            message: 'Circuit breaker reset successfully',
            reset_at: Date.now()
        });
    } catch (error) {
        res.status(500).json({
            success: false,
            service: req.params.service,
            error: 'Failed to reset circuit breaker',
            details: error.message
        });
    }
});

router.get('/retry-stats', (req, res) => {
    try {
        const recovery = req.app.locals.recoverySystem;
        const status = recovery.getStatus();
        
        // Calculate retry statistics
        const retryStats = {
            active_retries: status.retryStates.length,
            retry_details: status.retryStates.map(([key, state]) => {
                const [requestId, operationName] = key.split(':');
                return {
                    request_id: requestId,
                    operation: operationName,
                    attempt: state.attempt,
                    last_error: state.lastError,
                    next_retry: state.nextRetry,
                    next_retry_in_seconds: Math.max(0, Math.floor((state.nextRetry - Date.now()) / 1000))
                };
            })
        };
        
        res.json({
            success: true,
            timestamp: Date.now(),
            retry_stats: retryStats
        });
    } catch (error) {
        res.status(500).json({
            success: false,
            error: 'Failed to get retry statistics',
            details: error.message
        });
    }
});

router.post('/test-retry', async (req, res) => {
    try {
        const { operation_name = 'test', should_fail = false, max_retries = 3 } = req.body;
        const recovery = req.app.locals.recoverySystem;
        
        // Create test operation
        let attempt = 0;
        const testOperation = async () => {
            attempt++;
            if (should_fail && attempt < max_retries) {
                throw new Error(`Test failure on attempt ${attempt}`);
            }
            return { success: true, attempt, message: 'Test operation completed' };
        };
        
        const result = await req.recovery.retry(testOperation, {
            operationName: operation_name,
            maxRetries: max_retries
        });
        
        res.json({
            success: true,
            test_result: result,
            total_attempts: attempt,
            completed_at: Date.now()
        });
    } catch (error) {
        res.status(500).json({
            success: false,
            error: 'Test retry failed',
            details: error.message,
            total_attempts: attempt || 0
        });
    }
});

router.delete('/reset', (req, res) => {
    try {
        const recovery = req.app.locals.recoverySystem;
        recovery.reset();
        
        res.json({
            success: true,
            message: 'Recovery system state reset successfully',
            reset_at: Date.now()
        });
    } catch (error) {
        res.status(500).json({
            success: false,
            error: 'Failed to reset recovery system',
            details: error.message
        });
    }
});

export default router;