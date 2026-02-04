# Stage 7 User Guide - Part 2

## Assumption Checks

### Why Assumptions Matter

Most statistical tests make assumptions about the data. When assumptions are violated:
- Results may be inaccurate
- P-values may be misleading
- Effect sizes may be biased

The system automatically checks all relevant assumptions and provides guidance.

### Common Assumptions

#### 1. Normality

**What it means**: Data follows a bell-shaped (normal) distribution

**How it's tested**:
- Shapiro-Wilk test (p > .05 indicates normality)
- Q-Q plot visualization
- Skewness and kurtosis values

**Example output**:
```
Normality Check
─────────────────────────────────────────────
Shapiro-Wilk test: W = 0.976, p = .234

✅ PASSED: Data appears normally distributed
─────────────────────────────────────────────
```

**If violated**:
- Consider non-parametric alternative (Mann-Whitney, Wilcoxon, etc.)
- Apply data transformation (log, square root)
- Use bootstrap methods
- Proceed if sample size is large (Central Limit Theorem, n > 30)

#### 2. Homogeneity of Variances

**What it means**: Groups have similar spread/variability

**How it's tested**:
- Levene's test (p > .05 indicates equal variances)
- Variance ratios

**Example output**:
```
Homogeneity of Variances
─────────────────────────────────────────────
Levene's test: F(1, 96) = 1.82, p = .180

✅ PASSED: Variances are approximately equal
─────────────────────────────────────────────
```

**If violated**:
- Use Welch's t-test (doesn't assume equal variances)
- Apply variance-stabilizing transformation
- Use robust methods

#### 3. Independence of Observations

**What it means**: Each observation is unrelated to others

**How it's checked**:
- Study design review
- Clustering/repeated measures detection
- Durbin-Watson test (for regression)

**Example output**:
```
Independence Check
─────────────────────────────────────────────
Based on study design: Single measurement per participant

✅ PASSED: No evidence of dependency
─────────────────────────────────────────────
```

**If violated**:
- Use repeated measures or mixed models
- Adjust for clustering
- Account for time-series correlation

#### 4. Sphericity (Repeated Measures ANOVA)

**What it means**: Variances of differences between conditions are equal

**How it's tested**:
- Mauchly's test (p > .05 indicates sphericity)

**If violated**:
- Apply Greenhouse-Geisser or Huynh-Feldt correction
- Use multivariate approach (MANOVA)

### Assumption Check Dashboard

```
┌──────────────────────────────────────────┐
│ Assumption Checks                        │
├──────────────────────────────────────────┤
│ ✅ Normality            Passed           │
│ ✅ Equal Variances      Passed           │
│ ✅ Independence         Passed           │
│ ⚠️  Outliers Detected   2 outliers       │
├──────────────────────────────────────────┤
│ Overall: Assumptions largely met         │
│ Recommendation: Proceed with analysis    │
└──────────────────────────────────────────┘
```

---

## APA Reporting

### Automatic APA Formatting

The system generates APA 7th edition formatted results for direct use in manuscripts.

### Example 1: Independent t-test

**Generated text**:
> An independent-samples t-test was conducted to compare blood pressure levels between treatment and control groups. There was a significant difference in blood pressure for treatment (*M* = 128.40, *SD* = 12.30) and control groups (*M* = 135.70, *SD* = 14.10); *t*(96) = -2.85, *p* = .005, *d* = 0.56. These results suggest that the treatment effectively reduced blood pressure. Specifically, the treatment group had, on average, 7.30 mmHg lower blood pressure than the control group.

### Example 2: One-Way ANOVA

**Generated text**:
> A one-way analysis of variance (ANOVA) was conducted to evaluate the effect of teaching method on exam scores. The ANOVA revealed a significant effect of teaching method on exam scores, *F*(2, 87) = 8.42, *p* < .001, η² = .16. Post hoc comparisons using the Tukey HSD test indicated that Method A (*M* = 82.3, *SD* = 8.4) was significantly different from Method C (*M* = 74.1, *SD* = 9.2), *p* = .002. However, Method B (*M* = 79.5, *SD* = 7.8) did not differ significantly from either Method A (*p* = .283) or Method C (*p* = .071).

### Example 3: Chi-Square Test

**Generated text**:
> A chi-square test of independence was performed to examine the relation between smoking status and lung disease. The relation between these variables was significant, χ²(1, *N* = 200) = 12.45, *p* < .001, Cramér's *V* = .25. Smokers were more likely to have lung disease than non-smokers.

### Example 4: Correlation

**Generated text**:
> A Pearson correlation was conducted to assess the relationship between study time and exam scores. There was a strong positive correlation between the two variables, *r*(48) = .68, *p* < .001, indicating that students who studied more tended to achieve higher exam scores. Approximately 46% of the variance in exam scores was accounted for by study time.

### Tables

**Descriptive Statistics Table** (APA Format):

```
Table 1
Descriptive Statistics for Blood Pressure by Treatment Group

Group          n     M      SD     95% CI
─────────────────────────────────────────────
Treatment     50   128.40  12.30  [124.90, 131.90]
Control       48   135.70  14.10  [131.60, 139.80]
─────────────────────────────────────────────
Note. CI = confidence interval.
```

---

## Common Pitfalls

### 1. Confusing Statistical and Practical Significance

**Pitfall**: Reporting p < .001 without considering effect size

**Example**:
- Study with 10,000 participants finds 0.5 mmHg difference in blood pressure
- p < .001 (highly significant)
- But 0.5 mmHg is clinically meaningless

**Solution**: Always report and interpret effect sizes alongside p-values

### 2. Multiple Testing Without Correction

**Pitfall**: Running 20 tests and reporting only the significant ones

