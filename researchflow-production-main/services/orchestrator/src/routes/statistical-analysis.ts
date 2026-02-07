/**
 * Statistical Analysis Route - Stage 7
 * 
 * Handles Stage 7 (Statistical Analysis) execution including:
 * - Descriptive statistics
 * - Hypothesis testing (t-tests, ANOVA, chi-square, non-parametric)
 * - Effect size calculations
 * - Assumption checking with remediation
 * - APA-style reporting
 * 
 * Routes to StatisticalAnalysisAgent in worker service.
 */

import { Router, Request, Response } from 'express';
import * as z from 'zod';

import { config } from '../config/env';
import { asyncHandler } from '../middleware/asyncHandler';
import { requirePermission } from '../middleware/rbac';
import { logAction } from '../services/audit-service';
import { createLogger } from '../utils/logger';

const router = Router();
const logger = createLogger('statistical-analysis-route');

// Worker service URL
const WORKER_URL = config.workerUrl;

// =============================================================================
// Request Schemas
// =============================================================================

/**
 * Study data schema matching Python StudyData type
 */
const StudyDataSchema = z.object({
  groups: z.array(z.string()).optional().describe('Group labels for each observation'),
  outcomes: z.record(z.array(z.number())).describe('Outcome variables as dict of variable_name -> values'),
  covariates: z.record(z.union([z.array(z.number()), z.array(z.string())])).optional().describe('Optional covariates'),
  metadata: z.record(z.unknown()).default({}).describe('Study metadata'),
});

/**
 * Statistical analysis request schema
 */
const StatisticalAnalysisRequestSchema = z.object({
  study_data: StudyDataSchema,
  research_id: z.string().optional(),
  analysis_id: z.string().optional(),
  options: z.object({
    test_type: z.enum([
      't_test_independent',
      't_test_paired',
      'mann_whitney',
      'wilcoxon',
      'anova_oneway',
      'kruskal_wallis',
      'chi_square',
    ]).optional().describe('Specific test type to use (auto-detected if not provided)'),
    confidence_level: z.number().min(0.5).max(0.99).default(0.95),
    alpha: z.number().min(0.001).max(0.1).default(0.05),
    calculate_effect_size: z.boolean().default(true),
    check_assumptions: z.boolean().default(true),
    generate_visualizations: z.boolean().default(true),
  }).optional(),
});

// =============================================================================
// Routes
// =============================================================================

/**
 * POST /api/research/:id/stage/7/execute
 * 
 * Execute statistical analysis for Stage 7 of research workflow.
 * 
 * This is the primary endpoint for running StatisticalAnalysisAgent.
 */
