-- Migration: 015_transparency_compliance.sql
-- Description: Transparency & Compliance tables for Phases 8-14
-- Created: January 30, 2026
-- Covers: Evidence Bundles, HTI-1 Source Attributes, FAVES, Audit v2

-- ============================================================================
-- PHASE 8: Evidence Bundle System
-- ============================================================================

-- Model Registry: Track all registered AI models
CREATE TABLE IF NOT EXISTS model_registry (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    version VARCHAR(50) NOT NULL,
    semantic_version VARCHAR(20) NOT NULL, -- e.g., "1.2.3"
    framework VARCHAR(50) NOT NULL CHECK (framework IN ('PYTORCH', 'TENSORFLOW', 'SKLEARN', 'XGB', 'LIGHTGBM', 'CUSTOM')),
    git_commit_sha VARCHAR(40),
    container_digest VARCHAR(255),
    intended_use TEXT NOT NULL,
    contraindications TEXT[],
    status VARCHAR(20) DEFAULT 'DRAFT' CHECK (status IN ('DRAFT', 'VALIDATED', 'APPROVED', 'DEPRECATED', 'ARCHIVED')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID REFERENCES users(id),
    approved_by UUID REFERENCES users(id),
    approved_at TIMESTAMPTZ,
    UNIQUE(name, version)
);

-- Evidence Bundles: Transparency artifacts per model version
CREATE TABLE IF NOT EXISTS evidence_bundles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_id UUID NOT NULL REFERENCES model_registry(id) ON DELETE CASCADE,
    bundle_json JSONB NOT NULL,
    bundle_markdown TEXT,
    bundle_pdf_path VARCHAR(500),
    schema_version VARCHAR(20) DEFAULT '1.0.0',
    generated_at TIMESTAMPTZ DEFAULT NOW(),
    generated_by VARCHAR(100) NOT NULL, -- 'system' or user email
    sbom_reference VARCHAR(500),
    UNIQUE(model_id, schema_version)
);

-- Performance Metrics: Granular metrics per model
CREATE TABLE IF NOT EXISTS performance_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_id UUID NOT NULL REFERENCES model_registry(id) ON DELETE CASCADE,
    metric_type VARCHAR(50) NOT NULL CHECK (metric_type IN ('AUC', 'SENSITIVITY', 'SPECIFICITY', 'PPV', 'NPV', 'CALIBRATION', 'BRIER_SCORE', 'F1', 'ACCURACY')),
    overall_value DECIMAL(10, 6) NOT NULL,
    confidence_interval_lower DECIMAL(10, 6),
    confidence_interval_upper DECIMAL(10, 6),
    validation_cohort VARCHAR(255) NOT NULL,
    sample_size INTEGER NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Stratified Metrics: Demographics breakdown
CREATE TABLE IF NOT EXISTS stratified_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_id UUID NOT NULL REFERENCES model_registry(id) ON DELETE CASCADE,
    stratum_type VARCHAR(50) NOT NULL CHECK (stratum_type IN ('SEX', 'RACE', 'AGE_GROUP', 'SITE', 'COMORBIDITY', 'CUSTOM')),
    stratum_value VARCHAR(100) NOT NULL,
    metric_type VARCHAR(50) NOT NULL,
    value DECIMAL(10, 6) NOT NULL,
    sample_size INTEGER NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- PHASE 9: HTI-1 Source Attributes
-- ============================================================================

-- Predictive DSI: Decision Support Intervention registry
CREATE TABLE IF NOT EXISTS predictive_dsi (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    model_id UUID REFERENCES model_registry(id),
    status VARCHAR(20) DEFAULT 'DRAFT' CHECK (status IN ('DRAFT', 'VALIDATED', 'APPROVED', 'DEPRECATED')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID REFERENCES users(id),
    approved_by UUID REFERENCES users(id),
    approved_at TIMESTAMPTZ
);

-- Source Attributes: HTI-1 required attributes
CREATE TABLE IF NOT EXISTS source_attributes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dsi_id UUID NOT NULL REFERENCES predictive_dsi(id) ON DELETE CASCADE,
    attribute_key VARCHAR(50) NOT NULL CHECK (attribute_key IN (
        'intended_use', 'input_features', 'output_format',
        'training_data_summary', 'validation_summary',
        'performance_overall', 'performance_stratified',
        'known_limitations', 'safety_controls', 'update_policy'
    )),
    attribute_value JSONB NOT NULL,
    is_missing BOOLEAN DEFAULT FALSE,
    plain_language_description TEXT NOT NULL,
    schema_version VARCHAR(20) DEFAULT '1.0.0',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(dsi_id, attribute_key)
);

