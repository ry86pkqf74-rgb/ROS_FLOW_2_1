/**
 * Library Mock Handlers
 * 
 * MSW handlers for library/artifact API endpoints
 */

import { http, HttpResponse, delay } from 'msw';

// Types
type ArtifactType = 'dataset' | 'figure' | 'table' | 'code' | 'document' | 'model';
type ArtifactStatus = 'processing' | 'ready' | 'failed' | 'archived';

interface Artifact {
  id: string;
  name: string;
  type: ArtifactType;
  status: ArtifactStatus;
  size: number;
  mimeType: string;
  createdAt: string;
  updatedAt: string;
  createdBy: { id: string; name: string };
  tags: string[];
  workflowId?: string;
  metadata: Record<string, unknown>;
  previewUrl?: string;
  downloadUrl?: string;
}

// Mock data
const mockArtifacts: Artifact[] = [
  {
    id: 'art-001',
    name: 'patient_cohort_analysis.csv',
    type: 'dataset',
    status: 'ready',
    size: 2456789,
    mimeType: 'text/csv',
    createdAt: new Date(Date.now() - 86400000 * 5).toISOString(),
    updatedAt: new Date(Date.now() - 86400000 * 2).toISOString(),
    createdBy: { id: 'u1', name: 'Dr. Sarah Chen' },
    tags: ['cohort', 'cardiovascular', 'cleaned'],
    workflowId: 'wf-001',
    metadata: { rows: 15432, columns: 48, hasHeaders: true },
    previewUrl: '/api/library/art-001/preview',
    downloadUrl: '/api/library/art-001/download',
  },
  {
    id: 'art-002',
    name: 'survival_curve.png',
    type: 'figure',
    status: 'ready',
    size: 145678,
    mimeType: 'image/png',
    createdAt: new Date(Date.now() - 86400000 * 3).toISOString(),
    updatedAt: new Date(Date.now() - 86400000 * 3).toISOString(),
    createdBy: { id: 'u2', name: 'James Wilson' },
    tags: ['figure', 'survival', 'kaplan-meier'],
    workflowId: 'wf-001',
    metadata: { width: 1200, height: 800, dpi: 300 },
    previewUrl: '/api/library/art-002/preview',
    downloadUrl: '/api/library/art-002/download',
  },
  {
    id: 'art-003',
    name: 'regression_results.xlsx',
    type: 'table',
    status: 'ready',
    size: 45678,
    mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    createdAt: new Date(Date.now() - 86400000 * 2).toISOString(),
    updatedAt: new Date(Date.now() - 86400000).toISOString(),
    createdBy: { id: 'u2', name: 'James Wilson' },
    tags: ['statistics', 'regression', 'results'],
    workflowId: 'wf-002',
    metadata: { sheets: ['Main', 'Sensitivity Analysis'] },
    previewUrl: '/api/library/art-003/preview',
    downloadUrl: '/api/library/art-003/download',
  },
  {
    id: 'art-004',
    name: 'data_preprocessing.py',
    type: 'code',
    status: 'ready',
    size: 12345,
    mimeType: 'text/x-python',
    createdAt: new Date(Date.now() - 86400000 * 7).toISOString(),
    updatedAt: new Date(Date.now() - 86400000 * 4).toISOString(),
    createdBy: { id: 'u2', name: 'James Wilson' },
    tags: ['python', 'preprocessing', 'pipeline'],
    metadata: { language: 'python', lines: 342 },
    previewUrl: '/api/library/art-004/preview',
    downloadUrl: '/api/library/art-004/download',
  },
  {
    id: 'art-005',
    name: 'model_training_results.json',
    type: 'model',
    status: 'processing',
    size: 0,
    mimeType: 'application/json',
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    createdBy: { id: 'u1', name: 'Dr. Sarah Chen' },
    tags: ['ml', 'training', 'in-progress'],
    workflowId: 'wf-002',
    metadata: { progress: 67 },
  },
  {
    id: 'art-006',
    name: 'failed_analysis.csv',
    type: 'dataset',
    status: 'failed',
    size: 0,
    mimeType: 'text/csv',
    createdAt: new Date(Date.now() - 3600000).toISOString(),
    updatedAt: new Date(Date.now() - 1800000).toISOString(),
    createdBy: { id: 'u3', name: 'Maria Garcia' },
    tags: ['failed'],
    workflowId: 'wf-003',
    metadata: { error: 'Invalid data format in column "Results"' },
  },
];

