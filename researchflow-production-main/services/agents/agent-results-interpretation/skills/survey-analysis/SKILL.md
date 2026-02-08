---
name: survey-analysis
description: Specialized guidance for interpreting survey and questionnaire research results, including response rate evaluation, sampling methodology, question design critique, and common survey-specific biases. Load this skill when the study involves survey data, polls, or questionnaire-based research.
---

# Survey & Questionnaire Analysis Skill

## When to Load This Skill

Load this skill whenever the study being interpreted is:
- A cross-sectional survey or poll
- A longitudinal panel survey
- A questionnaire-based study (e.g., patient satisfaction, employee engagement, public opinion)
- A census or large-scale population survey
- Any study using Likert scales, rating scales, or structured response formats
- Mixed-methods research where a survey is a primary data source

---

## Response Rate Evaluation

Response rate is one of the most critical indicators of survey quality. Use this framework:

### Response Rate Benchmarks
| Mode | Excellent | Good | Acceptable | Concerning |
|------|-----------|------|------------|------------|
| Mail surveys | > 60% | 40–60% | 20–40% | < 20% |
| Online surveys (general pop) | > 30% | 20–30% | 10–20% | < 10% |
| Online surveys (targeted/panel) | > 50% | 30–50% | 15–30% | < 15% |
| Phone surveys | > 40% | 25–40% | 10–25% | < 10% |
| In-person/intercept | > 70% | 50–70% | 30–50% | < 30% |
| Employee/organizational | > 70% | 50–70% | 30–50% | < 30% |

### How to Calculate
- **AAPOR Standard**: Response Rate = Complete interviews / (Complete + Partial + Refusals + Non-contacts + Unknown eligibility × estimated eligibility rate)
- Always ask: Was the denominator clearly defined? Were partial completes included?

### Non-Response Bias Assessment
- Were responders compared to non-responders on available demographics?
- Was a non-response bias analysis conducted (e.g., wave analysis, comparison to known population parameters)?
- Are there systematic patterns in who didn't respond (younger, lower income, etc.)?

---

## Sampling Methodology Evaluation

### Probability Sampling (Preferred)
- **Simple random sampling**: Every member has equal chance. Gold standard but rare in practice.
- **Stratified sampling**: Ensures representation of key subgroups. Check if proportionate or disproportionate (disproportionate requires weighting).
- **Cluster sampling**: Samples groups, then individuals within. Introduces design effects — check if standard errors were adjusted.
- **Systematic sampling**: Every kth member. Vulnerable to periodicity in the sampling frame.

### Non-Probability Sampling (Requires Extra Caution)
- **Convenience sampling**: Not generalizable. Flag this prominently.
- **Snowball sampling**: Useful for hard-to-reach populations but introduces network bias.
- **Quota sampling**: Mimics stratification but without random selection. Better than convenience, worse than stratified.
- **Opt-in online panels**: Increasingly common. Require weighting and adjustment. Generalizability is debatable.

### Key Questions to Ask
- Was the sampling frame clearly defined and appropriate for the target population?
- Was the sample size justified with a power analysis or margin of error calculation?
- Were sampling weights applied? If so, were they appropriate?
- What was the coverage rate? (Does the sampling frame cover the full target population?)

---

## Margin of Error and Confidence Intervals

### Standard Margin of Error Formula
For a proportion at 95% confidence:
- MoE = 1.96 × √(p(1-p)/n)
- At p = 0.50 (maximum variability): MoE ≈ 1/√n

### Quick Reference Table (95% CI, p = 0.50)
| Sample Size | Margin of Error |
|-------------|----------------|
| 100 | ± 9.8% |
| 250 | ± 6.2% |
| 500 | ± 4.4% |
| 1,000 | ± 3.1% |
| 1,500 | ± 2.5% |
| 2,000 | ± 2.2% |
| 5,000 | ± 1.4% |
| 10,000 | ± 1.0% |

### Important Caveats
- MoE applies to the FULL sample. Subgroup analyses have wider margins.
- Design effects from cluster sampling inflate the MoE — check if DEFF was reported.
- Non-probability samples technically don't have a valid MoE (though pseudo-MoE is often reported).
- MoE doesn't account for non-response bias or measurement error.

---

## Question Design Critique

When the survey instrument is available, evaluate for these common flaws:

### Common Question Design Problems
- **Double-barreled questions**: Ask about two things at once ("How satisfied are you with our product quality and price?"). Impossible to interpret clearly.
- **Leading questions**: Suggest a desired answer ("Don't you agree that...?" or "Given the well-known benefits of X, how do you feel about...?").
- **Loaded questions**: Contain emotionally charged language or assumptions.
- **Social desirability bias**: Questions on sensitive topics (drug use, income, prejudice) tend to get biased responses. Check for anonymous administration or validated indirect measures.
- **Acquiescence bias**: Tendency to agree. Check if the scale includes reverse-coded items.
- **Primacy/recency effects**: First and last response options are chosen more often. Check if response order was randomized.
- **Scale anchoring**: Inconsistent scale endpoints across questions confuse respondents.
- **Missing "don't know" or "not applicable" options**: Forced responses on unfamiliar topics introduce noise.