-- Source Attributes Audit: Change tracking for STEWARD compliance
CREATE TABLE IF NOT EXISTS source_attributes_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_attribute_id UUID NOT NULL REFERENCES source_attributes(id) ON DELETE CASCADE,
    changed_by UUID NOT NULL REFERENCES users(id),
    changed_at TIMESTAMPTZ DEFAULT NOW(),
    old_value JSONB,
    new_value JSONB NOT NULL,
    change_reason TEXT NOT NULL CHECK (char_length(change_reason) >= 10),
    approved_by UUID REFERENCES users(id)
);

-- ============================================================================
-- PHASE 10: FAVES Compliance
-- ============================================================================

-- FAVES Evaluations: Store evaluation results
CREATE TABLE IF NOT EXISTS faves_evaluations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_id UUID NOT NULL REFERENCES model_registry(id) ON DELETE CASCADE,
    model_version VARCHAR(50) NOT NULL,
    evaluated_at TIMESTAMPTZ DEFAULT NOW(),
    evaluated_by VARCHAR(100) NOT NULL,
    overall_status VARCHAR(20) CHECK (overall_status IN ('PASS', 'FAIL', 'PARTIAL', 'NOT_EVALUATED')),
    overall_score DECIMAL(5, 2),
    deployment_allowed BOOLEAN DEFAULT FALSE,

    -- Dimension scores
    fair_score DECIMAL(5, 2),
    fair_passed BOOLEAN,
    appropriate_score DECIMAL(5, 2),
    appropriate_passed BOOLEAN,
    valid_score DECIMAL(5, 2),
    valid_passed BOOLEAN,
    effective_score DECIMAL(5, 2),
    effective_passed BOOLEAN,
    safe_score DECIMAL(5, 2),
    safe_passed BOOLEAN,

    -- Details
    result_json JSONB NOT NULL,
    blocking_issues TEXT[],
    ci_run_id VARCHAR(100),
    git_commit_sha VARCHAR(40),
    schema_version VARCHAR(20) DEFAULT '1.0.0'
);

-- FAVES Artifacts: Track required documentation
CREATE TABLE IF NOT EXISTS faves_artifacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_id UUID NOT NULL REFERENCES model_registry(id) ON DELETE CASCADE,
    dimension VARCHAR(20) NOT NULL CHECK (dimension IN ('FAIR', 'APPROPRIATE', 'VALID', 'EFFECTIVE', 'SAFE')),
    artifact_name VARCHAR(255) NOT NULL,
    artifact_path VARCHAR(500),
    is_required BOOLEAN DEFAULT TRUE,
    exists_flag BOOLEAN DEFAULT FALSE,
    last_modified TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(model_id, dimension, artifact_name)
);

-- ============================================================================
-- PHASE 11: Reporting Checklists
-- ============================================================================

-- Checklist Templates: TRIPOD+AI, CONSORT-AI, etc.
CREATE TABLE IF NOT EXISTS checklist_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    checklist_type VARCHAR(50) NOT NULL CHECK (checklist_type IN ('TRIPOD_AI', 'CONSORT_AI', 'CUSTOM')),
    schema_version VARCHAR(20) DEFAULT '1.0.0',
    items_json JSONB NOT NULL, -- Array of checklist items
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Checklist Submissions: Completed checklists per model
CREATE TABLE IF NOT EXISTS checklist_submissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_id UUID NOT NULL REFERENCES model_registry(id) ON DELETE CASCADE,
    template_id UUID NOT NULL REFERENCES checklist_templates(id),
    submitted_by UUID REFERENCES users(id),
    submitted_at TIMESTAMPTZ DEFAULT NOW(),
    status VARCHAR(20) DEFAULT 'DRAFT' CHECK (status IN ('DRAFT', 'SUBMITTED', 'APPROVED', 'REJECTED')),
    completion_percentage DECIMAL(5, 2),
    items_json JSONB NOT NULL, -- Completed items with status
    reviewer_notes TEXT,
    approved_by UUID REFERENCES users(id),
    approved_at TIMESTAMPTZ
);

