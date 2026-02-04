# Stage 7 Statistical Analysis - API Implementation Guide

## Quick Start

### 1. Create API Route File

**File**: `services/orchestrator/routes/statistical-analysis.ts`

```typescript
import { Router } from 'express';
import { z } from 'zod';
import { db } from '../db';
import { requireAuth } from '../middleware/auth';

const router = Router();

// Validation schema
const StatisticalAnalysisSchema = z.object({
  analysisName: z.string().min(1),
  testType: z.enum([
    't_test_independent',
    't_test_paired',
    'anova_one_way',
    'mann_whitney',
    'kruskal_wallis',
    'chi_square',
  ]),
  dependentVariable: z.string(),
  independentVariables: z.array(z.string()),
  covariates: z.array(z.string()).optional(),
  confidenceLevel: z.number().min(0).max(1).default(0.95),
  alphaLevel: z.number().min(0).max(1).default(0.05),
  data: z.object({
    groups: z.array(z.any()),
    outcomes: z.array(z.any()),
  }),
});

// Execute statistical analysis
router.post(
  '/research/:researchId/stage/7/execute',
  requireAuth,
  async (req, res) => {
    try {
      const { researchId } = req.params;
      const input = StatisticalAnalysisSchema.parse(req.body);

      // 1. Get or create manifest
      let manifest = await db.query(
        'SELECT * FROM project_manifests WHERE research_id = $1',
        [researchId]
      );

      if (manifest.rows.length === 0) {
        manifest = await db.query(
          `INSERT INTO project_manifests (research_id, current_stage, governance_mode)
           VALUES ($1, 7, 'LIVE') RETURNING *`,
          [researchId]
        );
      }

      const manifestId = manifest.rows[0].id;

      // 2. Create stage output record
      const stageOutput = await db.query(
        `INSERT INTO stage_outputs (
          manifest_id, research_id, stage_number, stage_name, status, input_data, started_at
        ) VALUES ($1, $2, $3, $4, $5, $6, NOW()) RETURNING *`,
        [manifestId, researchId, 7, 'Statistical Analysis', 'running', input]
      );

      const stageOutputId = stageOutput.rows[0].id;

      // 3. Create statistical analysis record
      const analysis = await db.query(
        `INSERT INTO statistical_analysis_results (
          stage_output_id, manifest_id, research_id, analysis_name, test_type,
          status, dependent_variable, independent_variables, covariates,
          confidence_level, alpha_level, execution_started_at
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, NOW())
        RETURNING *`,
        [
          stageOutputId,
          manifestId,
          researchId,
          input.analysisName,
          input.testType,
          'running',
          input.dependentVariable,
          JSON.stringify(input.independentVariables),
          JSON.stringify(input.covariates || []),
          input.confidenceLevel,
          input.alphaLevel,
        ]
      );

      const analysisId = analysis.rows[0].id;

      // 4. Execute analysis (call Python worker)
      const workerResponse = await fetch('http://localhost:8000/api/statistical-analysis', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          analysis_id: analysisId,
          test_type: input.testType,
          data: input.data,
          config: {
            dependent_variable: input.dependentVariable,
            independent_variables: input.independentVariables,
            confidence_level: input.confidenceLevel,
            alpha_level: input.alphaLevel,
          },
        }),
      });

      const results = await workerResponse.json();

      // 5. Store results in database
      await storeStatisticalResults(analysisId, results);

      // 6. Update status
      await db.query(
        `UPDATE statistical_analysis_results 
         SET status = 'completed', execution_completed_at = NOW(),
             execution_time_ms = EXTRACT(EPOCH FROM (NOW() - execution_started_at)) * 1000
         WHERE id = $1`,
        [analysisId]
      );

      await db.query(
        `UPDATE stage_outputs 
         SET status = 'completed', completed_at = NOW(),
             output_data = $1,
             execution_time_ms = EXTRACT(EPOCH FROM (NOW() - started_at)) * 1000
         WHERE id = $2`,
        [JSON.stringify(results), stageOutputId]
      );

      // 7. Return complete results
      const completeResults = await db.query(
        'SELECT get_complete_statistical_analysis($1) as results',
        [analysisId]
      );

      res.json({
        success: true,
        analysisId,
        results: completeResults.rows[0].results,
      });
    } catch (error) {
      console.error('Statistical analysis error:', error);
      res.status(500).json({
        success: false,
        error: error.message,
      });
    }
  }
);

// Helper function to store results
async function storeStatisticalResults(analysisId: string, results: any) {
  // Store descriptive statistics
  if (results.descriptive) {
    for (const desc of results.descriptive) {
      await db.query(
        `INSERT INTO descriptive_statistics (
          analysis_id, variable_name, group_name, n, missing_count,
          mean, median, std_dev, min_value, max_value, q1, q3, iqr,
          skewness, kurtosis
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)`,
        [
          analysisId,
          desc.variable_name,
          desc.group_name,
          desc.n,
          desc.missing,
          desc.mean,
          desc.median,
          desc.std,
          desc.min_value,
          desc.max_value,
          desc.q25,
          desc.q75,
          desc.iqr,
          desc.skewness,
          desc.kurtosis,
        ]
      );
    }
  }

  // Store hypothesis test results
  if (results.inferential) {
    const testResult = await db.query(
      `INSERT INTO hypothesis_test_results (
        analysis_id, test_name, test_type, test_statistic, p_value,
        degrees_of_freedom, ci_lower, ci_upper, is_significant,
        interpretation, apa_format
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
      RETURNING id`,
      [
        analysisId,
        results.inferential.test_name,
        results.inferential.test_type,
        results.inferential.statistic,
        results.inferential.p_value,
        JSON.stringify(results.inferential.df),
        results.inferential.ci_lower,
        results.inferential.ci_upper,
        results.inferential.p_value < 0.05,
        results.inferential.interpretation,
        results.inferential.apa_format,
      ]
    );

    const testResultId = testResult.rows[0].id;

    // Store effect sizes
    if (results.effect_sizes) {
      await db.query(
        `INSERT INTO effect_sizes (
          analysis_id, test_result_id, cohens_d, hedges_g, eta_squared,
          magnitude, interpretation
        ) VALUES ($1, $2, $3, $4, $5, $6, $7)`,
        [
          analysisId,
          testResultId,
          results.effect_sizes.cohens_d,
          results.effect_sizes.hedges_g,
          results.effect_sizes.eta_squared,
          results.effect_sizes.magnitude,
          results.effect_sizes.interpretation,
        ]
      );
    }
  }

  // Store assumption checks
  if (results.assumptions) {
    for (const [assumptionType, check] of Object.entries(results.assumptions)) {
      if (typeof check === 'object') {
        await db.query(
          `INSERT INTO assumption_checks (
            analysis_id, assumption_name, assumption_type, test_name,
            test_statistic, p_value, status, passed, remediation_suggestion
          ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)`,
          [
            analysisId,
            assumptionType,
            assumptionType,
            check.test,
            check.statistic,
            check.p_value,
            check.passed ? 'passed' : 'violated',
            check.passed,
            check.remediation,
          ]
        );
      }
    }
  }

  // Store visualizations
  if (results.visualizations) {
    for (let i = 0; i < results.visualizations.length; i++) {
      const viz = results.visualizations[i];
      await db.query(
        `INSERT INTO statistical_visualizations (
          analysis_id, viz_type, title, caption, x_label, y_label,
          data_spec, display_order
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)`,
        [
          analysisId,
          viz.type,
          viz.title,
          viz.caption,
          viz.x_label,
          viz.y_label,
          JSON.stringify(viz.data),
          i,
        ]
      );
    }
  }
}

// Get analysis results
router.get('/research/:researchId/stage/7/results/:analysisId', requireAuth, async (req, res) => {
  try {
    const { analysisId } = req.params;

    const results = await db.query(
      'SELECT get_complete_statistical_analysis($1) as results',
      [analysisId]
    );

    if (!results.rows[0].results) {
      return res.status(404).json({ error: 'Analysis not found' });
    }

    res.json(results.rows[0].results);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// List analyses for research
router.get('/research/:researchId/stage/7/analyses', requireAuth, async (req, res) => {
  try {
    const { researchId } = req.params;

    const analyses = await db.query(
      `SELECT id, analysis_name, test_type, status, created_at, 
              execution_time_ms, dependent_variable, independent_variables
       FROM statistical_analysis_results
       WHERE research_id = $1
       ORDER BY created_at DESC`,
      [researchId]
    );

    res.json(analyses.rows);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

export default router;
```

### 2. Register Route

**File**: `services/orchestrator/server.ts`

```typescript
import statisticalAnalysisRoutes from './routes/statistical-analysis';

// ... other routes

app.use('/api/statistical-analysis', statisticalAnalysisRoutes);
```

### 3. Create Python Worker Endpoint

**File**: `services/worker/api_server.py`

```python
@app.post("/api/statistical-analysis")
async def execute_statistical_analysis(request: Request):
    """Execute statistical analysis using the StatisticalAnalysisAgent."""
    data = await request.json()
    
    from agents.analysis import StatisticalAnalysisAgent, StudyData
    
    # Create agent
    agent = StatisticalAnalysisAgent()
    
    # Prepare data
    study_data = StudyData(
        groups=data['data']['groups'],
        outcomes=data['data']['outcomes'],
        covariates=data.get('covariates', []),
        metadata={
            'analysis_id': data['analysis_id'],
            'test_type': data['test_type'],
            **data.get('config', {})
        }
    )
    
    # Execute analysis
    result = await agent.execute(study_data)
    
    # Return results
    return {
        'success': True,
        'descriptive': [d.dict() for d in result.descriptive],
        'inferential': result.inferential.dict() if result.inferential else None,
        'effect_sizes': result.effect_sizes.dict() if result.effect_sizes else None,
        'assumptions': {
            'normality': result.assumptions.normality,
            'homogeneity': result.assumptions.homogeneity,
            'independence': result.assumptions.independence,
            'passed': result.assumptions.passed,
        } if result.assumptions else {},
        'visualizations': [v.dict() for v in result.figure_specs],
        'tables': result.tables,
    }
```

### 4. Update Frontend

**File**: `services/web/src/components/stages/Stage07StatisticalModeling.tsx`

Add API integration:

```typescript
const onRunModel = async (modelId: string) => {
  const model = models.find(m => m.id === modelId);
  if (!model) return;

  updateModel(modelId, { status: 'running' });

  try {
    const response = await fetch(`/api/statistical-analysis/research/${researchId}/stage/7/execute`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        analysisName: model.name,
        testType: model.type,
        dependentVariable: model.dependentVariable,
        independentVariables: model.independentVariables,
        covariates: model.covariates || [],
        confidenceLevel: model.confidenceLevel,
        alphaLevel: 0.05,
        data: studyData, // From props or state
      }),
    });

    const result = await response.json();

    if (result.success) {
      updateModel(modelId, {
        status: 'completed',
        completedAt: new Date(),
        fitStatistics: result.results.fit_statistics || {},
        coefficients: result.results.coefficients || [],
        residualPlots: result.results.visualizations || [],
        assumptions: result.results.assumptions || [],
      });
    } else {
      updateModel(modelId, {
        status: 'failed',
        errorMessage: result.error,
      });
    }
  } catch (error) {
    updateModel(modelId, {
      status: 'failed',
      errorMessage: error.message,
    });
  }
};
```

## Testing

### 1. Test Database Schema
```bash
psql -h localhost -U postgres -d researchflow_dev -f migrations/018_stage07_statistical_analysis.sql
```

### 2. Test API Endpoint
```bash
curl -X POST http://localhost:3000/api/statistical-analysis/research/test-123/stage/7/execute \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "analysisName": "Test Analysis",
    "testType": "t_test_independent",
    "dependentVariable": "outcome",
    "independentVariables": ["treatment"],
    "confidenceLevel": 0.95,
    "data": {
      "groups": [[10, 12, 14], [15, 17, 19]],
      "outcomes": [[10, 12, 14], [15, 17, 19]]
    }
  }'
```

### 3. Test Frontend Integration
```typescript
// In browser console
const testData = {
  analysisName: "Test T-Test",
  testType: "t_test_independent",
  dependentVariable: "bp_systolic",
  independentVariables: ["treatment_group"],
  data: {
    groups: [[120, 125, 130], [115, 118, 122]],
    outcomes: [[120, 125, 130], [115, 118, 122]]
  }
};

fetch('/api/statistical-analysis/research/your-research-id/stage/7/execute', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(testData)
}).then(r => r.json()).then(console.log);
```

## Deployment Checklist

- [ ] Database migration applied to all environments
- [ ] API routes registered in orchestrator
- [ ] Python worker endpoint deployed
- [ ] Frontend updated with API integration
- [ ] Environment variables configured
- [ ] Error handling tested
- [ ] Performance benchmarks met (<2s for typical analysis)
- [ ] Documentation updated
- [ ] User acceptance testing complete

---

**Status**: Implementation guide ready  
**Next**: Execute implementation steps  
**Estimated Time**: 4-6 hours
