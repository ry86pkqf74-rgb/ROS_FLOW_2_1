-- Migration: Stage 7 Statistical Analysis Tables
-- Purpose: Store detailed statistical analysis results, assumptions, and visualizations
-- Date: 2024-02-03

-- ============================================================================
-- STATISTICAL ANALYSIS RESULTS
-- ============================================================================
CREATE TABLE IF NOT EXISTS statistical_analysis_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stage_output_id UUID NOT NULL REFERENCES stage_outputs(id) ON DELETE CASCADE,
    manifest_id UUID NOT NULL REFERENCES project_manifests(id) ON DELETE CASCADE,
    research_id VARCHAR(255),
    
    -- Analysis metadata
    analysis_name VARCHAR(255) NOT NULL,
    test_type VARCHAR(100) NOT NULL, -- 't_test_independent', 'anova_one_way', etc.
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    
    -- Input configuration
    dependent_variable VARCHAR(255),
    independent_variables JSONB DEFAULT '[]',
    covariates JSONB DEFAULT '[]',
    grouping_variable VARCHAR(255),
    confidence_level DECIMAL(3,2) DEFAULT 0.95,
    alpha_level DECIMAL(3,2) DEFAULT 0.05,
    hypothesis_type VARCHAR(20) DEFAULT 'two_tailed',
    
    -- Execution details
    execution_started_at TIMESTAMPTZ,
    execution_completed_at TIMESTAMPTZ,
    execution_time_ms INTEGER,
    error_message TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT valid_confidence CHECK (confidence_level > 0 AND confidence_level < 1),
    CONSTRAINT valid_alpha CHECK (alpha_level > 0 AND alpha_level < 1)
);

-- ============================================================================
-- DESCRIPTIVE STATISTICS
-- ============================================================================
CREATE TABLE IF NOT EXISTS descriptive_statistics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_id UUID NOT NULL REFERENCES statistical_analysis_results(id) ON DELETE CASCADE,
    
    -- Variable information
    variable_name VARCHAR(255) NOT NULL,
    group_name VARCHAR(255),
    
    -- Sample statistics
    n INTEGER NOT NULL,
    missing_count INTEGER DEFAULT 0,
    
    -- Central tendency
    mean DECIMAL,
    median DECIMAL,
    mode DECIMAL,
    
    -- Dispersion
    std_dev DECIMAL,
    variance DECIMAL,
    std_error DECIMAL,
    min_value DECIMAL,
    max_value DECIMAL,
    range DECIMAL,
    
    -- Quartiles
    q1 DECIMAL,
    q2 DECIMAL,
    q3 DECIMAL,
    iqr DECIMAL,
    
    -- Shape
    skewness DECIMAL,
    kurtosis DECIMAL,
    
    -- Distribution type
    distribution_type VARCHAR(50), -- 'normal', 'skewed', 'bimodal', etc.
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- HYPOTHESIS TEST RESULTS
-- ============================================================================
CREATE TABLE IF NOT EXISTS hypothesis_test_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_id UUID NOT NULL REFERENCES statistical_analysis_results(id) ON DELETE CASCADE,
    
    -- Test identification
    test_name VARCHAR(255) NOT NULL,
    test_type VARCHAR(100) NOT NULL,
    
    -- Test statistics
    test_statistic DECIMAL,
    statistic_name VARCHAR(50), -- 't', 'F', 'chi-square', 'U', etc.
    p_value DECIMAL NOT NULL,
    degrees_of_freedom JSONB, -- Can be single number or array [df1, df2]
    
    -- Confidence interval
    ci_lower DECIMAL,
    ci_upper DECIMAL,
    ci_level DECIMAL(3,2),
    
    -- Decision
    is_significant BOOLEAN,
    alpha_level DECIMAL(3,2),
    
    -- Interpretation
    interpretation TEXT,
    direction VARCHAR(20), -- 'two_sided', 'greater', 'less'
    
    -- APA formatted result
    apa_format TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- EFFECT SIZES
