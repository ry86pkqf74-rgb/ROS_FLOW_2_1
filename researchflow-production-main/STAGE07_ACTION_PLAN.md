# Stage 7 - Statistical Analysis: Action Plan

## 🎯 Current Achievement: Core Functionality COMPLETE ✅

```
┌────────────────────────────────────────────────────────────────┐
│                    STAGE 7 ARCHITECTURE                        │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Frontend (React/TypeScript)                                   │
│  └─> API Call: POST /api/research/:id/stage/7/execute         │
│                        ↓                                        │
│  Orchestrator Service (Express/TypeScript)                     │
│  └─> Route Handler: statistical-analysis.routes.ts            │
│                        ↓                                        │
│  Worker Service (FastAPI/Python)                               │
│  └─> Agent: StatisticalAnalysisAgent                          │
│      ├─> Test Execution (scipy, statsmodels)                  │
│      ├─> Assumption Checking                                   │
│      ├─> Effect Size Calculation                              │
│      └─> Visualization Specs Generation                       │
│                        ↓                                        │
│  PostgreSQL Database                                           │
│  └─> Table: statistical_analysis_results                      │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

---

## 📊 Implementation Status Matrix

| Component | Status | Coverage | Priority |
|-----------|--------|----------|----------|
| Backend Agent | ✅ Complete | 95% | Done |
| Database Schema | ✅ Complete | 100% | Done |
| API Routes | ✅ Complete | 100% | Done |
| Type Definitions | ✅ Complete | 100% | Done |
| Core Tests (7) | ✅ Complete | 100% | Done |
| Mercury Enhancements (15) | ⏳ Pending | 0% | High |
| Frontend Components | ⏳ Pending | 0% | High |
| Visualizations | ⏳ Pending | 0% | Medium |
| Documentation | ⏳ Partial | 50% | Medium |
| E2E Testing | ⏳ Partial | 60% | Low |

---

## 🚀 Implementation Roadmap

### Week 1: Mercury Enhancements (High Priority)

#### Day 1-2: Core Enhancements
```python
# File: services/worker/agents/analysis/statistical_analysis_agent.py

Tasks:
1. Implement Welch's t-test (Line ~510)
   - Add equal_var=False parameter handling
   - Calculate Welch-Satterthwaite df
   - Est: 30 minutes

2. Add Tukey HSD post-hoc (Line ~580)
   - Use statsmodels.stats.multicomp
   - Return pairwise comparisons
   - Est: 45 minutes

3. Implement Cramér's V (Line ~640)
   - Calculate effect size for chi-square
   - Add interpretation thresholds
   - Est: 20 minutes

4. Generate Q-Q plots (Line ~770)
   - Create FigureSpec for Q-Q plot
   - Add histogram with normal overlay
   - Est: 1 hour
```

**Total Estimated Time: 2.5 hours**

#### Day 3-4: Additional Tests
```python
Tasks:
5. Fisher's exact test
   - Alternative for small chi-square samples
   - Est: 30 minutes

6. Correlation tests (Pearson, Spearman)
   - Add to test repertoire
   - Include scatter plot specs
   - Est: 45 minutes

7. Anderson-Darling normality test
   - Enhanced normality checking
   - Est: 30 minutes

8. Dunn's test (Kruskal-Wallis post-hoc)
   - Requires scikit-posthocs
   - Est: 45 minutes
```

**Total Estimated Time: 2.5 hours**

#### Day 5: Polish & Testing
```python
Tasks:
9. LaTeX table export
   - Publication-ready formatting
   - Est: 45 minutes

10. Power analysis
    - Sample size calculations
    - Est: 1 hour

11. Add remaining effect sizes
    - Glass's delta, omega-squared
    - Est: 30 minutes

12-15. Testing & documentation
    - Unit tests for all new methods
    - Update API documentation
    - Est: 1.5 hours
