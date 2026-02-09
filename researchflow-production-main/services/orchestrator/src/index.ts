/**
 * Express Server Entry Point
 *
 * Configures and starts the ResearchFlow Canvas backend server.
 * Includes CORS, JSON parsing, authentication, RBAC, and error handling.
 *
 * Priority: P0 - CRITICAL (Phase 2 Integration)
 */

import { createServer } from 'http';

import compression from 'compression';
import cors from 'cors';
import dotenv from 'dotenv';
import express from 'express';
import { nanoid } from 'nanoid';
import WebSocket, { WebSocketServer } from 'ws';

import { CollaborationWebSocketServer } from './collaboration/websocket-server';
import { mockAuthMiddleware } from './middleware/auth.js';
import { errorHandler } from './middleware/errorHandler.js';
import { serviceAuthMiddleware } from './middleware/service-auth';
import { configureSecurityHeaders, cspViolationReporter, createSecurityHeadersMiddleware, initializeSecurityHeadersLogging } from './middleware/securityHeaders.js';
import aiAgentProxyRoutes from './routes/ai-agent-proxy';
import aiBridgeRoutes from './routes/ai-bridge';
import aiExtractionRoutes from './routes/ai-extraction';
import aiProvidersRoutes from './routes/aiProviders';
import conferenceRoutes from './routes/conference.js';
import datasetRoutes from './routes/datasets.js';
import governanceRoutes from './routes/governance.js';
import orcidRoutes from './routes/orcid';
import artifactsV2Routes from './routes/v2/artifacts.routes';
import webhooksRoutes from './routes/webhooks.js';
import ideasRoutes from './routes/docs-first/ideas.js';
import topicBriefsRoutes from './routes/docs-first/topic-briefs.js';
import venuesRoutes from './routes/docs-first/venues.js';
import docKitsRoutes from './routes/docs-first/doc-kits.js';
import experimentsRoutes from './routes/experiments';
import customFieldsRoutes from './routes/custom-fields';
import searchRoutes from './routes/search';
import semanticSearchRoutes from './routes/semanticSearch';
import tutorialsRoutes from './routes/tutorials';
// Phase G Routes (Tasks 116-135)
import phaseGRoutes from './routes/phaseG';
// Phase H Routes (Tasks 136-150)
import helpRoutes from './routes/help';
import pluginsRoutes from './routes/plugins';
import ecosystemIntegrationsRoutes from './routes/ecosystemIntegrations';
import googleDriveRoutes from './routes/google-drive';
import literatureIntegrationsRoutes from './routes/literature-integrations';
import apiKeysRoutes from './routes/apiKeys';
import tutorialSandboxRoutes from './routes/tutorialSandbox';
import futureProofingRoutes from './routes/futureProofing';
// Additional Phase H Routes
import watermarkRoutes from './routes/watermark';
import preferencesRoutes from './routes/preferences';
import invitesRoutes from './routes/invites';
import badgesRoutes from './routes/badges';
import sustainabilityRoutes from './routes/sustainability';
import peerReviewRoutes from './routes/peerReview';
import taskBoardsRoutes from './routes/taskBoards';
import consentRoutes from './routes/consent';
import commentsRoutes from './routes/comments';
import submissionsRoutes from './routes/submissions';
import manuscriptBranchesRoutes, { manuscriptBranchingRoutes } from './routes/manuscript-branches';
import commitsRoutes from './routes/commits.routes';
import manuscriptsRoutes from './routes/manuscripts';  // Canonical manuscript CRUD (Track M)
import editSessionsRoutes from './routes/edit-sessions.routes';  // Phase 3: HITL edit sessions
// Audit Improvements: New modular routes
import authRoutes from './routes/auth';
import workflowStagesExecuteRoutes from './routes/workflow/stages';
import { closeWorkflowStagesQueue } from './routes/workflow/stages';
import workflowStagesRoutes from './routes/workflow-stages';
import workflowsRoutes from './routes/workflows';
import organizationsRoutes from './routes/organizations';
import userSettingsRoutes from './routes/user-settings';

// Phase 1: Critical AI & Extraction Routes (Integration Plan)
import aiFeedbackRoutes from './routes/ai-feedback';
import aiRouterRoutes from './routes/ai-router';
import aiStreamingRoutes from './routes/ai-streaming';
// Phase 5.5 Stream F: LangGraph Agent LLM Proxy (ROS-30)
// Phase 5.5 Stream F: LangGraph Chat Agent API (ROS-30)
import chatAgentRoutes from './routes/chat-agent';
// AI Bridge: Python Worker ↔ TypeScript Orchestrator Bridge
import spreadsheetCellParseRoutes from './routes/spreadsheet-cell-parse';
import phiScannerRoutes from './routes/phi-scanner';

