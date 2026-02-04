/**
 * Stage 13 - Results Writing (manuscript writing pipeline)
 * PHI gate (critical), statistical results, figure/table insertion
 */

import * as React from 'react';
import { useState, useCallback } from 'react';
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Shield, AlertTriangle, Check, ImagePlus, Table2 } from 'lucide-react';
import { scanPhi } from '@/lib/api';
import { useToast } from '@/hooks/use-toast';

interface StageProps {
  workflowId: string;
  manuscriptId?: string;
  onComplete: () => void;
}

export function Stage13ResultsWriting({
  workflowId,
  manuscriptId,
  onComplete,
}: StageProps) {
  const [content, setContent] = useState('');
  const [phiStatus, setPhiStatus] = useState<'pending' | 'clear' | 'violations'>('pending');
  const [violations, setViolations] = useState<string[]>([]);
  const [isScanning, setIsScanning] = useState(false);
  const { toast } = useToast();

  const handleScanPHI = useCallback(async () => {
    setIsScanning(true);
    setViolations([]);
    try {
      const result = await scanPhi({
        content: content || ' ',
        contentType: 'text',
        governanceMode: 'DEMO',
        projectId: workflowId,
        stageId: 13,
      });
      const hasViolations = result.hasViolations ?? (result.violations?.length ?? 0) > 0;
      setPhiStatus(hasViolations ? 'violations' : 'clear');
      setViolations(
        (result.violations ?? []).map(
          (v) => v.type || v.suggestion || `Violation at ${v.location?.start ?? '?'}-${v.location?.end ?? '?'}`
        )
      );
      if (hasViolations) {
        toast({
          title: 'PHI detected',
          description: `${result.violations?.length ?? 0} item(s) require redaction.`,
          variant: 'destructive',
        });
      } else {
        toast({
          title: 'PHI scan passed',
          description: 'Content is safe to proceed.',
        });
      }
    } catch (err) {
      setPhiStatus('pending');
      setViolations([]);
      toast({
        title: 'PHI scan failed',
        description: err instanceof Error ? err.message : 'Failed to scan content for PHI',
        variant: 'destructive',
      });
    } finally {
      setIsScanning(false);
    }
  }, [content, workflowId, toast]);

  return (
    <div className="space-y-6">
      <Alert variant={phiStatus === 'clear' ? 'default' : phiStatus === 'violations' ? 'destructive' : 'default'}>
        <Shield className="h-4 w-4" />
        <AlertDescription>
          {phiStatus === 'clear' ? (
            <span className="flex items-center gap-2">
              <Check className="h-4 w-4 text-green-500" />
              PHI scan passed - content is safe to proceed
            </span>
          ) : phiStatus === 'violations' ? (
            <span className="flex flex-col gap-1">
              <span className="flex items-center gap-2">
                <AlertTriangle className="h-4 w-4" />
                PHI detected - {violations.length} item(s) require redaction
              </span>
              {violations.length > 0 && (
                <ul className="mt-2 list-disc pl-4 text-sm">
                  {violations.slice(0, 5).map((v, i) => (
                    <li key={i}>{v}</li>
                  ))}
                  {violations.length > 5 && (
                    <li>...and {violations.length - 5} more</li>
                  )}
                </ul>
              )}
            </span>
          ) : (
            'PHI scan required before proceeding'
          )}
        </AlertDescription>
      </Alert>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            Stage 13: Results Writing
            <Badge variant={phiStatus === 'clear' ? 'default' : 'destructive'}>
              {phiStatus === 'clear' ? 'PHI Cleared' : 'PHI Check Required'}
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <textarea
            value={content}
            onChange={(e) => {
              setContent(e.target.value);
              setPhiStatus('pending');
            }}
            className="w-full h-64 p-4 border rounded-lg resize-y"
            placeholder="Enter results content..."
          />
          <div className="flex gap-2">
            <Button type="button" variant="outline" size="sm">
              <ImagePlus className="h-4 w-4 mr-1" />
              Insert figure placeholder
            </Button>
            <Button type="button" variant="outline" size="sm">
              <Table2 className="h-4 w-4 mr-1" />
              Insert table placeholder
            </Button>
          </div>
        </CardContent>
      </Card>

      <div className="flex justify-end gap-2">
        <Button
          variant="outline"
          onClick={handleScanPHI}
          disabled={isScanning}
        >
          {isScanning ? 'Scanning...' : 'Scan for PHI'}
        </Button>
        <Button onClick={onComplete} disabled={phiStatus !== 'clear' || isScanning}>
          Complete Stage
        </Button>
      </div>
    </div>
  );
}

export default Stage13ResultsWriting;
