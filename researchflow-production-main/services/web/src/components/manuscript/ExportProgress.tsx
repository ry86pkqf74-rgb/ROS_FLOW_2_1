/**
 * ExportProgress - Multi-step progress indicator for manuscript export
 */

import React from 'react';
import { Loader2, CheckCircle, XCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { cn } from '@/lib/utils';

export interface ExportProgressProps {
  progress: number;
  currentStep: string;
  estimateSeconds?: number;
  onCancel?: () => void;
  status: 'processing' | 'completed' | 'failed';
  className?: string;
}

export function ExportProgress({
  progress,
  currentStep,
  estimateSeconds,
  onCancel,
  status,
  className,
}: ExportProgressProps) {
  const hasEstimate = typeof estimateSeconds === 'number' && estimateSeconds > 0;
  const estimateLabel = hasEstimate
    ? `About ${Math.ceil(estimateSeconds / 60)} min remaining`
    : null;

  return (
    <div className={cn('space-y-3', className)}>
      {status === 'processing' && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin shrink-0" />
          <span>{currentStep || 'Exporting...'}</span>
        </div>
      )}
      {status === 'completed' && (
        <div className="flex items-center gap-2 text-sm text-green-600 dark:text-green-500">
          <CheckCircle className="h-4 w-4 shrink-0" />
          <span>{currentStep || 'Export ready'}</span>
        </div>
      )}
      {status === 'failed' && (
        <div className="flex items-center gap-2 text-sm text-destructive">
          <XCircle className="h-4 w-4 shrink-0" />
          <span>{currentStep || 'Export failed'}</span>
        </div>
      )}

      {(status === 'processing' || status === 'completed') && (
        <Progress value={progress} className="h-2" />
      )}

      {estimateLabel && status === 'processing' && (
        <p className="text-xs text-muted-foreground">{estimateLabel}</p>
      )}

      {status === 'processing' && onCancel && (
        <Button variant="outline" size="sm" onClick={onCancel}>
          Cancel
        </Button>
      )}
    </div>
  );
}
