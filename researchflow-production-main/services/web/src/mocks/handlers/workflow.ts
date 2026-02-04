/**
 * Workflow Mock Handlers
 * 
 * MSW handlers for workflow-related API endpoints:
 * - Workflow listing and details
 * - Workflow execution states
 * - Stage progress
 */

import { http, HttpResponse, delay } from 'msw';

// Types
type WorkflowStatus = 'pending' | 'running' | 'completed' | 'failed' | 'paused' | 'cancelled';

interface WorkflowStage {
  id: string;
  name: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped';
  startedAt?: string;
  completedAt?: string;
  error?: string;
}

interface Workflow {
  id: string;
  name: string;
  status: WorkflowStatus;
  createdAt: string;
  startedAt?: string;
  completedAt?: string;
  stages: WorkflowStage[];
  progress: number;
  error?: string;
}

// Mock data
const mockWorkflows: Workflow[] = [
  {
    id: 'wf-001',
    name: 'Manuscript Analysis Pipeline',
    status: 'completed',
    createdAt: new Date(Date.now() - 86400000 * 2).toISOString(),
    startedAt: new Date(Date.now() - 86400000 * 2 + 1000).toISOString(),
    completedAt: new Date(Date.now() - 86400000 * 2 + 3600000).toISOString(),
    progress: 100,
    stages: [
      { id: 's1', name: 'Document Parsing', status: 'completed', startedAt: new Date().toISOString(), completedAt: new Date().toISOString() },
      { id: 's2', name: 'PHI Scanning', status: 'completed', startedAt: new Date().toISOString(), completedAt: new Date().toISOString() },
      { id: 's3', name: 'Content Extraction', status: 'completed', startedAt: new Date().toISOString(), completedAt: new Date().toISOString() },
      { id: 's4', name: 'Analysis', status: 'completed', startedAt: new Date().toISOString(), completedAt: new Date().toISOString() },
      { id: 's5', name: 'Report Generation', status: 'completed', startedAt: new Date().toISOString(), completedAt: new Date().toISOString() },
    ],
  },
  {
    id: 'wf-002',
    name: 'Statistical Validation',
    status: 'running',
    createdAt: new Date(Date.now() - 3600000).toISOString(),
    startedAt: new Date(Date.now() - 3600000 + 1000).toISOString(),
    progress: 60,
    stages: [
      { id: 's1', name: 'Data Loading', status: 'completed', startedAt: new Date().toISOString(), completedAt: new Date().toISOString() },
      { id: 's2', name: 'Validation', status: 'completed', startedAt: new Date().toISOString(), completedAt: new Date().toISOString() },
      { id: 's3', name: 'Statistical Tests', status: 'running', startedAt: new Date().toISOString() },
      { id: 's4', name: 'Result Formatting', status: 'pending' },
      { id: 's5', name: 'Export', status: 'pending' },
    ],
  },
  {
    id: 'wf-003',
    name: 'Figure Generation',
    status: 'failed',
    createdAt: new Date(Date.now() - 7200000).toISOString(),
    startedAt: new Date(Date.now() - 7200000 + 1000).toISOString(),
    progress: 40,
    error: 'Failed to generate figure: Invalid data format in column "Results"',
    stages: [
      { id: 's1', name: 'Data Preparation', status: 'completed', startedAt: new Date().toISOString(), completedAt: new Date().toISOString() },
      { id: 's2', name: 'Chart Generation', status: 'failed', startedAt: new Date().toISOString(), error: 'Invalid data format' },
      { id: 's3', name: 'Styling', status: 'skipped' },
      { id: 's4', name: 'Export', status: 'skipped' },
    ],
  },
  {
    id: 'wf-004',
    name: 'Conference Prep Bundle',
    status: 'pending',
    createdAt: new Date().toISOString(),
    progress: 0,
    stages: [
      { id: 's1', name: 'Initialize', status: 'pending' },
      { id: 's2', name: 'Compile Materials', status: 'pending' },
      { id: 's3', name: 'Format Check', status: 'pending' },
      { id: 's4', name: 'Package', status: 'pending' },
    ],
  },
];

