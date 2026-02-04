/**
 * Manuscript API client
 */

import { api, apiFetch } from './client';

interface GenerateSectionOptions {
  abstractStyle?: string;
  journalStyle?: string;
  wordLimit?: number;
  signal?: AbortSignal;
}

export interface GenerationResult {
  content: string;
  wordCount: number;
  qualityScore: number;
  suggestions: string[];
  transparencyLog: Record<string, unknown>;
}

interface GenerationResponse {
  generationId?: string;
  result?: GenerationResult;
  status: 'pending' | 'processing' | 'complete' | 'error';
}

interface ManuscriptExportOptions {
  format: 'docx' | 'pdf' | 'latex' | 'markdown';
  journalStyle?: string;
  includeSupplementary?: boolean;
}

/** Normalize backend section response to GenerationResult shape */
function toGenerationResult(payload: {
  content: string;
  validation?: { wordCount?: number };
  [key: string]: unknown;
}): GenerationResult {
  const wordCount =
    typeof payload.validation?.wordCount === 'number'
      ? payload.validation.wordCount
      : payload.content.split(/\s+/).filter(Boolean).length;
  return {
    content: payload.content ?? '',
    wordCount,
    qualityScore: 0,
    suggestions: [],
    transparencyLog: {},
  };
}

export const manuscriptApi = {
  /**
   * Generate a manuscript section.
   * Maps to existing backend: /api/manuscript/generate/results | discussion | title-keywords | full.
   * Uses projectId as manuscriptId for existing routes; abstract/methods return not-implemented until backend adds them.
   */
  generateSection: async (
    projectId: string,
    section: string,
    options?: GenerateSectionOptions
  ): Promise<GenerationResponse> => {
    const { signal, ...bodyOptions } = options ?? {};
    const manuscriptId = projectId;

    const baseUrl =
      (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '') || '';
    const endpoint = (path: string) =>
      path.startsWith('http') ? path : `${baseUrl}${path.startsWith('/') ? '' : '/'}${path}`;

    if (section === 'abstract' || section === 'methods') {
      throw new Error(
        `${section} generation is not yet implemented; backend endpoints for abstract/methods are pending.`
      );
    }

    if (section === 'results') {
      const res = await apiFetch<{
        content?: string;
        validation?: { wordCount?: number };
        [key: string]: unknown;
      }>(endpoint('/api/manuscript/generate/results'), {
        method: 'POST',
        body: JSON.stringify({
          manuscriptId,
          analysisResults: {},
          options: bodyOptions,
        }),
        signal,
      });
      if (res.error) throw new Error(res.error.error || 'Generation failed');
      const data = res.data;
      if (!data) throw new Error('No response data');
      return {
        status: 'complete',
        result: toGenerationResult(data),
      };
    }

    if (section === 'discussion') {
      const res = await apiFetch<{
        content?: string;
        validation?: { wordCount?: number };
        [key: string]: unknown;
      }>(endpoint('/api/manuscript/generate/discussion'), {
        method: 'POST',
        body: JSON.stringify({
          manuscriptId,
          resultsSection: '',
          literatureContext: [],
          options: bodyOptions,
        }),
        signal,
      });
      if (res.error) throw new Error(res.error.error || 'Generation failed');
      const data = res.data;
      if (!data) throw new Error('No response data');
      return {
        status: 'complete',
        result: toGenerationResult(data),
      };
    }

    if (section === 'full') {
      const res = await apiFetch<{
        sections?: { results?: { content?: string }; discussion?: { content?: string } };
        [key: string]: unknown;
      }>(endpoint('/api/manuscript/generate/full'), {
        method: 'POST',
        body: JSON.stringify({
          manuscriptId,
          analysisResults: {},
          options: bodyOptions,
        }),
        signal,
      });
      if (res.error) throw new Error(res.error.error || 'Generation failed');
      const data = res.data;
      if (!data?.sections) throw new Error('No response data');
      const content =
        [data.sections.results?.content, data.sections.discussion?.content]
          .filter(Boolean)
          .join('\n\n') || '';
      return {
        status: 'complete',
        result: toGenerationResult({ content }),
      };
    }

    throw new Error(`Unknown section: ${section}`);
  },

  /**
   * Get generation status (for async generation; backend does not return generationId yet)
   */
  getGenerationStatus: async (
    projectId: string,
    generationId: string
  ): Promise<GenerationResponse> => {
    const res = await api.get<GenerationResponse>(
      `/api/projects/${projectId}/manuscript/generation/${generationId}`
    );
    if (res.error) throw new Error(res.error.error || 'Failed to get status');
    return res.data ?? { status: 'error' };
  },

  /**
   * Get generated manuscript
   */
  getManuscript: async (projectId: string): Promise<{
    sections: Record<string, string>;
    metadata: Record<string, unknown>;
  }> => {
    const res = await api.get<{
      sections: Record<string, string>;
      metadata: Record<string, unknown>;
    }>(`/api/projects/${projectId}/manuscript`);
    if (res.error) throw new Error(res.error.error || 'Failed to get manuscript');
    return res.data ?? { sections: {}, metadata: {} };
  },

  /**
   * Export manuscript (uses fetch for blob response)
   */
  exportManuscript: async (
    projectId: string,
    options: ManuscriptExportOptions
  ): Promise<Blob> => {
    const baseUrl =
      (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '') || '';
    const url = `${baseUrl}/api/projects/${projectId}/manuscript/export`;
    const token =
      typeof window !== 'undefined'
        ? localStorage.getItem('access_token') || sessionStorage.getItem('access_token')
        : null;
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(options),
      credentials: 'include',
    });
    if (!response.ok) throw new Error('Export failed');
    return response.blob();
  },

  /**
   * Get available journal styles
   */
  getJournalStyles: async (): Promise<{
    styles: Array<{ id: string; name: string; description: string }>;
  }> => {
    const res = await api.get<{
      styles: Array<{ id: string; name: string; description: string }>;
    }>('/api/manuscript/styles');
    if (res.error) throw new Error(res.error.error || 'Failed to get styles');
    return res.data ?? { styles: [] };
  },
};

export default manuscriptApi;
