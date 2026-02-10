/**
 * Tests for Data Import Service
 * Task 144 - Data import wizards
 */

import { describe, it, expect } from 'vitest';

import {
  previewSource,
  createImportJob,
  getImportJob,
  listImportJobs,
  cancelImportJob,
  executeImport,
  type ImportConfig,
} from '../dataImportService';

describe('DataImportService', () => {
  const userId = 'test-user';
  const tenantId = 'test-tenant';
  const baseConfig = {
    sourceType: 'CSV',
    sourceConfig: { fileContent: 'a,b\n1,2' },
    targetResearchId: '11111111-1111-1111-1111-111111111111',
    targetArtifactName: 'Test Artifact',
    columnMappings: [
      {
        name: 'column_a',
        originalName: 'a',
        type: 'STRING',
        nullable: true,
        phiStatus: 'CLEAN',
        transform: 'NONE',
      },
    ],
    options: {
      hasHeader: true,
      delimiter: ',',
      encoding: 'utf-8',
      skipRows: 0,
      dateFormat: 'YYYY-MM-DD',
      enablePHIScan: true,
      autoPHIScrub: false,
    },
  } satisfies ImportConfig;

  describe('previewSource', () => {
    it('should preview CSV source', async () => {
      const preview = await previewSource('CSV', {
        fileContent: 'name,age,email\nJohn,30,john@example.com\nJane,25,jane@example.com',
      });

      expect(preview.columns.length).toBeGreaterThan(0);
      expect(preview.sampleRows.length).toBeGreaterThan(0);
      expect(preview.totalRows).toBeGreaterThan(0);
    });

    it('should detect column types', async () => {
      const preview = await previewSource('CSV', {
        fileContent: 'name,age,active\nJohn,30,true\nJane,25,false',
      });

      expect(preview.columns.some(c => c.type === 'STRING')).toBe(true);
      expect(preview.columns.some(c => c.type === 'INTEGER')).toBe(true);
      expect(preview.columns.some(c => c.type === 'NUMBER')).toBe(true);
    });

    it('should detect PHI in data', async () => {
      const preview = await previewSource('CSV', {
        fileContent: 'name,ssn,dob\nJohn Doe,123-45-6789,1990-01-15',
      });

      expect(preview.phiWarnings).toBeDefined();
      expect(preview.phiWarnings.length).toBeGreaterThan(0);
      expect(preview.phiWarnings.some(w => w.category === 'SSN')).toBe(true);
    });

    it('should preview JSON source', async () => {
      await expect(previewSource('JSON', {
        fileContent: JSON.stringify([
          { name: 'John', age: 30 },
          { name: 'Jane', age: 25 },
        ]),
      })).rejects.toThrow('Unsupported source type');
    });
  });

  describe('createImportJob', () => {
    it('should create a new import job', () => {
      const job = createImportJob({
        ...baseConfig,
        targetArtifactName: 'Test Import',
      }, userId, tenantId);

      expect(job.id).toBeDefined();
      expect(job.config.targetArtifactName).toBe('Test Import');
      expect(job.status).toBe('PENDING');
      expect(job.userId).toBe(userId);
    });

    it('should create job with column mapping', () => {
      const job = createImportJob({
        ...baseConfig,
        targetArtifactName: 'Mapped Import',
        columnMappings: [
          {
            name: 'column_a',
            originalName: 'a',
            type: 'NUMBER',
            nullable: true,
            phiStatus: 'CLEAN',
            transform: 'NONE',
          },
        ],
      }, userId, tenantId);

      expect(job.config.columnMappings).toBeDefined();
      expect(job.config.columnMappings[0].name).toBe('column_a');
    });
  });

  describe('getImportJob', () => {
    it('should return job by id', () => {
      const created = createImportJob({
        ...baseConfig,
        targetArtifactName: 'Get Test',
        sourceConfig: {},
      }, userId, tenantId);

      const job = getImportJob(created.id);
      expect(job).toBeDefined();
      expect(job?.id).toBe(created.id);
    });

    it('should return undefined for unknown job', () => {
      const job = getImportJob('non-existent-job');
      expect(job).toBeUndefined();
    });
  });

  describe('listImportJobs', () => {
    it('should list jobs for tenant', () => {
      const testTenantId = `list-tenant-${Date.now()}`;

      createImportJob({
        ...baseConfig,
        targetArtifactName: 'Job 1',
        sourceConfig: {},
      }, userId, testTenantId);

      createImportJob({
        ...baseConfig,
        targetArtifactName: 'Job 2',
        sourceConfig: {},
      }, userId, testTenantId);

      const jobs = listImportJobs(testTenantId);
      expect(jobs.length).toBe(2);
    });

    it('should filter by status', () => {
      const testTenantId = `status-tenant-${Date.now()}`;

      createImportJob({
        ...baseConfig,
        targetArtifactName: 'Pending Job',
        sourceConfig: {},
      }, userId, testTenantId);

      const jobs = listImportJobs(testTenantId, { status: 'PENDING' });
      expect(jobs.every(j => j.status === 'PENDING')).toBe(true);
    });
  });

  describe('cancelImportJob', () => {
    it('should cancel a pending job', () => {
      const job = createImportJob({
        ...baseConfig,
        targetArtifactName: 'Cancel Test',
        sourceConfig: {},
      }, userId, tenantId);

      const success = cancelImportJob(job.id);
      expect(success).toBe(true);

      const cancelled = getImportJob(job.id);
      expect(cancelled?.status).toBe('CANCELLED');
    });

    it('should return false for completed job', async () => {
      const job = createImportJob({
        ...baseConfig,
        targetArtifactName: 'Complete Test',
      }, userId, tenantId);

      await executeImport(job.id);

      const success = cancelImportJob(job.id);
      expect(success).toBe(false);
    });
  });

  describe('executeImport', () => {
    it('should execute import and update status', async () => {
      const job = createImportJob({
        ...baseConfig,
        targetArtifactName: 'Execute Test',
        sourceConfig: { fileContent: 'a,b\n1,2\n3,4' },
      }, userId, tenantId);

      const result = await executeImport(job.id);

      expect(result.status).toBe('COMPLETED');
      expect(result.resultArtifactId).toBeDefined();
      expect(result.rowsProcessed).toBeGreaterThan(0);
    });

    it('should throw error for non-existent job', async () => {
      await expect(executeImport('non-existent')).rejects.toThrow('Import job not found');
    });
  });
});