-- ============================================================================
-- PHASE 13: Enhanced Audit Logging (v2)
-- ============================================================================

-- Audit Events v2: Regulatory-grade logging
CREATE TABLE IF NOT EXISTS audit_events_v2 (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id UUID NOT NULL, -- Correlation ID
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    event_type VARCHAR(50) NOT NULL CHECK (event_type IN (
        'MODEL_INFERENCE', 'MODEL_REGISTRATION', 'MODEL_DEPLOYMENT', 'MODEL_ROLLBACK',
        'DATA_ACCESS', 'DATA_EXPORT', 'CONFIG_CHANGE', 'USER_ACTION', 'SYSTEM_EVENT',
        'APPROVAL_REQUEST', 'APPROVAL_GRANTED', 'APPROVAL_DENIED',
        'PHI_DETECTED', 'DRIFT_ALERT', 'SAFETY_EVENT'
    )),

    -- Actor
    actor_user_id UUID REFERENCES users(id),
    actor_service_account VARCHAR(100),
    actor_system_component VARCHAR(100),
    actor_role VARCHAR(50),
    actor_ip_address INET,

    -- Scope
    organization_id UUID,
    project_id UUID,
    governance_mode VARCHAR(10) CHECK (governance_mode IN ('DEMO', 'LIVE')),

    -- Model context
    model_id UUID REFERENCES model_registry(id),
    model_version VARCHAR(50),
    model_tier VARCHAR(20) CHECK (model_tier IN ('NANO', 'MINI', 'STANDARD', 'FRONTIER')),

    -- Prompt/Template (reference only)
    prompt_template_id UUID,
    prompt_version VARCHAR(20),

    -- Input/Output hashing (reproducibility without PHI)
    input_hash VARCHAR(64), -- SHA-256
    output_hash VARCHAR(64),
    input_token_count INTEGER,
    output_token_count INTEGER,

    -- PHI scanning
    phi_scan_result VARCHAR(20) CHECK (phi_scan_result IN ('PASS', 'FAIL', 'SKIPPED', 'ERROR')),
    phi_scan_rule_version VARCHAR(20),
    phi_categories_detected TEXT[],

    -- Artifacts
    artifact_ids UUID[],

    -- Action details
    action VARCHAR(255) NOT NULL,
    action_details JSONB,
    outcome VARCHAR(20) CHECK (outcome IN ('SUCCESS', 'FAILURE', 'PARTIAL', 'PENDING')),
    error_message TEXT,
    latency_ms INTEGER,

    -- Hash chain (tamper-evident)
    previous_event_hash VARCHAR(64),
    sequence_number BIGINT,
    chain_id UUID,
    event_hash VARCHAR(64),

    -- Metadata
    schema_version VARCHAR(20) DEFAULT '2.0.0',
    source_service VARCHAR(100) NOT NULL,
    environment VARCHAR(20) CHECK (environment IN ('development', 'staging', 'production'))
);

-- Audit Approvals: Linked approval events
CREATE TABLE IF NOT EXISTS audit_approvals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    audit_event_id UUID NOT NULL REFERENCES audit_events_v2(id) ON DELETE CASCADE,
    approved_by UUID NOT NULL REFERENCES users(id),
    approved_at TIMESTAMPTZ DEFAULT NOW(),
    approval_type VARCHAR(50) CHECK (approval_type IN ('DEPLOYMENT', 'DATA_ACCESS', 'CONFIG_CHANGE', 'OVERRIDE')),
    rationale TEXT NOT NULL CHECK (char_length(rationale) >= 10),
    conditions TEXT[],
    expires_at TIMESTAMPTZ
);

-- Hash Chain Checkpoints: Periodic verification anchors
CREATE TABLE IF NOT EXISTS audit_chain_checkpoints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chain_id UUID NOT NULL,
    checkpoint_sequence BIGINT NOT NULL,
    checkpoint_hash VARCHAR(64) NOT NULL,
    events_count INTEGER NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    external_anchor VARCHAR(500), -- Optional blockchain/external anchor
    UNIQUE(chain_id, checkpoint_sequence)
);

-- ============================================================================
-- PHASE 14: Post-Deployment Monitoring
-- ============================================================================