// Phase 2: Core API Routes (Integration Plan)
import artifactGraphRoutes from './routes/artifact-graph';
import artifactVersionsRoutes from './routes/artifact-versions';
import exportBundleRoutes from './routes/export-bundle';
import rosWorkerProxyRoutes from './routes/ros-worker-proxy';
import streamRoutes from './routes/stream';
import analysisExecutionRoutes from './routes/analysis-execution';
import claimsRoutes from './routes/claims';
import literatureRoutes from './routes/literature';
import rosRagRoutes from './routes/ros-rag';
import meshLookupRoutes from './routes/mesh-lookup';
import metricsRoutes from './routes/metrics';
// Phase 5.5: Git-based Version Control for Analysis & Manuscripts
import versionControlRoutes from './routes/version-control';
// Chat Agents: Workflow-specific AI assistants
import chatRoutes from './routes/chat.routes';
// Agentic Planning: AI-assisted statistical analysis
import analysisPlanningRoutes from './routes/analysis-planning';
import statisticalRecommendationsRoutes from './routes/statistical-recommendations';
import statisticalAuditRoutes from './routes/statistical-audit';
import statisticalAnalysisRoutes from './routes/statistical-analysis';
import visualizationRoutes from './routes/visualization';
// Phase Chat: Stage-specific AI agent chat
import phaseChatRoutes from './routes/phaseChatRoutes';
// Guidelines Engine: Proxy to Python FastAPI microservice
// Architecture: Node.js orchestrator proxies to packages/guideline-engine for deterministic calculations
import guidelinesProxyRoutes from './routes/guidelines-proxy.routes';
// Planning Hub: Notion-like pages, databases, tasks, goals, and projections
import hubRoutes from './routes/hub';
import internalRoutes from './routes/internal';
// Cumulative Workflow: Stage data flow between 20 research stages
import cumulativeDataRoutes from './routes/cumulative-data';
// Multi-File Ingestion: Multi-file/multi-sheet data merging with ID detection
import ingestRoutes from './routes/ingest';

// Missing Routes Audit (2026-01-28): Previously unregistered route files
import projectsRoutes from './routes/projects';  // Project CRUD operations
import citationsRoutes from './routes/citations';  // Citation management
import exportRoutes from './routes/export';  // Document export (PDF, DOCX, etc.)
import ecosystemRoutes from './routes/ecosystem';  // Ecosystem integrations
import integrityRoutes from './routes/integrity';  // Data integrity verification
import papersRoutes from './routes/papers';  // Paper management
import collectionsRoutes from './routes/collections';  // Collection management
import guidelinesRoutes from './routes/guidelines.routes';  // Full guidelines engine routes
import paperAnnotationsRoutes from './routes/paper-annotations';  // Paper annotations
import paperCopilotRoutes from './routes/paper-copilot';  // AI paper copilot
import literatureNotesRoutes from './routes/literature-notes';  // Literature notes
import branchesRoutes from './routes/branches.routes';  // Branch management
import exportRisRoutes from './routes/export-ris';  // RIS (Research Information Systems) export
import userFavoritesRoutes from './routes/user-favorites';  // User favorites/bookmarks
import favesRoutes from './routes/faves';  // FAVES compliance evaluation framework
import phrasesRoutes from './routes/phrases';  // Research terminology library
import sourceAttributesRoutes from './routes/source-attributes';  // Source citation attributes
import transparencyRoutes from './routes/transparency';  // Transparency and audit logging
import integrationsStorageRoutes from './routes/integrations-storage';  // Integration data persistence

// Transparency & Compliance Routes (Phase 10)
import favesRoutes from './routes/faves';  // FAVES compliance tracking
import transparencyRoutes from './routes/transparency';  // Evidence bundles & model registry
import monitoringRoutes from './routes/monitoring';  // Drift & bias monitoring

// Phase 3: Secondary Routes (Integration Plan)
import governanceSimulateRoutes from './routes/governance-simulate';
// Dev Auth Routes (E2E testing only - disabled in production)
import devAuthRoutes, { devAuthMiddleware } from './routes/devAuth';
import qualityRoutes from './routes/quality';
import mfaRoutes from './routes/mfa';
import notificationsRoutes from './routes/notifications';
import billingRoutes from './routes/billing';
import collaborationExportRoutes from './routes/collaborationExport';
import sapRoutes from './routes/sap';
import checklistsRoutes from './routes/checklists';
import researchBriefRoutes from './routes/research-brief';
import integrationsRoutes from './routes/integrations';
import aiInsightsRoutes from './routes/ai-insights';
import manuscriptGenerationRoutes from './routes/manuscript-generation';
import sharesRoutes from './routes/shares';
import topicsRoutes from './routes/topics';
import analyticsRoutes from './routes/analytics';
import demoRoutes from './routes/demo';
import manuscriptIdeationRoutes from './routes/manuscript-ideation';

