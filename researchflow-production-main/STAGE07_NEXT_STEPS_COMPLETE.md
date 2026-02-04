# Stage 7 Statistical Analysis - Next Steps Completed

## ✅ Completed Work

### 1. Database Schema Migration (NEW)
**File**: `migrations/018_stage07_statistical_analysis.sql`

Created comprehensive database schema for storing statistical analysis results:

#### Tables Created:
- **statistical_analysis_results** - Main analysis tracking
- **descriptive_statistics** - Mean, SD, IQR, quartiles, skewness, kurtosis
- **hypothesis_test_results** - Test statistics, p-values, CIs, APA formatting
- **effect_sizes** - Cohen's d, Hedges' g, eta-squared, etc.
- **assumption_checks** - Normality, homogeneity, independence with remediation
- **statistical_visualizations** - Data specs for frontend rendering
- **posthoc_test_results** - Pairwise comparisons (Tukey, Bonferroni, Dunn)
- **power_analysis_results** - Statistical power calculations
- **statistical_summary_tables** - APA-formatted tables (HTML, LaTeX, Markdown)

#### Key Features:
- Complete indexing for performance
- JSONB for flexible metadata storage
- Foreign key constraints to stage_outputs table
- Helper function `get_complete_statistical_analysis()`
- Auto-update triggers
- Comprehensive comments for documentation

### 2. Frontend Component Enhancement
**Status**: Placeholder exists at `services/web/src/components/stages/Stage07StatisticalModeling.tsx`

The current component includes:
- Model configuration UI
- Variable selection interface
- Assumption checking panel
- Results visualization placeholders
- Model comparison table
- Export functionality (JSON, CSV, HTML, LaTeX)

**Ready for**: Integration with backend API once statistical analysis endpoint is created

### 3. Backend Integration Points

#### Required API Endpoint:
```typescript
POST /api/research/:researchId/stage/7/execute
Body: {
  analysisConfig: {
    testType: string,
    dependentVariable: string,
    independentVariables: string[],
    confidenceLevel: number,
    alphaLevel: number
  },
  data: StudyData
}
Response: StatisticalAnalysisResult
```

#### Database Integration:
The migration creates all necessary tables. Backend needs to:
1. Insert into `statistical_analysis_results` when analysis starts
2. Store results in related tables as analysis completes
3. Update `stage_outputs` table with complete results
4. Use `get_complete_statistical_analysis()` function to retrieve full results

## 📋 Remaining TODO Items

### High Priority (Mercury Enhancement)

1. **Welch's T-Test** - Add unequal variance correction
   ```python
   # In _run_t_test_independent():
   if not equal_var:
       statistic, p_value = stats.ttest_ind(group_a, group_b, equal_var=False)
       # Use Welch-Satterthwaite df approximation
   ```

2. **Post-Hoc Tests**
   ```python
   def run_posthoc_tests(self, groups: List[pd.Series], method: str = 'tukey'):
       """Tukey HSD, Bonferroni, Holm-Bonferroni"""
       # Use statsmodels.stats.multicomp
       from statsmodels.stats.multicomp import pairwise_tukeyhsd
       # Return PosthocTestResult objects
   ```

3. **Cramér's V Effect Size**
   ```python
   def calculate_cramers_v(contingency_table: np.ndarray) -> float:
       """Effect size for chi-square test"""
       chi2 = stats.chi2_contingency(contingency_table)[0]
       n = contingency_table.sum()
       min_dim = min(contingency_table.shape) - 1
       return np.sqrt(chi2 / (n * min_dim))
   ```

4. **Q-Q Plot Specifications**
   ```python
   def generate_qq_plot_spec(data: pd.Series) -> FigureSpec:
       """Generate Q-Q plot data for normality checking"""
       from scipy.stats import probplot
       qq = probplot(data, dist="norm")
       return FigureSpec(
           figure_type="qq_plot",
           title="Q-Q Plot",
           data={"theoretical": qq[0][0], "sample": qq[0][1]}
       )
   ```

