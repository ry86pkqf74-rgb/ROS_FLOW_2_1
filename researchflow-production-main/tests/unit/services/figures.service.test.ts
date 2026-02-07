/**
 * Unit Tests - Figures Service
 * 
 * Tests the FiguresService class and database operations for visualization figures.
 * Tests CRUD operations, PHI scanning, and statistics functionality.
 */

import { describe, test, expect, beforeEach, afterEach, vi, beforeAll, afterAll } from 'vitest';
import { Pool } from 'pg';
import { FiguresService, createFiguresService, type FigureCreateInput } from '../../../services/orchestrator/src/services/figures.service';

// Mock database pool for unit testing
const mockPool = {
  query: vi.fn(),
} as unknown as Pool;

describe('FiguresService', () => {
  let service: FiguresService;
  const testResearchId = 'test-research-123';
  const testFigureId = 'test-figure-456';

  beforeEach(() => {
    service = new FiguresService(mockPool);
    vi.clearAllMocks();
  });

  describe('createFigure', () => {
    test('should create figure successfully', async () => {
      const mockFigureRow = {
        id: testFigureId,
        research_id: testResearchId,
        figure_type: 'bar_chart',
        title: 'Test Chart',
        image_data: Buffer.from('test-data'),
        size_bytes: 100,
        dpi: 300,
        chart_config: '{}',
        phi_findings: '[]',
        metadata: '{}',
        created_at: new Date(),
      };

      (mockPool.query as any).mockResolvedValueOnce({
        rows: [mockFigureRow],
      });

      const input: FigureCreateInput = {
        research_id: testResearchId,
        figure_type: 'bar_chart',
        title: 'Test Chart',
        image_data: Buffer.from('test-data'),
        generated_by: 'test',
      };

      const result = await service.createFigure(input);

      expect(result.id).toBe(testFigureId);
      expect(result.research_id).toBe(testResearchId);
      expect(result.figure_type).toBe('bar_chart');
      expect(result.title).toBe('Test Chart');
      expect(result.size_bytes).toBe(100);
      
      // Verify database call
      expect(mockPool.query).toHaveBeenCalledTimes(1);
      const [query, values] = (mockPool.query as any).mock.calls[0];
      expect(query).toContain('INSERT INTO figures');
      expect(values).toContain(testResearchId);
      expect(values).toContain('bar_chart');
      expect(values).toContain('Test Chart');
    });

    test('should handle missing optional fields', async () => {
      const mockFigureRow = {
        id: testFigureId,
        research_id: testResearchId,
        figure_type: 'line_chart',
        title: null,
        caption: null,
        image_data: Buffer.from('data'),
        size_bytes: 50,
        chart_config: '{}',
        phi_findings: '[]',
        metadata: '{}',
      };

      (mockPool.query as any).mockResolvedValueOnce({
        rows: [mockFigureRow],
      });

      const input: FigureCreateInput = {
        research_id: testResearchId,
        figure_type: 'line_chart',
        image_data: Buffer.from('data'),
        generated_by: 'test',
      };

      const result = await service.createFigure(input);

      expect(result.id).toBe(testFigureId);
      expect(result.title).toBeNull();
      expect(result.caption).toBeNull();
    });

    test('should calculate size_bytes from image_data', async () => {
      const imageData = Buffer.from('test-image-data-larger');
      const expectedSize = imageData.length;

      const mockFigureRow = {
        id: testFigureId,
        research_id: testResearchId,
        figure_type: 'scatter_plot',
        image_data: imageData,
        size_bytes: expectedSize,
        chart_config: '{}',
        phi_findings: '[]',
        metadata: '{}',
      };

      (mockPool.query as any).mockResolvedValueOnce({
        rows: [mockFigureRow],
      });

      const input: FigureCreateInput = {
        research_id: testResearchId,
        figure_type: 'scatter_plot',
        image_data: imageData,
        generated_by: 'test',
      };

      await service.createFigure(input);

      // Verify size_bytes was calculated correctly
      const [, values] = (mockPool.query as any).mock.calls[0];
      const sizeBytesIndex = 8; // Based on the INSERT query order
      expect(values[sizeBytesIndex]).toBe(expectedSize);
    });

    test('should handle database errors', async () => {
      (mockPool.query as any).mockRejectedValueOnce(
        new Error('Database connection failed')
      );

      const input: FigureCreateInput = {
        research_id: testResearchId,
        figure_type: 'bar_chart',
        image_data: Buffer.from('data'),
        generated_by: 'test',
      };

      await expect(service.createFigure(input)).rejects.toThrow(
        'Database connection failed'
      );
    });
  });

  describe('getFigureById', () => {
    test('should retrieve figure by ID', async () => {
      const mockFigureRow = {
        id: testFigureId,
        research_id: testResearchId,
        figure_type: 'box_plot',
        title: 'Box Plot Title',
        chart_config: '{"show_outliers": true}',
        phi_findings: '[{"type": "test"}]',
        metadata: '{"version": "1.0"}',
      };

      (mockPool.query as any).mockResolvedValueOnce({
        rows: [mockFigureRow],
      });

      const result = await service.getFigureById(testFigureId);

      expect(result).not.toBeNull();
      expect(result!.id).toBe(testFigureId);
      expect(result!.figure_type).toBe('box_plot');
      
      // Verify JSON parsing
      expect(result!.chart_config).toEqual({ show_outliers: true });
      expect(result!.phi_findings).toEqual([{ type: 'test' }]);
      expect(result!.metadata).toEqual({ version: '1.0' });
      
      // Verify database query
      expect(mockPool.query).toHaveBeenCalledWith(
        expect.stringContaining('SELECT * FROM figures'),
        [testFigureId]
      );
    });

    test('should return null for non-existent figure', async () => {
      (mockPool.query as any).mockResolvedValueOnce({
        rows: [],
      });

      const result = await service.getFigureById('non-existent-id');

      expect(result).toBeNull();
    });

    test('should handle database errors', async () => {
      (mockPool.query as any).mockRejectedValueOnce(
        new Error('Connection timeout')
      );

      await expect(
        service.getFigureById(testFigureId)
      ).rejects.toThrow('Connection timeout');
    });
  });

  describe('listFigures', () => {
    test('should list figures with default options', async () => {
      const mockFigures = [
        {
          id: 'fig-1',
          research_id: testResearchId,
          figure_type: 'bar_chart',
          chart_config: '{}',
          phi_findings: '[]',
          metadata: '{}',
          created_at: new Date('2024-01-01'),
        },
        {
          id: 'fig-2',
          research_id: testResearchId,
          figure_type: 'line_chart',
          chart_config: '{}',
          phi_findings: '[]',
          metadata: '{}',
          created_at: new Date('2024-01-02'),
        },
      ];

      // Mock count query
      (mockPool.query as any).mockResolvedValueOnce({
        rows: [{ count: '2' }],
      });

      // Mock list query
      (mockPool.query as any).mockResolvedValueOnce({
        rows: mockFigures,
      });

      const result = await service.listFigures();

      expect(result.total).toBe(2);
      expect(result.figures).toHaveLength(2);
      expect(result.figures[0].id).toBe('fig-1');
      expect(result.figures[1].id).toBe('fig-2');
      
      // Verify default pagination
      expect(mockPool.query).toHaveBeenCalledTimes(2);
      const [, listValues] = (mockPool.query as any).mock.calls[1];
      expect(listValues).toContain(50); // default limit
      expect(listValues).toContain(0);  // default offset
    });

    test('should filter by research_id', async () => {
      (mockPool.query as any).mockResolvedValueOnce({ rows: [{ count: '1' }] });
      (mockPool.query as any).mockResolvedValueOnce({ rows: [] });

      await service.listFigures({ research_id: testResearchId });

      // Verify WHERE clause includes research_id
      const [countQuery, countValues] = (mockPool.query as any).mock.calls[0];
      expect(countQuery).toContain('WHERE');
      expect(countQuery).toContain('research_id = $');
      expect(countValues).toContain(testResearchId);
    });

    test('should filter by figure_type and phi_scan_status', async () => {
      (mockPool.query as any).mockResolvedValueOnce({ rows: [{ count: '0' }] });
      (mockPool.query as any).mockResolvedValueOnce({ rows: [] });

      await service.listFigures({
        figure_type: 'forest_plot',
        phi_scan_status: 'PASS',
        limit: 10,
        offset: 20,
      });

      const [countQuery, countValues] = (mockPool.query as any).mock.calls[0];
      expect(countQuery).toContain('figure_type = $');
      expect(countQuery).toContain('phi_scan_status = $');
      expect(countValues).toContain('forest_plot');
      expect(countValues).toContain('PASS');

      const [listQuery, listValues] = (mockPool.query as any).mock.calls[1];
      expect(listValues).toContain(10); // custom limit
      expect(listValues).toContain(20); // custom offset
    });

    test('should include deleted figures when requested', async () => {
      (mockPool.query as any).mockResolvedValueOnce({ rows: [{ count: '1' }] });
      (mockPool.query as any).mockResolvedValueOnce({ rows: [] });

      await service.listFigures({ include_deleted: true });

      const [countQuery] = (mockPool.query as any).mock.calls[0];
      expect(countQuery).not.toContain('deleted_at IS NULL');
    });
  });

  describe('updatePhiScanResult', () => {
    test('should update PHI scan results successfully', async () => {
      const mockUpdatedFigure = {
        id: testFigureId,
        phi_scan_status: 'PASS',
        phi_risk_level: 'SAFE',
        phi_findings: '[{"status": "clean"}]',
        chart_config: '{}',
        metadata: '{}',
        updated_at: new Date(),
      };

      (mockPool.query as any).mockResolvedValueOnce({
        rows: [mockUpdatedFigure],
      });

      const result = await service.updatePhiScanResult(
        testFigureId,
        'PASS',
        'SAFE',
        [{ status: 'clean' }]
      );

      expect(result).not.toBeNull();
      expect(result!.phi_scan_status).toBe('PASS');
      expect(result!.phi_risk_level).toBe('SAFE');
      expect(result!.phi_findings).toEqual([{ status: 'clean' }]);
      
      // Verify database query
      const [query, values] = (mockPool.query as any).mock.calls[0];
      expect(query).toContain('UPDATE figures');
      expect(query).toContain('phi_scan_status = $2');
      expect(values).toContain(testFigureId);
      expect(values).toContain('PASS');
      expect(values).toContain('SAFE');
    });

    test('should return null for non-existent figure', async () => {
      (mockPool.query as any).mockResolvedValueOnce({
        rows: [],
      });

      const result = await service.updatePhiScanResult(
        'non-existent-id',
        'FAIL'
      );

      expect(result).toBeNull();
    });
  });

  describe('deleteFigure', () => {
    test('should soft delete figure successfully', async () => {
      (mockPool.query as any).mockResolvedValueOnce({
        rows: [{ id: testFigureId }],
      });

      const result = await service.deleteFigure(testFigureId);

      expect(result).toBe(true);
      
      // Verify soft delete query
      const [query, values] = (mockPool.query as any).mock.calls[0];
      expect(query).toContain('UPDATE figures');
      expect(query).toContain('deleted_at = CURRENT_TIMESTAMP');
      expect(query).toContain('WHERE id = $1 AND deleted_at IS NULL');
      expect(values).toContain(testFigureId);
    });

    test('should return false for non-existent figure', async () => {
      (mockPool.query as any).mockResolvedValueOnce({
        rows: [],
      });

      const result = await service.deleteFigure('non-existent-id');

      expect(result).toBe(false);
    });
  });

  describe('getFigureStats', () => {
    test('should return figure statistics', async () => {
      const mockStatsRows = [
        {
          total: '5',
          figure_type: null,
          phi_scan_status: null,
          total_size: '1024000',
        },
        {
          total: '3',
          figure_type: 'bar_chart',
          phi_scan_status: null,
          total_size: null,
        },
        {
          total: '2',
          figure_type: 'line_chart',
          phi_scan_status: null,
          total_size: null,
        },
        {
          total: '4',
          figure_type: null,
          phi_scan_status: 'PASS',
          total_size: null,
        },
        {
          total: '1',
          figure_type: null,
          phi_scan_status: 'PENDING',
          total_size: null,
        },
      ];

      (mockPool.query as any).mockResolvedValueOnce({
        rows: mockStatsRows,
      });

      const result = await service.getFigureStats(testResearchId);

      expect(result.total).toBe(5);
      expect(result.total_size_bytes).toBe(1024000);
      expect(result.by_type).toEqual({
        bar_chart: 3,
        line_chart: 2,
      });
      expect(result.by_status).toEqual({
        PASS: 4,
        PENDING: 1,
      });

      // Verify query includes ROLLUP
      const [query, values] = (mockPool.query as any).mock.calls[0];
      expect(query).toContain('GROUP BY ROLLUP');
      expect(values).toContain(testResearchId);
    });

    test('should handle empty statistics', async () => {
      (mockPool.query as any).mockResolvedValueOnce({
        rows: [],
      });

      const result = await service.getFigureStats(testResearchId);

      expect(result.total).toBe(0);
      expect(result.total_size_bytes).toBe(0);
      expect(result.by_type).toEqual({});
      expect(result.by_status).toEqual({});
    });
  });

  describe('createFiguresService factory function', () => {
    test('should create service with pool', () => {
      const service = createFiguresService(mockPool);
      
      expect(service).toBeInstanceOf(FiguresService);
      expect(service).toHaveProperty('createFigure');
      expect(service).toHaveProperty('getFigureById');
      expect(service).toHaveProperty('listFigures');
    });
  });

  describe('JSON parsing', () => {
    test('should handle invalid JSON gracefully', async () => {
      const mockFigureRow = {
        id: testFigureId,
        research_id: testResearchId,
        figure_type: 'bar_chart',
        chart_config: 'invalid json',
        phi_findings: '[]',
        metadata: '{}',
      };

      (mockPool.query as any).mockResolvedValueOnce({
        rows: [mockFigureRow],
      });

      // Should throw an error due to invalid JSON
      await expect(
        service.getFigureById(testFigureId)
      ).rejects.toThrow();
    });

    test('should handle already parsed objects', async () => {
      const mockFigureRow = {
        id: testFigureId,
        research_id: testResearchId,
        figure_type: 'bar_chart',
        chart_config: { already: 'parsed' },
        phi_findings: [{ already: 'parsed' }],
        metadata: { version: '2.0' },
      };

      (mockPool.query as any).mockResolvedValueOnce({
        rows: [mockFigureRow],
      });

      const result = await service.getFigureById(testFigureId);

      expect(result!.chart_config).toEqual({ already: 'parsed' });
      expect(result!.phi_findings).toEqual([{ already: 'parsed' }]);
      expect(result!.metadata).toEqual({ version: '2.0' });
    });
  });
});"