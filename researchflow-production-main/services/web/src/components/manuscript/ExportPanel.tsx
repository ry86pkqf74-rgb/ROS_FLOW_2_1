/**
 * ExportPanel - Manuscript export with format, journal style, options, and download
 */

import React, { useState, useCallback, useEffect } from 'react';
import { Download, Eye, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { useManuscriptExport } from '@/hooks/useManuscriptExport';
import { exportApi, type ExportFormat } from '@/api/export';
import { JournalStyleSelector } from './JournalStyleSelector';
import { ExportProgress } from './ExportProgress';
import { ManuscriptPreview } from './ManuscriptPreview';
import { cn } from '@/lib/utils';

const STORAGE_FORMAT = 'researchflow_export_format';
const STORAGE_JOURNAL = 'researchflow_export_journal_style';

const FORMAT_OPTIONS: { value: ExportFormat; label: string }[] = [
  { value: 'docx', label: 'DOCX' },
  { value: 'pdf', label: 'PDF' },
  { value: 'latex', label: 'LaTeX' },
  { value: 'html', label: 'Markdown' },
  { value: 'odt', label: 'ODT' },
  { value: 'epub', label: 'EPUB' },
];

export interface ExportPanelProps {
  manuscriptId: string;
  manuscriptTitle?: string;
  onClose?: () => void;
  defaultFormat?: ExportFormat;
  defaultJournalKey?: string | null;
  className?: string;
}

export function ExportPanel({
  manuscriptId,
  manuscriptTitle,
  onClose,
  defaultFormat,
  defaultJournalKey,
  className,
}: ExportPanelProps) {
  const [format, setFormat] = useState<ExportFormat>(() => {
    if (defaultFormat) return defaultFormat;
    try {
      const s = localStorage.getItem(STORAGE_FORMAT);
      if (s && FORMAT_OPTIONS.some((o) => o.value === s)) return s as ExportFormat;
    } catch {
      // ignore
    }
    return 'docx';
  });
  const [journalKey, setJournalKey] = useState<string | null>(() => {
    if (defaultJournalKey !== undefined) return defaultJournalKey;
    try {
      return localStorage.getItem(STORAGE_JOURNAL);
    } catch {
      return null;
    }
  });
  const [includeSupplementary, setIncludeSupplementary] = useState(false);
  const [includeTrackChanges, setIncludeTrackChanges] = useState(false);
  const [includeComplianceAppendix, setIncludeComplianceAppendix] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewMarkdown, setPreviewMarkdown] = useState<string | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);

  const {
    jobId,
    status,
    progress,
    currentStep,
    error,
    startExport,
    download,
    cancel,
    reset,
  } = useManuscriptExport();

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_FORMAT, format);
    } catch {
      // ignore
    }
  }, [format]);
  useEffect(() => {
    try {
      if (journalKey) localStorage.setItem(STORAGE_JOURNAL, journalKey);
    } catch {
      // ignore
    }
  }, [journalKey]);

  const handleStartExport = useCallback(async () => {
    reset();
    const options = {
      output_format: format,
      include_track_changes: includeTrackChanges,
      include_comments: false,
      include_supplementary: includeSupplementary,
      custom_options: includeComplianceAppendix
        ? { include_compliance_appendix: true }
        : undefined,
      ...(journalKey ? { citation_style: journalKey } : {}),
    };
    await startExport(manuscriptId, options);
  }, [
    manuscriptId,
    format,
    journalKey,
    includeSupplementary,
    includeTrackChanges,
    includeComplianceAppendix,
    startExport,
    reset,
  ]);

  const handlePreview = useCallback(async () => {
    setPreviewLoading(true);
    setPreviewMarkdown(null);
    setPreviewOpen(true);
    try {
      const data = await exportApi.getPreview(manuscriptId, {
        output_format: format,
        ...(journalKey ? { template: journalKey } : {}),
      });
      setPreviewMarkdown(data.preview_markdown ?? '');
    } catch {
      setPreviewMarkdown('');
    } finally {
      setPreviewLoading(false);
    }
  }, [manuscriptId, format, journalKey]);

  const handleDownload = useCallback(() => {
    if (jobId) download(jobId);
  }, [jobId, download]);

  const handleCancel = useCallback(() => {
    if (jobId) cancel(jobId);
  }, [jobId, cancel]);

  const isProcessing = status === 'processing';
  const isCompleted = status === 'completed';
  const isFailed = status === 'failed';

  return (
    <Card className={cn('w-full', className)}>
      <CardHeader>
        <CardTitle>Export manuscript</CardTitle>
        <CardDescription>
          Choose format, journal style, and options. Preview before exporting if needed.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Format */}
        <div className="space-y-2">
          <Label>Format</Label>
          <Select
            value={format}
            onValueChange={(v) => setFormat(v as ExportFormat)}
            disabled={isProcessing}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {FORMAT_OPTIONS.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Journal style */}
        <JournalStyleSelector
          value={journalKey}
          onChange={setJournalKey}
          disabled={isProcessing}
        />

        {/* Options */}
        <div className="space-y-3">
          <Label>Options</Label>
          <div className="flex items-center justify-between">
            <span className="text-sm">Include supplementary materials</span>
            <Switch
              checked={includeSupplementary}
              onCheckedChange={setIncludeSupplementary}
              disabled={isProcessing}
            />
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm">Include track changes</span>
            <Switch
              checked={includeTrackChanges}
              onCheckedChange={setIncludeTrackChanges}
              disabled={isProcessing}
            />
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm">Include compliance appendix</span>
            <Switch
              checked={includeComplianceAppendix}
              onCheckedChange={setIncludeComplianceAppendix}
              disabled={isProcessing}
            />
          </div>
        </div>

        {/* Preview before export */}
        <Button
          variant="outline"
          className="w-full"
          onClick={handlePreview}
          disabled={isProcessing}
        >
          <Eye className="mr-2 h-4 w-4" />
          Preview before export
        </Button>

        {/* Progress */}
        {(isProcessing || isCompleted || isFailed) && (
          <ExportProgress
            progress={progress}
            currentStep={currentStep}
            status={isProcessing ? 'processing' : isCompleted ? 'completed' : 'failed'}
            onCancel={isProcessing ? handleCancel : undefined}
          />
        )}

        {/* Error */}
        {error && (
          <p className="text-sm text-destructive">{error}</p>
        )}

        {/* Actions */}
        <div className="flex gap-2">
          {isCompleted && jobId ? (
            <Button className="flex-1" onClick={handleDownload}>
              <Download className="mr-2 h-4 w-4" />
              Download
            </Button>
          ) : (
            <Button
              className="flex-1"
              onClick={handleStartExport}
              disabled={isProcessing}
            >
              {isProcessing ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Exporting...
                </>
              ) : (
                <>
                  <Download className="mr-2 h-4 w-4" />
                  Export
                </>
              )}
            </Button>
          )}
          {onClose && (
            <Button variant="outline" onClick={onClose}>
              Close
            </Button>
          )}
        </div>
      </CardContent>

      {/* Preview dialog */}
      <Dialog open={previewOpen} onOpenChange={setPreviewOpen}>
        <DialogContent className="max-w-4xl max-h-[85vh] flex flex-col">
          <DialogHeader>
            <DialogTitle>Preview</DialogTitle>
          </DialogHeader>
          <div className="flex-1 min-h-0 overflow-hidden">
            {previewLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
              </div>
            ) : (
              <ManuscriptPreview
                manuscriptId={manuscriptId}
                previewMarkdown={previewMarkdown ?? undefined}
                title={manuscriptTitle}
                printMode={false}
              />
            )}
          </div>
        </DialogContent>
      </Dialog>
    </Card>
  );
}
