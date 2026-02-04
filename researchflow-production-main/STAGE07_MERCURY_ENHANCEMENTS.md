# Stage 7 - Mercury Enhancement Tasks

## Overview
Fill in the 15 TODO markers in the statistical analysis agent with advanced statistical methods.

## High Priority Enhancements

### 1. Welch's T-Test (Unequal Variances)
**File**: `services/worker/agents/analysis/statistical_analysis_agent.py`
**Line**: ~510
**Current TODO**: `TODO (Mercury): Add Welch's correction option for unequal variances`

```python
def _run_t_test_independent_welch(self, group_a: pd.Series, group_b: pd.Series) -> HypothesisTestResult:
    """Independent t-test with Welch's correction for unequal variances."""
    statistic, p_value = stats.ttest_ind(group_a, group_b, equal_var=False)
    
    # Welch-Satterthwaite degrees of freedom
    var_a = group_a.var()
    var_b = group_b.var()
    n_a = len(group_a)
    n_b = len(group_b)
    
    df = (var_a/n_a + var_b/n_b)**2 / (
        (var_a/n_a)**2/(n_a-1) + (var_b/n_b)**2/(n_b-1)
    )
    
    return HypothesisTestResult(
        test_name="Welch's t-test",
        test_type=TestType.T_TEST_INDEPENDENT,
        statistic=float(statistic),
        p_value=float(p_value),
        df=float(df),
        interpretation=generate_interpretation(...)
    )
```

### 2. Post-Hoc Tests (Tukey HSD, Bonferroni)
**File**: `services/worker/agents/analysis/statistical_analysis_agent.py`
**Lines**: ~580, ~595
**Current TODO**: `TODO (Mercury): Add post-hoc tests (Tukey HSD, Bonferroni)`

```python
def run_posthoc_tukey(self, data: pd.DataFrame, outcome_var: str, group_var: str) -> List[Dict]:
    """Tukey HSD post-hoc test for ANOVA."""
    from statsmodels.stats.multicomp import pairwise_tukeyhsd
    
    tukey_result = pairwise_tukeyhsd(
        endog=data[outcome_var],
        groups=data[group_var],
        alpha=0.05
    )
    
    results = []
    for row in tukey_result.summary().data[1:]:
        results.append({
            'group_a': row[0],
            'group_b': row[1],
            'mean_diff': float(row[2]),
            'p_value': float(row[3]),
            'ci_lower': float(row[4]),
            'ci_upper': float(row[5]),
            'significant': row[6] == 'True'
        })
    
    return results
```

### 3. Cramér's V Effect Size
**File**: `services/worker/agents/analysis/statistical_analysis_agent.py`
**Line**: ~640
**Current TODO**: `TODO (Mercury): Add Cramér's V effect size`

```python
def calculate_cramers_v(self, contingency_table: np.ndarray) -> float:
    """Calculate Cramér's V effect size for chi-square test."""
    chi2 = stats.chi2_contingency(contingency_table)[0]
    n = contingency_table.sum()
    min_dim = min(contingency_table.shape[0] - 1, contingency_table.shape[1] - 1)
    
    if min_dim == 0:
        return 0.0
    
    return np.sqrt(chi2 / (n * min_dim))
```

### 4. Q-Q Plot & Histogram Specifications
**File**: `services/worker/agents/analysis/statistical_analysis_agent.py`
**Line**: ~770
**Current TODO**: `TODO (Mercury): Add Q-Q plots, histogram specifications for visual checks`

```python
def generate_normality_diagnostics(self, data: pd.Series, var_name: str) -> List[FigureSpec]:
    """Generate Q-Q plot and histogram for normality assessment."""
    from scipy.stats import probplot
    
    # Q-Q plot
    qq_data = probplot(data, dist="norm")
    qq_spec = FigureSpec(
        figure_type="qq_plot",
        title=f"Q-Q Plot: {var_name}",
        data={
            "theoretical_quantiles": qq_data[0][0].tolist(),
            "sample_quantiles": qq_data[0][1].tolist(),
            "fit_line": {
                "slope": qq_data[1][0],
                "intercept": qq_data[1][1]
            }
        },
        x_label="Theoretical Quantiles",
        y_label="Sample Quantiles",
        caption="Q-Q plot for assessing normality assumption"
    )
    
    # Histogram
    hist_values, hist_bins = np.histogram(data, bins='auto')
    hist_spec = FigureSpec(
        figure_type="histogram",
        title=f"Distribution: {var_name}",
        data={
            "values": hist_values.tolist(),
            "bins": hist_bins.tolist(),
            "mean": float(data.mean()),
            "std": float(data.std())
        },
        x_label=var_name,
        y_label="Frequency",
        caption="Histogram showing data distribution"
    )
    
    return [qq_spec, hist_spec]
```

## Medium Priority Enhancements

### 5. Fisher's Exact Test
```python
def _run_fisher_exact(self, contingency_table: np.ndarray) -> HypothesisTestResult:
    """Fisher's exact test for 2x2 contingency tables (small samples)."""
    if contingency_table.shape != (2, 2):
        raise ValueError("Fisher's exact test requires 2x2 table")
    
    odds_ratio, p_value = stats.fisher_exact(contingency_table)
    
    return HypothesisTestResult(
        test_name="Fisher's exact test",
        test_type=TestType.CHI_SQUARE,
        statistic=float(odds_ratio),
        p_value=float(p_value),
        interpretation=f"Fisher's exact test {'was' if p_value < 0.05 else 'was not'} significant"
    )
```

