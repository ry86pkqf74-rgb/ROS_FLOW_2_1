import { serveStatic } from "./static";

import { createServer } from "http";

import cors from "cors";
import dotenv from "dotenv";
import express, { type Request, Response, NextFunction } from "express";

import { registerRoutes } from "./routes";
import {
  createDefaultLimiter,
  createAuthLimiter,
  createApiLimiter,
  createPerIpLimiter,
  createPerUserLimiter,
  closeRedisClient,
} from "./src/middleware/rateLimit";
import { AdvancedErrorRecovery } from "./src/middleware/recovery";
import { SecurityEnhancementMiddleware } from "./src/middleware/security-enhancements";
import {
  configureSecurityHeaders,
  cspViolationReporter,
  apiSecurityHeaders,
  initializeSecurityHeadersLogging,
} from "./src/middleware/securityHeaders";
import { serviceAuthMiddleware } from "./src/middleware/service-auth";
import backupRouter from "./src/routes/backup-recovery";
import complianceRouter from "./src/routes/compliance";
import healthRouter from "./src/routes/health";
import recoveryRouter from "./src/routes/recovery";
import securityRouter from "./src/routes/security";
import { optionalAuth } from "./src/services/authService";
import { BackupRecoveryService } from "./src/services/backup-recovery.service";
import { ComplianceAuditService } from "./src/services/compliance-audit.service";
import { createLogger, type LogLevel } from "./src/utils/logger";

// Load environment variables
dotenv.config();

// Create logger instance
const logger = createLogger('orchestrator');

const app = express();
const httpServer = createServer(app);

// Initialize Phase 3 production hardening systems

// Advanced Error Recovery System
const recoverySystem = new AdvancedErrorRecovery({
  maxRetries: parseInt(process.env.MAX_RETRIES || '5', 10),
  baseDelay: parseInt(process.env.BASE_RETRY_DELAY || '1000', 10),
  maxDelay: parseInt(process.env.MAX_RETRY_DELAY || '30000', 10),
  enableSelfHealing: process.env.ENABLE_SELF_HEALING !== 'false',
  healthCheckInterval: parseInt(process.env.HEALTH_CHECK_INTERVAL || '30000', 10),
  cascadeTimeout: parseInt(process.env.CASCADE_TIMEOUT || '5000', 10)
});

// Backup & Disaster Recovery System
const backupService = new BackupRecoveryService({
  enableCompression: process.env.ENABLE_BACKUP_COMPRESSION !== 'false',
  enableEncryption: process.env.ENABLE_BACKUP_ENCRYPTION !== 'false',
  retentionDays: parseInt(process.env.BACKUP_RETENTION_DAYS || '30', 10)
});

// Security Enhancement System
const securityMiddleware = new SecurityEnhancementMiddleware({
  enableTLS13: process.env.ENABLE_TLS13 !== 'false',
  enableJWTSecurity: process.env.ENABLE_JWT_SECURITY !== 'false',
  enableRateLimiting: process.env.ENABLE_SECURITY_RATE_LIMITING !== 'false',
  enableDDoSProtection: process.env.ENABLE_DDOS_PROTECTION !== 'false'
});

// Compliance & Audit System
const complianceService = new ComplianceAuditService({
  enableGDPR: process.env.ENABLE_GDPR_COMPLIANCE !== 'false',
  enableSOX: process.env.ENABLE_SOX_COMPLIANCE !== 'false',
  enableAuditLogging: process.env.ENABLE_AUDIT_LOGGING !== 'false',
  enableDataRetention: process.env.ENABLE_DATA_RETENTION !== 'false'
});

// Make systems available to routes
app.locals.recoverySystem = recoverySystem;
app.locals.backupService = backupService;
app.locals.securityMiddleware = securityMiddleware;
app.locals.complianceService = complianceService;

// CORS configuration for production
const corsOptions = {
  origin: process.env.CORS_ORIGIN || "*",
  credentials: true,
  methods: ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
  allowedHeaders: ["Content-Type", "Authorization", "X-Requested-With"],
};