router.post(
  '/research/:id/stage/7/execute',
  requirePermission('ANALYZE'),
  asyncHandler(async (req: Request, res: Response) => {
    const startTime = Date.now();
    const researchId = req.params.id;
    const requestId = `stat_analysis_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

    logger.info('Statistical analysis requested', { researchId, requestId });

    // Validate request
    const parseResult = StatisticalAnalysisRequestSchema.safeParse(req.body);
    if (!parseResult.success) {
      logger.warn('Invalid statistical analysis request', { 
        researchId, 
        errors: parseResult.error.issues 
      });

      return res.status(400).json({
        error: 'INVALID_REQUEST',
        message: 'Invalid statistical analysis request',
        details: parseResult.error.issues,
        request_id: requestId,
      });
    }

    const { study_data, analysis_id, options } = parseResult.data;

    // Enrich metadata with research context
    study_data.metadata = {
      ...study_data.metadata,
      research_id: researchId,
      analysis_id: analysis_id || requestId,
      requested_by: req.user?.id || 'anonymous',
      requested_at: new Date().toISOString(),
    };

    try {
      // Call worker's statistical analysis endpoint
      logger.info('Calling worker statistical analysis service', { 
        researchId, 
        workerUrl: WORKER_URL 
      });

      const workerResponse = await fetch(`${WORKER_URL}/api/analysis/statistical`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Request-ID': requestId,
          'X-Research-ID': researchId,
        },
        body: JSON.stringify({
          study_data,
          options,
        }),
        signal: AbortSignal.timeout(300000), // 5 minute timeout
      });

      if (!workerResponse.ok) {
        const errorText = await workerResponse.text();
        logger.error('Worker statistical analysis failed', {
          researchId,
          status: workerResponse.status,
          error: errorText,
        });

        return res.status(workerResponse.status).json({
          error: 'ANALYSIS_FAILED',
          message: `Worker returned ${workerResponse.status}`,
          details: errorText,
          request_id: requestId,
        });
      }

      const analysisResult = await workerResponse.json();

      // Log successful analysis
      await logAction({
        userId: req.user?.id || 'anonymous',
        action: 'STATISTICAL_ANALYSIS',
        resourceType: 'research',
        resourceId: researchId,
        metadata: {
          analysis_id: analysis_id || requestId,
          stage: 7,
          sample_size: study_data.groups?.length || 0,
          outcome_variables: Object.keys(study_data.outcomes || {}),
          test_performed: analysisResult.inferential?.test_type || 'unknown',
          quality_score: analysisResult.quality_score || null,
          duration_ms: Date.now() - startTime,
        },
      });

      logger.info('Statistical analysis completed successfully', {
        researchId,
        requestId,
        durationMs: Date.now() - startTime,
        testType: analysisResult.inferential?.test_type,
      });

      return res.json({
        request_id: requestId,
        research_id: researchId,
        status: 'completed',
        result: analysisResult,
        duration_ms: Date.now() - startTime,
      });

    } catch (error) {
      logger.error('Statistical analysis error', {
        researchId,
        requestId,
        error: error instanceof Error ? error.message : 'Unknown error',
      });

      return res.status(503).json({
        error: 'SERVICE_UNAVAILABLE',
        message: error instanceof Error ? error.message : 'Worker service unavailable',
        request_id: requestId,
      });
    }
  })
);

/**
 * POST /api/analysis/statistical/validate
 * 
 * Validate study data before running analysis.
 * Checks data quality, sample sizes, missing values, etc.
 */
router.post(
  '/analysis/statistical/validate',
  requirePermission('ANALYZE'),
  asyncHandler(async (req: Request, res: Response) => {
    const requestId = `validate_${Date.now()}`;

    // Validate request schema
    const parseResult = StudyDataSchema.safeParse(req.body);
    if (!parseResult.success) {
      return res.status(400).json({
        error: 'INVALID_DATA',
        message: 'Invalid study data format',
        details: parseResult.error.issues,
        request_id: requestId,
      });
    }

    const study_data = parseResult.data;

    // Basic validation checks
    const warnings: string[] = [];
    const errors: string[] = [];

    // Check sample size
    const sampleSize = study_data.groups?.length || 
                       (Object.values(study_data.outcomes)[0]?.length || 0);
    
    if (sampleSize < 3) {
      errors.push('Sample size too small (n < 3)');
    } else if (sampleSize < 10) {
      warnings.push('Small sample size (n < 10) - some tests may be unreliable');
    }

    // Check for missing values
    for (const [varName, values] of Object.entries(study_data.outcomes || {})) {
      const nullCount = values.filter(v => v === null || v === undefined).length;
      if (nullCount > 0) {
        warnings.push(`${varName}: ${nullCount} missing values (${(nullCount/values.length*100).toFixed(1)}%)`);
      }
    }

    // Check group balance (if groups provided)
    if (study_data.groups && study_data.groups.length > 0) {
      const groupCounts = study_data.groups.reduce((acc, g) => {
        acc[g] = (acc[g] || 0) + 1;
        return acc;
      }, {} as Record<string, number>);

      const groupSizes = Object.values(groupCounts);
      const maxSize = Math.max(...groupSizes);
      const minSize = Math.min(...groupSizes);

      if (maxSize / minSize > 2) {
        warnings.push('Groups are unbalanced (size ratio > 2:1)');
      }
    }

    const isValid = errors.length === 0;

    return res.json({
      request_id: requestId,
      valid: isValid,
      warnings,
      errors,
      metadata: {
        sample_size: sampleSize,
        outcome_variables: Object.keys(study_data.outcomes || {}).length,
        has_groups: Boolean(study_data.groups),
        has_covariates: Boolean(study_data.covariates),
      },
    });
  })
);

/**
 * GET /api/analysis/statistical/tests
 * 
 * List available statistical tests with descriptions.
 */
router.get('/analysis/statistical/tests', (_req: Request, res: Response) => {
  res.json({
    tests: [
      {
        type: 't_test_independent',
        name: 'Independent t-test',
        description: 'Compare means of two independent groups',
        assumptions: ['normality', 'homogeneity'],
        sample_size_min: 3,
        groups: 2,
      },
      {
        type: 't_test_paired',
        name: 'Paired t-test',
        description: 'Compare means of two paired groups',
        assumptions: ['normality'],
        sample_size_min: 3,
        groups: 2,
      },
      {
        type: 'mann_whitney',
        name: 'Mann-Whitney U test',
        description: 'Non-parametric alternative to independent t-test',
        assumptions: ['independence'],
        sample_size_min: 3,
        groups: 2,
      },
      {
        type: 'wilcoxon',
        name: 'Wilcoxon signed-rank test',
        description: 'Non-parametric alternative to paired t-test',
        assumptions: ['independence'],
        sample_size_min: 3,
        groups: 2,
      },
      {
        type: 'anova_oneway',
        name: 'One-way ANOVA',
        description: 'Compare means of three or more independent groups',
        assumptions: ['normality', 'homogeneity'],
        sample_size_min: 3,
        groups: '3+',
      },
      {
        type: 'kruskal_wallis',
        name: 'Kruskal-Wallis H test',
        description: 'Non-parametric alternative to one-way ANOVA',
        assumptions: ['independence'],
        sample_size_min: 3,
        groups: '3+',
      },
      {
        type: 'chi_square',
        name: 'Chi-square test of independence',
        description: 'Test association between categorical variables',
        assumptions: ['expected_counts >= 5'],
        sample_size_min: 5,
        groups: '2+',
      },
    ],
  });
});

/**
 * GET /api/analysis/statistical/health
 * 
 * Health check for statistical analysis service.
 */
router.get('/analysis/statistical/health', async (_req: Request, res: Response) => {
  let workerStatus = 'unknown';

  try {
    const workerResponse = await fetch(`${WORKER_URL}/health`, {
      method: 'GET',
      signal: AbortSignal.timeout(5000),
    });
    workerStatus = workerResponse.ok ? 'healthy' : 'unhealthy';
  } catch {
    workerStatus = 'unreachable';
  }

  res.json({
    status: 'healthy',
    service: 'statistical-analysis',
    stage: 7,
    worker_url: WORKER_URL,
    worker_status: workerStatus,
    timestamp: new Date().toISOString(),
  });
});

export default router;
