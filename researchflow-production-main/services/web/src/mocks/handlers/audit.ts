/**
 * Audit Log Mock Handlers
 * 
 * MSW handlers for audit log API endpoints
 */

import { http, HttpResponse, delay } from 'msw';

// Types
type AuditAction = 
  | 'workflow.created' | 'workflow.started' | 'workflow.completed' | 'workflow.failed'
  | 'phi.accessed' | 'phi.denied' | 'phi.approved'
  | 'document.viewed' | 'document.edited' | 'document.exported'
  | 'model.invoked' | 'model.tier_changed'
  | 'user.login' | 'user.logout';

interface AuditLogEntry {
  id: string;
  timestamp: string;
  action: AuditAction;
  actor: {
    id: string;
    name: string;
    email: string;
    role: string;
  };
  resource: {
    type: string;
    id: string;
    name: string;
  };
  details: Record<string, unknown>;
  metadata: {
    ip?: string;
    userAgent?: string;
    sessionId?: string;
  };
}

// Generate mock audit entries
const generateAuditEntries = (count: number): AuditLogEntry[] => {
  const actions: AuditAction[] = [
    'workflow.created', 'workflow.started', 'workflow.completed',
    'phi.accessed', 'phi.denied', 'phi.approved',
    'document.viewed', 'document.edited',
    'model.invoked'
  ];
  
  const actors = [
    { id: 'u1', name: 'Dr. Sarah Chen', email: 'sarah.chen@research.org', role: 'Principal Investigator' },
    { id: 'u2', name: 'James Wilson', email: 'j.wilson@research.org', role: 'Data Analyst' },
    { id: 'u3', name: 'Maria Garcia', email: 'm.garcia@research.org', role: 'Research Coordinator' },
    { id: 'u4', name: 'System', email: 'system@researchflow.ai', role: 'Automated Process' },
  ];
  
  const resources = [
    { type: 'workflow', id: 'wf-001', name: 'Manuscript Analysis Pipeline' },
    { type: 'workflow', id: 'wf-002', name: 'Statistical Validation' },
    { type: 'document', id: 'doc-001', name: 'Study Protocol v2.3' },
    { type: 'document', id: 'doc-002', name: 'Patient Cohort Data' },
    { type: 'dataset', id: 'ds-001', name: 'Clinical Trial Results' },
  ];
  
  return Array.from({ length: count }, (_, i) => {
    const action = actions[Math.floor(Math.random() * actions.length)];
    const actor = actors[Math.floor(Math.random() * actors.length)];
    const resource = resources[Math.floor(Math.random() * resources.length)];
    const timestamp = new Date(Date.now() - i * 600000 - Math.random() * 300000);
    
    return {
      id: `audit-${Date.now()}-${i}`,
      timestamp: timestamp.toISOString(),
      action,
      actor,
      resource,
      details: {
        modelTier: action.startsWith('model') ? ['NANO', 'MINI', 'FRONTIER'][Math.floor(Math.random() * 3)] : undefined,
        phiFields: action.startsWith('phi') ? ['patient_name', 'dob', 'mrn'] : undefined,
        duration: action.includes('completed') ? Math.floor(Math.random() * 5000) + 1000 : undefined,
      },
      metadata: {
        ip: '192.168.1.' + Math.floor(Math.random() * 255),
        sessionId: `session-${Math.random().toString(36).substring(7)}`,
      },
    };
  });
};

const mockAuditEntries = generateAuditEntries(100);

