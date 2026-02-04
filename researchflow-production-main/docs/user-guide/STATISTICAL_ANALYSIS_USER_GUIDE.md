# Statistical Analysis User Guide

## 🎯 Complete Guide to ResearchFlow Statistical Analysis

Welcome to the ResearchFlow Statistical Analysis module! This comprehensive guide will walk you through performing professional-grade statistical analyses with publication-ready results.

## 📋 Table of Contents

1. [Getting Started](#getting-started)
2. [Data Preparation](#data-preparation)
3. [Analysis Configuration](#analysis-configuration)
4. [Interpreting Results](#interpreting-results)
5. [Creating Visualizations](#creating-visualizations)
6. [Exporting Results](#exporting-results)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)

## 🚀 Getting Started

### Accessing Statistical Analysis

1. **From the Dashboard**: Click "Statistical Analysis" in the main navigation
2. **From a Research Project**: Select "Analyze Data" from your project menu
3. **Direct URL**: Navigate to `/statistical-analysis`

### System Requirements

- **Browser**: Chrome 90+, Firefox 88+, Safari 14+, Edge 90+
- **Data Size**: Up to 100,000 rows (larger datasets on request)
- **File Formats**: CSV, Excel (.xlsx), TSV, JSON

## 📊 Data Preparation

### Uploading Your Dataset

1. **Click "Upload Dataset"** or drag and drop your file
2. **File Format**: Ensure data is in CSV or Excel format
3. **Column Headers**: First row should contain variable names
4. **Data Quality**: Review the automatic quality assessment

### Data Quality Checklist

✅ **Column Names**: Use descriptive, concise names without special characters
✅ **Missing Data**: Clearly marked (empty cells, "NA", or "NULL")
✅ **Data Types**: Consistent formatting within columns
✅ **Outliers**: Review flagged extreme values
✅ **Sample Size**: Ensure adequate power for your analysis

### Example Data Structure

```csv
participant_id,age,sex,treatment_group,outcome_score,baseline_score
P001,45,Male,Treatment,85.2,72.1
P002,52,Female,Control,78.9,73.4
P003,38,Male,Treatment,91.6,68.7
```

## ⚙️ Analysis Configuration

### Step 1: Test Selection

The system provides **guided test selection** based on your data structure:

#### Comparing Groups
- **Independent t-test**: Compare means between two independent groups
- **Paired t-test**: Compare means within the same subjects (before/after)
- **One-Way ANOVA**: Compare means across multiple groups
- **Chi-square**: Test associations between categorical variables

#### Relationships
- **Pearson Correlation**: Linear relationships between continuous variables
- **Spearman Correlation**: Monotonic relationships (non-parametric)
- **Linear Regression**: Predict continuous outcomes
- **Logistic Regression**: Predict binary outcomes

#### Advanced Methods
- **Repeated Measures ANOVA**: Longitudinal/time series analyses
- **Survival Analysis**: Time-to-event analyses
- **Non-parametric tests**: When assumptions are violated

### Step 2: Variable Assignment

**Dependent Variable**: The outcome you're measuring
**Independent Variable(s)**: The predictor(s) or grouping factor(s)
**Covariates**: Additional variables to control for

### Step 3: Analysis Options

#### Confidence Level
- **90%**: For exploratory analyses
- **95%**: Standard for most research (recommended)
- **99%**: For critical decisions requiring high certainty

#### Multiple Comparison Correction
- **None**: Single comparison only
- **Bonferroni**: Conservative correction
- **FDR (Benjamini-Hochberg)**: Balance between Type I and II errors (recommended)
- **Holm**: Step-down method

#### Advanced Options
- **Bootstrap confidence intervals**: For robust estimation
- **Effect size calculations**: Always recommended
- **Assumption checking**: Automatic diagnostic tests

## 📈 Interpreting Results

### Understanding the Results Dashboard

#### Summary Tab
- **Key Findings**: Plain-language interpretation
- **Statistical Significance**: p-value and confidence intervals
- **Effect Size**: Practical significance measure
- **Recommendations**: Next steps and considerations

#### Descriptive Statistics
- **Central Tendency**: Mean, median, mode
- **Variability**: Standard deviation, range, IQR
- **Distribution**: Skewness, kurtosis
- **Sample Sizes**: Valid cases per group

#### Inferential Statistics
- **Test Statistic**: t, F, χ², etc.
- **Degrees of Freedom**: For proper interpretation
- **P-value**: Probability of observing results if null hypothesis is true
- **Confidence Intervals**: Range of plausible values
- **Effect Size**: Magnitude of the effect

#### Statistical Assumptions
- **Normality**: Shapiro-Wilk test, Q-Q plots
- **Homogeneity of Variance**: Levene's test
- **Independence**: Study design consideration
- **Linearity**: For regression analyses

### Effect Size Interpretation

#### Cohen's d (for t-tests)
- **Small**: d = 0.20
- **Medium**: d = 0.50
- **Large**: d = 0.80

#### Eta-squared (for ANOVA)
- **Small**: η² = 0.01
- **Medium**: η² = 0.06
- **Large**: η² = 0.14

#### Correlation Coefficients
- **Small**: r = 0.10
- **Medium**: r = 0.30
- **Large**: r = 0.50

## 📊 Creating Visualizations

### Available Chart Types

#### Diagnostic Plots
- **Q-Q Plots**: Check normality assumption
- **Histograms**: Visualize data distribution
- **Box Plots**: Compare groups and identify outliers
- **Residual Plots**: Assess regression assumptions

#### Results Plots
- **Bar Charts**: Group comparisons
- **Scatter Plots**: Correlations and regression
- **Forest Plots**: Effect sizes with confidence intervals
- **Survival Curves**: Time-to-event analyses

### Customization Options

1. **View Mode**: Grid layout or single view
2. **Export Options**: PNG, SVG, PDF formats
3. **Color Schemes**: Publication-ready palettes
4. **Labels and Titles**: Customize for your audience

## 📄 Exporting Results

### Quick Export Presets

#### Full Report
- **Format**: PDF
- **Content**: All sections with visualizations
- **Use Case**: Complete documentation

#### Results Summary
- **Format**: Word Document
- **Content**: Key findings and statistics
- **Use Case**: Manuscript preparation

#### Data Export
- **Format**: CSV
- **Content**: Raw statistics and results
- **Use Case**: Further analysis or meta-analysis

### Custom Export Options

#### Content Selection
- ✅ Descriptive Statistics
- ✅ Hypothesis Test Results
- ✅ Effect Sizes
- ✅ Assumption Checks
- ✅ Visualizations
- ✅ APA-Formatted Text

#### Format Options
- **PDF**: Publication-ready reports
- **Word**: Editable documents
- **HTML**: Interactive web reports
- **CSV**: Raw data export
- **JSON**: Complete machine-readable format

#### Template Selection
- **Default**: Standard scientific format
- **APA Style**: Psychology/social science format
- **Nature**: High-impact journal style
- **Clinical**: Medical research format
- **Minimal**: Clean, simplified design

## 📚 Best Practices

### Before Analysis

1. **Plan Your Analysis**: Define hypotheses before data collection
2. **Check Sample Size**: Ensure adequate statistical power
3. **Data Cleaning**: Address missing data and outliers
4. **Assumption Verification**: Understand test requirements

### During Analysis

1. **Effect Sizes**: Always report practical significance
2. **Confidence Intervals**: Provide precision estimates
3. **Multiple Testing**: Apply appropriate corrections
4. **Assumption Checking**: Verify test validity

### After Analysis

1. **Clinical Significance**: Consider real-world importance
2. **Replication**: Validate findings in independent samples
3. **Reporting**: Follow established guidelines (CONSORT, STROBE, etc.)
4. **Data Sharing**: Make data and analysis code available

### Common Pitfalls to Avoid

❌ **p-hacking**: Don't fish for significant results
❌ **Multiple Testing**: Correct for multiple comparisons
❌ **Assumption Violations**: Check and address violations
❌ **Overinterpretation**: Correlation ≠ causation
❌ **Cherry Picking**: Report all planned analyses

## 🔧 Troubleshooting

### Common Issues and Solutions

#### "Analysis Failed to Execute"
**Possible Causes:**
- Insufficient sample size
- All values in a group are identical
- Severe assumption violations

**Solutions:**
- Check sample sizes (n > 30 recommended)
- Review data for data entry errors
- Consider non-parametric alternatives

#### "Assumptions Violated"
**Normality Violation:**
- Use non-parametric tests (Mann-Whitney, Kruskal-Wallis)
- Apply data transformations (log, square root)
- Use robust statistical methods

**Homogeneity Violation:**
- Use Welch's t-test instead of Student's t-test
- Apply Brown-Forsythe test for ANOVA
- Consider robust ANOVA methods

#### "Missing Data Detected"
**Options:**
- **Complete Case Analysis**: Use only cases with complete data
- **Multiple Imputation**: Estimate missing values (advanced)
- **Pairwise Deletion**: Use all available data for each analysis

#### "Large Dataset Performance"
**Optimization Tips:**
- Use data sampling for initial exploration
- Filter to relevant variables only
- Consider cloud-based analysis for very large datasets

### Getting Help

#### In-App Support
- **Tooltips**: Hover over any element for quick help
- **Context Help**: Click the "?" icon for detailed explanations
- **Error Messages**: Follow specific guidance for issues

#### Documentation
- **User Guide**: This comprehensive guide
- **Video Tutorials**: Step-by-step walkthroughs
- **FAQ**: Common questions and answers
- **Best Practices**: Scientific and statistical guidance

#### Contact Support
- **Email**: support@researchflow.ai
- **Live Chat**: Available during business hours
- **Community Forum**: Peer support and discussions

## 📖 Example Workflows

### Example 1: Clinical Trial Analysis

**Scenario**: Comparing treatment efficacy between two groups

```
Data: 200 patients, treatment vs. control
Primary Outcome: Recovery time (continuous)
Analysis: Independent samples t-test
```

**Steps:**
1. Upload clinical trial dataset
2. Select "Independent Samples t-test"
3. Assign outcome_score to dependent variable
4. Assign treatment_group to grouping variable
5. Set 95% confidence level
6. Run analysis
7. Export APA-formatted results

**Interpretation:**
- Check effect size (Cohen's d)
- Verify assumptions were met
- Report confidence intervals
- Consider clinical significance

### Example 2: Longitudinal Study

**Scenario**: Tracking patient improvement over time

```
Data: 50 patients, 4 time points
Primary Outcome: Symptom severity (continuous)
Analysis: Repeated Measures ANOVA
```

**Steps:**
1. Upload longitudinal dataset
2. Select "Repeated Measures ANOVA"
3. Assign severity_score to dependent variable
4. Assign time_point to within-subject factor
5. Include treatment_group as between-subject factor
6. Check sphericity assumption
7. Review post-hoc comparisons

### Example 3: Biomarker Validation

**Scenario**: Validating diagnostic accuracy

```
Data: 500 samples, disease vs. healthy
Primary Outcome: Disease status (binary)
Predictor: Biomarker level (continuous)
Analysis: ROC Analysis
```

**Steps:**
1. Upload biomarker dataset
2. Select "ROC Analysis"
3. Assign biomarker_level to predictor
4. Assign disease_status to outcome
5. Generate ROC curve
6. Calculate optimal cutoff point
7. Report sensitivity and specificity

## 🎓 Statistical Concepts Explained

### P-values
The probability of observing your results (or more extreme) if the null hypothesis were true.
- **p < 0.05**: Traditionally considered "significant"
- **p < 0.01**: "Highly significant"
- **p < 0.001**: "Very highly significant"

**Important**: p-values don't tell you the size or importance of an effect!

### Confidence Intervals
A range of values that likely contains the true population parameter.
- **95% CI**: If we repeated the study 100 times, 95 intervals would contain the true value
- **Narrow intervals**: More precise estimates
- **Wide intervals**: Less precise estimates

### Effect Sizes
Quantify the magnitude of differences or relationships.
- **Standardized**: Allow comparison across studies
- **Interpretable**: Meaningful in real-world terms
- **Required**: Essential for meta-analyses

### Statistical Power
The probability of detecting a true effect.
- **Low power (< 0.80)**: May miss real effects
- **Adequate power (≥ 0.80)**: Reasonable chance of detection
- **High power (≥ 0.90)**: Very likely to detect effects

## 📋 Checklist for Quality Analysis

### Pre-Analysis ✅
- [ ] Research question clearly defined
- [ ] Appropriate study design used
- [ ] Sample size adequate for research question
- [ ] Data quality checked and cleaned
- [ ] Analysis plan pre-specified

### Analysis ✅
- [ ] Appropriate statistical test selected
- [ ] Assumptions checked and addressed
- [ ] Effect sizes calculated
- [ ] Confidence intervals reported
- [ ] Multiple testing corrections applied

### Post-Analysis ✅
- [ ] Results interpreted in context
- [ ] Clinical/practical significance considered
- [ ] Limitations acknowledged
- [ ] Findings replicated if possible
- [ ] Results reported transparently

## 🏆 Advanced Features

### Power Analysis
Calculate required sample sizes or achieved power for your study.

### Missing Data Analysis
Advanced imputation methods for handling incomplete data.

### Robust Statistics
Methods that are less sensitive to outliers and assumption violations.

### Bayesian Analysis
Alternative statistical framework providing probability statements about parameters.

### Meta-Analysis
Combine results from multiple studies for stronger evidence.

---

## 🎯 Summary

The ResearchFlow Statistical Analysis module provides a comprehensive, user-friendly platform for conducting rigorous statistical analyses. From data upload through publication-ready exports, the system guides you through best practices while maintaining scientific rigor.

**Key Benefits:**
- ✅ Guided analysis workflow
- ✅ Automatic assumption checking
- ✅ Publication-quality outputs
- ✅ Comprehensive documentation
- ✅ Professional support

**Ready to get started?** Upload your data and begin your analysis journey!

---

*For additional support, contact our team at support@researchflow.ai or visit our help center.*