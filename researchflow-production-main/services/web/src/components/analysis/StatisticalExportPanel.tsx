/**
 * Statistical Analysis Export Panel
 *
 * Specialized export functionality for statistical analysis results,
 * supporting multiple formats and customizable content sections.
 */

import React, { useState, useCallback } from 'react';
import { Download, FileText, FileImage, FileSpreadsheet, Clock, Check, AlertTriangle } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Separator } from '@/components/ui/separator';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';

import {
  StatisticalAnalysisResult,
  ExportFormat,
  ExportAnalysisRequest
} from '@/types/statistical-analysis';

interface StatisticalExportPanelProps {
  /** Analysis results to export */
  results: StatisticalAnalysisResult;
  /** Called when export is initiated */
  onExport: (request: ExportAnalysisRequest) => Promise<{ downloadUrl: string; filename: string }>;
  /** Whether export is currently in progress */
  isExporting?: boolean;
}

interface ExportState {
  format: ExportFormat;
  sections: {
    descriptiveStats: boolean;
    hypothesisTest: boolean;
    effectSizes: boolean;
    assumptions: boolean;
    visualizations: boolean;
    apaText: boolean;
  };
  template: string;
  filename: string;
  includeRawData: boolean;
  includeCode: boolean;
  customNotes: string;
}

const EXPORT_FORMATS: Array<{
  value: ExportFormat;
  label: string;
  description: string;
  icon: React.ReactNode;
  supports: string[];
}> = [
  {
    value: 'pdf',
    label: 'PDF Report',
    description: 'Publication-ready formatted report',
    icon: <FileText className="h-4 w-4" />,
    supports: ['All sections', 'Custom formatting', 'High-quality charts']
  },
  {
    value: 'docx',
    label: 'Word Document',
    description: 'Editable Microsoft Word document',
    icon: <FileText className="h-4 w-4" />,
    supports: ['All sections', 'Editable text', 'Tables and charts']
  },
  {
    value: 'html',
    label: 'Web Page',
    description: 'Interactive HTML report',
    icon: <FileText className="h-4 w-4" />,
    supports: ['Interactive charts', 'Responsive layout', 'Online sharing']
  },
  {
    value: 'csv',
    label: 'CSV Data',
    description: 'Raw data and statistics only',
    icon: <FileSpreadsheet className="h-4 w-4" />,
    supports: ['Descriptive stats', 'Test results', 'Raw data']
  },
  {
    value: 'json',
    label: 'JSON Data',
    description: 'Complete machine-readable format',
    icon: <FileText className="h-4 w-4" />,
    supports: ['Complete results', 'API integration', 'Data analysis']
  }
];

const TEMPLATES = [
  { value: 'default', label: 'Default Report', description: 'Standard scientific format' },
  { value: 'apa', label: 'APA Style', description: 'American Psychological Association format' },
  { value: 'nature', label: 'Nature Style', description: 'Nature journal format' },
  { value: 'clinical', label: 'Clinical Trial', description: 'Clinical research format' },
  { value: 'minimal', label: 'Minimal', description: 'Clean, minimal design' }
];

