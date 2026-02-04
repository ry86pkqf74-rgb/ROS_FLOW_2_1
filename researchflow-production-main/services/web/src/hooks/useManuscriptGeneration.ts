/**
 * useManuscriptGeneration - Hook for manuscript generation with progress tracking
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import { manuscriptApi } from '@/api/manuscript';

interface GenerationOptions {
  abstractStyle?: string;
  journalStyle?: string;
  wordLimit?: number;
}

interface GenerationResult {
  content: string;
  wordCount: number;
  qualityScore: number;
  suggestions: string[];
  transparencyLog: Record<string, unknown>;
}

interface UseManuscriptGenerationReturn {
  isGenerating: boolean;
  progress: number;
  currentStep: string;
  error: string | null;
  result: GenerationResult | null;
  generateSection: (
    section: string,
    options?: GenerationOptions
  ) => Promise<GenerationResult | null>;
  generateFullManuscript: (
    options?: GenerationOptions
  ) => Promise<GenerationResult | null>;
  cancelGeneration: () => void;
}

export function useManuscriptGeneration(
  projectId: string
): UseManuscriptGenerationReturn {
  const [isGenerating, setIsGenerating] = useState(false);
  const [progress, setProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<GenerationResult | null>(null);

  const abortControllerRef = useRef<AbortController | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  const connectWebSocket = useCallback((generationId: string) => {
    const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/generation/${generationId}`;

    wsRef.current = new WebSocket(wsUrl);

    wsRef.current.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === 'progress') {
        setProgress(data.progress);
        setCurrentStep(data.step);
      } else if (data.type === 'complete') {
        setResult(data.result);
        setIsGenerating(false);
        setProgress(100);
        wsRef.current?.close();
      } else if (data.type === 'error') {
        setError(data.message);
        setIsGenerating(false);
        wsRef.current?.close();
      }
    };

    wsRef.current.onerror = () => {
      setError('WebSocket connection failed');
      setIsGenerating(false);
    };
  }, []);

  const generateSection = useCallback(
    async (
      section: string,
      options?: GenerationOptions
    ): Promise<GenerationResult | null> => {
      setIsGenerating(true);
      setProgress(0);
      setCurrentStep(`Preparing ${section} generation...`);
      setError(null);
      setResult(null);

      abortControllerRef.current = new AbortController();

      try {
        const response = await manuscriptApi.generateSection(
          projectId,
          section,
          {
            ...options,
            signal: abortControllerRef.current.signal,
          }
        );

        // Connect to WebSocket for progress when backend returns generationId
        if (response.generationId) {
          connectWebSocket(response.generationId);
        }

        // For sync responses (current backend)
        if (response.result) {
          setResult(response.result);
          setIsGenerating(false);
          setProgress(100);
          return response.result;
        }

        return null;
      } catch (err) {
        if (err instanceof Error && err.name === 'AbortError') {
          setCurrentStep('Generation cancelled');
        } else {
          setError(err instanceof Error ? err.message : 'Generation failed');
        }
        setIsGenerating(false);
        return null;
      }
    },
    [projectId, connectWebSocket]
  );

  const generateFullManuscript = useCallback(
    async (options?: GenerationOptions): Promise<GenerationResult | null> => {
      return generateSection('full', options);
    },
    [generateSection]
  );

  const cancelGeneration = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    if (wsRef.current) {
      wsRef.current.close();
    }
    setIsGenerating(false);
    setCurrentStep('Cancelled');
  }, []);

  return {
    isGenerating,
    progress,
    currentStep,
    error,
    result,
    generateSection,
    generateFullManuscript,
    cancelGeneration,
  };
}