export const workflowHandlers = [
  /**
   * List all workflows
   */
  http.get('/api/workflows', async ({ request }) => {
    const url = new URL(request.url);
    const status = url.searchParams.get('status');
    const forceEmpty = url.searchParams.get('_empty');
    
    await delay(200);
    
    // Force empty state for testing
    if (forceEmpty === 'true') {
      return HttpResponse.json({
        workflows: [],
        total: 0,
      });
    }
    
    let filtered = mockWorkflows;
    if (status) {
      filtered = mockWorkflows.filter(w => w.status === status);
    }
    
    return HttpResponse.json({
      workflows: filtered,
      total: filtered.length,
    });
  }),

  /**
   * Get single workflow by ID
   */
  http.get('/api/workflows/:id', async ({ params, request }) => {
    const url = new URL(request.url);
    const forceStatus = url.searchParams.get('_status') as WorkflowStatus | null;
    const forceError = url.searchParams.get('_error');
    
    await delay(150);
    
    // Force 404 for testing
    if (forceError === 'notfound') {
      return new HttpResponse(null, { status: 404 });
    }
    
    // Force server error for testing
    if (forceError === 'server') {
      return HttpResponse.json(
        { error: 'Internal server error' },
        { status: 500 }
      );
    }
    
    const workflow = mockWorkflows.find(w => w.id === params.id);
    
    if (!workflow) {
      return new HttpResponse(null, { status: 404 });
    }
    
    // Allow forcing status for testing
    if (forceStatus) {
      return HttpResponse.json({
        ...workflow,
        status: forceStatus,
      });
    }
    
    return HttpResponse.json(workflow);
  }),

  /**
   * Create new workflow
   */
  http.post('/api/workflows', async ({ request }) => {
    const body = await request.json() as { name: string; type: string };
    
    await delay(300);
    
    const newWorkflow: Workflow = {
      id: `wf-${Date.now()}`,
      name: body.name,
      status: 'pending',
      createdAt: new Date().toISOString(),
      progress: 0,
      stages: [
        { id: 's1', name: 'Initialize', status: 'pending' },
        { id: 's2', name: 'Process', status: 'pending' },
        { id: 's3', name: 'Finalize', status: 'pending' },
      ],
    };
    
    mockWorkflows.unshift(newWorkflow);
    
    return HttpResponse.json(newWorkflow, { status: 201 });
  }),

  /**
   * Start workflow execution
   */
  http.post('/api/workflows/:id/start', async ({ params }) => {
    await delay(200);
    
    const workflow = mockWorkflows.find(w => w.id === params.id);
    
    if (!workflow) {
      return new HttpResponse(null, { status: 404 });
    }
    
    workflow.status = 'running';
    workflow.startedAt = new Date().toISOString();
    workflow.stages[0].status = 'running';
    workflow.stages[0].startedAt = new Date().toISOString();
    
    return HttpResponse.json(workflow);
  }),

  /**
   * Cancel workflow execution
   */
  http.post('/api/workflows/:id/cancel', async ({ params }) => {
    await delay(200);
    
    const workflow = mockWorkflows.find(w => w.id === params.id);
    
    if (!workflow) {
      return new HttpResponse(null, { status: 404 });
    }
    
    workflow.status = 'cancelled';
    
    return HttpResponse.json(workflow);
  }),

  /**
   * Pause workflow execution
   */
  http.post('/api/workflows/:id/pause', async ({ params }) => {
    await delay(200);
    
    const workflow = mockWorkflows.find(w => w.id === params.id);
    
    if (!workflow) {
      return new HttpResponse(null, { status: 404 });
    }
    
    workflow.status = 'paused';
    
    return HttpResponse.json(workflow);
  }),

  /**
   * Resume workflow execution
   */
  http.post('/api/workflows/:id/resume', async ({ params }) => {
    await delay(200);
    
    const workflow = mockWorkflows.find(w => w.id === params.id);
    
    if (!workflow) {
      return new HttpResponse(null, { status: 404 });
    }
    
    workflow.status = 'running';
    
    return HttpResponse.json(workflow);
  }),
];

export default workflowHandlers;