export const libraryHandlers = [
  /**
   * List artifacts
   */
  http.get('/api/library', async ({ request }) => {
    const url = new URL(request.url);
    const type = url.searchParams.get('type');
    const status = url.searchParams.get('status');
    const tag = url.searchParams.get('tag');
    const search = url.searchParams.get('search');
    const forceEmpty = url.searchParams.get('_empty');
    const page = parseInt(url.searchParams.get('page') || '1');
    const limit = parseInt(url.searchParams.get('limit') || '20');
    
    await delay(200);
    
    if (forceEmpty === 'true') {
      return HttpResponse.json({
        artifacts: [],
        total: 0,
        page,
        limit,
      });
    }
    
    let filtered = [...mockArtifacts];
    
    if (type) {
      filtered = filtered.filter(a => a.type === type);
    }
    if (status) {
      filtered = filtered.filter(a => a.status === status);
    }
    if (tag) {
      filtered = filtered.filter(a => a.tags.includes(tag));
    }
    if (search) {
      const searchLower = search.toLowerCase();
      filtered = filtered.filter(a => 
        a.name.toLowerCase().includes(searchLower) ||
        a.tags.some(t => t.toLowerCase().includes(searchLower))
      );
    }
    
    const start = (page - 1) * limit;
    const paged = filtered.slice(start, start + limit);
    
    return HttpResponse.json({
      artifacts: paged,
      total: filtered.length,
      page,
      limit,
    });
  }),

  /**
   * Get artifact by ID
   */
  http.get('/api/library/:id', async ({ params, request }) => {
    const url = new URL(request.url);
    const forceStatus = url.searchParams.get('_status') as ArtifactStatus | null;
    
    await delay(150);
    
    const artifact = mockArtifacts.find(a => a.id === params.id);
    
    if (!artifact) {
      return new HttpResponse(null, { status: 404 });
    }
    
    if (forceStatus) {
      return HttpResponse.json({ ...artifact, status: forceStatus });
    }
    
    return HttpResponse.json(artifact);
  }),

  /**
   * Upload artifact
   */
  http.post('/api/library/upload', async ({ request }) => {
    await delay(500);
    
    const formData = await request.formData();
    const file = formData.get('file') as File | null;
    const tags = formData.get('tags') as string | null;
    
    const newArtifact: Artifact = {
      id: `art-${Date.now()}`,
      name: file?.name || 'uploaded_file',
      type: 'document',
      status: 'processing',
      size: file?.size || 0,
      mimeType: file?.type || 'application/octet-stream',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      createdBy: { id: 'current-user', name: 'Current User' },
      tags: tags ? tags.split(',').map(t => t.trim()) : [],
      metadata: {},
    };
    
    mockArtifacts.unshift(newArtifact);
    
    return HttpResponse.json(newArtifact, { status: 201 });
  }),

  /**
   * Delete artifact
   */
  http.delete('/api/library/:id', async ({ params }) => {
    await delay(200);
    
    const index = mockArtifacts.findIndex(a => a.id === params.id);
    
    if (index === -1) {
      return new HttpResponse(null, { status: 404 });
    }
    
    mockArtifacts.splice(index, 1);
    
    return new HttpResponse(null, { status: 204 });
  }),

  /**
   * Archive artifact
   */
  http.post('/api/library/:id/archive', async ({ params }) => {
    await delay(200);
    
    const artifact = mockArtifacts.find(a => a.id === params.id);
    
    if (!artifact) {
      return new HttpResponse(null, { status: 404 });
    }
    
    artifact.status = 'archived';
    artifact.updatedAt = new Date().toISOString();
    
    return HttpResponse.json(artifact);
  }),

  /**
   * Get available tags
   */
  http.get('/api/library/tags', async () => {
    await delay(100);
    
    const allTags = mockArtifacts.flatMap(a => a.tags);
    const tagCounts = allTags.reduce((acc, tag) => {
      acc[tag] = (acc[tag] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);
    
    return HttpResponse.json({
      tags: Object.entries(tagCounts)
        .map(([name, count]) => ({ name, count }))
        .sort((a, b) => b.count - a.count),
    });
  }),

  /**
   * Get storage stats
   */
  http.get('/api/library/stats', async () => {
    await delay(100);
    
    const totalSize = mockArtifacts.reduce((sum, a) => sum + a.size, 0);
    const byType = mockArtifacts.reduce((acc, a) => {
      acc[a.type] = (acc[a.type] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);
    
    return HttpResponse.json({
      totalArtifacts: mockArtifacts.length,
      totalSize,
      byType,
      byStatus: {
        ready: mockArtifacts.filter(a => a.status === 'ready').length,
        processing: mockArtifacts.filter(a => a.status === 'processing').length,
        failed: mockArtifacts.filter(a => a.status === 'failed').length,
        archived: mockArtifacts.filter(a => a.status === 'archived').length,
      },
    });
  }),
];

export default libraryHandlers;
