/**
 * Governance Mock Handlers
 * 
 * MSW handlers for governance-related API endpoints:
 * - PHI access control
 * - Governance mode (DEMO/LIVE)
 * - Approvals
 * - Model tier information
 */

import { http, HttpResponse, delay } from 'msw';

// Types
interface PHIAccessStatus {
  status: 'blocked' | 'requires-approval' | 'approved' | 'demo-mode';
  resourceId: string;
  stewardName?: string;
  approvalTimestamp?: string;
  reason?: string;
}

interface GovernanceMode {
  mode: 'DEMO' | 'LIVE';
  switchedAt: string;
  switchedBy: string;
}

interface ApprovalRequest {
  id: string;
  resourceId: string;
  requestedBy: string;
  requestedAt: string;
  status: 'pending' | 'approved' | 'denied';
  reviewedBy?: string;
  reviewedAt?: string;
}

// Mock data
const mockGovernanceMode: GovernanceMode = {
  mode: 'DEMO',
  switchedAt: new Date().toISOString(),
  switchedBy: 'system',
};

const mockApprovalRequests: ApprovalRequest[] = [
  {
    id: 'apr-001',
    resourceId: 'manuscript-123',
    requestedBy: 'user-456',
    requestedAt: new Date(Date.now() - 3600000).toISOString(),
    status: 'pending',
  },
  {
    id: 'apr-002',
    resourceId: 'dataset-789',
    requestedBy: 'user-456',
    requestedAt: new Date(Date.now() - 86400000).toISOString(),
    status: 'approved',
    reviewedBy: 'steward-001',
    reviewedAt: new Date(Date.now() - 43200000).toISOString(),
  },
];

export const governanceHandlers = [
  /**
   * Get current governance mode
   */
  http.get('/api/governance/mode', async () => {
    await delay(100);
    return HttpResponse.json(mockGovernanceMode);
  }),

  /**
   * Switch governance mode (DEMO <-> LIVE)
   */
  http.post('/api/governance/mode', async ({ request }) => {
    const body = await request.json() as { mode: 'DEMO' | 'LIVE' };
    await delay(300);
    
    mockGovernanceMode.mode = body.mode;
    mockGovernanceMode.switchedAt = new Date().toISOString();
    mockGovernanceMode.switchedBy = 'current-user';
    
    return HttpResponse.json(mockGovernanceMode);
  }),

  /**
   * Check PHI access status for a resource
   */
  http.get('/api/governance/phi-access/:resourceId', async ({ params, request }) => {
    const url = new URL(request.url);
    const forceStatus = url.searchParams.get('_status');
    
    await delay(150);
    
    // Allow forcing status for testing
    if (forceStatus) {
      const response: PHIAccessStatus = {
        status: forceStatus as PHIAccessStatus['status'],
        resourceId: params.resourceId as string,
      };
      
      if (forceStatus === 'approved') {
        response.stewardName = 'Dr. Jane Smith';
        response.approvalTimestamp = new Date().toISOString();
      }
      
      return HttpResponse.json(response);
    }
    
    // Default: in DEMO mode, always blocked
    if (mockGovernanceMode.mode === 'DEMO') {
      return HttpResponse.json({
        status: 'demo-mode',
        resourceId: params.resourceId,
        reason: 'PHI access is disabled in DEMO mode',
      });
    }
    
    // In LIVE mode, check approvals
    const approval = mockApprovalRequests.find(
      a => a.resourceId === params.resourceId && a.status === 'approved'
    );
    
    if (approval) {
      return HttpResponse.json({
        status: 'approved',
        resourceId: params.resourceId,
        stewardName: 'Dr. Jane Smith',
        approvalTimestamp: approval.reviewedAt,
      });
    }
    
    const pendingRequest = mockApprovalRequests.find(
      a => a.resourceId === params.resourceId && a.status === 'pending'
    );
    
    return HttpResponse.json({
      status: pendingRequest ? 'requires-approval' : 'blocked',
      resourceId: params.resourceId,
    });
  }),

  /**
   * Request PHI access approval
   */
  http.post('/api/governance/phi-access/:resourceId/request', async ({ params }) => {
    await delay(200);
    
    const newRequest: ApprovalRequest = {
      id: `apr-${Date.now()}`,
      resourceId: params.resourceId as string,
      requestedBy: 'current-user',
      requestedAt: new Date().toISOString(),
      status: 'pending',
    };
    
    mockApprovalRequests.push(newRequest);
    
    return HttpResponse.json(newRequest, { status: 201 });
  }),

  /**
   * List approval requests
   */
  http.get('/api/governance/approvals', async ({ request }) => {
    const url = new URL(request.url);
    const status = url.searchParams.get('status');
    
    await delay(150);
    
    let filtered = mockApprovalRequests;
    if (status) {
      filtered = mockApprovalRequests.filter(a => a.status === status);
    }
    
    return HttpResponse.json({
      requests: filtered,
      total: filtered.length,
    });
  }),

  /**
   * Get model tier information for a request
   */
  http.get('/api/governance/model-tier/:requestId', async ({ params, request }) => {
    const url = new URL(request.url);
    const forceTier = url.searchParams.get('_tier');
    
    await delay(100);
    
    const tier = forceTier || ['NANO', 'MINI', 'FRONTIER'][Math.floor(Math.random() * 3)];
    
    return HttpResponse.json({
      requestId: params.requestId,
      tier,
      modelId: tier === 'FRONTIER' ? 'claude-3-opus' : tier === 'MINI' ? 'claude-3-sonnet' : 'claude-3-haiku',
      reason: `Selected based on task complexity`,
    });
  }),

  /**
   * Get transparency data for a request
   */
  http.get('/api/governance/transparency/:requestId', async ({ params }) => {
    await delay(200);
    
    const tiers = ['NANO', 'MINI', 'FRONTIER'] as const;
    const tier = tiers[Math.floor(Math.random() * 3)];
    
    return HttpResponse.json({
      requestId: params.requestId,
      modelTier: tier,
      modelId: tier === 'FRONTIER' ? 'claude-3-opus' : tier === 'MINI' ? 'claude-3-sonnet' : 'claude-3-haiku',
      latencyMs: Math.floor(Math.random() * 3000) + 500,
      costCents: Math.floor(Math.random() * 50) + 1,
      inputTokens: Math.floor(Math.random() * 5000) + 100,
      outputTokens: Math.floor(Math.random() * 2000) + 50,
      dataSummary: 'Manuscript text (3 sections), methodology description, statistical results',
      redactions: ['Patient Name', 'MRN', 'Date of Birth', 'Phone Number'],
      auditLogUrl: `/audit/logs/${params.requestId}`,
      timestamp: new Date().toISOString(),
    });
  }),
];

export default governanceHandlers;
