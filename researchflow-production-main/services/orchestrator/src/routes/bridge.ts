/**
 * TypeScript-Python Bridge Router
 * 
 * Exposes TypeScript manuscript-engine services to Python workflow stages
 * via HTTP API at /api/services/{serviceName}/{methodName}
 */

import fs from 'fs';
import path from 'path';

import {
  claudeWriterService,
  abstractGeneratorService,
  introductionBuilderService,
  methodsPopulatorService,
  irbGeneratorService,
  resultsScaffoldService,
  discussionBuilderService,
  titleGeneratorService,
  keywordGeneratorService,
  referencesBuilderService,
  acknowledgmentsService,
  coiDisclosureService,
  authorManagerService,
  visualizationService,
  citationManagerService,
  exportService,
  peerReviewService,
  grammarCheckerService,
  readabilityService,
  complianceCheckerService,
  pubmedService,
  semanticScholarService,
  arxivService,
  finalPhiScanService,
  plagiarismCheckService,
  litReviewService,
  litMatrixService,
  toneAdjusterService,
  paraphraseService,
  sentenceBuilderService,
  synonymFinderService,
  clarityAnalyzerService,
  claimVerifierService,
  medicalNLPService,
  transitionSuggesterService,
} from '@researchflow/manuscript-engine';
import {
  Router,
  Request,
  Response,
  NextFunction,
} from 'express';
import rateLimit from 'express-rate-limit';
import RedisStore from 'rate-limit-redis';
import yaml from 'yaml';


import { ServiceDiscovery } from '../services/discovery.js';
import { getRedisClient, isCacheAvailable } from '../utils/cache.js';
import { CircuitBreakerRegistry } from '../utils/circuit-breaker.js';
import { logger } from '../utils/logger.js';
import { tracingMiddleware, traceServiceCall } from '../utils/tracing.js';


const router = Router();

// Global tracing + request/response logging
router.use(tracingMiddleware);

// Service registry (using singletons from manuscript-engine)
const SERVICE_REGISTRY: Record<string, any> = {
  'claude-writer': claudeWriterService,
  'abstract-generator': abstractGeneratorService,
  'methods-populator': methodsPopulatorService,
  'irb-generator': irbGeneratorService,
  'pubmed': pubmedService,
  'semantic-scholar': semanticScholarService,
  'arxiv': arxivService,
  'results-scaffold': resultsScaffoldService,
  'visualization': visualizationService,
  'citation-manager': citationManagerService,
  'export': exportService,
  'peer-review': peerReviewService,
  'grammar-checker': grammarCheckerService,
  'readability': readabilityService,
  'compliance-checker': complianceCheckerService,
  'introduction-builder': introductionBuilderService,
  'discussion-builder': discussionBuilderService,
  'title-generator': titleGeneratorService,
  'keyword-generator': keywordGeneratorService,
  'references-builder': referencesBuilderService,
  'acknowledgments': acknowledgmentsService,
  'coi-disclosure': coiDisclosureService,
  'author-manager': authorManagerService,
  'final-phi-scan': finalPhiScanService,
  'plagiarism-check': plagiarismCheckService,
  'lit-review': litReviewService,
  'lit-matrix': litMatrixService,
  'tone-adjuster': toneAdjusterService,
  'paraphrase': paraphraseService,
  'sentence-builder': sentenceBuilderService,
  'synonym-finder': synonymFinderService,
  'clarity-analyzer': clarityAnalyzerService,
  'claim-verifier': claimVerifierService,
  'medical-nlp': medicalNLPService,
  'transition-suggester': transitionSuggesterService,
};

// Mesh primitives
const circuits = new CircuitBreakerRegistry({
  failureThreshold: Number(process.env.BRIDGE_CIRCUIT_FAILURE_THRESHOLD ?? 5),
  recoveryTimeoutMs: Number(process.env.BRIDGE_CIRCUIT_RECOVERY_TIMEOUT_MS ?? 15_000),
  halfOpenSuccessThreshold: Number(process.env.BRIDGE_CIRCUIT_HALF_OPEN_SUCCESS_THRESHOLD ?? 1),
});

const discovery = new ServiceDiscovery(circuits);
for (const name of Object.keys(SERVICE_REGISTRY)) {
  discovery.registerService(name, {
    version: (SERVICE_REGISTRY[name] as any)?.version,
    instances: [{ id: `${name}-singleton`, health: 'HEALTHY' }],
  });
}