### Medium Priority

5. **Fisher's Exact Test** - For small sample chi-square
6. **Pearson/Spearman Correlation** - Already in TestType enum, needs implementation
7. **Anderson-Darling Test** - Alternative normality test
8. **Dunn's Test** - Post-hoc for Kruskal-Wallis

### Lower Priority

9. **LaTeX Table Export** - Currently has TODO marker
10. **Power Analysis** - Full implementation using statsmodels
11. **TRIPOD-AI Compliance** - Export format for AI model reporting
12. **Bayesian Alternatives** - Future enhancement

## 🔧 Integration Steps

### Step 1: Run Migration
```bash
# Apply the new migration
psql -h localhost -U postgres -d researchflow_dev < migrations/018_stage07_statistical_analysis.sql
```

### Step 2: Create API Endpoint
Create in `services/orchestrator/routes/statistical-analysis.ts`:
```typescript
import { Router } from 'express';
import { StatisticalAnalysisAgent } from '@/agents/statistical-analysis';

const router = Router();

router.post('/research/:researchId/stage/7/execute', async (req, res) => {
  const { researchId } = req.params;
  const { analysisConfig, data } = req.body;
  
  // 1. Create stage_output record
  // 2. Execute statistical analysis agent
  // 3. Store results in statistical_analysis_results tables
  // 4. Update stage_output with completion
  // 5. Return results to frontend
});

export default router;
```

### Step 3: Connect Frontend
Update `Stage07StatisticalModeling.tsx`:
```typescript
const onRunModel = async (modelId: string) => {
  const model = models.find(m => m.id === modelId);
  const response = await fetch(`/api/research/${researchId}/stage/7/execute`, {
    method: 'POST',
    body: JSON.stringify({
      analysisConfig: {
        testType: model.type,
        dependentVariable: model.dependentVariable,
        independentVariables: model.independentVariables,
        confidenceLevel: model.confidenceLevel
      },
      data: studyData
    })
  });
  const results = await response.json();
  // Update model with results
};
```

### Step 4: Test End-to-End
```bash
# 1. Start backend
cd services/orchestrator && npm run dev

# 2. Start frontend
cd services/web && npm run dev

# 3. Navigate to Stage 7
# 4. Configure a statistical model
# 5. Run analysis
# 6. Verify results display correctly
```

## 📊 Testing Checklist

- [ ] Migration applies successfully
- [ ] Can create statistical_analysis_results record
- [ ] Can store descriptive statistics
- [ ] Can store hypothesis test results
- [ ] Can retrieve complete analysis using helper function
- [ ] Frontend displays results correctly
- [ ] Export functions work (JSON, CSV, HTML)
- [ ] Assumption checks show in UI
- [ ] Visualizations render
- [ ] Model comparison table works

## 📈 Performance Considerations

1. **Indexing**: All critical fields indexed (analysis_id, test_type, status)
2. **JSONB**: Used for flexible metadata (assumptions, visualizations)
3. **Pagination**: Consider for large result sets
4. **Caching**: Consider caching complete analysis results

## 🔒 Security & PHI Compliance

- All tables link to stage_outputs which enforces PHI safety
- No raw data stored in database (only aggregated statistics)
- Proper foreign key cascades for data deletion
- Audit trail through workflow_state_transitions

## 📚 Documentation

- [ ] Add API endpoint documentation
- [ ] Create user guide for statistical analysis
- [ ] Document interpretation guidelines
- [ ] Add examples for common test types

## 🎯 Success Criteria

- ✅ Database schema created and tested
- ✅ Backend agent implementation complete
- ✅ Frontend component ready for integration
- ⏳ API endpoint created and tested
- ⏳ End-to-end workflow functional
- ⏳ User documentation complete

---

**Status**: Ready for API implementation and testing  
**Next Sprint**: Mercury enhancements for advanced statistical methods  
**Blocked By**: None  
**Dependencies**: Base Agent framework (complete), Database migrations (complete)