-- Drift Metrics: Track input/output drift
CREATE TABLE IF NOT EXISTS drift_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_id UUID NOT NULL REFERENCES model_registry(id) ON DELETE CASCADE,
    drift_type VARCHAR(20) NOT NULL CHECK (drift_type IN ('INPUT', 'OUTPUT', 'CONCEPT')),
    feature_name VARCHAR(100),
    metric_name VARCHAR(50) NOT NULL, -- PSI, KL_DIVERGENCE, etc.
    baseline_value DECIMAL(10, 6),
    current_value DECIMAL(10, 6) NOT NULL,
    threshold_warning DECIMAL(10, 6) DEFAULT 0.1,
    threshold_critical DECIMAL(10, 6) DEFAULT 0.25,
    alert_level VARCHAR(20) CHECK (alert_level IN ('NORMAL', 'WARNING', 'CRITICAL')),
    measured_at TIMESTAMPTZ DEFAULT NOW(),
    window_start TIMESTAMPTZ,
    window_end TIMESTAMPTZ,
    sample_size INTEGER
);

-- Bias Metrics: Track fairness over time
CREATE TABLE IF NOT EXISTS bias_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_id UUID NOT NULL REFERENCES model_registry(id) ON DELETE CASCADE,
    metric_name VARCHAR(50) NOT NULL, -- demographic_parity_gap, equalized_odds, etc.
    stratum_type VARCHAR(50) NOT NULL,
    stratum_value VARCHAR(100) NOT NULL,
    baseline_value DECIMAL(10, 6),
    current_value DECIMAL(10, 6) NOT NULL,
    tolerance DECIMAL(10, 6) DEFAULT 0.05,
    alert_triggered BOOLEAN DEFAULT FALSE,
    measured_at TIMESTAMPTZ DEFAULT NOW(),
    window_start TIMESTAMPTZ,
    window_end TIMESTAMPTZ,
    sample_size INTEGER
);

-- Safety Events: Incident tracking
CREATE TABLE IF NOT EXISTS safety_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_id UUID NOT NULL REFERENCES model_registry(id),
    event_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('INFO', 'WARNING', 'ERROR', 'CRITICAL')),
    description TEXT NOT NULL,
    details JSONB,
    auto_paused BOOLEAN DEFAULT FALSE,
    linear_ticket_id VARCHAR(50),
    slack_thread_ts VARCHAR(50),
    resolution_status VARCHAR(20) DEFAULT 'OPEN' CHECK (resolution_status IN ('OPEN', 'INVESTIGATING', 'RESOLVED', 'FALSE_POSITIVE')),
    resolved_by UUID REFERENCES users(id),
    resolved_at TIMESTAMPTZ,
    resolution_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- INDEXES
-- ============================================================================

-- Model Registry
CREATE INDEX IF NOT EXISTS idx_model_registry_name ON model_registry(name);
CREATE INDEX IF NOT EXISTS idx_model_registry_status ON model_registry(status);

-- Evidence Bundles
CREATE INDEX IF NOT EXISTS idx_evidence_bundles_model ON evidence_bundles(model_id);

-- Performance Metrics
CREATE INDEX IF NOT EXISTS idx_perf_metrics_model ON performance_metrics(model_id);
CREATE INDEX IF NOT EXISTS idx_perf_metrics_type ON performance_metrics(metric_type);

-- Stratified Metrics
CREATE INDEX IF NOT EXISTS idx_strat_metrics_model ON stratified_metrics(model_id);
CREATE INDEX IF NOT EXISTS idx_strat_metrics_stratum ON stratified_metrics(stratum_type, stratum_value);

-- Source Attributes
CREATE INDEX IF NOT EXISTS idx_source_attrs_dsi ON source_attributes(dsi_id);
CREATE INDEX IF NOT EXISTS idx_source_attrs_key ON source_attributes(attribute_key);

-- FAVES
CREATE INDEX IF NOT EXISTS idx_faves_eval_model ON faves_evaluations(model_id);
CREATE INDEX IF NOT EXISTS idx_faves_artifacts_model ON faves_artifacts(model_id);

-- Checklists
CREATE INDEX IF NOT EXISTS idx_checklist_sub_model ON checklist_submissions(model_id);
CREATE INDEX IF NOT EXISTS idx_checklist_sub_template ON checklist_submissions(template_id);