-- ============================================================================
CREATE TABLE IF NOT EXISTS effect_sizes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_id UUID NOT NULL REFERENCES statistical_analysis_results(id) ON DELETE CASCADE,
    test_result_id UUID REFERENCES hypothesis_test_results(id) ON DELETE CASCADE,
    
    -- Effect size metrics
    cohens_d DECIMAL,
    hedges_g DECIMAL,
    glass_delta DECIMAL,
    eta_squared DECIMAL,
    partial_eta_squared DECIMAL,
    omega_squared DECIMAL,
    epsilon_squared DECIMAL,
    cramers_v DECIMAL,
    phi DECIMAL,
    odds_ratio DECIMAL,
    relative_risk DECIMAL,
    
    -- Interpretation
    magnitude VARCHAR(50), -- 'negligible', 'small', 'medium', 'large'
    interpretation TEXT,
    
    -- Confidence intervals for effect sizes
    ci_lower DECIMAL,
    ci_upper DECIMAL,
    ci_level DECIMAL(3,2),
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- ASSUMPTION CHECKS
-- ============================================================================
CREATE TABLE IF NOT EXISTS assumption_checks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_id UUID NOT NULL REFERENCES statistical_analysis_results(id) ON DELETE CASCADE,
    
    -- Assumption details
    assumption_name VARCHAR(100) NOT NULL,
    assumption_type VARCHAR(50) NOT NULL, -- 'normality', 'homogeneity', 'independence', etc.
    description TEXT,
    
    -- Test information
    test_name VARCHAR(100),
    test_statistic DECIMAL,
    p_value DECIMAL,
    threshold DECIMAL,
    
    -- Status
    status VARCHAR(20) NOT NULL, -- 'not_checked', 'passed', 'violated', 'warning'
    passed BOOLEAN,
    
    -- Feedback
    warning_message TEXT,
    remediation_suggestion TEXT,
    alternative_tests JSONB DEFAULT '[]',
    
    -- Visual diagnostics metadata
    diagnostic_plots JSONB, -- References to Q-Q plots, histograms, etc.
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- VISUALIZATION SPECIFICATIONS
-- ============================================================================
CREATE TABLE IF NOT EXISTS statistical_visualizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_id UUID NOT NULL REFERENCES statistical_analysis_results(id) ON DELETE CASCADE,
    
    -- Visualization metadata
    viz_type VARCHAR(50) NOT NULL, -- 'boxplot', 'histogram', 'qq_plot', 'scatter', etc.
    title VARCHAR(255),
    caption TEXT,
    
    -- Axis labels
    x_label VARCHAR(255),
    y_label VARCHAR(255),
    
    -- Data specification (JSON structure for frontend rendering)
    data_spec JSONB NOT NULL,
    
    -- Layout configuration
    layout_config JSONB,
    
    -- Ordering
    display_order INTEGER DEFAULT 0,
    
    -- Association
    assumption_check_id UUID REFERENCES assumption_checks(id) ON DELETE SET NULL,
    test_result_id UUID REFERENCES hypothesis_test_results(id) ON DELETE SET NULL,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- POST-HOC TEST RESULTS
-- ============================================================================
CREATE TABLE IF NOT EXISTS posthoc_test_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_id UUID NOT NULL REFERENCES statistical_analysis_results(id) ON DELETE CASCADE,
    primary_test_id UUID REFERENCES hypothesis_test_results(id) ON DELETE CASCADE,
    
    -- Comparison details
    test_name VARCHAR(100) NOT NULL, -- 'Tukey HSD', 'Bonferroni', 'Dunn', etc.
    group_a VARCHAR(255) NOT NULL,
    group_b VARCHAR(255) NOT NULL,
    
    -- Results
    test_statistic DECIMAL,
    p_value DECIMAL NOT NULL,
    adjusted_p_value DECIMAL,
    mean_difference DECIMAL,
    ci_lower DECIMAL,
    ci_upper DECIMAL,
    
    -- Decision
    is_significant BOOLEAN,
    
    -- Effect size for this comparison
    cohens_d DECIMAL,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- POWER ANALYSIS RESULTS