```

**Total Estimated Time: 3.5 hours**

**Week 1 Total: ~9 hours**

---

### Week 2: Frontend Integration

#### Day 1: Form Components
```typescript
// File: client/src/components/Stage7/StatisticalAnalysisForm.tsx

Components:
1. DataInputPanel
   - Manual entry (groups + outcomes)
   - Dataset selector (from uploaded files)
   - CSV import

2. TestTypeSelector
   - Dropdown with test descriptions
   - Auto-suggestion based on data type

3. OptionsPanel
   - Alpha level (0.01, 0.05, 0.10)
   - Confidence level (90%, 95%, 99%)
   - Checkboxes: effect sizes, assumptions, visualizations
```

**Estimated Time: 3 hours**

#### Day 2-3: Results Display
```typescript
// File: client/src/components/Stage7/StatisticalResults.tsx

Components:
1. DescriptiveStats
   - Table with mean, SD, SE, CI
   - Group-wise statistics

2. InferentialResults
   - Test statistic, p-value highlighting
   - Interpretation text
   - Confidence intervals

3. EffectSizes
   - Effect size value + interpretation
   - Visual indicator (small/medium/large)

4. AssumptionChecks
   - Status badges (passed/warning/failed)
   - Remediation suggestions
   - Alternative test links

5. ExportPanel
   - CSV download
   - LaTeX table
   - JSON results
```

**Estimated Time: 4 hours**

#### Day 4-5: Visualizations
```typescript
// File: client/src/components/Stage7/Visualizations.tsx

Components:
1. BoxPlotChart (using recharts)
2. QQPlot (custom D3.js)
3. Histogram (recharts with normal curve overlay)
4. ScatterPlot (for correlations)
```

**Estimated Time: 5 hours**

**Week 2 Total: ~12 hours**

---

### Week 3: Testing & Documentation

#### Testing Checklist
- [ ] Unit tests for all new statistical methods
- [ ] Integration tests with real datasets
- [ ] Frontend component tests (Jest + React Testing Library)
- [ ] E2E tests with Playwright
- [ ] Performance testing (large datasets)
- [ ] Error handling scenarios

**Estimated Time: 6 hours**

#### Documentation
- [ ] User guide: "How to Run Statistical Analysis"
- [ ] API documentation (Swagger/OpenAPI)
- [ ] Statistical interpretation guide
- [ ] Example workflows with screenshots
- [ ] Demo video (screencast)

**Estimated Time: 4 hours**

**Week 3 Total: ~10 hours**

---

## 🎬 Quick Start: First Enhancement

### Implement Welch's T-Test (30 minutes)

**Step 1: Open the agent file**
```bash
code services/worker/agents/analysis/statistical_analysis_agent.py
```

**Step 2: Find the TODO at line ~510**
```python
# TODO (Mercury): Add Welch's correction option for unequal variances
```

**Step 3: Replace with implementation**
```python
def _run_t_test_independent_welch(
    self, 
    group_a: pd.Series, 
    group_b: pd.Series,
    confidence_level: float = 0.95
) -> HypothesisTestResult:
    """Independent t-test with Welch's correction for unequal variances."""
    
    # Perform Welch's t-test (equal_var=False)
    statistic, p_value = stats.ttest_ind(group_a, group_b, equal_var=False)
    
    # Calculate Welch-Satterthwaite degrees of freedom
    var_a = group_a.var()
    var_b = group_b.var()
    n_a = len(group_a)
    n_b = len(group_b)
    
    df = (var_a/n_a + var_b/n_b)**2 / (
        (var_a/n_a)**2/(n_a-1) + (var_b/n_b)**2/(n_b-1)
    )
    
    # Calculate confidence interval
    alpha = 1 - confidence_level
    t_critical = stats.t.ppf(1 - alpha/2, df)
    mean_diff = group_a.mean() - group_b.mean()
    se_diff = np.sqrt(var_a/n_a + var_b/n_b)
    ci_lower = mean_diff - t_critical * se_diff
    ci_upper = mean_diff + t_critical * se_diff
    
    return HypothesisTestResult(
        test_name="Welch's t-test",
        test_type=TestType.T_TEST_INDEPENDENT,
        statistic=float(statistic),
        p_value=float(p_value),
        df=float(df),
        confidence_interval=(float(ci_lower), float(ci_upper)),
        interpretation=self._generate_interpretation(
            p_value=p_value,
            alpha=1 - confidence_level,
            test_name="Welch's t-test"
        )
    )
