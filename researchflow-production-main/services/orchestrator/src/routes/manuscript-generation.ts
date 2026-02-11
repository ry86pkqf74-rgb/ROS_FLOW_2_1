/**
 * Manuscript Generation Router
 * Phase 3.1: Pipeline integration for IMRaD structure
 * 
 * Wires together:
 * - ResultsScaffoldService
 * - DiscussionBuilderService
 * - TitleGeneratorService
 * - KeywordGeneratorService
 * 
 * Endpoints:
 * - POST /api/manuscript/generate/results
 * - POST /api/manuscript/generate/discussion
 * - POST /api/manuscript/generate/title-keywords
 * - POST /api/manuscript/generate/full
 * - POST /api/manuscript/validate/section
 */

import { validateWordBudget, DEFAULT_BUDGETS } from '@researchflow/manuscript-engine';
import { phiEngine } from '@researchflow/phi-engine';
import { Router, Request, Response } from 'express';

import { requireAuth } from '../middleware/auth';
import { logAction } from '../services/audit-service';
import { asString } from '../utils/asString';
import {
  runSectionVerifyGate,
  runIMRaDPipeline,
  type SectionWriterOutput,
  type IMRaDPipelineInput,
} from '../services/imrad-section-gate.service';

const router = Router();

// Worker service URL
const WORKER_URL = process.env.WORKER_URL || 'http://worker:8000';

/**
 * Generate Results section scaffold
 */
router.post('/generate/results', async (req: Request, res: Response) => {
  try {
    const { manuscriptId, datasetId, analysisResults, options } = req.body;
    const userId = (req as any).user?.id;
    
    if (!manuscriptId || !analysisResults) {
      return res.status(400).json({ 
        error: 'manuscriptId and analysisResults are required' 
      });
    }
    
    // Call worker service
    const response = await fetch(`${WORKER_URL}/api/manuscript/scaffold/results`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        dataset_id: datasetId,
        analysis_results: analysisResults,
        options: {
          include_tables: options?.includeTables ?? true,
          include_figures: options?.includeFigures ?? true,
          statistical_detail: options?.statisticalDetail ?? 'standard',
          ...options
        }
      })
    });
    
    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Worker error: ${error}`);
    }
    
    const result = await response.json();
    
    // Validate word budget
    const validation = validateWordBudget(result.content, 'results');
    
    // Log action
    await logAction({
      eventType: 'RESULTS_GENERATED',
      action: 'GENERATE',
      resourceType: 'MANUSCRIPT_SECTION',
      resourceId: manuscriptId,
      userId,
      details: { 
        wordCount: validation.wordCount,
        withinBudget: validation.valid,
        tablesCount: result.tables?.length || 0,
        figuresCount: result.figures?.length || 0
      }
    });
    
    res.json({
      section: 'results',
      content: result.content,
      tables: result.tables || [],
      figures: result.figures || [],
      statistics: result.statistics || {},
      validation,
      metadata: {
        generatedAt: new Date().toISOString(),
        datasetId,
        version: result.version || 1
      }
    });
  } catch (error) {
    console.error('[ManuscriptGen] Results generation failed:', error);
    res.status(500).json({ error: 'Failed to generate results section' });
  }
});

/**
 * Generate Discussion section
 */
router.post('/generate/discussion', async (req: Request, res: Response) => {
  try {
    const { manuscriptId, resultsSection, literatureContext, options } = req.body;
    const userId = (req as any).user?.id;
    
    if (!manuscriptId || !resultsSection) {
      return res.status(400).json({ 
        error: 'manuscriptId and resultsSection are required' 
      });
    }
    
    // Call worker service
    const response = await fetch(`${WORKER_URL}/api/manuscript/build/discussion`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        results_section: resultsSection,
        literature_context: literatureContext || [],
        options: {
          include_limitations: options?.includeLimitations ?? true,
          include_future_directions: options?.includeFutureDirections ?? true,
          comparison_depth: options?.comparisonDepth ?? 'moderate',
          ...options
        }
      })
    });
    
    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Worker error: ${error}`);
    }
    
    const result = await response.json();
    
    // Validate word budget
    const validation = validateWordBudget(result.content, 'discussion');
    
    // Log action
    await logAction({
      eventType: 'DISCUSSION_GENERATED',
      action: 'GENERATE',
      resourceType: 'MANUSCRIPT_SECTION',
      resourceId: manuscriptId,
      userId,
      details: { 
        wordCount: validation.wordCount,
        withinBudget: validation.valid,
        citationsUsed: result.citationsUsed?.length || 0
      }
    });
    
    res.json({
      section: 'discussion',
      content: result.content,
      subsections: result.subsections || {},
      citationsUsed: result.citationsUsed || [],
      validation,
      metadata: {
        generatedAt: new Date().toISOString(),
        version: result.version || 1
      }
    });
  } catch (error) {
    console.error('[ManuscriptGen] Discussion generation failed:', error);
    res.status(500).json({ error: 'Failed to generate discussion section' });
  }
});

