# Stage 7: Statistical Analysis - User Guide

## Table of Contents
1. [Overview](#overview)
2. [Getting Started](#getting-started)
3. [Selecting the Right Statistical Test](#selecting-the-right-statistical-test)
4. [Variable Configuration](#variable-configuration)
5. [Understanding Results](#understanding-results)
6. [Interpreting Effect Sizes](#interpreting-effect-sizes)
7. [Assumption Checks](#assumption-checks)
8. [APA Reporting](#apa-reporting)
9. [Common Pitfalls](#common-pitfalls)
10. [Troubleshooting](#troubleshooting)

---

## Overview

Stage 7 provides comprehensive statistical analysis capabilities for your research data. The system guides you through:

- **Test Selection**: Choose appropriate statistical methods based on your research question
- **Variable Configuration**: Define dependent, independent, and grouping variables
- **Assumption Checking**: Automatically verify statistical assumptions
- **Results Interpretation**: Get clear, actionable insights
- **APA Formatting**: Generate publication-ready statistical reporting

### Key Features

- ✅ **15+ Statistical Tests**: From t-tests to regression models
- ✅ **Automatic Assumption Checking**: Normality, homogeneity, independence
- ✅ **Effect Size Calculations**: Cohen's d, eta squared, and more
- ✅ **Multiple Comparison Corrections**: Bonferroni, Holm, FDR
- ✅ **Publication-Ready Output**: APA 7th edition formatting
- ✅ **Interactive Visualizations**: Q-Q plots, histograms, boxplots

---

## Getting Started

### Step 1: Ensure Your Data is Ready

Before starting statistical analysis, verify:

- [ ] Data is uploaded and validated (Stage 3)
- [ ] Missing values are handled appropriately
- [ ] Variables are correctly typed (continuous, categorical, binary)
- [ ] Outliers have been identified and addressed
- [ ] Sample size is adequate for planned analyses

### Step 2: Navigate to Stage 7

1. Open your research project
2. Click on **Stage 7: Statistical Analysis** in the workflow sidebar
3. You'll see the analysis configuration interface

### Step 3: Choose Your Analysis Approach

Two options:

**Option A: Guided Selection**
- Answer questions about your study design
- System recommends appropriate tests
- Best for: Researchers new to statistical testing

**Option B: Direct Selection**
- Choose test type from dropdown menu
- Configure manually
- Best for: Experienced researchers with specific test in mind

---

## Selecting the Right Statistical Test

### Decision Tree

Use this decision tree to select the appropriate test:

#### 1. What type of outcome variable do you have?

**Continuous Outcome (e.g., blood pressure, test scores)**

- **Comparing 2 groups**:
  - Independent groups → **Independent t-test** (or Mann-Whitney if non-normal)
  - Paired/matched data → **Paired t-test** (or Wilcoxon if non-normal)
  
- **Comparing 3+ groups**:
  - Independent groups → **One-way ANOVA** (or Kruskal-Wallis if non-normal)
  - Repeated measures → **Repeated Measures ANOVA** (or Friedman if non-normal)
  
- **Relationship between two continuous variables**:
  - Linear relationship → **Pearson correlation** (or Spearman if non-linear/non-normal)
  - Predicting outcome → **Linear regression**

**Categorical/Binary Outcome (e.g., yes/no, disease/healthy)**

- **Comparing groups**:
  - 2x2 table → **Chi-square test** (or Fisher's exact if small sample)
  - Larger tables → **Chi-square test**
  
- **Predicting outcome**:
  - Binary outcome → **Logistic regression**

### Test Selection Examples

#### Example 1: Clinical Trial
**Research Question**: Does the new drug reduce blood pressure compared to placebo?

- Outcome: Blood pressure (continuous)
- Groups: Drug vs Placebo (2 independent groups)
- **Recommended Test**: Independent t-test
- **Alternative if non-normal**: Mann-Whitney U test

#### Example 2: Longitudinal Study
**Research Question**: Does anxiety decrease from baseline to 3-month follow-up?

- Outcome: Anxiety score (continuous)
- Measurements: Baseline vs 3-month (paired data)
- **Recommended Test**: Paired t-test
- **Alternative if non-normal**: Wilcoxon signed-rank test

#### Example 3: Multi-Group Comparison
**Research Question**: Do three teaching methods differ in exam performance?

- Outcome: Exam score (continuous)
- Groups: Method A, B, C (3 independent groups)
- **Recommended Test**: One-way ANOVA
- **Alternative if non-normal**: Kruskal-Wallis test

#### Example 4: Association Study
**Research Question**: Is smoking associated with lung disease?

- Outcome: Disease status (yes/no)
- Predictor: Smoking status (yes/no)
- **Recommended Test**: Chi-square test
- **Alternative if small sample**: Fisher's exact test

---

## Variable Configuration

### Variable Types

The system recognizes four variable types:

1. **Continuous**: Numeric values on an interval/ratio scale
   - Examples: Age, blood pressure, test scores
   - Required for: t-tests, ANOVA, correlation, regression

2. **Categorical**: Discrete categories (3+ levels)
   - Examples: Treatment group, ethnicity, education level
   - Required for: Chi-square, ANOVA grouping

3. **Binary**: Two categories only
   - Examples: Gender (M/F), disease (yes/no), treatment (active/control)
   - Required for: t-tests, Fisher's exact, logistic regression

4. **Ordinal**: Ordered categories
   - Examples: Likert scales, disease severity (mild/moderate/severe)
   - Can use: Non-parametric tests (Mann-Whitney, Kruskal-Wallis)

### Variable Roles

Each variable must have a defined role:

- **Dependent Variable** (Outcome): What you're measuring
- **Independent Variable** (Predictor): What you think affects the outcome
- **Grouping Variable**: Defines comparison groups
- **Covariate**: Control variable to adjust for confounding

### Configuration Interface

```
┌─────────────────────────────────────────┐
│ Test Type: Independent t-test           │
├─────────────────────────────────────────┤
│ Dependent Variable (Required)           │
│ ├─ Select: [blood_pressure ▼]          │
│ └─ Type: Continuous                     │
│                                         │
│ Grouping Variable (Required)            │
│ ├─ Select: [treatment_group ▼]         │
│ └─ Type: Binary                         │
│                                         │
│ Confidence Level: 95% [━━━━━━━━━] 99%  │
│ Alpha Level: 0.05                       │
│                                         │
│ Options:                                │
│ ☐ Two-tailed test                      │
│ ☐ Assume equal variances               │
│ ☐ Apply Bonferroni correction          │
└─────────────────────────────────────────┘
```

### Validation

The system automatically validates your configuration:

- ✅ **Green checkmark**: Configuration is valid
- ⚠️ **Yellow warning**: Configuration may work but has issues
- ❌ **Red error**: Configuration cannot proceed

Common validation errors:

- "Test requires at least 1 continuous dependent variable"
- "Grouping variable must have exactly 2 levels for t-test"
- "Insufficient sample size (n < 30) - consider non-parametric alternative"

---

## Understanding Results

### Results Dashboard

After executing analysis, you'll see five main sections:

```
┌──────────────────────────────────────────┐
│ 1. Descriptive Statistics                │
│ 2. Hypothesis Test Results               │
│ 3. Effect Sizes & Practical Significance │
│ 4. Assumption Checks                      │
│ 5. Recommendations & Interpretations      │
└──────────────────────────────────────────┘
```

### 1. Descriptive Statistics

**What it shows**: Summary statistics for each group/variable

**Example output**:
```
Group Statistics
─────────────────────────────────────────────
                  Treatment    Control
                  (n = 50)    (n = 48)
─────────────────────────────────────────────
Blood Pressure
  Mean (SD)       128.4 (12.3)  135.7 (14.1)
  Median          127.0         134.5
  95% CI          [124.9, 131.9] [131.6, 139.8]
  Range           [105, 158]    [110, 170]
```

**How to interpret**:
- Compare means and standard deviations
- Check if medians differ from means (indicates skewness)
- Look at confidence intervals - do they overlap?
- Examine ranges for outliers

### 2. Hypothesis Test Results

**What it shows**: Statistical test outcome, p-value, significance

**Example output**:
```
Independent Samples t-test
─────────────────────────────────────────────
t(96) = -2.85, p = .005

Result: Statistically significant at α = .05
─────────────────────────────────────────────
```

**How to interpret**:

- **Test statistic**: Magnitude of difference (larger = bigger difference)
- **Degrees of freedom**: Sample size information (in parentheses)
- **P-value**: Probability of observing this result if null hypothesis is true
  - p < .05: Statistically significant (reject null hypothesis)
  - p ≥ .05: Not statistically significant (fail to reject null)
- **Confidence interval**: Range of plausible values for the effect

**Important**: Statistical significance ≠ practical significance!

### 3. Effect Sizes & Practical Significance

**What it shows**: Magnitude of the effect, regardless of sample size

**Example output**:
```
Effect Size
─────────────────────────────────────────────
Cohen's d = 0.56, 95% CI [0.17, 0.95]
Interpretation: Medium effect size
─────────────────────────────────────────────
```

**Guidelines for interpreting effect sizes**:

| Test Type | Effect Size | Small | Medium | Large |
|-----------|-------------|-------|--------|-------|
| t-test | Cohen's d | 0.20 | 0.50 | 0.80 |
| ANOVA | Eta squared (η²) | 0.01 | 0.06 | 0.14 |
| Chi-square | Cramér's V | 0.10 | 0.30 | 0.50 |
| Correlation | Pearson's r | 0.10 | 0.30 | 0.50 |

**Why it matters**: A large sample can make tiny, meaningless differences "significant". Effect sizes tell you if the difference actually matters in practice.

---

(Continued in next section...)