### 6. Correlation Tests
```python
def run_correlation(self, data: pd.DataFrame, var_x: str, var_y: str, method: str = 'pearson') -> HypothesisTestResult:
    """Pearson or Spearman correlation."""
    if method == 'pearson':
        r, p_value = stats.pearsonr(data[var_x], data[var_y])
        test_name = "Pearson correlation"
    else:
        r, p_value = stats.spearmanr(data[var_x], data[var_y])
        test_name = "Spearman correlation"
    
    return HypothesisTestResult(
        test_name=test_name,
        test_type=TestType.CORRELATION_PEARSON if method == 'pearson' else TestType.CORRELATION_SPEARMAN,
        statistic=float(r),
        p_value=float(p_value),
        interpretation=f"Correlation coefficient r = {r:.3f}, p = {p_value:.3f}"
    )
```

### 7. Anderson-Darling Test
```python
def _check_normality_anderson(self, data: pd.Series) -> Dict[str, Any]:
    """Anderson-Darling test for normality."""
    result = stats.anderson(data, dist='norm')
    
    # Use 5% significance level (index 2)
    critical_value = result.critical_values[2]
    significance = result.significance_level[2]
    
    return {
        "test": "Anderson-Darling",
        "statistic": float(result.statistic),
        "critical_value": float(critical_value),
        "significance_level": float(significance),
        "passed": result.statistic < critical_value
    }
```

### 8. Dunn's Test (Post-Hoc for Kruskal-Wallis)
```python
def run_posthoc_dunn(self, data: pd.DataFrame, outcome_var: str, group_var: str) -> List[Dict]:
    """Dunn's test for Kruskal-Wallis post-hoc comparisons."""
    from scikit_posthocs import posthoc_dunn
    
    dunn_result = posthoc_dunn(data, val_col=outcome_var, group_col=group_var)
    
    results = []
    groups = dunn_result.index.tolist()
    
    for i, group_a in enumerate(groups):
        for group_b in groups[i+1:]:
            p_value = dunn_result.loc[group_a, group_b]
            results.append({
                'group_a': group_a,
                'group_b': group_b,
                'p_value': float(p_value),
                'adjusted_p_value': float(p_value),  # Already Bonferroni-adjusted
                'significant': p_value < 0.05
            })
    
    return results
```

## Lower Priority Enhancements

### 9. LaTeX Table Export
```python
def export_table_latex(self, result: StatisticalResult) -> str:
    """Export results as LaTeX table."""
    lines = [
        "\\begin{table}[htbp]",
        "\\centering",
        "\\caption{Statistical Analysis Results}",
        "\\begin{tabular}{lcccc}",
        "\\hline",
        "Variable & Mean & SD & t & p \\\\"",
        "\\hline"
    ]
    
    for desc in result.descriptive:
        lines.append(
            f"{desc.variable_name} & {desc.mean:.2f} & {desc.std:.2f} & & \\\\"
        )
    
    if result.inferential:
        lines.append(f"& & & {result.inferential.statistic:.2f} & {result.inferential.p_value:.3f} \\\\")
    
    lines.extend([
        "\\hline",
        "\\end{tabular}",
        "\\end{table}"
    ])
    
    return "\n".join(lines)
```

### 10. Power Analysis
```python
def calculate_power(self, effect_size: float, n: int, alpha: float = 0.05) -> Dict[str, Any]:
    """Calculate statistical power."""
    from statsmodels.stats.power import ttest_power
    
    power = ttest_power(effect_size, n, alpha)
    
    # Calculate required N for 80% and 90% power
    from statsmodels.stats.power import tt_solve_power
    n_80 = tt_solve_power(effect_size, power=0.80, alpha=alpha)
    n_90 = tt_solve_power(effect_size, power=0.90, alpha=alpha)
    
    return {
        "observed_power": float(power),
        "required_n_80": int(np.ceil(n_80)),
        "required_n_90": int(np.ceil(n_90)),
        "effect_size": effect_size,
        "sample_size": n,
        "alpha": alpha
    }
```

## Implementation Plan

### Phase 1 (Sprint 1): High Priority
- [ ] Welch's t-test
- [ ] Tukey HSD post-hoc
- [ ] Cramér's V effect size
- [ ] Q-Q plots and histograms

### Phase 2 (Sprint 2): Medium Priority
- [ ] Fisher's exact test
- [ ] Correlation tests
- [ ] Anderson-Darling normality
- [ ] Dunn's post-hoc test

### Phase 3 (Sprint 3): Lower Priority
- [ ] LaTeX export
- [ ] Power analysis
- [ ] Additional effect sizes (Glass's delta, omega-squared)
- [ ] TRIPOD-AI compliance

## Dependencies

```bash
# Add to requirements.txt
statsmodels>=0.14.0
scikit-posthocs>=0.7.0
```

## Testing Checklist

For each enhancement:
- [ ] Unit test added
- [ ] Integration test with agent workflow
- [ ] Documentation updated
- [ ] Example added to README
- [ ] Frontend integration verified

## Success Metrics

- All 15 TODO markers resolved
- Test coverage >90%
- Performance: <1s for typical analyses
- User documentation complete
- No regressions in existing tests

---

**Status**: Ready for implementation  
**Estimated Effort**: 3 sprints  
**Priority**: Medium (core functionality complete, these are enhancements)