/**
 * Generate Title and Keywords
 */
router.post('/generate/title-keywords', async (req: Request, res: Response) => {
  try {
    const { manuscriptId, abstract, sections, options } = req.body;
    const userId = (req as any).user?.id;
    
    if (!manuscriptId || !abstract) {
      return res.status(400).json({ 
        error: 'manuscriptId and abstract are required' 
      });
    }
    
    // Generate titles
    const titleResponse = await fetch(`${WORKER_URL}/api/manuscript/generate/title`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        abstract,
        sections: sections || {},
        options: {
          count: options?.titleCount ?? 5,
          style: options?.titleStyle ?? 'descriptive',
          max_length: options?.maxTitleLength ?? 150
        }
      })
    });
    
    // Generate keywords
    const keywordResponse = await fetch(`${WORKER_URL}/api/manuscript/generate/keywords`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        abstract,
        sections: sections || {},
        options: {
          count: options?.keywordCount ?? 6,
          include_mesh: options?.includeMeSH ?? true
        }
      })
    });
    
    if (!titleResponse.ok || !keywordResponse.ok) {
      throw new Error('Worker generation failed');
    }
    
    const titles = await titleResponse.json();
    const keywords = await keywordResponse.json();
    
    // Log action
    await logAction({
      eventType: 'TITLE_KEYWORDS_GENERATED',
      action: 'GENERATE',
      resourceType: 'MANUSCRIPT',
      resourceId: manuscriptId,
      userId,
      details: { 
        titlesGenerated: titles.suggestions?.length || 0,
        keywordsGenerated: keywords.keywords?.length || 0
      }
    });
    
    res.json({
      titles: titles.suggestions || [],
      keywords: keywords.keywords || [],
      meshTerms: keywords.meshTerms || [],
      metadata: {
        generatedAt: new Date().toISOString()
      }
    });
  } catch (error) {
    console.error('[ManuscriptGen] Title/Keywords generation failed:', error);
    res.status(500).json({ error: 'Failed to generate title and keywords' });
  }
});

/**
 * Generate full manuscript structure
 */
router.post('/generate/full', async (req: Request, res: Response) => {
  try {
    const { 
      manuscriptId, 
      datasetId, 
      analysisResults, 
      literatureContext,
      existingAbstract,
      options 
    } = req.body;
    const userId = (req as any).user?.id;
    
    if (!manuscriptId || !analysisResults) {
      return res.status(400).json({ 
        error: 'manuscriptId and analysisResults are required' 
      });
    }
    
    const results: Record<string, any> = {};
    const errors: string[] = [];
    
    // 1. Generate Results
    try {
      const resultsResponse = await fetch(`${WORKER_URL}/api/manuscript/scaffold/results`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          dataset_id: datasetId,
          analysis_results: analysisResults,
          options: options?.results || {}
        })
      });
      results.results = await resultsResponse.json();
    } catch (e) {
      errors.push('Results generation failed');
    }
    
    // 2. Generate Discussion (using results)
    if (results.results) {
      try {
        const discussionResponse = await fetch(`${WORKER_URL}/api/manuscript/build/discussion`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            results_section: results.results.content,
            literature_context: literatureContext || [],
            options: options?.discussion || {}
          })
        });
        results.discussion = await discussionResponse.json();
      } catch (e) {
        errors.push('Discussion generation failed');
      }
    }
    
    // 3. Generate Title and Keywords
    const abstractText = existingAbstract || 
      `${results.results?.content?.substring(0, 500) || ''} ${results.discussion?.content?.substring(0, 500) || ''}`;
    
    try {
      const [titleRes, keywordRes] = await Promise.all([
        fetch(`${WORKER_URL}/api/manuscript/generate/title`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ abstract: abstractText, options: options?.title || {} })
        }),
        fetch(`${WORKER_URL}/api/manuscript/generate/keywords`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ abstract: abstractText, options: options?.keywords || {} })
        })
      ]);
      
      results.titles = await titleRes.json();
      results.keywords = await keywordRes.json();
    } catch (e) {
      errors.push('Title/Keywords generation failed');
    }
    
    // Validate all sections
    const validations: Record<string, any> = {};
    if (results.results?.content) {
      validations.results = validateWordBudget(results.results.content, 'results');
    }
    if (results.discussion?.content) {
      validations.discussion = validateWordBudget(results.discussion.content, 'discussion');
    }
    
    // Log action
    await logAction({
      eventType: 'FULL_MANUSCRIPT_GENERATED',
      action: 'GENERATE',
      resourceType: 'MANUSCRIPT',
      resourceId: manuscriptId,
      userId,
      details: { 
        sectionsGenerated: Object.keys(results).length,
        errors: errors.length,
        validations
      }
    });
    
    res.json({
      manuscriptId,
      sections: results,
      validations,
      errors: errors.length > 0 ? errors : undefined,
      metadata: {
        generatedAt: new Date().toISOString(),
        datasetId,
        complete: errors.length === 0
      }
    });
  } catch (error) {
    console.error('[ManuscriptGen] Full generation failed:', error);
    res.status(500).json({ error: 'Failed to generate manuscript' });
  }
});

