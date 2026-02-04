/**
 * Manuscript Export API client
 * Wires to /api/export (Track B Phase 15)
 */

import { api } from './client';

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '') || '';

function getAuthToken(): string | null {
  return typeof window !== 'undefined'
    ? localStorage.getItem('access_token') || sessionStorage.getItem('access_token')
    : null;
}

export type ExportFormat = 'docx' | 'pdf' | 'latex' | 'html' | 'odt' | 'epub';

export interface StartExportOptions {
  output_format: ExportFormat;
  template_id?: string;
  citation_style?: string;
  include_track_changes?: boolean;
  include_comments?: boolean;
  include_supplementary?: boolean;
  custom_options?: Record<string, unknown>;
}

export interface StartExportResponse {
  job_id: string;
  status: string;
  message?: string;
  poll_url?: string;
}

export interface JobStatusResponse {
  id: string;
  status: 'processing' | 'completed' | 'failed';
  progress?: number;
  output_url?: string;
  output_filename?: string;
  error_code?: string;
  error_message?: string;
  manuscript_title?: string;
  started_at?: string;
  completed_at?: string;
}

export interface PreviewOptions {
  output_format?: ExportFormat;
  template?: string;
  csl_style?: string;
  bibliography?: string;
  metadata?: Record<string, unknown>;
  redaction_patterns?: string[];
}

export interface PreviewResponse {
  manuscript_id: string;
  title?: string;
  output_format: string;
  template?: string;
  csl_style?: string;
  bibliography?: string;
  metadata?: Record<string, unknown>;
  preview_markdown: string;
}

export const exportApi = {
  /**
   * Start manuscript export. Returns job_id; poll getJobStatus until completed/failed.
   */
  async startExport(
    manuscriptId: string,
    options: StartExportOptions
  ): Promise<StartExportResponse> {
    const res = await api.post<StartExportResponse>(
      `/api/export/manuscripts/${manuscriptId}`,
      options
    );
    if (res.error) throw new Error(res.error.error || 'Failed to start export');
    const data = res.data;
    if (!data?.job_id) throw new Error('No job_id in response');
    return data;
  },

  /**
   * Get export job status (and progress).
   */
  async getJobStatus(jobId: string): Promise<JobStatusResponse> {
    const res = await api.get<JobStatusResponse>(`/api/export/jobs/${jobId}`);
    if (res.error) throw new Error(res.error.error || 'Failed to get job status');
    if (!res.data) throw new Error('No job status');
    return res.data;
  },

  /**
   * Download exported file as blob. Caller should trigger save (e.g. object URL + <a download>).
   */
  async downloadExport(jobId: string): Promise<Blob> {
    const base = API_BASE_URL || (typeof window !== 'undefined' ? window.location.origin : '');
    const url = `${base}/api/export/jobs/${jobId}/download`;
    const token = getAuthToken();
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      credentials: 'include',
    });
    if (!response.ok) throw new Error('Download failed');
    return response.blob();
  },

  /**
   * Cancel/delete export job.
   */
  async cancelJob(jobId: string): Promise<void> {
    const res = await api.delete<{ success: boolean; id: string }>(
      `/api/export/jobs/${jobId}`
    );
    if (res.error) throw new Error(res.error.error || 'Failed to cancel job');
  },

  /**
   * Get preview before export (redacted markdown + resolved options).
   */
  async getPreview(
    manuscriptId: string,
    body: PreviewOptions = {}
  ): Promise<PreviewResponse> {
    const res = await api.post<PreviewResponse>(
      `/api/export/manuscripts/${manuscriptId}/preview`,
      body
    );
    if (res.error) throw new Error(res.error.error || 'Failed to get preview');
    if (!res.data) throw new Error('No preview data');
    return res.data;
  },
};

export default exportApi;
