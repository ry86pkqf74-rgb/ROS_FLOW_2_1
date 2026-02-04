/**
 * Compliance API Client
 *
 * Project-scoped compliance status, TRIPOD/CONSORT checklists,
 * HTI-1 transparency report, and audit export.
 */

import { api } from './client';

export interface ChecklistItem {
  id: string;
  section: string;
  item: string;
  status: 'complete' | 'partial' | 'missing' | 'na';
  notes?: string;
  linkedSection?: string;
}

export interface AuditEvent {
  id: string;
  timestamp: string;
  action: string;
  user: string;
  details: string;
}

export interface ComplianceData {
  overallScore: number;
  tripodScore: number;
  consortScore: number;
  hti1Score: number;
  tripodItems: ChecklistItem[];
  consortItems: ChecklistItem[];
  auditEvents: AuditEvent[];
  lastUpdated: string;
}

export interface TransparencyData {
  aiModelsUsed: Array<{ model: string; provider: string; calls: number }>;
  totalAICalls: number;
  averageLatency: number;
  decisionsLogged: number;
}

function unwrap<T>(res: { data: T | null; error: { error: string } | null }): T {
  if (res.error) throw new Error(res.error.error || 'Request failed');
  if (res.data == null) throw new Error('No data');
  return res.data;
}

export const complianceApi = {
  getComplianceStatus: async (projectId: string): Promise<ComplianceData> => {
    const res = await api.get<ComplianceData>(
      `/api/projects/${projectId}/compliance`
    );
    return unwrap(res);
  },

  getTransparencyReport: async (
    projectId: string
  ): Promise<TransparencyData> => {
    const res = await api.get<TransparencyData>(
      `/api/projects/${projectId}/compliance/transparency`
    );
    return unwrap(res);
  },

  exportComplianceReport: async (projectId: string): Promise<Blob> => {
    const baseUrl = (
      import.meta.env.VITE_API_BASE_URL || ''
    ).replace(/\/$/, '');
    const url = `${baseUrl}/api/projects/${projectId}/compliance/export`;
    const token =
      typeof window !== 'undefined'
        ? localStorage.getItem('access_token') ||
          sessionStorage.getItem('access_token')
        : null;
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      credentials: 'include',
    });
    if (!response.ok) throw new Error('Export failed');
    return response.blob();
  },

  updateChecklistItem: async (
    projectId: string,
    itemId: string,
    status: string
  ): Promise<unknown> => {
    const res = await api.patch<unknown>(
      `/api/projects/${projectId}/compliance/checklist/${itemId}`,
      { status }
    );
    return unwrap(res);
  },
};
