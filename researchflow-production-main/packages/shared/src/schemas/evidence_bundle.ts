/**
 * Evidence Bundle Schema
 * Transparency artifacts for TRIPOD+AI, HTI-1, and FAVES compliance
 *
 * @module packages/shared/src/schemas/evidence_bundle
 * @version 1.0.0
 */

import { z } from 'zod';

// Performance Metric Schema
export const PerformanceMetricSchema = z.object({
  metric_type: z.enum(['AUC', 'SENSITIVITY', 'SPECIFICITY', 'PPV', 'NPV', 'CALIBRATION', 'BRIER_SCORE']),
  overall_value: z.number().min(0).max(1),
  confidence_interval: z.object({
    lower: z.number(),
    upper: z.number(),
  }).optional(),
  validation_cohort: z.string(),
  sample_size: z.number().int().positive(),
});

// Stratified Metric Schema (by demographic groups)
export const StratifiedMetricSchema = z.object({
  stratum_type: z.enum(['SEX', 'RACE', 'AGE_GROUP', 'SITE', 'COMORBIDITY', 'CUSTOM']),
  stratum_value: z.string(),
  metrics: z.array(PerformanceMetricSchema),
});

// Model Metadata Schema
export const ModelMetadataSchema = z.object({
  model_id: z.string().uuid(),
  name: z.string().min(1),
  version: z.string(),
  semantic_version: z.string().regex(/^\d+\.\d+\.\d+$/),
  git_commit_sha: z.string().length(40).optional(),
  container_digest: z.string().optional(),
  framework: z.enum(['PYTORCH', 'TENSORFLOW', 'SKLEARN', 'XGB', 'LIGHTGBM', 'CUSTOM']),
  created_at: z.string().datetime(),
  updated_at: z.string().datetime(),
});

// Input Specification Schema
export const InputSpecSchema = z.object({
  features: z.array(z.object({
    name: z.string(),
    data_type: z.enum(['NUMERIC', 'CATEGORICAL', 'BOOLEAN', 'TEXT', 'IMAGE', 'TIME_SERIES']),
    source: z.string(),
    timeframe: z.string().optional(),
    required: z.boolean(),
    description: z.string(),
  })),
  preprocessing_steps: z.array(z.string()),
  missing_data_handling: z.string(),
});

// Output Specification Schema
export const OutputSpecSchema = z.object({
  prediction_type: z.enum(['BINARY', 'MULTICLASS', 'REGRESSION', 'PROBABILITY', 'RISK_SCORE']),
  output_range: z.object({
    min: z.number(),
    max: z.number(),
  }).optional(),
  thresholds: z.array(z.object({
    name: z.string(),
    value: z.number(),
    description: z.string(),
  })).optional(),
  confidence_intervals: z.boolean(),
  calibration_method: z.string().optional(),
});

// Training Summary Schema
export const TrainingSummarySchema = z.object({
  data_source: z.string(),
  timeframe: z.object({
    start: z.string().datetime(),
    end: z.string().datetime(),
  }),
  sample_size: z.number().int().positive(),
  inclusion_criteria: z.array(z.string()),
  exclusion_criteria: z.array(z.string()),
  demographic_breakdown: z.record(z.string(), z.number()),
  label_source: z.string(),
  label_timeframe: z.string().optional(),
});

// Validation Summary Schema
export const ValidationSummarySchema = z.object({
  validation_type: z.enum(['INTERNAL', 'EXTERNAL', 'TEMPORAL', 'GEOGRAPHIC']),
  sites: z.array(z.string()),
  timeframe: z.object({
    start: z.string().datetime(),
    end: z.string().datetime(),
  }),
  sample_size: z.number().int().positive(),
  demographic_breakdown: z.record(z.string(), z.number()).optional(),
});

// Limitation Schema
export const LimitationSchema = z.object({
  category: z.enum(['POPULATION', 'DATA_QUALITY', 'TEMPORAL', 'TECHNICAL', 'CLINICAL']),
  description: z.string(),
  severity: z.enum(['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']),
  mitigation: z.string().optional(),
});

// Safety Control Schema
export const SafetyControlSchema = z.object({
  control_type: z.enum(['HUMAN_OVERSIGHT', 'GUARDRAIL', 'THRESHOLD', 'ROLLBACK', 'MONITORING']),
  description: z.string(),
  trigger_condition: z.string().optional(),
  response_action: z.string(),
  responsible_role: z.string(),
});

// Update Policy Schema
export const UpdatePolicySchema = z.object({
  retraining_frequency: z.string(),
  drift_monitoring_enabled: z.boolean(),
  drift_thresholds: z.object({
    warning: z.number(),
    critical: z.number(),
  }).optional(),
  version_control: z.string(),
  rollback_procedure: z.string(),
});

// Complete Evidence Bundle Schema
export const EvidenceBundleSchema = z.object({
  bundle_id: z.string().uuid(),
  schema_version: z.literal('1.0.0'),
  generated_at: z.string().datetime(),
  generated_by: z.string(),

  // Core sections
  model_metadata: ModelMetadataSchema,
  intended_use: z.string().min(100),
  contraindications: z.array(z.string()),

  // Technical specifications
  input_spec: InputSpecSchema,
  output_spec: OutputSpecSchema,

  // Training and validation
  training_summary: TrainingSummarySchema,
  validation_summary: z.array(ValidationSummarySchema),

  // Performance metrics
  performance_metrics: z.array(PerformanceMetricSchema),
  stratified_metrics: z.array(StratifiedMetricSchema),

  // Safety and limitations
  limitations: z.array(LimitationSchema),
  safety_controls: z.array(SafetyControlSchema),
  update_policy: UpdatePolicySchema,

  // SBOM reference
  sbom_reference: z.string().optional(),
});

// Export types
export type PerformanceMetric = z.infer<typeof PerformanceMetricSchema>;
export type StratifiedMetric = z.infer<typeof StratifiedMetricSchema>;
export type ModelMetadata = z.infer<typeof ModelMetadataSchema>;
export type InputSpec = z.infer<typeof InputSpecSchema>;
export type OutputSpec = z.infer<typeof OutputSpecSchema>;
export type TrainingSummary = z.infer<typeof TrainingSummarySchema>;
export type ValidationSummary = z.infer<typeof ValidationSummarySchema>;
export type Limitation = z.infer<typeof LimitationSchema>;
export type SafetyControl = z.infer<typeof SafetyControlSchema>;
export type UpdatePolicy = z.infer<typeof UpdatePolicySchema>;
export type EvidenceBundle = z.infer<typeof EvidenceBundleSchema>;

// Validation helper
export function validateEvidenceBundle(data: unknown): EvidenceBundle {
  return EvidenceBundleSchema.parse(data);
}