**Issue**: With α = .05, expect 1 false positive per 20 tests by chance alone

**Solution**: 
- Apply multiple comparison corrections (Bonferroni, FDR)
- Pre-specify primary hypotheses
- Distinguish exploratory from confirmatory analyses

### 3. Assuming Causation from Correlation

**Pitfall**: "Ice cream sales cause drowning deaths" (both correlate with temperature)

**Solution**:
- Remember: Correlation ≠ Causation
- Consider confounding variables
- Use experimental designs for causal claims
- Report associations, not causal relationships (unless RCT)

### 4. Ignoring Assumption Violations

**Pitfall**: Running parametric test on severely non-normal data

**Solution**:
- Always check assumptions
- Use appropriate alternatives if violated
- Report assumption checks in methods section

### 5. Selective Reporting

**Pitfall**: Only reporting favorable or significant results

**Solution**:
- Report all planned analyses
- Distinguish planned from exploratory
- Report non-significant results
- Include effect sizes even when non-significant

### 6. Incorrect Interpretation of P-Values

**Common mistakes**:
- ❌ "p = .03 means 3% chance the null hypothesis is true"
- ❌ "p = .06 means no effect exists"
- ❌ "p < .001 means a large effect"

**Correct interpretation**:
- ✅ "p = .03 means if null hypothesis were true, we'd see results this extreme 3% of the time by chance"
- ✅ "p = .06 is not statistically significant at α = .05, but doesn't prove no effect exists"
- ✅ "p < .001 indicates strong evidence against null, but says nothing about effect size"

### 7. Sample Size Issues

**Pitfall**: 
- Too small: Underpowered to detect real effects (Type II error)
- Too large: Trivial effects become "significant" (misleading)

**Solution**:
- Conduct power analysis before data collection
- Report power post-hoc
- Consider effect sizes and confidence intervals

---

## Troubleshooting

### Issue: "Test requires at least 30 observations"

**Cause**: Sample size too small for Central Limit Theorem to apply

**Solutions**:
1. Use non-parametric alternative (Mann-Whitney instead of t-test)
2. Collect more data
3. Use bootstrap methods
4. Combine with other studies (meta-analysis)

### Issue: "Normality assumption violated"

**Cause**: Data is skewed or has outliers

**Solutions**:
1. Use non-parametric test
2. Transform data (log, square root, reciprocal)
3. Remove outliers (document justification)
4. Use robust methods
5. If n > 30-40, proceed anyway (CLT)

### Issue: "Unequal variances detected"

**Cause**: Groups have different spreads

**Solutions**:
1. Use Welch's t-test (for t-test)
2. Use robust ANOVA alternatives
3. Transform data
4. Use non-parametric alternatives

### Issue: "All p-values are significant"

**Cause**: Likely data issues or test selection problem

**Check**:
1. Did you select independent samples but have paired data?
2. Is sample size extremely large? (even tiny effects become significant)
3. Data entry errors?
4. Multiple testing issue?

### Issue: "No significant results"

**Not necessarily a problem!** 

**Consider**:
1. Was study adequately powered?
2. Are effect sizes meaningful even if non-significant?
3. Is null result actually the answer? (no effect exists)
4. Report confidence intervals - what effect sizes can be ruled out?

### Issue: "Results differ from published studies"

**Possible reasons**:
1. Different samples/populations
2. Different measurement methods
3. Publication bias (only significant results published)
4. Different analysis methods
5. Random variation

**Actions**:
1. Document differences clearly
2. Don't manipulate data to match expectations
3. Report honestly
4. Discuss in manuscript

---

## Quick Reference: Test Selection Table

| Research Question | Variable Types | Sample | Test |
|-------------------|----------------|--------|------|
| Compare 2 groups | Continuous outcome, Binary grouping | Independent | Independent t-test |
| Compare 2 groups | Continuous outcome, Binary grouping | Paired | Paired t-test |
| Compare 3+ groups | Continuous outcome, Categorical grouping | Independent | One-way ANOVA |
| Compare 3+ groups | Continuous outcome, Categorical grouping | Repeated | Repeated Measures ANOVA |
| Association 2 categorical | Both categorical/binary | Independent | Chi-square |
| Association 2 categorical | Both binary, small sample | Independent | Fisher's exact |
| Relationship 2 continuous | Both continuous | - | Pearson correlation |
| Predict continuous outcome | Mixed predictors | - | Linear regression |
| Predict binary outcome | Mixed predictors | - | Logistic regression |
| Non-normal, 2 groups | Continuous/ordinal, Binary grouping | Independent | Mann-Whitney U |
| Non-normal, 2 groups | Continuous/ordinal, Binary grouping | Paired | Wilcoxon signed-rank |
| Non-normal, 3+ groups | Continuous/ordinal, Categorical grouping | Independent | Kruskal-Wallis |
| Non-normal, 3+ groups | Continuous/ordinal, Categorical grouping | Repeated | Friedman |

---

## Additional Resources

### Within ResearchFlow

- **Stage 3**: Data validation and cleaning
- **Stage 6**: Sample size and power analysis
- **Stage 8**: Results visualization
- **Stage 9**: Manuscript preparation

### External Resources

- APA Style Guide (7th edition)
- Andy Field's "Discovering Statistics" textbook
- Statistical consulting services (contact your institution)

### Getting Help

If you encounter issues:

1. Check this user guide
2. Review assumption check recommendations
3. Consult statistical methods literature
4. Seek institutional statistical consulting
5. Contact ResearchFlow support

---

**Remember**: Statistical analysis is both an art and a science. Use these tools as aids to good judgment, not replacements for it. When in doubt, consult with a statistician before finalizing your analysis plan.
