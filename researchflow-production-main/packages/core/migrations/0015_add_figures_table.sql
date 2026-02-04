-- Migration: Add figures table for data visualization
-- Created: 2025-01-30
-- Purpose: Store generated charts and figures from DataVisualizationAgent

CREATE TABLE IF NOT EXISTS figures (
  id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid(),
  research_id VARCHAR NOT NULL,
  artifact_id VARCHAR REFERENCES artifacts(id) ON DELETE CASCADE,
  
  -- Chart metadata
  figure_type VARCHAR(50) NOT NULL, -- bar_chart, line_chart, scatter_plot, etc.
  title TEXT,
  caption TEXT,
  alt_text TEXT,
  
  -- Image data
  image_data BYTEA NOT NULL, -- PNG/SVG/PDF binary data
  image_format VARCHAR(10) DEFAULT 'png' NOT NULL,
  size_bytes INTEGER NOT NULL,
  width INTEGER,
  height INTEGER,
  dpi INTEGER DEFAULT 300,
  
  -- Configuration used
  chart_config JSONB DEFAULT '{}' NOT NULL,
  journal_style VARCHAR(50),
  color_palette VARCHAR(50),
  
  -- Source data reference (not the actual data, just metadata)
  source_data_ref VARCHAR, -- Reference to dataset or analysis output
  source_data_hash VARCHAR(64), -- SHA-256 hash for reproducibility
  
  -- Generation metadata
  generated_by VARCHAR NOT NULL,
  generation_duration_ms INTEGER,
  agent_version VARCHAR(20) DEFAULT '1.0.0',
  
  -- PHI safety
  phi_scan_status VARCHAR(20) DEFAULT 'PENDING',
  phi_risk_level VARCHAR(20),
  phi_findings JSONB DEFAULT '[]' NOT NULL,
  
  -- Audit
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
  deleted_at TIMESTAMP,
  
  -- Metadata
  metadata JSONB DEFAULT '{}' NOT NULL
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_figures_research_id ON figures(research_id);
CREATE INDEX IF NOT EXISTS idx_figures_artifact_id ON figures(artifact_id);
CREATE INDEX IF NOT EXISTS idx_figures_figure_type ON figures(figure_type);
CREATE INDEX IF NOT EXISTS idx_figures_created_at ON figures(created_at);
CREATE INDEX IF NOT EXISTS idx_figures_generated_by ON figures(generated_by);

-- Comments
COMMENT ON TABLE figures IS 'Generated data visualizations and charts';
COMMENT ON COLUMN figures.figure_type IS 'Type of visualization: bar_chart, line_chart, scatter_plot, box_plot, kaplan_meier, forest_plot, flowchart';
COMMENT ON COLUMN figures.image_data IS 'Binary image data (PNG, SVG, PDF)';
COMMENT ON COLUMN figures.chart_config IS 'Configuration used to generate the chart';
COMMENT ON COLUMN figures.source_data_hash IS 'SHA-256 hash of source data for reproducibility verification';
COMMENT ON COLUMN figures.phi_scan_status IS 'PHI scan status: PASS, FAIL, PENDING, OVERRIDE';