-- Audit Events v2
CREATE INDEX IF NOT EXISTS idx_audit_v2_request ON audit_events_v2(request_id);
CREATE INDEX IF NOT EXISTS idx_audit_v2_timestamp ON audit_events_v2(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_v2_event_type ON audit_events_v2(event_type);
CREATE INDEX IF NOT EXISTS idx_audit_v2_actor ON audit_events_v2(actor_user_id);
CREATE INDEX IF NOT EXISTS idx_audit_v2_model ON audit_events_v2(model_id);
CREATE INDEX IF NOT EXISTS idx_audit_v2_chain ON audit_events_v2(chain_id, sequence_number);

-- Drift Metrics
CREATE INDEX IF NOT EXISTS idx_drift_model ON drift_metrics(model_id);
CREATE INDEX IF NOT EXISTS idx_drift_measured ON drift_metrics(measured_at);
CREATE INDEX IF NOT EXISTS idx_drift_alert ON drift_metrics(alert_level);

-- Bias Metrics
CREATE INDEX IF NOT EXISTS idx_bias_model ON bias_metrics(model_id);
CREATE INDEX IF NOT EXISTS idx_bias_measured ON bias_metrics(measured_at);

-- Safety Events
CREATE INDEX IF NOT EXISTS idx_safety_model ON safety_events(model_id);
CREATE INDEX IF NOT EXISTS idx_safety_severity ON safety_events(severity);
CREATE INDEX IF NOT EXISTS idx_safety_status ON safety_events(resolution_status);

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Update timestamp trigger for model_registry
CREATE OR REPLACE FUNCTION update_model_registry_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER model_registry_updated
    BEFORE UPDATE ON model_registry
    FOR EACH ROW EXECUTE FUNCTION update_model_registry_timestamp();

-- Update timestamp trigger for source_attributes
CREATE OR REPLACE FUNCTION update_source_attributes_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER source_attributes_updated
    BEFORE UPDATE ON source_attributes
    FOR EACH ROW EXECUTE FUNCTION update_source_attributes_timestamp();

-- Audit trigger for source_attributes changes
CREATE OR REPLACE FUNCTION audit_source_attributes_changes()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'UPDATE' AND OLD.attribute_value IS DISTINCT FROM NEW.attribute_value THEN
        INSERT INTO source_attributes_audit (
            source_attribute_id, changed_by, old_value, new_value, change_reason
        ) VALUES (
            NEW.id,
            COALESCE(current_setting('app.current_user_id', true)::UUID, '00000000-0000-0000-0000-000000000000'::UUID),
            OLD.attribute_value,
            NEW.attribute_value,
            COALESCE(current_setting('app.change_reason', true), 'System update')
        );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER source_attributes_audit_trigger
    AFTER UPDATE ON source_attributes
    FOR EACH ROW EXECUTE FUNCTION audit_source_attributes_changes();

-- ============================================================================
-- SEED DATA: Checklist Templates
-- ============================================================================

-- TRIPOD+AI Checklist Template (27 items based on BMJ 2024)
INSERT INTO checklist_templates (name, description, checklist_type, items_json) VALUES
('TRIPOD+AI v2024', 'Transparent Reporting of a multivariable prediction model for Individual Prognosis Or Diagnosis + AI extension', 'TRIPOD_AI',
'{
  "items": [
    {"id": "T1", "section": "Title", "text": "Identify the study as developing and/or validating a multivariable prediction model, the target population, and outcome", "required": true},
    {"id": "T2", "section": "Abstract", "text": "Provide a summary of objectives, study design, setting, participants, sample size, predictors, outcome, statistical analysis, results, and conclusions", "required": true},
    {"id": "T3a", "section": "Introduction", "text": "Explain the medical context and rationale for developing or validating the prediction model", "required": true},
    {"id": "T3b", "section": "Introduction", "text": "Specify the objectives, including whether the study describes development, validation, or both", "required": true},
    {"id": "T4a", "section": "Methods-Source", "text": "Describe the study design or source of data", "required": true},
    {"id": "T4b", "section": "Methods-Source", "text": "Specify key study dates including start/end of accrual and follow-up", "required": true},
    {"id": "T5a", "section": "Methods-Participants", "text": "Specify key elements of the study setting, locations, and relevant dates", "required": true},
    {"id": "T5b", "section": "Methods-Participants", "text": "Give eligibility criteria for participants", "required": true},
    {"id": "T5c", "section": "Methods-Participants", "text": "Give details of treatments received, if relevant", "required": false},
    {"id": "T6a", "section": "Methods-Outcome", "text": "Clearly define the outcome that is predicted by the model", "required": true},
    {"id": "T6b", "section": "Methods-Outcome", "text": "Report any actions to blind assessment of the outcome to be predicted", "required": true},
    {"id": "T7a", "section": "Methods-Predictors", "text": "Clearly define all candidate predictors used for developing the model", "required": true},
    {"id": "T7b", "section": "Methods-Predictors", "text": "Report any actions to blind assessment of predictors for the outcome or other predictors", "required": false},
    {"id": "T8", "section": "Methods-Sample", "text": "Explain how the study size was determined", "required": true},
    {"id": "T9", "section": "Methods-Missing", "text": "Describe how missing data were handled", "required": true},
    {"id": "T10a", "section": "Methods-Analysis", "text": "Describe how predictors were handled in the analyses", "required": true},
    {"id": "T10b", "section": "Methods-Analysis", "text": "Specify type of model, modeling assumptions, and inference method", "required": true},
    {"id": "T10c", "section": "Methods-Analysis", "text": "Describe any model-building procedures (predictor selection, internal validation)", "required": true},
    {"id": "T10d", "section": "Methods-Analysis", "text": "Specify all measures used to assess model performance", "required": true},
    {"id": "T11", "section": "Methods-AI", "text": "Describe how the AI/ML algorithm was developed, trained, and validated", "required": true},
    {"id": "T12", "section": "Results-Participants", "text": "Describe the flow of participants through the study", "required": true},
    {"id": "T13a", "section": "Results-Descriptive", "text": "Describe characteristics of participants and summary of outcome events", "required": true},
    {"id": "T13b", "section": "Results-Descriptive", "text": "For validation, show comparison with the development data", "required": false},
    {"id": "T14", "section": "Results-Performance", "text": "Report performance measures with confidence intervals", "required": true},
    {"id": "T15", "section": "Discussion-Limitations", "text": "Discuss limitations of the study", "required": true},
    {"id": "T16", "section": "Discussion-Interpretation", "text": "Interpretation of results, considering objectives and other evidence", "required": true},
    {"id": "T17", "section": "Discussion-Implications", "text": "Discuss implications for practice and future research", "required": true}
  ]
}'
) ON CONFLICT (name) DO NOTHING;

