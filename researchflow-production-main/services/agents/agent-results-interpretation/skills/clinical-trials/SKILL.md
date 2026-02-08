---
name: clinical-trials
description: Specialized guidance for interpreting clinical trial results, including RCTs, non-inferiority trials, adaptive designs, and observational clinical studies. Load this skill when the study involves healthcare, pharmaceutical, or clinical research.
---

# Clinical Trials Interpretation Skill

## When to Load This Skill

Load this skill whenever the study being interpreted is:
- A randomized controlled trial (RCT) — parallel, crossover, factorial, or cluster
- A non-inferiority or equivalence trial
- An adaptive or platform trial
- A Phase I–IV pharmaceutical trial
- An observational clinical study (cohort, case-control) with clinical endpoints
- Any study reporting clinical outcomes (mortality, morbidity, adverse events, patient-reported outcomes)

---

## Key Metrics to Evaluate

### Primary Efficacy Metrics
- **Hazard Ratio (HR)**: Used in time-to-event analyses. HR < 1 favors the treatment group. Always check the 95% CI — if it crosses 1.0, the result is not statistically significant.
- **Odds Ratio (OR)**: Common in case-control studies and logistic regression. OR = 1 means no association. Interpret with caution when event rates are high (OR overestimates relative risk).
- **Relative Risk (RR)**: Preferred over OR when possible. RR = 1 means no difference.
- **Absolute Risk Reduction (ARR)**: The difference in event rates between groups. More clinically meaningful than relative measures.
- **Number Needed to Treat (NNT)**: NNT = 1/ARR. Lower NNT = more clinically impactful. NNT < 10 is generally considered strong; NNT > 50 suggests marginal benefit.
- **Number Needed to Harm (NNH)**: NNH = 1/Absolute Risk Increase. Compare NNT vs. NNH to assess benefit-risk balance.

### Secondary & Safety Metrics
- **Adverse Event (AE) rates**: Compare incidence between arms. Flag any serious adverse events (SAEs) or treatment-related deaths.
- **Kaplan-Meier survival curves**: Check for separation of curves, proportional hazards assumption, and median survival times.
- **Subgroup analyses**: Treat with caution — usually underpowered. Flag if results are driven by a single subgroup.
- **Intention-to-Treat (ITT) vs. Per-Protocol (PP)**: ITT preserves randomization and is the gold standard. PP can inflate treatment effects. Both should ideally be reported.

### Patient-Reported Outcomes (PROs)
- Check if validated instruments were used (e.g., EQ-5D, SF-36, FACT scales).
- Evaluate whether the minimum clinically important difference (MCID) was achieved, not just statistical significance.
- Assess timing of PRO collection relative to treatment.

---

## Reporting Standards Checklist (CONSORT)

When auditing a clinical trial, check for these CONSORT 2010 elements:

### Title & Abstract
- [ ] Identified as a randomised trial in the title
- [ ] Structured summary of trial design, methods, results, and conclusions

### Methods
- [ ] Eligibility criteria for participants clearly described
- [ ] Settings and locations where data were collected
- [ ] Interventions described with sufficient detail for replication
- [ ] Pre-specified primary and secondary outcomes with measurement methods and time points
- [ ] Sample size calculation with assumptions documented
- [ ] Randomisation method described (sequence generation, allocation concealment)
- [ ] Blinding described (who was blinded, how)

### Results
- [ ] Participant flow diagram (CONSORT flow diagram)
- [ ] Baseline demographic and clinical characteristics for each group
- [ ] Number of participants analysed in each group (ITT)
- [ ] Primary outcome: effect estimate with precision (CI)
- [ ] Harms and unintended effects reported

### Discussion
- [ ] Limitations addressed
- [ ] Generalisability discussed
- [ ] Interpretation consistent with results

---

## Clinical vs. Statistical Significance

This is one of the MOST IMPORTANT distinctions in clinical trial interpretation:

- **Statistically significant ≠ clinically meaningful.** A large trial can detect tiny differences that have no practical impact on patient care.
- **Always ask**: Does the effect size exceed the MCID for the outcome measure? Is the NNT reasonable for the condition?
- **Conversely**: A non-significant p-value does not mean "no effect" — it may reflect insufficient power. Check the confidence interval width.

### Red Flags
- Claiming clinical benefit based solely on p < 0.05 without discussing effect magnitude
- Emphasizing relative risk reductions without reporting absolute risk reductions (e.g., "50% reduction" when ARR is 0.2%)
- Post-hoc subgroup analyses presented as primary findings
- Composite endpoints where components have very different clinical weight
- Surrogate endpoints without established correlation to hard clinical outcomes

---

## Bias Assessment for Clinical Trials

Beyond standard biases, clinical trials are susceptible to:

- **Attrition bias**: Differential dropout between arms. Check if dropout rates and reasons differ.
- **Performance bias**: Unblinded participants or providers may behave differently. Especially relevant in open-label trials.
- **Detection bias**: Outcome assessors who know the allocation may assess differently.
- **Reporting bias**: Selective reporting of favorable outcomes. Compare registered protocol (ClinicalTrials.gov) against published results.
- **Sponsor bias**: Industry-funded trials show larger treatment effects on average. Note the funding source.
- **Lead-time bias**: Screening studies may appear to extend survival simply by detecting disease earlier.
- **Immortal time bias**: Common in observational clinical studies — the treatment group survives long enough to receive treatment by definition.

---

## Regulatory Context

When interpreting pivotal trials:
- **FDA approval threshold**: Typically requires two adequate and well-controlled studies, or one very large compelling study.
- **Accelerated approval**: May be based on surrogate endpoints — note if the endpoint is a validated or reasonably likely surrogate.
- **EMA considerations**: European Medicines Agency may weigh evidence differently. Note any discrepancies in regulatory decisions.
- **Post-marketing requirements**: Phase IV commitments, REMS programs, or black box warnings may indicate residual safety concerns.

---

## Template Phrases for Clinical Trial Interpretation

Use these calibrated phrases when writing clinical trial sections:

- "The observed hazard ratio of [X] (95% CI: [Y]–[Z]) suggests a [magnitude] [benefit/risk] for [treatment], though the confidence interval [does/does not] cross the null."
- "While statistically significant (p = [X]), the absolute risk reduction of [Y]% corresponds to an NNT of [Z], which [does/does not] represent a clinically meaningful benefit."
- "The results should be interpreted in the context of [open-label design / industry sponsorship / surrogate endpoint / short follow-up duration]."
- "Subgroup analyses suggested differential treatment effects in [subgroup], though these were not pre-specified and the study was not powered to detect subgroup differences."