-- ============================================================================
CREATE TABLE IF NOT EXISTS power_analysis_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_id UUID NOT NULL REFERENCES statistical_analysis_results(id) ON DELETE CASCADE,
    
    -- Input parameters
    effect_size DECIMAL NOT NULL,
    sample_size INTEGER,
    alpha_level DECIMAL(3,2) NOT NULL,
    
    -- Output
    statistical_power DECIMAL NOT NULL,
    
    -- Calculations
    required_n_for_80_power INTEGER,
    required_n_for_90_power INTEGER,
    minimum_detectable_effect DECIMAL,
    
    -- Context
    power_type VARCHAR(50), -- 'observed', 'a_priori', 'sensitivity'
    notes TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT valid_power CHECK (statistical_power >= 0 AND statistical_power <= 1)
);

-- ============================================================================
-- SUMMARY TABLES (APA format)
-- ============================================================================
CREATE TABLE IF NOT EXISTS statistical_summary_tables (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_id UUID NOT NULL REFERENCES statistical_analysis_results(id) ON DELETE CASCADE,
    
    -- Table metadata
    table_type VARCHAR(50) NOT NULL, -- 'descriptive', 'inferential', 'correlation_matrix', etc.
    title VARCHAR(255) NOT NULL,
    caption TEXT,
    
    -- Table content (APA formatted)
    html_content TEXT,
    latex_content TEXT,
    markdown_content TEXT,
    json_data JSONB,
    
    -- Ordering
    display_order INTEGER DEFAULT 0,
    
    -- Notes and footnotes
    footnotes JSONB DEFAULT '[]',
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_stat_analysis_stage_output ON statistical_analysis_results(stage_output_id);
CREATE INDEX IF NOT EXISTS idx_stat_analysis_manifest ON statistical_analysis_results(manifest_id);
CREATE INDEX IF NOT EXISTS idx_stat_analysis_research ON statistical_analysis_results(research_id);
CREATE INDEX IF NOT EXISTS idx_stat_analysis_test_type ON statistical_analysis_results(test_type);
CREATE INDEX IF NOT EXISTS idx_stat_analysis_status ON statistical_analysis_results(status);

CREATE INDEX IF NOT EXISTS idx_descriptive_analysis ON descriptive_statistics(analysis_id);
CREATE INDEX IF NOT EXISTS idx_descriptive_variable ON descriptive_statistics(variable_name);
CREATE INDEX IF NOT EXISTS idx_descriptive_group ON descriptive_statistics(group_name);

CREATE INDEX IF NOT EXISTS idx_hypothesis_analysis ON hypothesis_test_results(analysis_id);
CREATE INDEX IF NOT EXISTS idx_hypothesis_test_type ON hypothesis_test_results(test_type);
CREATE INDEX IF NOT EXISTS idx_hypothesis_significant ON hypothesis_test_results(is_significant);

CREATE INDEX IF NOT EXISTS idx_effect_analysis ON effect_sizes(analysis_id);
CREATE INDEX IF NOT EXISTS idx_effect_test ON effect_sizes(test_result_id);

CREATE INDEX IF NOT EXISTS idx_assumption_analysis ON assumption_checks(analysis_id);
CREATE INDEX IF NOT EXISTS idx_assumption_type ON assumption_checks(assumption_type);
CREATE INDEX IF NOT EXISTS idx_assumption_status ON assumption_checks(status);

CREATE INDEX IF NOT EXISTS idx_viz_analysis ON statistical_visualizations(analysis_id);
CREATE INDEX IF NOT EXISTS idx_viz_type ON statistical_visualizations(viz_type);

CREATE INDEX IF NOT EXISTS idx_posthoc_analysis ON posthoc_test_results(analysis_id);
CREATE INDEX IF NOT EXISTS idx_posthoc_primary ON posthoc_test_results(primary_test_id);

CREATE INDEX IF NOT EXISTS idx_power_analysis ON power_analysis_results(analysis_id);

CREATE INDEX IF NOT EXISTS idx_summary_analysis ON statistical_summary_tables(analysis_id);
CREATE INDEX IF NOT EXISTS idx_summary_type ON statistical_summary_tables(table_type);

-- ============================================================================
-- FUNCTIONS: Get complete analysis results
-- ============================================================================
CREATE OR REPLACE FUNCTION get_complete_statistical_analysis(p_analysis_id UUID)
RETURNS JSONB AS $$
DECLARE
    result JSONB;
    analysis_record RECORD;
BEGIN
    -- Get main analysis record
    SELECT * INTO analysis_record
    FROM statistical_analysis_results
    WHERE id = p_analysis_id;
    
    IF NOT FOUND THEN
        RETURN NULL;
    END IF;
    
    -- Build complete result object
    result := jsonb_build_object(
        'id', analysis_record.id,
        'analysis_name', analysis_record.analysis_name,
        'test_type', analysis_record.test_type,
        'status', analysis_record.status,
        'config', jsonb_build_object(
            'dependent_variable', analysis_record.dependent_variable,
            'independent_variables', analysis_record.independent_variables,
            'covariates', analysis_record.covariates,
            'confidence_level', analysis_record.confidence_level
        ),
        'descriptive_stats', (
            SELECT jsonb_agg(row_to_json(d))
            FROM descriptive_statistics d
            WHERE d.analysis_id = p_analysis_id
        ),
        'hypothesis_tests', (
            SELECT jsonb_agg(row_to_json(h))
            FROM hypothesis_test_results h
            WHERE h.analysis_id = p_analysis_id
        ),
        'effect_sizes', (
            SELECT jsonb_agg(row_to_json(e))
            FROM effect_sizes e
            WHERE e.analysis_id = p_analysis_id
        ),
        'assumptions', (
            SELECT jsonb_agg(row_to_json(a))
            FROM assumption_checks a
            WHERE a.analysis_id = p_analysis_id
        ),
        'visualizations', (
            SELECT jsonb_agg(row_to_json(v))
            FROM statistical_visualizations v
            WHERE v.analysis_id = p_analysis_id
            ORDER BY v.display_order
        ),
        'posthoc_tests', (
            SELECT jsonb_agg(row_to_json(p))
            FROM posthoc_test_results p
            WHERE p.analysis_id = p_analysis_id
        ),
        'power_analysis', (
            SELECT row_to_json(pa)
            FROM power_analysis_results pa
            WHERE pa.analysis_id = p_analysis_id
            LIMIT 1
        ),
        'summary_tables', (
            SELECT jsonb_agg(row_to_json(st))
            FROM statistical_summary_tables st
            WHERE st.analysis_id = p_analysis_id
            ORDER BY st.display_order
        ),
        'execution_time_ms', analysis_record.execution_time_ms,
        'created_at', analysis_record.created_at
    );
    
    RETURN result;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- TRIGGER: Auto-update timestamp
-- ============================================================================
CREATE OR REPLACE FUNCTION update_statistical_analysis_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_stat_analysis_timestamp ON statistical_analysis_results;
CREATE TRIGGER trigger_stat_analysis_timestamp
    BEFORE UPDATE ON statistical_analysis_results
    FOR EACH ROW
    EXECUTE FUNCTION update_statistical_analysis_timestamp();

-- ============================================================================
-- COMMENTS FOR DOCUMENTATION
-- ============================================================================
COMMENT ON TABLE statistical_analysis_results IS 'Main table for statistical analysis results from Stage 7';
COMMENT ON TABLE descriptive_statistics IS 'Descriptive statistics (mean, SD, etc.) for each variable and group';
COMMENT ON TABLE hypothesis_test_results IS 'Results from hypothesis tests (t-tests, ANOVA, chi-square, etc.)';
COMMENT ON TABLE effect_sizes IS 'Effect size calculations with interpretations';
COMMENT ON TABLE assumption_checks IS 'Statistical assumption checks with pass/fail status and remediation';
COMMENT ON TABLE statistical_visualizations IS 'Visualization specifications for frontend rendering';
COMMENT ON TABLE posthoc_test_results IS 'Post-hoc pairwise comparison results';
COMMENT ON TABLE power_analysis_results IS 'Statistical power calculations';
COMMENT ON TABLE statistical_summary_tables IS 'APA-formatted summary tables';
COMMENT ON FUNCTION get_complete_statistical_analysis IS 'Returns complete statistical analysis with all related data';
