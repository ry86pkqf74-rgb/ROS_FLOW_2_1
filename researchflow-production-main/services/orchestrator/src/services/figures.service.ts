/**
 * Figures Database Service
 * 
 * Handles database operations for generated visualization figures.
 * Implements CRUD operations with PHI scanning and metadata management.
 */

import { Pool } from 'pg';
import { z } from 'zod';

import { createLogger } from '../utils/logger';

const logger = createLogger('figures-service');

// =============================================================================
// Types and Schemas
// =============================================================================

const FigureSchema = z.object({
  id: z.string().optional(),
  research_id: z.string(),
  artifact_id: z.string().optional(),
  figure_type: z.enum([
    'bar_chart',
    'line_chart', 
    'scatter_plot',
    'box_plot',
    'forest_plot',
    'flowchart',
    'kaplan_meier',
  ]),
  title: z.string().optional(),
  caption: z.string().optional(),
  alt_text: z.string().optional(),
  image_data: z.instanceof(Buffer),
  image_format: z.enum(['png', 'svg', 'pdf']).default('png'),
  size_bytes: z.number(),
  width: z.number().optional(),
  height: z.number().optional(),
  dpi: z.number().default(300),
  chart_config: z.record(z.any()).default({}),
  journal_style: z.string().optional(),
  color_palette: z.string().optional(),
  source_data_ref: z.string().optional(),
  source_data_hash: z.string().optional(),
  generated_by: z.string(),
  generation_duration_ms: z.number().optional(),
  agent_version: z.string().default('1.0.0'),
  phi_scan_status: z.enum(['PENDING', 'PASS', 'FAIL', 'OVERRIDE']).default('PENDING'),
  phi_risk_level: z.enum(['SAFE', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL']).optional(),
  phi_findings: z.array(z.any()).default([]),
  metadata: z.record(z.any()).default({}),
});

export type Figure = z.infer<typeof FigureSchema>;

export interface FigureCreateInput {
  research_id: string;
  artifact_id?: string;
  figure_type: Figure['figure_type'];
  title?: string;
  caption?: string;
  alt_text?: string;
  image_data: Buffer;
  image_format?: Figure['image_format'];
  width?: number;
  height?: number;
  dpi?: number;
  chart_config?: Record<string, any>;
  journal_style?: string;
  color_palette?: string;
  source_data_ref?: string;
  source_data_hash?: string;
  generated_by: string;
  generation_duration_ms?: number;
  agent_version?: string;
  metadata?: Record<string, any>;
}

export interface FigureListOptions {
  research_id?: string;
  figure_type?: Figure['figure_type'];
  phi_scan_status?: Figure['phi_scan_status'];
  limit?: number;
  offset?: number;
  include_deleted?: boolean;
}

// =============================================================================
// Service Class
// =============================================================================

export class FiguresService {
  constructor(private pool: Pool) {}

  /**
   * Create a new figure record in the database
   */
  async createFigure(input: FigureCreateInput): Promise<Figure> {
    logger.info('Creating figure', { 
      researchId: input.research_id,
      figureType: input.figure_type,
      sizeBytes: input.image_data.length,
    });

    const validated = FigureSchema.parse({
      ...input,
      size_bytes: input.image_data.length,
    });

    const query = `
      INSERT INTO figures (
        research_id, artifact_id, figure_type, title, caption, alt_text,
        image_data, image_format, size_bytes, width, height, dpi,
        chart_config, journal_style, color_palette, source_data_ref,
        source_data_hash, generated_by, generation_duration_ms, agent_version,
        phi_scan_status, phi_risk_level, phi_findings, metadata
      ) VALUES (
        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15,
        $16, $17, $18, $19, $20, $21, $22, $23, $24
      ) RETURNING *
    `;

    const values = [
      validated.research_id,
      validated.artifact_id,
      validated.figure_type,
      validated.title,
      validated.caption,
      validated.alt_text,
      validated.image_data,
      validated.image_format,
      validated.size_bytes,
      validated.width,
      validated.height,
      validated.dpi,
      JSON.stringify(validated.chart_config),
      validated.journal_style,
      validated.color_palette,
      validated.source_data_ref,
      validated.source_data_hash,
      validated.generated_by,
      validated.generation_duration_ms,
      validated.agent_version,
      validated.phi_scan_status,
      validated.phi_risk_level,
      JSON.stringify(validated.phi_findings),
      JSON.stringify(validated.metadata),
    ];

    try {
      const result = await this.pool.query(query, values);
      const figure = this._parseFigureRow(result.rows[0]);
      
      logger.info('Figure created', { 
        figureId: figure.id,
        researchId: figure.research_id,
      });

      return figure;
    } catch (error) {
      logger.error('Failed to create figure', {
        researchId: input.research_id,
        error: error instanceof Error ? error.message : 'Unknown error',
      });
      throw error;
    }
  }

  /**
   * Get a figure by ID
   */
  async getFigureById(id: string): Promise<Figure | null> {
    const query = `
      SELECT * FROM figures 
      WHERE id = $1 AND deleted_at IS NULL
    `;

    try {
      const result = await this.pool.query(query, [id]);
      return result.rows.length > 0 ? this._parseFigureRow(result.rows[0]) : null;
    } catch (error) {
      logger.error('Failed to get figure by ID', {
        figureId: id,
        error: error instanceof Error ? error.message : 'Unknown error',
      });
      throw error;
    }
  }

  /**
   * List figures with optional filtering
   */
  async listFigures(options: FigureListOptions = {}): Promise<{
    figures: Figure[];
    total: number;
  }> {
    const {
      research_id,
      figure_type,
      phi_scan_status,
      limit = 50,
      offset = 0,
      include_deleted = false,
    } = options;

    // Build WHERE clause
    const conditions: string[] = [];
    const values: any[] = [];
    let paramIndex = 1;

    if (research_id) {
      conditions.push(`research_id = $${paramIndex++}`);
      values.push(research_id);
    }

    if (figure_type) {
      conditions.push(`figure_type = $${paramIndex++}`);
      values.push(figure_type);
    }

    if (phi_scan_status) {
      conditions.push(`phi_scan_status = $${paramIndex++}`);
      values.push(phi_scan_status);
    }

    if (!include_deleted) {
      conditions.push('deleted_at IS NULL');
    }

    const whereClause = conditions.length > 0 ? `WHERE ${conditions.join(' AND ')}` : '';

    // Get total count
    const countQuery = `SELECT COUNT(*) FROM figures ${whereClause}`;
    const countResult = await this.pool.query(countQuery, values);
    const total = parseInt(countResult.rows[0].count);

    // Get paginated results
    const listQuery = `
      SELECT * FROM figures 
      ${whereClause}
      ORDER BY created_at DESC
      LIMIT $${paramIndex++} OFFSET $${paramIndex++}
    `;
    
    values.push(limit, offset);

    try {
      const result = await this.pool.query(listQuery, values);
      const figures = result.rows.map(row => this._parseFigureRow(row));

      logger.info('Listed figures', {
        researchId: research_id,
        figureType: figure_type,
        total,
        returned: figures.length,
      });

      return { figures, total };
    } catch (error) {
      logger.error('Failed to list figures', {
        options,
        error: error instanceof Error ? error.message : 'Unknown error',
      });
      throw error;
    }
  }

  /**
   * Update PHI scan results for a figure
   */
  async updatePhiScanResult(
    id: string,
    phi_scan_status: Figure['phi_scan_status'],
    phi_risk_level?: Figure['phi_risk_level'],
    phi_findings?: any[]
  ): Promise<Figure | null> {
    const query = `
      UPDATE figures 
      SET 
        phi_scan_status = $2,
        phi_risk_level = $3,
        phi_findings = $4,
        updated_at = CURRENT_TIMESTAMP
      WHERE id = $1 AND deleted_at IS NULL
      RETURNING *
    `;

    const values = [
      id,
      phi_scan_status,
      phi_risk_level,
      JSON.stringify(phi_findings || []),
    ];

    try {
      const result = await this.pool.query(query, values);
      if (result.rows.length === 0) {
        return null;
      }

      const figure = this._parseFigureRow(result.rows[0]);
      
      logger.info('Updated PHI scan result', {
        figureId: id,
        phiScanStatus: phi_scan_status,
        phiRiskLevel: phi_risk_level,
      });

      return figure;
    } catch (error) {
      logger.error('Failed to update PHI scan result', {
        figureId: id,
        error: error instanceof Error ? error.message : 'Unknown error',
      });
      throw error;
    }
  }

  /**
   * Soft delete a figure
   */
  async deleteFigure(id: string): Promise<boolean> {
    const query = `
      UPDATE figures 
      SET 
        deleted_at = CURRENT_TIMESTAMP,
        updated_at = CURRENT_TIMESTAMP
      WHERE id = $1 AND deleted_at IS NULL
      RETURNING id
    `;

    try {
      const result = await this.pool.query(query, [id]);
      const deleted = result.rows.length > 0;
      
      if (deleted) {
        logger.info('Figure deleted', { figureId: id });
      } else {
        logger.warn('Figure not found for deletion', { figureId: id });
      }

      return deleted;
    } catch (error) {
      logger.error('Failed to delete figure', {
        figureId: id,
        error: error instanceof Error ? error.message : 'Unknown error',
      });
      throw error;
    }
  }

  /**
   * Get figure statistics for a research project
   */
  async getFigureStats(research_id: string): Promise<{
    total: number;
    by_type: Record<string, number>;
    by_status: Record<string, number>;
    total_size_bytes: number;
  }> {
    const query = `
      SELECT 
        COUNT(*) as total,
        figure_type,
        phi_scan_status,
        SUM(size_bytes) as total_size
      FROM figures 
      WHERE research_id = $1 AND deleted_at IS NULL
      GROUP BY ROLLUP(figure_type), ROLLUP(phi_scan_status)
    `;

    try {
      const result = await this.pool.query(query, [research_id]);
      
      // Parse rollup results
      const stats = {
        total: 0,
        by_type: {} as Record<string, number>,
        by_status: {} as Record<string, number>,
        total_size_bytes: 0,
      };

      result.rows.forEach(row => {
        if (row.figure_type === null && row.phi_scan_status === null) {
          // Grand total
          stats.total = parseInt(row.total);
          stats.total_size_bytes = parseInt(row.total_size || '0');
        } else if (row.figure_type && row.phi_scan_status === null) {
          // By type
          stats.by_type[row.figure_type] = parseInt(row.total);
        } else if (row.figure_type === null && row.phi_scan_status) {
          // By status
          stats.by_status[row.phi_scan_status] = parseInt(row.total);
        }
      });

      return stats;
    } catch (error) {
      logger.error('Failed to get figure statistics', {
        researchId: research_id,
        error: error instanceof Error ? error.message : 'Unknown error',
      });
      throw error;
    }
  }

  /**
   * Parse database row to Figure object
   */
  private _parseFigureRow(row: any): Figure {
    return {
      ...row,
      chart_config: typeof row.chart_config === 'string' 
        ? JSON.parse(row.chart_config) 
        : row.chart_config,
      phi_findings: typeof row.phi_findings === 'string'
        ? JSON.parse(row.phi_findings)
        : row.phi_findings,
      metadata: typeof row.metadata === 'string'
        ? JSON.parse(row.metadata)
        : row.metadata,
    };
  }
}

// =============================================================================
// Factory Function
// =============================================================================

/**
 * Create a FiguresService instance with database pool
 */
export function createFiguresService(pool: Pool): FiguresService {
  return new FiguresService(pool);
}