/**
 * Validate a section against word budget
 */
router.post('/validate/section', async (req: Request, res: Response) => {
  try {
    const { content, section, customBudget } = req.body;
    
    if (!content || !section) {
      return res.status(400).json({ 
        error: 'content and section are required' 
      });
    }
    
    const budgets = customBudget ? [customBudget] : DEFAULT_BUDGETS;
    const validation = validateWordBudget(content, section, budgets);
    
    res.json({
      section,
      ...validation,
      budget: budgets.find(b => b.section === section) || null
    });
  } catch (error) {
    console.error('[ManuscriptGen] Validation failed:', error);
    res.status(500).json({ error: 'Failed to validate section' });
  }
});

// ──────────────────────────────────────────────────────────────
// IMRaD Gated Pipeline Endpoints (Step 4 — verify-after-write)
// ──────────────────────────────────────────────────────────────

/**
 * POST /api/manuscript/generate/gated-full
 *
 * Run the full IMRaD pipeline with verify-after-write quality gates.
 * Each section is written sequentially; after each write, agent-verify
 * checks that every claim is grounded in evidence.
 *
 * LIVE mode:  blocks progression if any section fails verification.
 * DEMO mode:  emits warnings but continues.
 *
 * Body: {
 *   manuscriptId: string,
 *   outline: string[],
 *   verifiedClaims: object[],
 *   extractionRows: object[],
 *   groundingPack: object,
 *   styleParams?: object,
 *   governanceMode: 'LIVE' | 'DEMO',
 * }
 */
router.post('/generate/gated-full', requireAuth, async (req: Request, res: Response) => {
  try {
    const {
      manuscriptId,
      outline,
      verifiedClaims,
      extractionRows,
      groundingPack,
      styleParams,
      governanceMode,
    } = req.body;
    const userId = (req as any).user?.id;

    if (!manuscriptId || !groundingPack) {
      return res.status(400).json({
        error: 'manuscriptId and groundingPack are required',
      });
    }

    const requestId = `gated-${manuscriptId}-${Date.now()}`;
    const mode: 'LIVE' | 'DEMO' = governanceMode === 'LIVE' ? 'LIVE' : 'DEMO';

    const pipelineInput: IMRaDPipelineInput = {
      manuscriptId,
      outline: outline || [],
      verifiedClaims: verifiedClaims || [],
      extractionRows: extractionRows || [],
      groundingPack: groundingPack || {},
      styleParams: styleParams || {},
      governanceMode: mode,
      requestId,
      userId,
    };

    const result = await runIMRaDPipeline(pipelineInput);

    await logAction({
      eventType: result.allGatesPassed ? 'GATED_PIPELINE_PASSED' : 'GATED_PIPELINE_BLOCKED',
      action: 'GATED_GENERATE',
      resourceType: 'MANUSCRIPT',
      resourceId: manuscriptId,
      userId,
      details: {
        governanceMode: mode,
        allGatesPassed: result.allGatesPassed,
        blockedAt: result.blockedAt,
        sectionsCompleted: result.sections.length,
      },
    });

    const statusCode = result.blockedAt ? 422 : 200;
    res.status(statusCode).json({
      manuscriptId,
      pipeline: 'imrad-gated',
      governanceMode: mode,
      allGatesPassed: result.allGatesPassed,
      blockedAt: result.blockedAt || null,
      sections: result.sections.map((s) => ({
        section: s.section,
        gatePass: s.gateResult.gatePass,
        blocked: s.gateResult.blocked,
        sectionMarkdown: s.gateResult.sectionMarkdown,
        claimsCount: s.gateResult.claimsWithEvidence.length,
        verifiedClaimsCount: s.gateResult.claimVerdicts.length,
        failedClaimsCount: s.gateResult.claimVerdicts.filter(
          (v) => v.verdict !== 'pass',
        ).length,
        warnings: s.gateResult.warnings,
        claimVerdicts: s.gateResult.claimVerdicts,
      })),
      metadata: {
        generatedAt: new Date().toISOString(),
        requestId,
      },
    });
  } catch (error) {
    console.error('[ManuscriptGen] Gated pipeline failed:', error);
    res.status(500).json({ error: 'Gated IMRaD pipeline failed' });
  }
});

