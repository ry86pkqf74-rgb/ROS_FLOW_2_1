/**
 * Statistical Explanation Dashboard
 *
 * Features:
 * - Decision tree visualization (Mermaid)
 * - Interactive reasoning viewer
 * - Audit trail timeline
 * - Export for IRB/compliance
 */

import React, { useState, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { DecisionTimeline, type DecisionEvent } from './DecisionTimeline';
import { MermaidDiagram } from './MermaidDiagram';
import { useToast } from '@/hooks/use-toast';
import {
  ListOrdered,
  GitBranch,
  FileText,
  Download,
  Copy,
  Loader2,
  FileJson,
  Shield,
} from 'lucide-react';
import { cn } from '@/lib/utils';

export interface StatisticalAuditResponse {
  decisions: DecisionEvent[];
  methodology?: string;
  diagram?: string;
  summary?: string;
}

export interface ExplanationDashboardProps {
  analysisId: string;
}

async function fetchStatisticalAudit(analysisId: string): Promise<StatisticalAuditResponse> {
  const res = await fetch(`/api/audit/statistical/${analysisId}`, { credentials: 'include' });
  if (!res.ok) throw new Error('Failed to load statistical audit');
  return res.json();
}

function MethodologyPreview({
  methodology,
  onCopyToManuscript,
}: {
  methodology: string;
  onCopyToManuscript?: () => void;
}) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm flex items-center gap-2">
          <FileText className="h-4 w-4" />
          Methodology
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="rounded-md border bg-muted/30 p-4 text-sm whitespace-pre-wrap font-mono">
          {methodology || 'No methodology text available.'}
        </div>
        {onCopyToManuscript && (
          <Button variant="outline" size="sm" onClick={onCopyToManuscript}>
            <Copy className="h-4 w-4 mr-2" />
            Copy to manuscript
          </Button>
        )}
      </CardContent>
    </Card>
  );
}

function ExportOptions({
  analysisId,
  onExportStart,
  onExportEnd,
}: {
  analysisId: string;
  onExportStart?: () => void;
  onExportEnd?: () => void;
}) {
  const { toast } = useToast();
  const [exporting, setExporting] = useState<string | null>(null);

  const handleExport = useCallback(
    async (format: 'pdf' | 'json' | 'compliance') => {
      setExporting(format);
      onExportStart?.();
      try {
        const res = await fetch(
          `/api/audit/statistical/${analysisId}/export?format=${format}`,
          { method: 'POST', credentials: 'include' }
        );
        if (!res.ok) throw new Error('Export failed');
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `statistical-audit-${analysisId}-${format}.${format === 'json' ? 'json' : 'pdf'}`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        toast({ title: 'Export complete', description: `Downloaded as ${format.toUpperCase()}.` });
      } catch (e) {
        toast({
          title: 'Export failed',
          description: e instanceof Error ? e.message : 'Unknown error',
          variant: 'destructive',
        });
      } finally {
        setExporting(null);
        onExportEnd?.();
      }
    },
    [analysisId, toast, onExportStart, onExportEnd]
  );

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm flex items-center gap-2">
          <Download className="h-4 w-4" />
          Export for IRB / compliance
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-sm text-muted-foreground">
          Export the statistical decision trail and methodology for review or submission.
        </p>
        <div className="flex flex-wrap gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleExport('pdf')}
            disabled={!!exporting}
          >
            {exporting === 'pdf' ? (
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
            ) : (
              <Download className="h-4 w-4 mr-2" />
            )}
            PDF
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleExport('json')}
            disabled={!!exporting}
          >
            {exporting === 'json' ? (
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
            ) : (
              <FileJson className="h-4 w-4 mr-2" />
            )}
            JSON
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleExport('compliance')}
            disabled={!!exporting}
          >
            {exporting === 'compliance' ? (
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
            ) : (
              <Shield className="h-4 w-4 mr-2" />
            )}
            Compliance bundle
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

export function StatisticalExplanationDashboard({ analysisId }: ExplanationDashboardProps) {
  const { toast } = useToast();
  const { data: auditTrail, isLoading, error } = useQuery({
    queryKey: ['audit', 'statistical', analysisId],
    queryFn: () => fetchStatisticalAudit(analysisId),
    enabled: !!analysisId,
  });

  const handleCopyToManuscript = useCallback(() => {
    if (auditTrail?.methodology) {
      navigator.clipboard.writeText(auditTrail.methodology);
      toast({ title: 'Copied', description: 'Methodology copied to clipboard.' });
    }
  }, [auditTrail?.methodology, toast]);

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-[400px] w-full" />
      </div>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent className="p-6 text-center text-destructive">
          <p className="font-medium">Failed to load explanation</p>
          <p className="text-sm mt-1">{error instanceof Error ? error.message : 'Unknown error'}</p>
        </CardContent>
      </Card>
    );
  }

  const decisions = auditTrail?.decisions ?? [];
  const methodology = auditTrail?.methodology ?? '';
  const diagram = auditTrail?.diagram ?? '';

  return (
    <div className={cn('space-y-4')}>
      <Tabs defaultValue="decisions" className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="decisions" className="flex items-center gap-2">
            <ListOrdered className="h-4 w-4" />
            Decisions
          </TabsTrigger>
          <TabsTrigger value="tree" className="flex items-center gap-2">
            <GitBranch className="h-4 w-4" />
            Decision Tree
          </TabsTrigger>
          <TabsTrigger value="methodology" className="flex items-center gap-2">
            <FileText className="h-4 w-4" />
            Methodology
          </TabsTrigger>
          <TabsTrigger value="export" className="flex items-center gap-2">
            <Download className="h-4 w-4" />
            Export
          </TabsTrigger>
        </TabsList>

        <TabsContent value="decisions" className="mt-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">Decision timeline</CardTitle>
              <p className="text-xs text-muted-foreground">
                Chronological audit trail of statistical decisions for this analysis.
              </p>
            </CardHeader>
            <CardContent>
              <DecisionTimeline events={decisions} />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="tree" className="mt-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">Decision tree</CardTitle>
              <p className="text-xs text-muted-foreground">
                Visual representation of the decision flow (Mermaid).
              </p>
            </CardHeader>
            <CardContent>
              <MermaidDiagram diagram={diagram} className="min-h-[300px]" />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="methodology" className="mt-4">
          <MethodologyPreview methodology={methodology} onCopyToManuscript={handleCopyToManuscript} />
        </TabsContent>

        <TabsContent value="export" className="mt-4">
          <ExportOptions analysisId={analysisId} />
        </TabsContent>
      </Tabs>

      {auditTrail?.summary && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Summary</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">{auditTrail.summary}</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
