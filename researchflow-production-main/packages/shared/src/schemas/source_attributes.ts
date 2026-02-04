/**
 * HTI-1 Source Attributes Schema
 * Structured attributes for Predictive DSI (Decision Support Intervention)
 *
 * @module packages/shared/src/schemas/source_attributes
 * @version 1.0.0
 */

import { z } from 'zod';

// DSI Status
export const DSIStatusSchema = z.enum(['DRAFT', 'VALIDATED', 'APPROVED', 'DEPRECATED']);

// HTI-1 Required Attribute Keys
export const HTI1AttributeKeySchema = z.enum([
  'intended_use',
  'input_features',
  'output_format',
  'training_data_summary',
  'validation_summary',
  'performance_overall',
  'performance_stratified',
  'known_limitations',
  'safety_controls',
  'update_policy',
]);

// Predictive DSI Schema
export const PredictiveDSISchema = z.object({
  id: z.string().uuid(),
  name: z.string().min(1).max(255),
  description: z.string(),
  model_id: z.string().uuid().optional(),
  status: DSIStatusSchema,
  created_at: z.string().datetime(),
  updated_at: z.string().datetime(),
  created_by: z.string(),
  approved_by: z.string().optional(),
  approved_at: z.string().datetime().optional(),
});

// Source Attribute Value (JSONB flexible structure)
export const SourceAttributeValueSchema = z.union([
  z.string(),
  z.number(),
  z.boolean(),
  z.array(z.unknown()),
  z.record(z.unknown()),
]);

// Individual Source Attribute
export const SourceAttributeSchema = z.object({
  id: z.string().uuid(),
  dsi_id: z.string().uuid(),
  attribute_key: HTI1AttributeKeySchema,
  attribute_value: SourceAttributeValueSchema,
  is_missing: z.boolean().default(false),
  plain_language_description: z.string(),
  schema_version: z.string().default('1.0.0'),
  created_at: z.string().datetime(),
  updated_at: z.string().datetime(),
});

// Source Attribute Audit Entry
export const SourceAttributeAuditSchema = z.object({
  id: z.string().uuid(),
  source_attribute_id: z.string().uuid(),
  changed_by: z.string(),
  changed_at: z.string().datetime(),
  old_value: SourceAttributeValueSchema.nullable(),
  new_value: SourceAttributeValueSchema,
  change_reason: z.string().min(10),
  approved_by: z.string().optional(),
});

// Bulk Source Attributes Update Request
export const SourceAttributesUpdateSchema = z.object({
  dsi_id: z.string().uuid(),
  attributes: z.array(z.object({
    attribute_key: HTI1AttributeKeySchema,
    attribute_value: SourceAttributeValueSchema,
    plain_language_description: z.string(),
  })),
  change_reason: z.string().min(10),
});

// Plain Language Rendering Response
export const PlainLanguageResponseSchema = z.object({
  dsi_id: z.string().uuid(),
  dsi_name: z.string(),
  generated_at: z.string().datetime(),
  sections: z.array(z.object({
    title: z.string(),
    attribute_key: HTI1AttributeKeySchema,
    content: z.string(),
    is_missing: z.boolean(),
  })),
  completeness_score: z.number().min(0).max(100),
  missing_attributes: z.array(HTI1AttributeKeySchema),
});

// Specific HTI-1 Attribute Value Schemas
export const IntendedUseValueSchema = z.object({
  summary: z.string().min(50),
  target_population: z.string(),
  clinical_context: z.string(),
  decision_points: z.array(z.string()),
  out_of_scope: z.array(z.string()),
});

export const InputFeaturesValueSchema = z.array(z.object({
  name: z.string(),
  source: z.string(),
  data_type: z.string(),
  timeframe: z.string().optional(),
  required: z.boolean(),
}));

export const OutputFormatValueSchema = z.object({
  prediction_type: z.string(),
  range: z.object({ min: z.number(), max: z.number() }).optional(),
  thresholds: z.array(z.object({
    value: z.number(),
    label: z.string(),
    clinical_action: z.string(),
  })).optional(),
  confidence_included: z.boolean(),
});

export const PerformanceOverallValueSchema = z.object({
  primary_metric: z.string(),
  primary_value: z.number(),
  confidence_interval: z.object({ lower: z.number(), upper: z.number() }).optional(),
  additional_metrics: z.record(z.number()).optional(),
  validation_cohort_size: z.number(),
});

export const PerformanceStratifiedValueSchema = z.array(z.object({
  stratum: z.string(),
  subgroup: z.string(),
  metrics: z.record(z.number()),
  sample_size: z.number(),
}));

// Export types
export type DSIStatus = z.infer<typeof DSIStatusSchema>;
export type HTI1AttributeKey = z.infer<typeof HTI1AttributeKeySchema>;
export type PredictiveDSI = z.infer<typeof PredictiveDSISchema>;
export type SourceAttributeValue = z.infer<typeof SourceAttributeValueSchema>;
export type SourceAttribute = z.infer<typeof SourceAttributeSchema>;
export type SourceAttributeAudit = z.infer<typeof SourceAttributeAuditSchema>;
export type SourceAttributesUpdate = z.infer<typeof SourceAttributesUpdateSchema>;
export type PlainLanguageResponse = z.infer<typeof PlainLanguageResponseSchema>;
export type IntendedUseValue = z.infer<typeof IntendedUseValueSchema>;
export type InputFeaturesValue = z.infer<typeof InputFeaturesValueSchema>;
export type OutputFormatValue = z.infer<typeof OutputFormatValueSchema>;
export type PerformanceOverallValue = z.infer<typeof PerformanceOverallValueSchema>;
export type PerformanceStratifiedValue = z.infer<typeof PerformanceStratifiedValueSchema>;

// Validation helpers
export function validateSourceAttribute(data: unknown): SourceAttribute {
  return SourceAttributeSchema.parse(data);
}

export function validateSourceAttributesUpdate(data: unknown): SourceAttributesUpdate {
  return SourceAttributesUpdateSchema.parse(data);
}

// HTI-1 Attribute Descriptions (for UI/documentation)
export const HTI1_ATTRIBUTE_DESCRIPTIONS: Record<HTI1AttributeKey, string> = {
  intended_use: 'Plain-language description of what the DSI is designed to do',
  input_features: 'Data elements used by the algorithm with sources and timeframes',
  output_format: 'Prediction type, thresholds, confidence intervals',
  training_data_summary: 'Source, timeframe, inclusion/exclusion, demographic breakdown',
  validation_summary: 'Internal/external validation sites, time periods, cohort sizes',
  performance_overall: 'Primary metrics (AUC, sensitivity, specificity, calibration)',
  performance_stratified: 'Metrics by sex, race, age, site, other relevant strata',
  known_limitations: 'Failure modes, edge cases, populations where performance degrades',
  safety_controls: 'Human oversight requirements, guardrails, rollback procedures',
  update_policy: 'Frequency of retraining, drift monitoring, version control',
};
