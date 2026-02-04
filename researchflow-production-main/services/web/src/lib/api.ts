/**
 * Typed API endpoint functions for workflow, checklists, PHI scanner, and monitoring.
 * Uses the low-level api-client for HTTP calls.
 */

import { apiGet, apiPost, apiPut, apiPatch } from './api-client';
import type {
  WorkflowStagesResponse,
  WorkflowStage,
  WorkflowStageGroup,
  ChecklistResponse,
  PHIScanResult,
} from '@/types/api';

// ---------------------------------------------------------------------------
// Workflow API (/api/workflow)
// ---------------------------------------------------------------------------

export async function getWorkflowStages(): Promise<WorkflowStagesResponse> {
  return apiGet<WorkflowStagesResponse>('/api/workflow/stages');
}

export async function getWorkflowStage(
  stageId: number
): Promise<{ stage: WorkflowStage; group: WorkflowStageGroup | null; mode: string }> {
  return apiGet(`/api/workflow/stages/${stageId}`);
}

export async function approveAIStage(stageId: number): Promise<{ status: string; stageId: number; aiApproved: boolean; mode: string }> {
  return apiPost(`/api/workflow/stages/${stageId}/approve-ai`, {});
}

export async function revokeAIStage(stageId: number): Promise<{ status: string; stageId: number; aiApproved: boolean; mode: string }> {
  return apiPost(`/api/workflow/stages/${stageId}/revoke-ai`, {});
}

export async function attestStage(
  stageId: number,
  body: { attestationText?: string }
): Promise<{ status: string; stageId: number; attested: boolean; mode: string }> {
  return apiPost(`/api/workflow/stages/${stageId}/attest`, body);
}

export async function completeStage(
  stageId: number,
  body?: { metadata?: Record<string, unknown> }
): Promise<{ status: string; stageId: number; completed: boolean; mode: string }> {
  return apiPost(`/api/workflow/stages/${stageId}/complete`, body ?? {});
}

export async function getWorkflowLifecycle(): Promise<Record<string, unknown> & { mode: string }> {
  return apiGet('/api/workflow/lifecycle');
}

export async function transitionLifecycle(body: {
  newState: string;
  details?: Record<string, unknown>;
}): Promise<Record<string, unknown> & { status: string; mode: string }> {
  return apiPost('/api/workflow/lifecycle/transition', body);
}

export async function getWorkflowAuditLog(): Promise<{ sessionId: string; entries: unknown[]; count: number; mode: string }> {
  return apiGet('/api/workflow/audit-log');
}

export async function resetWorkflow(): Promise<{ status: string; sessionId: string; mode: string }> {
  return apiPost('/api/workflow/reset', {});
}

// ---------------------------------------------------------------------------
// Checklists API (/api/checklists)
// ---------------------------------------------------------------------------

export type ChecklistType = 'tripod_ai' | 'consort_ai';

export async function listChecklists(): Promise<{
  success: boolean;
  checklists: Array<{ type: string; name: string; description: string; items: number; url: string }>;
  total: number;
}> {
  return apiGet('/api/checklists');
}

export async function getChecklist(
  type: ChecklistType
): Promise<{ success: boolean; checklist: ChecklistResponse | Record<string, unknown>; metadata?: Record<string, unknown> }> {
  return apiGet(`/api/checklists/${type}`);
}

export async function getChecklistGuidance(
  type: ChecklistType,
  itemId: string
): Promise<Record<string, unknown>> {
  return apiGet(`/api/checklists/${type}/${itemId}/guidance`);
}

export async function validateChecklist(
  type: ChecklistType,
  body: { completions: Array<{ itemId: string; status: string }> }
): Promise<{ success: boolean; validation: Record<string, unknown>; summary?: Record<string, unknown> }> {
  return apiPost(`/api/checklists/${type}/validate`, body);
}

export async function getChecklistProgress(
  type: ChecklistType,
  body: { completions?: Array<{ itemId: string; status: string }> }
): Promise<{ success: boolean; progress: { progressPercentage: number; [key: string]: unknown } }> {
  return apiPost(`/api/checklists/${type}/progress`, body);
}

export async function exportChecklist(
  type: ChecklistType,
  body: {
    completions: Array<{ itemId: string; status: string }>;
    format?: 'json' | 'yaml' | 'csv';
    researchId?: string;
  }
): Promise<Blob | unknown> {
  return apiPost(`/api/checklists/${type}/export`, body);
}

export async function compareChecklists(): Promise<{ success: boolean; comparison: Record<string, unknown> }> {
  return apiGet('/api/checklists/compare/items');
}

// ---------------------------------------------------------------------------
// PHI Scanner API (/api/ros/phi)
// ---------------------------------------------------------------------------

export interface PhiScanRequest {
  content: string;
  contentType: 'text' | 'markdown' | 'html' | 'json' | 'csv';
  fileName?: string;
  projectId?: string;
  stageId?: number;
  governanceMode: 'DEMO' | 'LIVE';
  sensitivityLevel?: 'standard' | 'strict';
}

export async function scanPhi(body: PhiScanRequest): Promise<PHIScanResult & { passed?: boolean; scanId?: string }> {
  return apiPost('/api/ros/phi/scan', body);
}

export async function getPhiScan(id: string): Promise<{
  scanId: string;
  status: string;
  summary?: Record<string, unknown>;
  scannedAt: string;
  scanDurationMs?: number;
  findingsCount?: number;
}> {
  return apiGet(`/api/ros/phi/scan/${id}`);
}

export async function redactPhi(body: {
  content: string;
  findings: Array<{ id: string; redact: boolean; customRedaction?: string }>;
  redactionStyle?: 'mask' | 'remove' | 'bracket' | 'custom';
}): Promise<{ redactedContent: string; appliedRedactions: number; redactionStyle: string }> {
  return apiPost('/api/ros/phi/redact', body);
}

export async function createPhiAccessRequest(body: {
  projectId: string;
  reason: string;
  dataScope: string[];
  duration: 'session' | 'day' | 'week' | 'permanent';
}): Promise<{ requestId: string; status: string; message: string; createdAt: string }> {
  return apiPost('/api/ros/phi/access-requests', body);
}

export async function listPhiAccessRequests(params?: {
  status?: string;
  projectId?: string;
}): Promise<{ requests: unknown[]; total: number }> {
  return apiGet('/api/ros/phi/access-requests', { params: params as Record<string, string | number | boolean> });
}

// ---------------------------------------------------------------------------
// Monitoring API (/api/monitoring) – Phase G
// ---------------------------------------------------------------------------

export async function getMonitoringClusterStatus(): Promise<{ success: boolean; data: unknown }> {
  return apiGet('/api/monitoring/cluster/status');
}

export async function getMonitoringClusterServices(): Promise<{ success: boolean; data: unknown }> {
  return apiGet('/api/monitoring/cluster/services');
}

export async function getMonitoringMetricsHeatmap(
  type: 'cpu' | 'memory',
  windowMinutes?: number
): Promise<{ success: boolean; data: unknown }> {
  return apiGet('/api/monitoring/metrics/heatmap/' + type, {
    params: windowMinutes != null ? { window: windowMinutes } : undefined,
  });
}

export async function getMonitoringMetricsCache(): Promise<{ success: boolean; data: unknown }> {
  return apiGet('/api/monitoring/metrics/cache');
}

export async function getMonitoringMetricsLatency(): Promise<{ success: boolean; data: unknown }> {
  return apiGet('/api/monitoring/metrics/latency');
}