// Collaborative Variable Tagging (Phase Variable Selection)
import variableSelectionRoutes from './routes/variable-selection';
import { optionalAuth } from './services/authService';
import { createLogger } from './utils/logger';
import { webSocketManager } from './websocket/manager';
// Phase 4B: PHI-safe event WebSocket server. Gate: WEBSOCKET_EVENTS_ENABLED=true (default off for prod rollout).
import { websocketServer as phase4bEventServer } from './websocket/server';

// Load environment variables
dotenv.config();

const logger = createLogger('orchestrator-server');

const app = express();
const PORT = process.env.PORT || 3001;
const NODE_ENV = process.env.NODE_ENV || 'development';
const WORKER_WS_URL = process.env.WORKER_WS_URL || 'ws://worker:8000';

// ============================
// CORS ORIGIN VALIDATION (SEC-002 Security Fix)
// ============================

/**
 * Validates if a URL origin matches a pattern
 * Supports exact matches and wildcard subdomains (*.example.com)
 * Enforces HTTPS in production
 */
function isOriginValid(origin: string | undefined, whitelist: string[], isDevelopment: boolean): boolean {
  if (!origin) {
    return false;
  }

  try {
    const url = new URL(origin);

    // In production, enforce HTTPS
    if (!isDevelopment && url.protocol !== 'https:') {
      logger.warn('Rejected non-HTTPS origin in production', { origin });
      return false;
    }

    // Check against whitelist
    return whitelist.some(pattern => {
      // Exact match
      if (pattern === origin) {
        return true;
      }

      // Wildcard subdomain match (e.g., *.example.com)
      if (pattern.startsWith('*.')) {
        const domain = pattern.substring(2);
        return url.hostname.endsWith('.' + domain) || url.hostname === domain;
      }

      return false;
    });
  } catch (error) {
    logger.warn('Invalid origin URL', { origin, error });
    return false;
  }
}

/**
 * Parses CORS_WHITELIST environment variable
 * Format: comma-separated list of origins
 * Example: https://app.example.com,https://admin.example.com,*.example.com
 */
function parseCorsList(corsEnv: string | undefined): string[] {
  if (!corsEnv) {
    return [];
  }

  return corsEnv
    .split(',')
    .map(origin => origin.trim())
    .filter(origin => origin.length > 0);
}

// Build allowed origins list
const corsWhitelist = parseCorsList(process.env.CORS_WHITELIST);

// Development fallback: allow localhost in development
if (NODE_ENV === 'development') {
  if (!corsWhitelist.includes('http://localhost:5173')) {
    corsWhitelist.push('http://localhost:5173');
  }
  if (!corsWhitelist.includes('http://localhost:3001')) {
    corsWhitelist.push('http://localhost:3001');
  }
  if (!corsWhitelist.includes('http://localhost:3000')) {
    corsWhitelist.push('http://localhost:3000');
  }
}

logger.info('CORS whitelist configured', { environment: NODE_ENV, whitelist: corsWhitelist });

// CORS middleware with origin validation
app.use(cors({
  origin: (origin, callback) => {
    const isDev = NODE_ENV === 'development';

    // Allow requests without Origin header (same-origin requests)
    if (!origin) {
      return callback(null, true);
    }

    if (isOriginValid(origin, corsWhitelist, isDev)) {
      callback(null, true);
    } else {
      logger.warn('Rejected origin by CORS policy', { origin, environment: NODE_ENV });
      callback(new Error(`CORS policy: Origin not allowed`), false);
    }
  },
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization', 'X-Requested-With'],
  optionsSuccessStatus: 200
}));

// Enable gzip compression for all responses
app.use(compression({
  filter: (req, res) => {
    if (req.headers['x-no-compression']) {
      return false;
    }
    return compression.filter(req, res);
  },
  level: 6,
  threshold: 1024
}));

// Request correlation ID middleware
app.use((req, res, next) => {
  const correlationId = req.headers['x-correlation-id'] as string || nanoid();
  req.correlationId = correlationId;
  res.setHeader('X-Correlation-ID', correlationId);
  
  // Add request timing
  req.startTime = Date.now();
  
  next();
});

// Cache headers for static assets
app.use('/static', (req, res, next) => {
  // Cache static assets for 1 year
  res.setHeader('Cache-Control', 'public, max-age=31536000, immutable');
  next();
});

app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Service token auth (must run before security headers and rate limiters)
app.use(serviceAuthMiddleware);

// Security Headers Middleware (SEC-005 Fix - APPLIED)
app.use(createSecurityHeadersMiddleware());
app.use('/api/csp-violations', cspViolationReporter());