// Per-service rate limiter
async function buildRateLimiter() {
  const windowMs = Number(process.env.BRIDGE_RATE_LIMIT_WINDOW_MS ?? 60_000);
  const max = Number(process.env.BRIDGE_RATE_LIMIT_MAX ?? 120);

  try {
    const client = await getRedisClient();
    const store = new RedisStore({
      sendCommand: (...args: string[]) => (client as any).sendCommand(args),
    });

    return rateLimit({
      windowMs,
      max,
      standardHeaders: true,
      legacyHeaders: false,
      keyGenerator: (req) => {
        const serviceName = req.params.serviceName ?? 'unknown';
        // separate budgets per service and per caller ip
        const ip = (req.headers['x-forwarded-for'] as string | undefined) ?? req.ip;
        return `${serviceName}:${ip}`;
      },
      store,
      handler: (req, res) => {
        res.status(429).json({
          success: false,
          error: 'rate_limited',
          service: req.params.serviceName,
        });
      },
    });
  } catch {
    // fall back to in-memory store if redis unavailable
    return rateLimit({
      windowMs,
      max,
      standardHeaders: true,
      legacyHeaders: false,
      keyGenerator: (req) => {
        const serviceName = req.params.serviceName ?? 'unknown';
        const ip = (req.headers['x-forwarded-for'] as string | undefined) ?? req.ip;
        return `${serviceName}:${ip}`;
      },
    });
  }
}

let rateLimiterPromise: Promise<ReturnType<typeof rateLimit>> | undefined;
function rateLimiterMiddleware(req: Request, res: Response, next: NextFunction) {
  if (!rateLimiterPromise) rateLimiterPromise = buildRateLimiter();
  rateLimiterPromise.then((mw) => (mw as any)(req, res, next)).catch(next);
}

// OpenAPI validation middleware (lightweight): ensure route matches spec and method is allowed
// NOTE: This is not full schema validation, but provides docs-first enforcement without adding heavy deps.
let openapiCache: any | undefined;
function loadOpenApi() {
  if (openapiCache) return openapiCache;
  const specPath = path.resolve(process.cwd(), 'src/openapi/bridge-services.yaml');
  const raw = fs.readFileSync(specPath, 'utf-8');
  openapiCache = yaml.parse(raw);
  return openapiCache;
}

function openapiValidationMiddleware(req: Request, res: Response, next: NextFunction) {
  try {
    const spec = loadOpenApi();
    const paths = spec?.paths ?? {};

    // Only validate the two known endpoints in the spec
    if (req.method === 'GET' && req.path === '/health') return next();

    // POST /:serviceName/:methodName corresponds to /api/services/{serviceName}/{methodName}
    // Since router mounted at /api/services, we match '/{serviceName}/{methodName}'
    const m = req.path.match(/^\/([^/]+)\/([^/]+)$/);
    if (!m) return next();

    const postPath = '/api/services/{serviceName}/{methodName}';
    if (!paths[postPath]?.post) {
      return res.status(500).json({ success: false, error: 'openapi_spec_missing_route' });
    }

    if (req.method !== 'POST') {
      return res.status(405).json({ success: false, error: 'method_not_allowed' });
    }

    return next();
  } catch (err: any) {
    logger.error('openapi_validation_error', { error: err?.message ?? String(err) });
    return next();
  }
}

/**
 * GET /api/services/health
 * Health check endpoint returning available services
 */
router.get('/health', (_req: Request, res: Response) => {
  res.json({
    status: 'ok',
    services: Object.keys(SERVICE_REGISTRY),
    cacheAvailable: isCacheAvailable(),
    timestamp: new Date().toISOString(),
  });
});

/**
 * POST /api/services/:serviceName/:methodName
 * Dynamic service method invocation
 */
router.post(
  '/:serviceName/:methodName',
  openapiValidationMiddleware,
  rateLimiterMiddleware,
  async (req: Request, res: Response) => {
    const { serviceName, methodName } = req.params;

    try {
      // Validate service exists
      const service = SERVICE_REGISTRY[serviceName];
      if (!service) {
        return res.status(404).json({
          success: false,
          error: `Service '${serviceName}' not found`,
          availableServices: Object.keys(SERVICE_REGISTRY),
        });
      }

      // Validate method exists
      if (typeof service[methodName] !== 'function') {
        const availableMethods = Object.getOwnPropertyNames(Object.getPrototypeOf(service))
          .filter(m => m !== 'constructor' && typeof service[m] === 'function');

        return res.status(404).json({
          success: false,
          error: `Method '${methodName}' not found on service '${serviceName}'`,
          availableMethods,
        });
      }

      // Discovery + circuit breaker
      const instance = discovery.chooseInstance(serviceName);
      const breaker = circuits.get(serviceName);

      const result = await traceServiceCall(req, serviceName, methodName, async () => {
        return breaker.execute(async () => {
          // Execute method with request body as parameters
          return service[methodName](req.body);
        });
      });

      res.json({ success: true, data: result, instanceId: instance?.id });
    } catch (error: any) {
      const code = error?.code;
      if (code === 'CIRCUIT_OPEN') {
        return res.status(503).json({
          success: false,
          error: 'service_unavailable',
          reason: 'circuit_open',
          service: req.params.serviceName,
        });
      }

      logger.error('bridge_error', {
        service: req.params.serviceName,
        method: req.params.methodName,
        error: error?.message ?? String(error),
      });

      res.status(500).json({
        success: false,
        error: error?.message ?? 'Internal server error',
        service: req.params.serviceName,
        method: req.params.methodName,
      });
    }
  },
);

export default router;
