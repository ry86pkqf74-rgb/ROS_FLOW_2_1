/**
 * Stage 17 - Revision (manuscript writing pipeline)
 * Diff view, PHI re-scan, point-by-point response
 */

import * as React from 'react';
import { useState, useCallback } from 'react';
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  CardDescription,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Shield, AlertTriangle, Check, FileDiff } from 'lucide-react';
import { scanPhi } from '@/lib/api';
import { useToast } from '@/hooks/use-toast';

interface StageProps {
  workflowId: string;
  manuscriptId?: string;
  onComplete: () => void;
}

export function Stage17Revision({
  workflowId,
  manuscriptId,
  onComplete,
}: StageProps) {
  const [pointByPointResponse, setPointByPointResponse] = useState('');
  const [phiRescanStatus, setPhiRescanStatus] = useState<'pending' | 'clear' | 'violations'>('pending');
  const [isScanning, setIsScanning] = useState(false);
  const { toast } = useToast();

  const handleRescanPHI = useCallback(async () => {
    setIsScanning(true);
    try {
      const result = await scanPhi({
        content: pointByPointResponse || ' ',
        contentType: 'text',
        governanceMode: 'DEMO',
        projectId: workflowId,
        stageId: 17,
      });
      const hasViolations = result.hasViolations ?? (result.violations?.length ?? 0) > 0;
      setPhiRescanStatus(hasViolations ? 'violations' : 'clear');
      if (hasViolations) {
        toast({
          title: 'PHI detected on re-scan',
          description: 'Please redact before completing.',
          variant: 'destructive',
        });
      } else {
        toast({ title: 'PHI re-scan passed', description: 'No PHI detected.' });
      }
    } catch (err) {
      setPhiRescanStatus('pending');
      toast({
        title: 'PHI re-scan failed',
        description: err instanceof Error ? err.message : 'Scan failed',
        variant: 'destructive',
      });
    } finally {
      setIsScanning(false);
    }
  }, [pointByPointResponse, workflowId, toast]);

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileDiff className="h-5 w-5" />
            Diff view
          </CardTitle>
          <CardDescription>Compare manuscript versions (placeholder).</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">Diff view placeholder — integrate with version comparison when available.</p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            PHI re-scan
            <Badge variant={phiRescanStatus === 'clear' ? 'default' : phiRescanStatus === 'violations' ? 'destructive' : 'secondary'}>
              {phiRescanStatus === 'clear' ? 'PHI Cleared' : phiRescanStatus === 'violations' ? 'PHI Detected' : 'Pending'}
            </Badge>
          </CardTitle>
          <CardDescription>Re-scan revised content for PHI before finalizing.</CardDescription>
        </CardHeader>
        <CardContent>
          <Alert variant={phiRescanStatus === 'violations' ? 'destructive' : 'default'}>
            <Shield className="h-4 w-4" />
            <AlertDescription>
              {phiRescanStatus === 'clear' && (
                <span className="flex items-center gap-2">
                  <Check className="h-4 w-4 text-green-500" />
                  PHI re-scan passed
                </span>
              )}
              {phiRescanStatus === 'violations' && (
                <span className="flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4" />
                  PHI detected — redact before completing
                </span>
              )}
              {phiRescanStatus === 'pending' && 'Run re-scan to verify revised content.'}
            </AlertDescription>
          </Alert>
          <Button
            type="button"
            variant="outline"
            className="mt-2"
            onClick={handleRescanPHI}
            disabled={isScanning}
          >
            {isScanning ? 'Scanning...' : 'Re-scan for PHI'}
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Point-by-point response</CardTitle>
          <CardDescription>Author response to each reviewer comment.</CardDescription>
        </CardHeader>
        <CardContent>
          <Textarea
            value={pointByPointResponse}
            onChange={(e) => {
              setPointByPointResponse(e.target.value);
              setPhiRescanStatus('pending');
            }}
            className="min-h-[180px] resize-y"
            placeholder="e.g. Comment 1: We have added... Comment 2: We agree and revised..."
          />
        </CardContent>
      </Card>

      <div className="flex justify-end gap-2">
        <Button onClick={onComplete} disabled={phiRescanStatus !== 'clear'}>
          Complete Stage
        </Button>
      </div>
    </div>
  );
}

export default Stage17Revision;