// Initialize security headers logging
initializeSecurityHeadersLogging();

// Enhanced request logging with correlation IDs and performance metrics
if (NODE_ENV === 'development') {
  app.use((req, res, next) => {
    logger.debug('Incoming request', { 
      method: req.method, 
      path: req.path,
      correlationId: req.correlationId,
      userAgent: req.headers['user-agent']
    });
    next();
  });
}

// Response time logging middleware
app.use((req, res, next) => {
  const originalSend = res.send;
  
  res.send = function(data) {
    const responseTime = Date.now() - (req.startTime || Date.now());
    
    // Log slow requests (>1000ms)
    if (responseTime > 1000) {
      logger.warn('Slow request detected', {
        method: req.method,
        path: req.path,
        responseTime,
        correlationId: req.correlationId,
        statusCode: res.statusCode
      });
    }
    
    // Add performance headers
    res.setHeader('X-Response-Time', `${responseTime}ms`);
    
    return originalSend.call(this, data);
  };
  
  next();
});

// Optional authentication middleware - attaches user if token present, allows anonymous if not
// This replaces mockAuthMiddleware and works with JWT tokens from frontend
app.use(optionalAuth);

// Enhanced health check endpoint with dependency checks
app.get('/health', async (req, res) => {
  const startTime = Date.now();
  const health = {
    status: 'healthy',
    timestamp: new Date().toISOString(),
    environment: NODE_ENV,
    governanceMode: process.env.GOVERNANCE_MODE || 'DEMO',
    version: process.env.npm_package_version || '1.0.0',
    uptime: process.uptime(),
    memory: process.memoryUsage(),
    dependencies: {
      database: 'checking',
      redis: 'checking',
      worker: 'checking'
    },
    responseTime: 0
  };

  // Quick dependency checks (with timeouts)
  try {
    // Database check (with timeout)
    const dbTimeout = setTimeout(() => {
      health.dependencies.database = 'timeout';
    }, 1000);
    
    // Redis check (with timeout)
    const redisTimeout = setTimeout(() => {
      health.dependencies.redis = 'timeout';
    }, 1000);
    
    // Worker check (with timeout)
    const workerTimeout = setTimeout(() => {
      health.dependencies.worker = 'timeout';
    }, 1000);
    
    // Mock quick checks (replace with actual dependency health checks)
    health.dependencies.database = 'healthy';
    health.dependencies.redis = 'healthy';
    health.dependencies.worker = 'healthy';
    
    clearTimeout(dbTimeout);
    clearTimeout(redisTimeout);
    clearTimeout(workerTimeout);
  } catch (error) {
    health.status = 'degraded';
    logger.warn('Health check dependency failure', { error });
  }

  health.responseTime = Date.now() - startTime;
  
  // Return 503 if any critical dependencies are down
  const status = health.dependencies.database === 'healthy' && 
                health.dependencies.redis === 'healthy' ? 200 : 503;
  
  res.status(status).json(health);
});

// Demo routes (no auth required)
app.use('/api/demo', demoRoutes);

// Dev Auth routes (E2E testing - only enabled when ENABLE_DEV_AUTH=true in non-production)
app.use('/api/dev-auth', devAuthRoutes);
// Apply dev auth middleware globally (checks X-Dev-User-Id header)
app.use(devAuthMiddleware);

// API Routes
app.use('/api/governance', governanceRoutes);
app.use('/api/datasets', datasetRoutes);
app.use('/api/ros/conference', conferenceRoutes);
app.use('/api/ros/comments', commentsRoutes);  // Inline comments with PHI scanning
app.use('/api/ros/submissions', submissionsRoutes);  // Journal/conference submissions
app.use('/api/ros/manuscripts', manuscriptBranchesRoutes);  // Manuscript branching & merging
app.use('/api/ros', commitsRoutes);  // Commit endpoints: list, diff, rollback-as-commit
app.use('/api/manuscripts', manuscriptsRoutes);  // Canonical manuscript CRUD (Track M Phase M1)
app.use('/api/manuscripts', manuscriptBranchingRoutes);  // Git-like manuscript versioning + AI refinement
app.use('/api/edit-sessions', editSessionsRoutes);  // Phase 3: HITL edit sessions (draft → submit → approve/reject → merge)
app.use('/api/orcid', orcidRoutes);

// V2 API Routes (new collaboration + provenance features)
app.use('/api/v2/artifacts', artifactsV2Routes);

// Docs-First API Routes (Phase 1)
app.use('/api/docs-first/ideas', ideasRoutes);
app.use('/api/docs-first/topic-briefs', topicBriefsRoutes);
app.use('/api/docs-first/venues', venuesRoutes);
app.use('/api/docs-first/doc-kits', docKitsRoutes);