app.use(cors(corsOptions));

// Security headers middleware
app.use(configureSecurityHeaders());
app.use(apiSecurityHeaders());

declare module "http" {
  interface IncomingMessage {
    rawBody: unknown;
  }
}

app.use(
  express.json({
    limit: "50mb",
    verify: (req, _res, buf) => {
      req.rawBody = buf;
    },
  }),
);

app.use(express.urlencoded({ extended: false, limit: "50mb" }));

/**
 * Legacy log function - wraps structured logger for backward compatibility
 * @deprecated Use createLogger() from src/utils/logger.ts instead
 */
export function log(message: string, level: string = "info") {
  const logLevel = level as LogLevel;
  switch (logLevel) {
    case 'debug':
      logger.debug(message);
      break;
    case 'warn':
      logger.warn(message);
      break;
    case 'error':
      logger.error(message);
      break;
    default:
      logger.info(message);
  }
}

// Health check endpoints (root and /api for Docker/K8s)
app.use(healthRouter);
app.use("/api", healthRouter);

// Phase 3 Production Hardening Middleware (must be after CORS and body parsing)

// 1. Service token auth context first (sets req.auth so security + rate limiters can classify internal calls)
app.use(serviceAuthMiddleware);

// 2. Security enhancements (reads req.auth.isServiceToken to set authenticated and skip rate limit)
app.use(securityMiddleware.middleware());

// Recovery system (second layer)
app.use(recoverySystem.middleware());

// Phase 3 Management Endpoints
app.use("/api/recovery", recoveryRouter);
app.use("/api/backup", backupRouter);
app.use("/api/security", securityRouter);
app.use("/api/compliance", complianceRouter);

// Metrics endpoint - telemetry and runtime mode (no secrets)
import { getTelemetry } from "./src/utils/telemetry";

app.get("/api/metrics", (_req, res) => {
  const telemetry = getTelemetry();
  res.json(telemetry.getMetrics());
});

// Request logging middleware
app.use((req, res, next) => {
  const start = Date.now();
  const path = req.path;
  let capturedJsonResponse: Record<string, any> | undefined = undefined;

  const originalResJson = res.json;
  res.json = function (bodyJson, ...args) {
    capturedJsonResponse = bodyJson;
    return originalResJson.apply(res, [bodyJson, ...args]);
  };

  res.on("finish", () => {
    const duration = Date.now() - start;
    if (path.startsWith("/api")) {
      // Skip routine request log for internal service calls unless VERBOSE_INTERNAL_LOGS
      const isServiceCall = (req as { auth?: { isServiceToken?: boolean } }).auth?.isServiceToken === true;
      if (isServiceCall && process.env.VERBOSE_INTERNAL_LOGS !== 'true') {
        return;
      }
      // Use debug level for request logging to reduce noise in production
      logger.debug(`${req.method} ${path} ${res.statusCode} in ${duration}ms`, {
        method: req.method,
        path,
        statusCode: res.statusCode,
        duration,
      });
    }
  });

  next();
});