-- CONSORT-AI Checklist Template
INSERT INTO checklist_templates (name, description, checklist_type, items_json) VALUES
('CONSORT-AI v2024', 'Consolidated Standards of Reporting Trials - Artificial Intelligence Extension', 'CONSORT_AI',
'{
  "items": [
    {"id": "C1", "section": "Title-Abstract", "text": "Indicate that the intervention involves AI, and specify the type of AI system", "required": true},
    {"id": "C2", "section": "Introduction", "text": "Describe background and rationale for the AI intervention", "required": true},
    {"id": "C3", "section": "Methods-Intervention", "text": "Describe the AI system including inputs, outputs, and intended use", "required": true},
    {"id": "C4", "section": "Methods-Intervention", "text": "Describe how the AI intervention was integrated into clinical workflow", "required": true},
    {"id": "C5", "section": "Methods-Intervention", "text": "Describe human-AI interaction design and how recommendations were delivered", "required": true},
    {"id": "C6", "section": "Methods-Intervention", "text": "Specify the version of the AI system used during the trial", "required": true},
    {"id": "C7", "section": "Methods-Outcomes", "text": "Describe handling of edge cases and out-of-distribution inputs", "required": true},
    {"id": "C8", "section": "Methods-Analysis", "text": "Describe any error analysis performed on AI outputs", "required": true},
    {"id": "C9", "section": "Results", "text": "Report AI system performance metrics during the trial", "required": true},
    {"id": "C10", "section": "Results", "text": "Report adherence to AI recommendations and overrides", "required": true},
    {"id": "C11", "section": "Discussion", "text": "Discuss generalizability of findings given AI system characteristics", "required": true}
  ]
}'
) ON CONFLICT (name) DO NOTHING;