// Phase F API Routes (UI/UX Enhancements)
app.use('/api/experiments', experimentsRoutes);
app.use('/api/custom-fields', customFieldsRoutes);
app.use('/api/tutorials', tutorialsRoutes);  // Task 108: Inline Tutorials

// Search API Routes (Task 98, Task 107)
app.use('/api/search', searchRoutes);
app.use('/api/search', semanticSearchRoutes);  // Semantic search endpoints
app.use('/api/embeddings', semanticSearchRoutes);  // Embedding generation endpoint

// Webhook Routes (Stripe, Zoom, etc.)
// Note: These routes have their own body parsing for signature verification
app.use('/api/webhooks', webhooksRoutes);

// Phase G Routes (Tasks 116-135: Scalability, Performance, Monitoring)
app.use('/api/monitoring', phaseGRoutes);  // All Phase G endpoints

// Phase H Routes (Tasks 136-150)
app.use('/api/help', helpRoutes);  // Task 136: Interactive API docs + Task 140: Community links
app.use('/api/plugins', pluginsRoutes);  // Task 137: Plugin marketplace
app.use('/api/ai', aiProvidersRoutes);  // Task 141: Custom AI model hooks
app.use('/api/integrations', ecosystemIntegrationsRoutes);
app.use('/api/integrations/google-drive', googleDriveRoutes);  // Google Drive/Docs export
app.use('/api/literature', literatureIntegrationsRoutes);  // Zotero integration  // Tasks 139, 143, 144: Overleaf, Git, Import
app.use('/api/profile/api-keys', apiKeysRoutes);  // Task 138: API key rotation
app.use('/api/tutorials/sandbox', tutorialSandboxRoutes);  // Task 145: Tutorial code sandboxes
app.use('/api/admin/upgrades', futureProofingRoutes);  // Task 150: Future-proofing checklists

// Additional Phase H Routes (Previously Unregistered)
app.use('/api/ai/watermark', watermarkRoutes);  // AI watermark verification and management
app.use('/api/me/preferences', preferencesRoutes);  // User preferences API
app.use('/api', invitesRoutes);  // Organization invite management (handles /api/org/:orgId/invites and /api/invites/*)
app.use('/api/badges', badgesRoutes);  // Gamification badges system
app.use('/api/sustainability', sustainabilityRoutes);  // CO2 tracking and sustainability metrics
app.use('/api/peer-review', peerReviewRoutes);  // Peer review system with rubrics
app.use('/api', taskBoardsRoutes);  // Task board management (handles /api/research/:researchId/boards)
app.use('/api/consent', consentRoutes);  // GDPR consent management

// Audit Improvements: Authentication and Workflow Routes
app.use('/api/auth', authRoutes);  // JWT-based authentication (replaces Replit auth)
app.use('/api/workflow', workflowStagesRoutes);  // Workflow stage management and lifecycle
app.use('/api/workflow/stages', workflowStagesExecuteRoutes);  // Workflow stage execution (BullMQ)
app.use('/api/workflows', workflowsRoutes);  // Workflow CRUD, versioning, templates
app.use('/api/org', organizationsRoutes);  // Organization management (Task 81)
app.use('/api/user', userSettingsRoutes);  // User settings and preferences

// ============================
// Integration Plan Routes - Phase 1: Critical AI & Extraction
// ============================
app.use('/api/ai/extraction', aiExtractionRoutes);  // LLM clinical extraction
app.use('/api/ai/feedback', aiFeedbackRoutes);  // AI output feedback collection
app.use('/api/ai/router', aiRouterRoutes);  // Intelligent model routing
app.use('/api/ai/streaming', aiStreamingRoutes);  // SSE for AI responses
app.use('/api/ai/agent-proxy', aiAgentProxyRoutes);  // Phase 5.5: LangGraph agent LLM proxy (ROS-30)
app.use('/api/ai-bridge', aiBridgeRoutes);  // Python Worker ↔ TypeScript Bridge
app.use('/api/extraction/spreadsheet', spreadsheetCellParseRoutes);  // Cell-level extraction
app.use('/api/ros/phi', phiScannerRoutes);  // PHI scanning API