export const auditHandlers = [
  /**
   * List audit log entries with pagination and filtering
   */
  http.get('/api/audit/logs', async ({ request }) => {
    const url = new URL(request.url);
    const page = parseInt(url.searchParams.get('page') || '1');
    const limit = parseInt(url.searchParams.get('limit') || '20');
    const action = url.searchParams.get('action');
    const actorId = url.searchParams.get('actorId');
    const resourceType = url.searchParams.get('resourceType');
    const startDate = url.searchParams.get('startDate');
    const endDate = url.searchParams.get('endDate');
    const forceEmpty = url.searchParams.get('_empty');
    
    await delay(200);
    
    if (forceEmpty === 'true') {
      return HttpResponse.json({
        entries: [],
        total: 0,
        page,
        limit,
        hasMore: false,
      });
    }
    
    let filtered = [...mockAuditEntries];
    
    if (action) {
      filtered = filtered.filter(e => e.action === action);
    }
    if (actorId) {
      filtered = filtered.filter(e => e.actor.id === actorId);
    }
    if (resourceType) {
      filtered = filtered.filter(e => e.resource.type === resourceType);
    }
    if (startDate) {
      filtered = filtered.filter(e => new Date(e.timestamp) >= new Date(startDate));
    }
    if (endDate) {
      filtered = filtered.filter(e => new Date(e.timestamp) <= new Date(endDate));
    }
    
    const start = (page - 1) * limit;
    const paged = filtered.slice(start, start + limit);
    
    return HttpResponse.json({
      entries: paged,
      total: filtered.length,
      page,
      limit,
      hasMore: start + limit < filtered.length,
    });
  }),

  /**
   * Get single audit entry
   */
  http.get('/api/audit/logs/:id', async ({ params }) => {
    await delay(100);
    
    const entry = mockAuditEntries.find(e => e.id === params.id);
    
    if (!entry) {
      return new HttpResponse(null, { status: 404 });
    }
    
    return HttpResponse.json(entry);
  }),

  /**
   * Export audit logs
   */
  http.post('/api/audit/export', async ({ request }) => {
    const body = await request.json() as { format: 'csv' | 'json'; filters?: Record<string, string> };
    
    await delay(500);
    
    return HttpResponse.json({
      exportId: `export-${Date.now()}`,
      format: body.format,
      status: 'processing',
      downloadUrl: null,
    });
  }),

  /**
   * Get export status
   */
  http.get('/api/audit/export/:exportId', async ({ params }) => {
    await delay(100);
    
    return HttpResponse.json({
      exportId: params.exportId,
      status: 'completed',
      downloadUrl: `/api/audit/export/${params.exportId}/download`,
      expiresAt: new Date(Date.now() + 3600000).toISOString(),
    });
  }),

  /**
   * Get audit statistics
   */
  http.get('/api/audit/stats', async ({ request }) => {
    const url = new URL(request.url);
    const days = parseInt(url.searchParams.get('days') || '7');
    
    await delay(150);
    
    return HttpResponse.json({
      totalEntries: mockAuditEntries.length,
      period: `${days} days`,
      byAction: {
        'workflow.created': 15,
        'workflow.completed': 12,
        'phi.accessed': 8,
        'phi.denied': 3,
        'document.viewed': 45,
        'model.invoked': 28,
      },
      byActor: {
        'Dr. Sarah Chen': 35,
        'James Wilson': 28,
        'Maria Garcia': 22,
        'System': 15,
      },
      dailyTrend: Array.from({ length: days }, (_, i) => ({
        date: new Date(Date.now() - i * 86400000).toISOString().split('T')[0],
        count: Math.floor(Math.random() * 50) + 10,
      })).reverse(),
    });
  }),

  /**
   * Get statistical audit trail for an analysis (decision trail, methodology, diagram)
   * Backend route may be stubbed or implemented later.
   */
  http.get('/api/audit/statistical/:analysisId', async ({ params }) => {
    await delay(150);

    const decisions = [
      {
        id: 'd1',
        timestamp: new Date(Date.now() - 3600000).toISOString(),
        title: 'Model selection',
        description: 'Linear regression chosen for continuous outcome.',
        type: 'method',
      },
      {
        id: 'd2',
        timestamp: new Date(Date.now() - 1800000).toISOString(),
        title: 'Variable inclusion',
        description: 'Covariates age, sex, and baseline added.',
        type: 'variables',
      },
      {
        id: 'd3',
        timestamp: new Date().toISOString(),
        title: 'Significance threshold',
        description: 'Alpha = 0.05, two-tailed.',
        type: 'threshold',
      },
    ];

    return HttpResponse.json({
      decisions,
      methodology:
        'We used ordinary least squares regression with robust standard errors. Outcome was continuous; predictors were mean-centered. Assumptions were checked via residual plots.',
      diagram: 'graph TD; A[Start] --> B[Data check]; B --> C[Model fit]; C --> D[Assumptions]; D --> E[Report];',
      summary: 'Statistical audit trail for reproducibility and IRB compliance.',
    });
  }),

  /**
   * Export statistical audit (PDF, JSON, compliance bundle)
   */
  http.post('/api/audit/statistical/:analysisId/export', async ({ params, request }) => {
    await delay(300);
    const url = new URL(request.url);
    const format = url.searchParams.get('format') || 'json';

    if (format === 'json') {
      const body = {
        analysisId: params.analysisId,
        exportedAt: new Date().toISOString(),
        decisions: [],
        methodology: '',
      };
      return new HttpResponse(JSON.stringify(body, null, 2), {
        headers: { 'Content-Type': 'application/json', 'Content-Disposition': `attachment; filename="statistical-audit-${params.analysisId}.json"` },
      });
    }

    return new HttpResponse('PDF/compliance export placeholder', {
      status: 200,
      headers: { 'Content-Disposition': `attachment; filename="statistical-audit-${params.analysisId}.pdf"` },
    });
  }),
];

export default auditHandlers;