// Main application startup
(async () => {
  try {
    log("Starting ResearchFlow Orchestrator...");

    // Initialize security headers logging
    initializeSecurityHeadersLogging();

    // Optional auth before rate limiters so req.user is set for per-user vs per-IP limiting
    app.use(optionalAuth);

    // Initialize rate limiters
    log("Initializing rate limiters...");
    const defaultLimiter = await createDefaultLimiter();
    const authLimiter = await createAuthLimiter();
    const apiLimiter = await createApiLimiter();
    const perIpLimiter = await createPerIpLimiter();
    const perUserLimiter = await createPerUserLimiter();

    // Per-IP (unauthenticated) and per-user (authenticated) limiters first
    app.use(perIpLimiter);
    app.use(perUserLimiter);

    // Apply default rate limiter globally
    app.use(defaultLimiter);

    // Apply stricter auth limiter to authentication endpoints
    app.use(/\/(auth|login|signup|refresh-token)/, authLimiter);

    // Apply API limiter to all /api routes
    app.use(/^\/api\//, apiLimiter);

    log("Rate limiters configured");

    // Set up Phase 3 system event listeners for comprehensive logging
    
    // Recovery System Events
    recoverySystem.on('retry:success', (event) => {
      logger.debug('Retry operation succeeded', event);
      complianceService.logAuditEvent({
        eventType: 'system_recovery_success',
        action: 'retry_success',
        details: event,
        outcome: 'success',
        riskLevel: 'low'
      });
    });
    
    recoverySystem.on('retry:failed', (event) => {
      logger.error('Retry operation failed', event);
      complianceService.logAuditEvent({
        eventType: 'system_recovery_failure',
        action: 'retry_failed',
        details: event,
        outcome: 'failure',
        riskLevel: 'high'
      });
    });
    
    recoverySystem.on('health:changed', (event) => {
      logger.warn('Service health changed', event);
      complianceService.logAuditEvent({
        eventType: 'service_health_change',
        action: 'health_status_change',
        details: event,
        outcome: event.healthy ? 'success' : 'warning',
        riskLevel: event.healthy ? 'low' : 'medium'
      });
    });
    
    recoverySystem.on('healing:started', (event) => {
      logger.info('Service healing initiated', event);
      complianceService.logAuditEvent({
        eventType: 'service_healing_initiated',
        action: 'self_healing_start',
        details: event,
        outcome: 'success',
        riskLevel: 'medium'
      });
    });
    
    recoverySystem.on('healing:success', (event) => {
      logger.info('Service healing successful', event);
      complianceService.logAuditEvent({
        eventType: 'service_healing_success',
        action: 'self_healing_complete',
        details: event,
        outcome: 'success',
        riskLevel: 'low'
      });
    });
    
    recoverySystem.on('cascade:prevented', (event) => {
      logger.warn('Cascade failure prevented', event);
      complianceService.logAuditEvent({
        eventType: 'cascade_failure_prevented',
        action: 'cascade_prevention',
        details: event,
        outcome: 'success',
        riskLevel: 'high'
      });
    });
    
    // Backup System Events
    backupService.on('backup:completed', (event) => {
      logger.info('Backup completed', event);
      complianceService.logAuditEvent({
        eventType: 'backup_completed',
        action: 'data_backup',
        details: event,
        outcome: 'success',
        riskLevel: 'low',
        soxCategory: 'system_config'
      });
    });
    
    backupService.on('backup:failed', (event) => {
      logger.error('Backup failed', event);
      complianceService.logAuditEvent({
        eventType: 'backup_failed',
        action: 'data_backup',
        details: event,
        outcome: 'failure',
        riskLevel: 'critical',
        soxCategory: 'system_config'
      });
    });
    
    // Security System Events
    securityMiddleware.on && securityMiddleware.on('security:threat', (event) => {
      logger.warn('Security threat detected', event);
      complianceService.logAuditEvent({
        eventType: 'security_threat_detected',
        action: 'threat_detection',
        details: event,
        outcome: 'warning',
        riskLevel: 'critical'
      });
    });
    
    // Compliance System Events
    complianceService.on('compliance:critical', (event) => {
      logger.error('Critical compliance event', event);
    });
    
    complianceService.on('compliance:alert', (event) => {
      logger.warn('Compliance alert', event);
    });

    // Register CSP violation reporter endpoint before other routes
    app.post("/api/csp-violations", express.json(), cspViolationReporter());

    // Register API routes
    await registerRoutes(httpServer, app);
    log("Routes registered");

    // Initialize Workflow Stages Worker (BullMQ)
    try {
      const { initWorkflowStagesWorker } = await import("./src/services/workflow-stages/worker.js");
      initWorkflowStagesWorker();
      log("Workflow stages worker initialized");
    } catch (error) {
      logger.error("Failed to initialize workflow stages worker", {
        errorMessage: error instanceof Error ? error.message : String(error),
      });
      log("Continuing without workflow stage job processing");
    }

    // Initialize governance mode from database
    try {
      const { governanceConfigService } = await import("./src/services/governance-config.service.js");
      const mode = await governanceConfigService.initializeMode();
      log(`Governance mode initialized: ${mode}`);
    } catch (error) {
      logger.warn("Failed to initialize governance mode from database", {
        errorMessage: error instanceof Error ? error.message : String(error),
      });
      log("Falling back to environment variable GOVERNANCE_MODE");
    }

    // Global error handler
    app.use((err: any, _req: Request, res: Response, _next: NextFunction) => {
      const status = err.status || err.statusCode || 500;
      const message = err.message || "Internal Server Error";

      // Log error details using structured logger
      logger.error(`Request error: ${message}`, {
        statusCode: status,
        errorCode: err.code || "INTERNAL_ERROR",
        ...(process.env.NODE_ENV !== "production" && {
          stack: err.stack?.split('\n').slice(0, 5).join('\n'),
        }),
      });

      res.status(status).json({
        error: message,
        code: err.code || "INTERNAL_ERROR",
      });
    });

    // Serve static files in production or setup Vite in development
    if (process.env.NODE_ENV === "production") {
      serveStatic(app);
      log("Static files configured");
    } else {
      try {
        const { setupVite } = await import("./vite");
        await setupVite(httpServer, app);
        log("Vite development server configured");
      } catch (e) {
        log("Vite not available, running in API-only mode");
      }
    }

    // Start the server
    const port = parseInt(process.env.PORT || "3001", 10);
    const host = process.env.HOST || "0.0.0.0";

    httpServer.listen({ port, host }, () => {
      log(`Orchestrator running on http://${host}:${port}`);
      log(`Environment: ${process.env.NODE_ENV || "development"}`);
      log(`Governance Mode: ${process.env.GOVERNANCE_MODE || "DEMO"}`);
      log(`Worker URL: ${process.env.WORKER_CALLBACK_URL || "http://worker:8000"}`);
    });

    // Graceful shutdown with Phase 3 systems
    const shutdown = async (signal: string) => {
      log(`Received ${signal}, shutting down gracefully...`);

      try {
        // Log shutdown event
        await complianceService.logAuditEvent({
          eventType: 'system_shutdown',
          action: 'graceful_shutdown',
          details: { signal, timestamp: Date.now() },
          outcome: 'success',
          riskLevel: 'medium'
        });

        // Stop Phase 3 services
        log('Stopping Phase 3 production hardening services...');
        
        // Stop compliance service (flushes audit buffer)
        complianceService.stop();
        
        // Stop backup service
        backupService.stop();
        
        // Reset security middleware state
        securityMiddleware.reset();
        
        // Reset recovery system state
        recoverySystem.reset();
        
        // Close Redis client for rate limiting
        await closeRedisClient();

        // Shutdown Workflow Stages Worker
        try {
          const { shutdownWorkflowStagesWorker } = await import("./src/services/workflow-stages/worker.js");
          await shutdownWorkflowStagesWorker();
          log("Workflow stages worker shut down");
        } catch (error) {
          log(`Error shutting down workflow stages worker: ${error instanceof Error ? error.message : String(error)}`, 'error');
        }

        log('Phase 3 services stopped successfully');
        
      } catch (error) {
        log(`Error during shutdown: ${error instanceof Error ? error.message : String(error)}`, 'error');
      }

      httpServer.close(() => {
        log("HTTP server closed");
        process.exit(0);
      });

      // Force exit after timeout
      setTimeout(() => {
        log("Forcing shutdown after timeout", "warn");
        process.exit(1);
      }, 15000); // Extended timeout for Phase 3 cleanup
    };

    process.on("SIGTERM", () => shutdown("SIGTERM"));
    process.on("SIGINT", () => shutdown("SIGINT"));

  } catch (error) {
    logger.error("Failed to start orchestrator", {
      errorMessage: error instanceof Error ? error.message : String(error),
    });
    process.exit(1);
  }
})();