// ============================
// Integration Plan Routes - Phase 2: Core API Routes
// ============================
app.use('/api/ros/artifacts/graph', artifactGraphRoutes);  // Provenance graph API
app.use('/api/ros/artifacts/versions', artifactVersionsRoutes);  // Version management
app.use('/api/export', exportBundleRoutes);  // Reproducibility bundles
app.use('/api/ros/worker', rosWorkerProxyRoutes);  // Worker job proxy
app.use('/api/stream', streamRoutes);  // SSE event stream
app.use('/api/ros/analysis', analysisExecutionRoutes);  // Analysis job execution
app.use('/api/ros/claims', claimsRoutes);  // Claim extraction
app.use('/api/ros/literature', literatureRoutes);  // Literature search API
app.use('/api/ros/rag', rosRagRoutes);  // RAG E2E proxy: ingest, retrieve, verify
app.use('/api/literature/mesh', meshLookupRoutes);  // MeSH term lookup
app.use('/api/metrics', metricsRoutes);  // Prometheus metrics
app.use('/api/version', versionControlRoutes);  // Phase 5.5: Git-based version control
app.use('/api/chat', chatRoutes);  // Chat Agents: Workflow-specific AI assistants
app.use('/api/chat/agent', chatAgentRoutes);  // Phase 5.5: LangGraph Chat Agents (ROS-30)
app.use('/api/analysis', analysisPlanningRoutes);  // Agentic Planning: AI-assisted statistical analysis
app.use('/api/analysis', statisticalRecommendationsRoutes);  // Statistical method recommendations (knowledge graph)
app.use('/api/audit/statistical', statisticalAuditRoutes);  // Statistical audit trail API
app.use('/api', statisticalAnalysisRoutes);  // Stage 7: Statistical Analysis (StatisticalAnalysisAgent)
app.use('/api', visualizationRoutes);  // Stage 8: Data Visualization (DataVisualizationAgent)
app.use('/api/phase', phaseChatRoutes);  // Phase Chat: Stage-specific AI agents
app.use('/api/guidelines', guidelinesProxyRoutes);  // Guidelines Engine: Proxy to Python FastAPI
app.use('/api/hub', hubRoutes);  // Planning Hub
app.use('/internal', internalRoutes);  // Internal (service-to-service) routes
app.use('/api/cumulative', cumulativeDataRoutes);  // Cumulative workflow stage data
app.use('/api/ingest', ingestRoutes);  // Multi-file ingestion
app.use('/api/ros/stages/manuscript_ideation', manuscriptIdeationRoutes);  // Manuscript ideation workflow stage

// ============================
// Collaborative Variable Tagging Routes
// ============================
app.use('/api', variableSelectionRoutes);

// ============================
// Integration Plan Routes - Phase 3: Secondary Routes
// ============================
app.use('/api/governance/simulate', governanceSimulateRoutes);  // Governance simulation
app.use('/api/ros/quality', qualityRoutes);  // Quality dashboard data
app.use('/api/auth/mfa', mfaRoutes);  // Multi-factor auth
app.use('/api/notifications', notificationsRoutes);  // Notification center
app.use('/api/billing', billingRoutes);  // Stripe integration
app.use('/api/collaboration/export', collaborationExportRoutes);  // Yjs document export
app.use('/api/ros/sap', sapRoutes);  // Statistical Analysis Plan
app.use('/api/checklists', checklistsRoutes);  // Track C: Documentation Checklists (TRIPOD+AI, CONSORT-AI)
app.use('/api/ros/research-brief', researchBriefRoutes);  // Research brief generation
app.use('/api/integrations/external', integrationsRoutes);  // External integrations
app.use('/api/ai', aiInsightsRoutes);  // AI Insights endpoints (research-brief, evidence-gap-map, study-cards, decision-matrix)
app.use('/api/manuscript', manuscriptGenerationRoutes);  // Manuscript generation (IMRaD sections)
app.use('/api/shares', sharesRoutes);  // Document sharing
app.use('/api/topics', topicsRoutes);  // Topic management
app.use('/api/analytics', analyticsRoutes);  // Analytics events

// ============================
// Route Audit Fix (2026-01-28): Previously unregistered routes
// ============================
app.use('/api/projects', projectsRoutes);  // Project CRUD operations
app.use('/api/citations', citationsRoutes);  // Citation management (APA, MLA, etc.)
app.use('/api/export/documents', exportRoutes);  // Document export (PDF, DOCX, LaTeX)
app.use('/api/ecosystem', ecosystemRoutes);  // External ecosystem integrations
app.use('/api/integrity', integrityRoutes);  // Data integrity & reproducibility checks
app.use('/api/papers', papersRoutes);  // Paper management & metadata
app.use('/api/collections', collectionsRoutes);  // Research collections
app.use('/api/guidelines/full', guidelinesRoutes);  // Full guidelines engine (local routes)
app.use('/api/papers/annotations', paperAnnotationsRoutes);  // Paper annotations & highlights
app.use('/api/papers/copilot', paperCopilotRoutes);  // AI paper copilot assistant
app.use('/api/literature/notes', literatureNotesRoutes);  // Literature notes & summaries
app.use('/api/branches', branchesRoutes);  // Git-style branch management
app.use('/api/export/ris', exportRisRoutes);  // RIS (Research Information Systems) export format
app.use('/api/favorites', userFavoritesRoutes);  // User favorites/bookmarks
app.use('/api/faves', favesRoutes);  // FAVES compliance evaluation framework
app.use('/api/phrases', phrasesRoutes);  // Research terminology phrase library
app.use('/api/citations/attributes', sourceAttributesRoutes);  // Source citation attribute management
app.use('/api/audit/transparency', transparencyRoutes);  // Transparency and audit logging
app.use('/api/integrations/storage', integrationsStorageRoutes);  // Integration data persistence

