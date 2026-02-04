/**
 * useManuscriptExport - Hook for manuscript export with progress polling and download
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import { useToast } from '@/hooks/use-toast';
import {
  exportApi,
  type StartExportOptions,
  type ExportFormat,
} from '@/api/export';

export type ExportStatus =
  | 'idle'
  | 'processing'
  | 'completed'
  | 'failed'
  | 'cancelled';

export interface UseManuscriptExportReturn {
  jobId: string | null;
  status: ExportStatus;
  progress: number;
  currentStep: string;
  error: string | null;
  outputUrl: string | null;
  outputFilename: string | null;
  estimateSeconds: number | null;
  startExport: (
    manuscriptId: string,
    options: StartExportOptions
  ) => Promise<string | null>;
  download: (jobId: string, filename?: string | null) => Promise<void>;
  cancel: (jobId: string) => Promise<void>;
  reset: () => void;
}

const POLL_INTERVAL_MS = 1500;

export function useManuscriptExport(): UseManuscriptExportReturn {
  const { toast } = useToast();
  const [jobId, setJobId] = useState<string | null>(null);
  const [status, setStatus] = useState<ExportStatus>('idle');
  const [progress, setProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [outputUrl, setOutputUrl] = useState<string | null>(null);
  const [outputFilename, setOutputFilename] = useState<string | null>(null);
  const [estimateSeconds, setEstimateSeconds] = useState<number | null>(null);

  const pollTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const stopPolling = useCallback(() => {
    if (pollTimerRef.current) {
      clearTimeout(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  }, []);

  useEffect(() => {
    return () => stopPolling();
  }, [stopPolling]);

  const startExport = useCallback(
    async (
      manuscriptId: string,
      options: StartExportOptions
    ): Promise<string | null> => {
      setError(null);
      setProgress(0);
      setCurrentStep('Starting export...');
      setStatus('processing');
      setOutputUrl(null);
      setEstimateSeconds(null);

      try {
        const result = await exportApi.startExport(manuscriptId, options);
        const id = result.job_id;
        setJobId(id);

        const poll = async () => {
          try {
            const job = await exportApi.getJobStatus(id);
            setProgress(job.progress ?? 0);
            if (job.status === 'processing') {
              setCurrentStep(
                job.error_message || `Exporting (${job.progress ?? 0}%)...`
              );
              pollTimerRef.current = setTimeout(poll, POLL_INTERVAL_MS);
              return;
            }
            if (job.status === 'completed') {
              setProgress(100);
              setCurrentStep('Export ready');
              setStatus('completed');
              setOutputUrl(job.output_url ?? null);
              setOutputFilename(job.output_filename ?? null);
              stopPolling();
              toast({ title: 'Export ready', description: 'Your file is ready to download.' });
              return;
            }
            if (job.status === 'failed') {
              setStatus('failed');
              setError(job.error_message || 'Export failed');
              stopPolling();
              toast({
                title: 'Export failed',
                description: job.error_message || 'Unknown error',
                variant: 'destructive',
              });
            }
          } catch (err) {
            setStatus('failed');
            const msg = err instanceof Error ? err.message : 'Export failed';
            setError(msg);
            stopPolling();
            toast({
              title: 'Export failed',
              description: msg,
              variant: 'destructive',
            });
          }
        };

        pollTimerRef.current = setTimeout(poll, POLL_INTERVAL_MS);
        return id;
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Failed to start export';
        setError(msg);
        setStatus('failed');
        toast({
          title: 'Export failed',
          description: msg,
          variant: 'destructive',
        });
        return null;
      }
    },
    [toast, stopPolling]
  );

  const download = useCallback(
    async (id: string, filename?: string | null) => {
      try {
        const blob = await exportApi.downloadExport(id);
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download =
          filename ||
          (id === jobId ? outputFilename : null) ||
          `manuscript-export-${id}`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        toast({ title: 'Download complete', description: 'File saved.' });
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Download failed';
        toast({
          title: 'Download failed',
          description: msg,
          variant: 'destructive',
        });
      }
    },
    [toast, jobId, outputFilename]
  );

  const cancel = useCallback(
    async (id: string) => {
      try {
        await exportApi.cancelJob(id);
        stopPolling();
        setStatus('cancelled');
        setCurrentStep('Cancelled');
      } catch (err) {
        toast({
          title: 'Cancel failed',
          description: err instanceof Error ? err.message : 'Could not cancel',
          variant: 'destructive',
        });
      }
    },
    [toast, stopPolling]
  );

  const reset = useCallback(() => {
    stopPolling();
    setJobId(null);
    setStatus('idle');
    setProgress(0);
    setCurrentStep('');
    setError(null);
    setOutputUrl(null);
    setOutputFilename(null);
    setEstimateSeconds(null);
  }, [stopPolling]);

  return {
    jobId,
    status,
    progress,
    currentStep,
    error,
    outputUrl,
    outputFilename,
    estimateSeconds,
    startExport,
    download,
    cancel,
    reset,
  };
}