/**
 * POST /api/manuscript/generate/gated-section
 *
 * Write a single section and run verify gate.
 * Useful for incremental / retry workflows.
 *
 * Body: {
 *   manuscriptId: string,
 *   section: 'introduction' | 'methods' | 'results' | 'discussion',
 *   writerOutput: { sectionMarkdown, claimsWithEvidence, warnings?, overallPass },
 *   groundingPack: object,
 *   governanceMode: 'LIVE' | 'DEMO',
 * }
 */
router.post('/generate/gated-section', requireAuth, async (req: Request, res: Response) => {
  try {
    const { manuscriptId, section, writerOutput, groundingPack, governanceMode } = req.body;
    const userId = (req as any).user?.id;

    if (!manuscriptId || !section || !writerOutput || !groundingPack) {
      return res.status(400).json({
        error: 'manuscriptId, section, writerOutput, and groundingPack are required',
      });
    }

    const validSections = ['introduction', 'methods', 'results', 'discussion'];
    if (!validSections.includes(section)) {
      return res.status(400).json({
        error: `section must be one of: ${validSections.join(', ')}`,
      });
    }

    const mode: 'LIVE' | 'DEMO' = governanceMode === 'LIVE' ? 'LIVE' : 'DEMO';
    const requestId = `gate-${section}-${manuscriptId}-${Date.now()}`;

    const normalizedOutput: SectionWriterOutput = {
      sectionMarkdown: writerOutput.sectionMarkdown || '',
      claimsWithEvidence: writerOutput.claimsWithEvidence || [],
      warnings: writerOutput.warnings || [],
      overallPass: writerOutput.overallPass ?? false,
    };

    const gateResult = await runSectionVerifyGate(
      section,
      normalizedOutput,
      groundingPack,
      mode,
      requestId,
      userId,
      manuscriptId,
    );

    const statusCode = gateResult.blocked ? 422 : 200;
    res.status(statusCode).json({
      manuscriptId,
      section,
      governanceMode: mode,
      gatePass: gateResult.gatePass,
      blocked: gateResult.blocked,
      sectionMarkdown: gateResult.sectionMarkdown,
      claimsWithEvidence: gateResult.claimsWithEvidence,
      claimVerdicts: gateResult.claimVerdicts,
      warnings: gateResult.warnings,
      metadata: {
        generatedAt: new Date().toISOString(),
        requestId,
      },
    });
  } catch (error) {
    console.error('[ManuscriptGen] Gated section verification failed:', error);
    res.status(500).json({ error: 'Section verification gate failed' });
  }
});

/**
 * Get word budgets configuration
 */
router.get('/budgets', async (_req: Request, res: Response) => {
  res.json({
    budgets: DEFAULT_BUDGETS,
    description: 'Default word budgets for manuscript sections'
  });
});

/**
 * Update word budgets for a manuscript
 */