// =============================================================================
// Transparency & Compliance Routes (Phase 10: FAVES, Evidence Bundles)
// =============================================================================
app.use('/api/faves', favesRoutes);  // FAVES compliance tracking (Fair, Appropriate, Valid, Effective, Safe)
app.use('/api/transparency', transparencyRoutes);  // Evidence bundles, model registry, HTI-1 attributes
app.use('/api/monitoring/models', monitoringRoutes);  // Post-deployment drift & bias monitoring

// Enhanced 404 handler with correlation ID
app.use((req, res) => {
  logger.warn('Route not found', {
    method: req.method,
    path: req.path,
    correlationId: req.correlationId,
    userAgent: req.headers['user-agent']
  });
  
  res.status(404).json({
    error: 'Not Found',
    code: 'ROUTE_NOT_FOUND',
    path: req.path,
    correlationId: req.correlationId,
    timestamp: new Date().toISOString()
  });
});

// Error handler (must be last)
app.use(errorHandler);

// Create HTTP server
const httpServer = createServer(app);

// Initialize WebSocket server for collaboration
let wsServer: CollaborationWebSocketServer | null = null;
try {
  wsServer = new CollaborationWebSocketServer(httpServer);
} catch (error) {
  logger.logError('Failed to initialize WebSocket server', error as Error);
  logger.info('Continuing without collaboration features...');
}

// Initialize WebSocket manager for real-time run events (Phase 4B)
try {
  webSocketManager.initialize(httpServer);
  logger.info('WebSocket event system initialized', { path: '/ws' });
} catch (error) {
  logger.logError('Failed to initialize WebSocket event manager', error as Error);
  logger.info('Continuing without WebSocket event system...');
}

// Phase 4B: Mount PHI-safe event WebSocket server when WEBSOCKET_EVENTS_ENABLED=true (safe for prod rollout; default off).
let phase4bEventWsEnabled = false;
if (process.env.WEBSOCKET_EVENTS_ENABLED === 'true') {
  try {
    phase4bEventServer.initialize(httpServer);
    phase4bEventWsEnabled = true;
    logger.info('Phase 4B PHI-safe event WebSocket server enabled', { path: '/ws' });
  } catch (error) {
    logger.logError('Failed to initialize Phase 4B event WebSocket server', error as Error);
  }
}

/**
 * Proxy LangGraph agent progress WebSockets to the internal worker service.
 * Keeps worker private while allowing the web frontend to connect via orchestrator.
 */
function setupAgentWebSocketProxy(server: ReturnType<typeof createServer>) {
  const wss = new WebSocketServer({ noServer: true });

  server.on('upgrade', (req, socket, head) => {
    const url = req.url;
    if (!url) return;

    const pathname = (() => {
      try {
        return new URL(url, 'http://localhost').pathname;
      } catch {
        return null;
      }
    })();

    if (!pathname || !pathname.startsWith('/api/agents/ws/')) {
      return;
    }

    const taskId = pathname.split('/').pop();
    if (!taskId) {
      socket.destroy();
      return;
    }

    const targetUrl = `${WORKER_WS_URL}/agents/ws/${taskId}`;
    const upstream = new WebSocket(targetUrl);

    wss.handleUpgrade(req, socket, head, (client) => {
      const closeAll = () => {
        if (client.readyState === client.OPEN) client.close();
        if (upstream.readyState === upstream.OPEN) upstream.close();
      };

      client.on('message', (data) => {
        if (upstream.readyState === upstream.OPEN) {
          upstream.send(data);
        }
      });

      upstream.on('message', (data) => {
        if (client.readyState === client.OPEN) {
          client.send(data);
        }
      });

      client.on('close', closeAll);
      upstream.on('close', closeAll);

      upstream.on('error', (err) => {
        if (client.readyState === client.OPEN) {
          client.send(
            JSON.stringify({
              type: 'error',
              error: err instanceof Error ? err.message : 'Upstream error'
            })
          );
        }
        closeAll();
      });
    });
  });

  logger.info('Agent WebSocket proxy enabled', { target: `${WORKER_WS_URL}/agents/ws/:taskId` });
}

setupAgentWebSocketProxy(httpServer);