```

**Step 4: Update the dispatcher**
Find `_run_t_test_independent` and add:
```python
# Check for unequal variances
levene_stat, levene_p = stats.levene(group_a, group_b)
if levene_p < 0.05:
    # Variances are significantly different, use Welch's test
    return self._run_t_test_independent_welch(group_a, group_b, confidence_level)
```

**Step 5: Test it**
```bash
# Run unit tests
pytest services/worker/tests/test_statistical_agent.py::test_welchs_ttest -v

# Test via API
curl -X POST http://localhost:3001/api/research/test-123/stage/7/execute \
  -H "Content-Type: application/json" \
  -d '{
    "study_data": {
      "groups": ["A", "A", "A", "B", "B", "B"],
      "outcomes": {"score": [10, 11, 12, 50, 55, 60]}
    },
    "options": {"test_type": "t_test_independent"}
  }'
```

---

## 📈 Progress Tracking

### Completion Checklist

#### Mercury Enhancements (15 TODOs)
- [ ] 1. Welch's t-test
- [ ] 2. Tukey HSD post-hoc
- [ ] 3. Cramér's V effect size
- [ ] 4. Q-Q plots & histograms
- [ ] 5. Fisher's exact test
- [ ] 6. Correlation tests
- [ ] 7. Anderson-Darling test
- [ ] 8. Dunn's test
- [ ] 9. LaTeX table export
- [ ] 10. Power analysis
- [ ] 11. Glass's delta
- [ ] 12. Omega-squared
- [ ] 13. Bonferroni post-hoc
- [ ] 14. Mann-Whitney effect size
- [ ] 15. TRIPOD-AI compliance

#### Frontend Components (5)
- [ ] StatisticalAnalysisForm.tsx
- [ ] StatisticalResults.tsx
- [ ] Visualizations.tsx
- [ ] AssumptionChecklist.tsx
- [ ] ExportPanel.tsx

#### Documentation (4)
- [ ] User guide
- [ ] API docs
- [ ] Interpretation guide
- [ ] Demo video

---

## 🎯 Success Criteria

### Must Have (Week 1)
✅ Core functionality operational (DONE)
⏳ Top 4 Mercury enhancements complete
⏳ Basic results display in frontend

### Should Have (Week 2)
⏳ All 15 Mercury enhancements complete
⏳ Full frontend integration
⏳ Interactive visualizations

### Nice to Have (Week 3)
⏳ LaTeX export
⏳ Power analysis
⏳ Demo video
⏳ Comprehensive documentation

---

## 💡 Tips for Implementation

### Using AI Tools (Claude/GPT)
1. Show the TODO location and surrounding code
2. Request implementation with proper error handling
3. Ask for unit tests
4. Verify against existing patterns in the codebase

### Testing Strategy
1. Unit test each new method individually
2. Integration test with sample clinical trial data
3. Test edge cases (missing data, unequal groups, etc.)
4. Performance test with large datasets (n > 10,000)

### Code Review Checklist
- [ ] Follows existing code style
- [ ] Type hints complete
- [ ] Error handling present
- [ ] Logging statements added
- [ ] Documentation strings updated
- [ ] Tests pass
- [ ] No new linter warnings

---

**Ready to proceed?** Start with Welch's t-test implementation (30 min quick win!)

**Questions?** Check `STAGE07_MERCURY_ENHANCEMENTS.md` for detailed code examples.

**Status Updates**: Track progress in `STAGE07_STATUS.md`