### Likert Scale Best Practices
- 5-point and 7-point scales are most common. 7-point offers more granularity.
- Check if scale midpoint is labeled (important for interpretation).
- Odd-number scales include a neutral midpoint; even-number scales force a direction.
- Were scale items treated as ordinal (appropriate) or interval (debatable but common)?

---

## Survey-Specific Biases

Beyond general research biases, surveys are susceptible to:

### Pre-Survey Biases
- **Coverage bias**: Sampling frame doesn't cover the full target population (e.g., phone surveys miss those without phones).
- **Self-selection bias**: Respondents who choose to participate may differ systematically from non-respondents.
- **Undercoverage**: Certain groups systematically excluded from the sampling frame.

### During-Survey Biases
- **Social desirability bias**: Respondents give answers they think are socially acceptable.
- **Acquiescence bias**: Tendency to agree with statements regardless of content.
- **Demand characteristics**: Respondents guess the study's hypothesis and adjust answers.
- **Interviewer bias**: Characteristics of the interviewer (race, gender, tone) influence responses. More relevant to phone/in-person modes.
- **Mode effects**: Different survey modes (online vs. phone vs. in-person) can yield different results for the same questions.
- **Satisficing**: Respondents give "good enough" answers rather than thoughtful ones (straight-lining, speeding).

### Post-Survey Biases
- **Non-response bias**: If non-respondents differ systematically from respondents.
- **Weighting artifacts**: Over-weighting underrepresented groups can amplify noise.
- **Selective reporting**: Reporting only favorable results or cherry-picking subgroups.

---

## Statistical Methods Common in Survey Research

### Frequently Used Methods
- **Descriptive statistics**: Frequencies, percentages, means, medians. Check if weighted.
- **Cross-tabulations with chi-square tests**: Appropriate for categorical × categorical comparisons.
- **t-tests and ANOVA**: For comparing means across groups. Check assumptions (normality, equal variance).
- **Logistic regression**: Common for binary outcomes. Check for multicollinearity, model fit.
- **Ordered logistic / ordinal regression**: Appropriate for Likert-scale outcomes. Check proportional odds assumption.
- **Factor analysis**: Used to validate multi-item scales. Check KMO, Bartlett's test, eigenvalues, factor loadings.
- **Structural equation modeling (SEM)**: Common in behavioral/social science surveys. Check fit indices (CFI > 0.95, RMSEA < 0.06, SRMR < 0.08).

### Weighting Considerations
- **Raking/iterative proportional fitting**: Adjusts sample to match known population margins.
- **Propensity score weighting**: Used for non-probability samples. Check which variables were used.
- **Post-stratification**: Adjusts for known demographics. Check if weights are trimmed to avoid extreme values.
- **Design weights**: Account for unequal selection probabilities (e.g., disproportionate stratification).

---

## Reporting Standards (CHERRIES / CROSS)

### CHERRIES Checklist (for online surveys)
- [ ] Design: Survey design, target population, sample frame described
- [ ] IRB approval and informed consent documented
- [ ] Development and pre-testing of the questionnaire described
- [ ] Open vs. closed survey (access restrictions)
- [ ] Contact mode and delivery method specified
- [ ] Advertising the survey / recruitment strategy described
- [ ] Survey administration period stated
- [ ] Response rate with numerator and denominator defined
- [ ] Completeness of data (item-level missingness) reported
- [ ] Data analysis methods including weighting described

### Cross-Sectional Survey Reporting
- [ ] Clear research question or hypothesis
- [ ] Defined target population and sampling strategy
- [ ] Data collection period and mode specified
- [ ] Validated instruments or pilot testing described
- [ ] Response rate and non-response analysis
- [ ] Handling of missing data explained
- [ ] Appropriate statistical methods for survey design

---

## Template Phrases for Survey Interpretation

Use these calibrated phrases when writing survey sections:

- "The response rate of [X]% [meets/falls below] accepted thresholds for [survey mode], which [supports/limits] confidence in the representativeness of these findings."
- "Results should be interpreted with caution given the [convenience/self-selected/non-probability] sampling approach, which limits generalizability to the broader [target population]."
- "The margin of error of ±[X]% at the full-sample level widens considerably for subgroup analyses, particularly for [subgroup] (n = [Y]), where estimates are subject to greater uncertainty."
- "The observed [X]% agreement rate may be influenced by social desirability bias, particularly given the [non-anonymous administration / sensitive topic / face-to-face interview mode]."
- "While the Likert-scale data were analyzed using [parametric methods], the ordinal nature of the response scale means these results should be interpreted as approximations."
- "The cross-sectional design precludes causal inference; observed associations between [X] and [Y] may reflect reverse causation or confounding by unmeasured variables."