router.put('/budgets/:manuscriptId', async (req: Request, res: Response) => {
  try {
    const manuscriptId = asString(req.params.manuscriptId);
    const { budgets } = req.body;
    const userId = (req as any).user?.id;
    
    // Validate budget format
    for (const budget of budgets) {
      if (!budget.section || typeof budget.min !== 'number' || typeof budget.max !== 'number') {
        return res.status(400).json({ 
          error: 'Each budget must have section, min, and max' 
        });
      }
      if (budget.min >= budget.max) {
        return res.status(400).json({ 
          error: `Invalid budget for ${budget.section}: min must be less than max` 
        });
      }
    }
    
    // Store custom budgets (would use DB in production)
    // For now, return the validated budgets
    
    await logAction({
      eventType: 'BUDGETS_UPDATED',
      action: 'UPDATE',
      resourceType: 'MANUSCRIPT',
      resourceId: manuscriptId,
      userId,
      details: { budgets }
    });
    
    res.json({
      manuscriptId,
      budgets,
      updatedAt: new Date().toISOString()
    });
  } catch (error) {
    console.error('[ManuscriptGen] Budget update failed:', error);
    res.status(500).json({ error: 'Failed to update budgets' });
  }
});

   /**
    * POST /api/manuscript/:id/sections/introduction
    */
   router.post('/:id/sections/introduction', requireAuth, async (req, res) => {
     try {
       const { id } = req.params;
       const { hypothesis, literatureContext, researchQuestions } = req.body;
       
       // Mock response for now - will connect to worker
       res.json({
         section: 'introduction',
         content: `Introduction draft for manuscript ${id}`,
         wordCount: 500,
         citations: [],
         generatedAt: new Date().toISOString(),
       });
     } catch (error) {
       console.error('Error generating introduction:', error);
       res.status(500).json({ error: 'Failed to generate introduction' });
     }
   });

   /**
    * POST /api/manuscript/:id/sections/methods
    */
   router.post('/:id/sections/methods', requireAuth, async (req, res) => {
     try {
       const { id } = req.params;
       const { studyDesign, dataCollection, analysisApproach } = req.body;
       
       res.json({
         section: 'methods',
         content: `Methods draft for manuscript ${id}`,
         wordCount: 800,
         reportingChecklist: ['CONSORT', 'STROBE'],
         generatedAt: new Date().toISOString(),
       });
     } catch (error) {
       res.status(500).json({ error: 'Failed to generate methods' });
     }
   });

   /**
    * POST /api/manuscript/:id/sections/results
    * Includes PHI scanning before generation
    */
   router.post('/:id/sections/results', requireAuth, async (req, res) => {
     try {
       const { id } = req.params;
       const { statisticalResults, figures, tables } = req.body;
       
       // PHI check placeholder
       const hasPHI = false; // Will integrate real PHI scanning
       if (hasPHI) {
         return res.status(400).json({
           error: 'PHI detected in results data',
           violations: [],
           suggestion: 'Please redact PHI before generating results section',
         });
       }
       
       res.json({
         section: 'results',
         content: `Results draft for manuscript ${id}`,
         wordCount: 1000,
         figures: figures || [],
         tables: tables || [],
         phiCleared: true,
         generatedAt: new Date().toISOString(),
       });
     } catch (error) {
       res.status(500).json({ error: 'Failed to generate results' });
     }
   });

   /**
    * POST /api/manuscript/:id/sections/discussion
    */
   router.post('/:id/sections/discussion', requireAuth, async (req, res) => {
     try {
       const { id } = req.params;
       const { keyFindings, limitations, implications } = req.body;
       
       res.json({
         section: 'discussion',
         content: `Discussion draft for manuscript ${id}`,
         wordCount: 1200,
         strengthsWeaknesses: { strengths: [], weaknesses: [] },
         generatedAt: new Date().toISOString(),
       });
     } catch (error) {
       res.status(500).json({ error: 'Failed to generate discussion' });
     }
   });

   /**
    * POST /api/manuscript/:id/compile
    * Compile all sections into full manuscript
    */
   router.post('/:id/compile', requireAuth, async (req, res) => {
     try {
       const { id } = req.params;
       const { format, journalStyle } = req.body;
       
       res.json({
         manuscriptId: id,
         format: format || 'docx',
         downloadUrl: `/api/manuscript/${id}/download`,
         wordCount: 4500,
         pageCount: 15,
         compiledAt: new Date().toISOString(),
       });
     } catch (error) {
       res.status(500).json({ error: 'Failed to compile manuscript' });
     }
   });

export default router;