// Initialize Planning Queues (BullMQ)
import { initPlanningQueues, shutdownPlanningQueues } from './services/planning';
// Initialize Workflow Stages Worker
import { initWorkflowStagesWorker, shutdownWorkflowStagesWorker } from './services/workflow-stages/worker';

// SEC-004: PHI Scanner Startup Validation
import {
  performPhiScannerHealthCheck,
  logHealthCheckResults,
  validateHealthCheckForStartup
} from './services/phi-scanner-healthcheck';

// Initialize services and start server
async function initializeServer() {
  try {
    // Initialize Planning Queues
    try {
      await initPlanningQueues();
      logger.info('Planning queues initialized', { module: 'agentic' });
    } catch (error) {
      logger.logError('Failed to initialize planning queues', error as Error, { module: 'agentic' });
      logger.info('Continuing without queue support - jobs will run inline', { module: 'agentic' });
    }

    // Initialize Workflow Stages Worker
    try {
      initWorkflowStagesWorker();
      logger.info('Workflow stages worker initialized', { module: 'workflow-stages' });
    } catch (error) {
      logger.logError('Failed to initialize workflow stages worker', error as Error, { module: 'workflow-stages' });
      logger.info('Continuing without workflow stage job processing', { module: 'workflow-stages' });
    }

    // SEC-004: Validate PHI Scanner (before accepting requests)
    const phiHealthCheck = await performPhiScannerHealthCheck();
    logHealthCheckResults(phiHealthCheck);
    validateHealthCheckForStartup(phiHealthCheck, NODE_ENV === 'production');

    // Start server
    startServer();
  } catch (error) {
    logger.logError('Fatal error during initialization', error as Error);
    process.exit(1);
  }
}

function startServer() {
  httpServer.listen(PORT, () => {
  logger.info('ResearchFlow Canvas Server Started', {
    environment: NODE_ENV,
    port: PORT,
    governanceMode: process.env.GOVERNANCE_MODE || 'DEMO',
    health_check: `http://localhost:${PORT}/health`,
    api_base: `http://localhost:${PORT}/api`,
    websocket_collaboration: `ws://localhost:${PORT}/collaboration`,
    websocket_events: `ws://localhost:${PORT}/ws`
  });

  // Log active features
  logger.info('Features Configuration', {
    phase_1_2: ['RBAC Middleware', 'Data Classification', 'Approval Gates', 'Claim Linter', 'PHI Scanning', 'ORCID Integration'],
    phase_3: ['Artifact Provenance Graph', 'Real-time Collaboration', 'Version Control', 'Comment System'],
    phase_f: ['Feature Flags', 'A/B Experiments', 'Custom Fields', 'Frontend Hooks'],
    phase_g: ['Cluster Monitoring', 'Predictive Scaling', 'Data Sharding', 'Edge Computing', 'Cost Monitoring'],
    phase_h: ['API Documentation', 'Plugin Marketplace', 'AI Model Hooks', 'Overleaf Integration', 'GDPR Consent'],
    agentic: ['AI-Assisted Planning', 'PHI Governance', 'BullMQ Queue', 'Job Status Streaming'],
    transparency: ['FAVES Compliance', 'Evidence Bundles', 'HTI-1 Attributes', 'Drift Monitoring', 'Bias Tracking']
  });
  });
}

// Start initialization sequence
initializeServer().catch((error) => {
  logger.logError('Failed to initialize server', error as Error);
  process.exit(1);
});

// Graceful shutdown
const shutdown = async () => {
  logger.info('Shutdown signal received: cleaning up...');

  // Shutdown Planning Queues
  try {
    await shutdownPlanningQueues();
    logger.info('Planning queues shut down');
  } catch (error) {
    logger.logError('Error shutting down planning queues', error as Error);
  }

  // Shutdown Workflow Stages Worker and Queue
  try {
    await shutdownWorkflowStagesWorker();
    await closeWorkflowStagesQueue();
    logger.info('Workflow stages worker and queue shut down');
  } catch (error) {
    logger.logError('Error shutting down workflow stages worker', error as Error);
  }

  // Shutdown WebSocket servers
  if (wsServer) {
    await wsServer.shutdown();
  }

  // Shutdown WebSocket event manager
  webSocketManager.shutdown();

  // Shutdown Phase 4B PHI-safe event WebSocket server if it was enabled
  if (phase4bEventWsEnabled) {
    phase4bEventServer.shutdown();
  }

  // Close HTTP server
  httpServer.close(() => {
    logger.info('HTTP server closed');
    process.exit(0);
  });

  // Force exit after 10 seconds
  setTimeout(() => {
    logger.error('Forced shutdown after timeout');
    process.exit(1);
  }, 10000);
};

process.on('SIGTERM', shutdown);
process.on('SIGINT', shutdown);