export function StatisticalExportPanel({ 
  results, 
  onExport, 
  isExporting = false 
}: StatisticalExportPanelProps) {
  const [exportState, setExportState] = useState<ExportState>({
    format: 'pdf',
    sections: {
      descriptiveStats: true,
      hypothesisTest: true,
      effectSizes: true,
      assumptions: true,
      visualizations: true,
      apaText: true
    },
    template: 'default',
    filename: `statistical-analysis-${results.id}`,
    includeRawData: false,
    includeCode: false,
    customNotes: ''
  });

  const [exportProgress, setExportProgress] = useState(0);
  const [lastExport, setLastExport] = useState<{ url: string; filename: string } | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);

  // Update export state
  const updateExportState = useCallback((updates: Partial<ExportState>) => {
    setExportState(prev => ({ ...prev, ...updates }));
  }, []);

  // Toggle section inclusion
  const toggleSection = useCallback((section: keyof ExportState['sections']) => {
    setExportState(prev => ({
      ...prev,
      sections: {
        ...prev.sections,
        [section]: !prev.sections[section]
      }
    }));
  }, []);

  // Get selected format info
  const selectedFormat = EXPORT_FORMATS.find(f => f.value === exportState.format);

  // Estimate export size
  const estimatedSize = React.useMemo(() => {
    let size = 0;
    if (exportState.sections.descriptiveStats) size += 50;
    if (exportState.sections.hypothesisTest) size += 100;
    if (exportState.sections.assumptions) size += 75;
    if (exportState.sections.visualizations) size += 500;
    if (exportState.includeRawData) size += 200;
    
    const formatMultiplier = {
      pdf: 1.5,
      docx: 1.2,
      html: 0.8,
      csv: 0.2,
      json: 0.3
    };
    
    return Math.round(size * formatMultiplier[exportState.format]);
  }, [exportState]);

  // Handle export
  const handleExport = useCallback(async () => {
    setExportProgress(0);
    
    const request: ExportAnalysisRequest = {
      analysisId: results.id,
      format: exportState.format,
      sections: exportState.sections,
      template: exportState.template
    };

    try {
      // Simulate progress for user feedback
      const progressInterval = setInterval(() => {
        setExportProgress(prev => Math.min(prev + 10, 90));
      }, 200);

      const result = await onExport(request);
      
      clearInterval(progressInterval);
      setExportProgress(100);
      setLastExport(result);
      
      // Trigger download
      const link = document.createElement('a');
      link.href = result.downloadUrl;
      link.download = result.filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      setTimeout(() => {
        setExportProgress(0);
        setIsDialogOpen(false);
      }, 1000);
      
    } catch (error) {
      console.error('Export failed:', error);
      setExportProgress(0);
    }
  }, [results.id, exportState, onExport]);

  // Quick export presets
  const quickExportPresets = [
    {
      name: 'Full Report',
      description: 'Complete analysis with all sections',
      format: 'pdf' as ExportFormat,
      sections: {
        descriptiveStats: true,
        hypothesisTest: true,
        effectSizes: true,
        assumptions: true,
        visualizations: true,
        apaText: true
      }
    },
    {
      name: 'Results Only',
      description: 'Key findings without diagnostics',
      format: 'docx' as ExportFormat,
      sections: {
        descriptiveStats: true,
        hypothesisTest: true,
        effectSizes: true,
        assumptions: false,
        visualizations: false,
        apaText: true
      }
    },
    {
      name: 'Data Export',
      description: 'Raw data and statistics',
      format: 'csv' as ExportFormat,
      sections: {
        descriptiveStats: true,
        hypothesisTest: true,
        effectSizes: false,
        assumptions: false,
        visualizations: false,
        apaText: false
      }
    }
  ];

  const applyPreset = (preset: typeof quickExportPresets[0]) => {
    updateExportState({
      format: preset.format,
      sections: preset.sections
    });
  };

  return (
    <div className="space-y-4">
      {/* Quick Export Buttons */}
      <div className="flex flex-wrap gap-2">
        {quickExportPresets.map((preset, index) => (
          <Button
            key={index}
            variant="outline"
            size="sm"
            onClick={() => applyPreset(preset)}
            disabled={isExporting}
          >
            <Download className="h-4 w-4 mr-1" />
            {preset.name}
          </Button>
        ))}
        
        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogTrigger asChild>
            <Button variant="outline" size="sm" disabled={isExporting}>
              <Download className="h-4 w-4 mr-1" />
              Custom Export
            </Button>
          </DialogTrigger>
          
          <DialogContent className="max-w-2xl max-h-[90vh] overflow-auto">
            <DialogHeader>
              <DialogTitle>Customize Export</DialogTitle>
            </DialogHeader>
            
            <div className="space-y-6 mt-4">
              {/* Format Selection */}
              <div className="space-y-3">
                <Label className="text-sm font-medium">Export Format</Label>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {EXPORT_FORMATS.map(format => (
                    <div
                      key={format.value}
                      className={`border rounded-lg p-3 cursor-pointer transition-colors ${
                        exportState.format === format.value
                          ? 'border-blue-500 bg-blue-50'
                          : 'border-gray-200 hover:border-gray-300'
                      }`}
                      onClick={() => updateExportState({ format: format.value })}
                    >
                      <div className="flex items-center gap-2 mb-1">
                        {format.icon}
                        <span className="font-medium">{format.label}</span>
                      </div>
                      <p className="text-sm text-gray-600 mb-2">{format.description}</p>
                      <div className="flex flex-wrap gap-1">
                        {format.supports.map(feature => (
                          <Badge key={feature} variant="outline" className="text-xs">
                            {feature}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Sections to Include */}
              <div className="space-y-3">
                <Label className="text-sm font-medium">Sections to Include</Label>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-3">
                    {Object.entries(exportState.sections).slice(0, 3).map(([key, value]) => (
                      <div key={key} className="flex items-center space-x-2">
                        <Checkbox
                          checked={value}
                          onCheckedChange={() => toggleSection(key as keyof ExportState['sections'])}
                        />
                        <Label className="text-sm capitalize">
                          {key.replace(/([A-Z])/g, ' $1').toLowerCase()}
                        </Label>
                      </div>
                    ))}
                  </div>
                  <div className="space-y-3">
                    {Object.entries(exportState.sections).slice(3).map(([key, value]) => (
                      <div key={key} className="flex items-center space-x-2">
                        <Checkbox
                          checked={value}
                          onCheckedChange={() => toggleSection(key as keyof ExportState['sections'])}
                        />
                        <Label className="text-sm capitalize">
                          {key.replace(/([A-Z])/g, ' $1').toLowerCase()}
                        </Label>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Template Selection */}
              {(exportState.format === 'pdf' || exportState.format === 'docx' || exportState.format === 'html') && (
                <div className="space-y-2">
                  <Label className="text-sm font-medium">Report Template</Label>
                  <Select
                    value={exportState.template}
                    onValueChange={(value) => updateExportState({ template: value })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {TEMPLATES.map(template => (
                        <SelectItem key={template.value} value={template.value}>
                          <div>
                            <div className="font-medium">{template.label}</div>
                            <div className="text-xs text-gray-500">{template.description}</div>
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}

              {/* Additional Options */}
              <div className="space-y-3">
                <Label className="text-sm font-medium">Additional Options</Label>
                <div className="space-y-3">
                  <div className="flex items-center space-x-2">
                    <Checkbox
                      checked={exportState.includeRawData}
                      onCheckedChange={(checked) => updateExportState({ includeRawData: !!checked })}
                    />
                    <Label className="text-sm">Include raw data</Label>
                  </div>
                  
                  <div className="flex items-center space-x-2">
                    <Checkbox
                      checked={exportState.includeCode}
                      onCheckedChange={(checked) => updateExportState({ includeCode: !!checked })}
                    />
                    <Label className="text-sm">Include R/Python code</Label>
                  </div>
                </div>
              </div>

              {/* Filename */}
              <div className="space-y-2">
                <Label className="text-sm font-medium">Filename</Label>
                <Input
                  value={exportState.filename}
                  onChange={(e) => updateExportState({ filename: e.target.value })}
                  placeholder="Enter filename (without extension)"
                />
              </div>

              {/* Custom Notes */}
              <div className="space-y-2">
                <Label className="text-sm font-medium">Custom Notes (optional)</Label>
                <Textarea
                  value={exportState.customNotes}
                  onChange={(e) => updateExportState({ customNotes: e.target.value })}
                  placeholder="Add any additional notes to include in the report..."
                  rows={3}
                />
              </div>

              {/* Export Info */}
              <div className="bg-gray-50 rounded-lg p-3 space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span>Estimated size:</span>
                  <span className="font-medium">{estimatedSize} KB</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span>Format:</span>
                  <span className="font-medium">{selectedFormat?.label}</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span>Sections included:</span>
                  <span className="font-medium">
                    {Object.values(exportState.sections).filter(Boolean).length}/6
                  </span>
                </div>
              </div>

              {/* Export Progress */}
              {isExporting && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span>Generating export...</span>
                    <span>{exportProgress}%</span>
                  </div>
                  <Progress value={exportProgress} />
                </div>
              )}

              {/* Export Actions */}
              <div className="flex gap-2 pt-4 border-t">
                <Button
                  onClick={handleExport}
                  disabled={isExporting || Object.values(exportState.sections).every(v => !v)}
                  className="flex-1"
                >
                  {isExporting ? (
                    <>
                      <Clock className="h-4 w-4 mr-2" />
                      Generating...
                    </>
                  ) : (
                    <>
                      <Download className="h-4 w-4 mr-2" />
                      Export {selectedFormat?.label}
                    </>
                  )}
                </Button>
                
                <Button
                  variant="outline"
                  onClick={() => setIsDialogOpen(false)}
                  disabled={isExporting}
                >
                  Cancel
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {/* Last Export Info */}
      {lastExport && (
        <Alert>
          <Check className="h-4 w-4" />
          <AlertDescription>
            Successfully exported: <strong>{lastExport.filename}</strong>
            <Button variant="link" className="h-auto p-0 ml-2" asChild>
              <a href={lastExport.url} target="_blank" rel="noopener noreferrer">
                Download again
              </a>
            </Button>
          </AlertDescription>
        </Alert>
      )}

      {/* Export Tips */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Export Tips</CardTitle>
        </CardHeader>
        <CardContent className="text-xs text-gray-600 space-y-2">
          <div className="flex items-start gap-2">
            <span>•</span>
            <span>PDF reports are best for sharing and publication</span>
          </div>
          <div className="flex items-start gap-2">
            <span>•</span>
            <span>Word documents allow for easy editing and collaboration</span>
          </div>
          <div className="flex items-start gap-2">
            <span>•</span>
            <span>CSV exports are ideal for further data analysis</span>
          </div>
          <div className="flex items-start gap-2">
            <span>•</span>
            <span>JSON format preserves all analysis metadata</span>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export default StatisticalExportPanel;