/**
 * FAVES Compliance Result Schema
 * Fair, Appropriate, Valid, Effective, Safe evaluation results
 *
 * @module packages/shared/src/schemas/faves_result
 * @version 1.0.0
 */

import * as z from 'zod';

// FAVES Dimension
export const FAVESDimensionSchema = z.enum(['FAIR', 'APPROPRIATE', 'VALID', 'EFFECTIVE', 'SAFE']);

// FAVES Result Status
export const FAVESStatusSchema = z.enum(['PASS', 'FAIL', 'PARTIAL', 'NOT_EVALUATED']);

// Individual Metric Result
export const MetricResultSchema = z.object({
  metric_name: z.string(),
  value: z.number(),
  threshold: z.number(),
  passed: z.boolean(),
  unit: z.string().optional(),
  description: z.string().optional(),
});

// Artifact Reference
export const ArtifactReferenceSchema = z.object({
  name: z.string(),
  path: z.string(),
  required: z.boolean(),
  exists: z.boolean(),
  last_modified: z.string().datetime().optional(),
});

// Single FAVES Dimension Result
export const FAVESDimensionResultSchema = z.object({
  dimension: FAVESDimensionSchema,
  status: FAVESStatusSchema,
  score: z.number().min(0).max(100),
  passed: z.boolean(),

  // Metrics for this dimension
  metrics: z.array(MetricResultSchema),

  // Required artifacts
  required_artifacts: z.array(ArtifactReferenceSchema),

  // Missing requirements
  missing_requirements: z.array(z.string()),

  // Recommendations
  recommendations: z.array(z.string()).optional(),
});

// Complete FAVES Evaluation Result
export const FAVESResultSchema = z.object({
  evaluation_id: z.string().uuid(),
  model_id: z.string().uuid(),
  model_version: z.string(),
  evaluated_at: z.string().datetime(),
  evaluated_by: z.string(),

  // Overall result
  overall_status: FAVESStatusSchema,
  overall_score: z.number().min(0).max(100),
  deployment_allowed: z.boolean(),

  // Individual dimension results
  dimensions: z.object({
    fair: FAVESDimensionResultSchema,
    appropriate: FAVESDimensionResultSchema,
    valid: FAVESDimensionResultSchema,
    effective: FAVESDimensionResultSchema,
    safe: FAVESDimensionResultSchema,
  }),

  // Summary
  total_metrics_passed: z.number().int().nonnegative(),
  total_metrics_failed: z.number().int().nonnegative(),
  total_artifacts_present: z.number().int().nonnegative(),
  total_artifacts_missing: z.number().int().nonnegative(),

  // Blocking issues
  blocking_issues: z.array(z.string()),

  // Metadata
  schema_version: z.literal('1.0.0'),
  ci_run_id: z.string().optional(),
  git_commit_sha: z.string().optional(),
});

// FAVES Requirements Matrix (for reference/validation)
export const FAVESRequirementsSchema = z.object({
  fair: z.object({
    metrics: z.array(z.string()),
    artifacts: z.array(z.string()),
    thresholds: z.record(z.number()),
  }),
  appropriate: z.object({
    metrics: z.array(z.string()),
    artifacts: z.array(z.string()),
    thresholds: z.record(z.number()),
  }),
  valid: z.object({
    metrics: z.array(z.string()),
    artifacts: z.array(z.string()),
    thresholds: z.record(z.number()),
  }),
  effective: z.object({
    metrics: z.array(z.string()),
    artifacts: z.array(z.string()),
    thresholds: z.record(z.number()),
  }),
  safe: z.object({
    metrics: z.array(z.string()),
    artifacts: z.array(z.string()),
    thresholds: z.record(z.number()),
  }),
});

// FAVES Historical Entry (for tracking over versions)
export const FAVESHistoryEntrySchema = z.object({
  evaluation_id: z.string().uuid(),
  model_version: z.string(),
  evaluated_at: z.string().datetime(),
  overall_score: z.number(),
  dimension_scores: z.object({
    fair: z.number(),
    appropriate: z.number(),
    valid: z.number(),
    effective: z.number(),
    safe: z.number(),
  }),
  deployment_allowed: z.boolean(),
});

// Export types
export type FAVESDimension = z.infer<typeof FAVESDimensionSchema>;
export type FAVESStatus = z.infer<typeof FAVESStatusSchema>;
export type MetricResult = z.infer<typeof MetricResultSchema>;
export type ArtifactReference = z.infer<typeof ArtifactReferenceSchema>;
export type FAVESDimensionResult = z.infer<typeof FAVESDimensionResultSchema>;
export type FAVESResult = z.infer<typeof FAVESResultSchema>;
export type FAVESRequirements = z.infer<typeof FAVESRequirementsSchema>;
export type FAVESHistoryEntry = z.infer<typeof FAVESHistoryEntrySchema>;

// Validation helper
export function validateFAVESResult(data: unknown): FAVESResult {
  return FAVESResultSchema.parse(data);
}

// Default FAVES Requirements (from execution plan)
export const DEFAULT_FAVES_REQUIREMENTS: FAVESRequirements = {
  fair: {
    metrics: ['stratified_auc', 'stratified_sensitivity', 'stratified_specificity', 'demographic_parity', 'bias_test_score'],
    artifacts: ['representativeness_report.json', 'fairness_analysis.md'],
    thresholds: {
      demographic_parity_gap: 0.1,
      min_subgroup_auc: 0.7,
    },
  },
  appropriate: {
    metrics: ['intended_use_coverage_score', 'workflow_fit_score'],
    artifacts: ['intended_use.md', 'out_of_scope.md', 'workflow_integration.md'],
    thresholds: {
      intended_use_coverage: 0.9,
      workflow_fit: 0.8,
    },
  },
  valid: {
    metrics: ['calibration_error', 'brier_score', 'external_validation_auc'],
    artifacts: ['calibration_report.json', 'external_validation.md'],
    thresholds: {
      calibration_error: 0.1,
      brier_score: 0.25,
      external_validation_auc: 0.7,
    },
  },
  effective: {
    metrics: ['decision_curve_auc', 'net_benefit_at_threshold'],
    artifacts: ['utility_analysis.md', 'actionability_doc.md'],
    thresholds: {
      net_benefit_positive: 0,
    },
  },
  safe: {
    metrics: ['error_rate_by_subgroup', 'failure_mode_coverage'],
    artifacts: ['error_analysis.md', 'rollback_policy.md', 'monitoring_plan.md'],
    thresholds: {
      max_error_rate: 0.05,
      failure_mode_coverage: 0.9,
    },
  },
};

// Helper to check if deployment is allowed
export function isDeploymentAllowed(result: FAVESResult): boolean {
  return result.dimensions.fair.passed &&
         result.dimensions.appropriate.passed &&
         result.dimensions.valid.passed &&
         result.dimensions.effective.passed &&
         result.dimensions.safe.passed;
}
