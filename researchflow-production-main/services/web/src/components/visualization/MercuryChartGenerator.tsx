/**
 * Mercury Chart Generator Component
 * 
 * Generates publication-quality charts using Mercury backend (DataVisualizationAgent).
 * Integrates with existing Plotly-based InteractiveChartBuilder for preview.
 * 
 * Features:
 * - Chart type selection (7 types)
 * - Configuration panel (styles, colors, DPI)
 * - Real-time preview
 * - Export to Mercury backend
 * - Download options (PNG, SVG, PDF)
 */

import React, { useState, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useToast } from '@/hooks/use-toast';
import { Loader2, Download, FileImage, Sparkles } from 'lucide-react';
import { useVisualization } from '@/hooks/useVisualization';

export interface MercuryChartConfig {
  chart_type: 'bar_chart' | 'line_chart' | 'scatter_plot' | 'box_plot' | 'forest_plot' | 'flowchart' | 'kaplan_meier';
  data: Record<string, any>;
  config?: {
    title?: string;
    x_label?: string;
    y_label?: string;
    show_error_bars?: boolean;
    show_markers?: boolean;
    show_trendline?: boolean;
    show_confidence_bands?: boolean;
    show_outliers?: boolean;
    show_means?: boolean;
    color_palette?: string;
    journal_style?: string;
    dpi?: number;
    width?: number;
    height?: number;
  };
  research_id?: string;
}

export interface MercuryChartGeneratorProps {
  researchId?: string;
  initialData?: Record<string, any>;
  onChartGenerated?: (result: any) => void;
}

const CHART_TYPES = [
  { value: 'bar_chart', label: 'Bar Chart', icon: '📊' },
  { value: 'line_chart', label: 'Line Chart', icon: '📈' },
  { value: 'scatter_plot', label: 'Scatter Plot', icon: '⚬' },
  { value: 'box_plot', label: 'Box Plot', icon: '☐' },
  { value: 'forest_plot', label: 'Forest Plot', icon: '🌲' },
  { value: 'flowchart', label: 'Flowchart', icon: '📋' },
  { value: 'kaplan_meier', label: 'Kaplan-Meier', icon: '📉' },
];

const JOURNAL_STYLES = [
  { value: 'nature', label: 'Nature' },
  { value: 'jama', label: 'JAMA' },
  { value: 'nejm', label: 'NEJM' },
  { value: 'lancet', label: 'The Lancet' },
  { value: 'bmj', label: 'BMJ' },
  { value: 'plos', label: 'PLOS ONE' },
  { value: 'apa', label: 'APA Style' },
];

const COLOR_PALETTES = [
  { value: 'colorblind_safe', label: 'Colorblind Safe (Default)' },
  { value: 'grayscale', label: 'Grayscale' },
  { value: 'viridis', label: 'Viridis' },
  { value: 'pastel', label: 'Pastel' },
  { value: 'bold', label: 'Bold' },
];

const DPI_OPTIONS = [
  { value: 72, label: '72 DPI (Screen)' },
  { value: 150, label: '150 DPI (Draft)' },
  { value: 300, label: '300 DPI (Print)' },
  { value: 600, label: '600 DPI (High-Res)' },
];

export function MercuryChartGenerator({
  researchId,
  initialData,
  onChartGenerated,
}: MercuryChartGeneratorProps) {
  const { toast } = useToast();
  const { generateChart, loading } = useVisualization();

  const [chartType, setChartType] = useState<string>('bar_chart');
  const [title, setTitle] = useState('');
  const [xLabel, setXLabel] = useState('');
  const [yLabel, setYLabel] = useState('');
  const [journalStyle, setJournalStyle] = useState('nature');
  const [colorPalette, setColorPalette] = useState('colorblind_safe');
  const [dpi, setDpi] = useState(300);
  const [chartResult, setChartResult] = useState<any>(null);

  const handleGenerate = useCallback(async () => {
    if (!initialData) {
      toast({
        title: 'No data provided',
        description: 'Please provide data for chart generation',
        variant: 'destructive',
      });
      return;
    }

    const config: MercuryChartConfig = {
      chart_type: chartType as any,
      data: initialData,
      config: {
        title: title || undefined,
        x_label: xLabel || undefined,
        y_label: yLabel || undefined,
        journal_style: journalStyle,
        color_palette: colorPalette,
        dpi,
      },
      research_id: researchId,
    };

    try {
      const result = await generateChart(config);
      setChartResult(result);
      
      toast({
        title: 'Chart generated',
        description: 'Publication-quality chart generated successfully',
      });

      onChartGenerated?.(result);
    } catch (error) {
      toast({
        title: 'Generation failed',
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: 'destructive',
      });
    }
  }, [
    chartType,
    title,
    xLabel,
    yLabel,
    journalStyle,
    colorPalette,
    dpi,
    initialData,
    researchId,
    generateChart,
    toast,
    onChartGenerated,
  ]);

  const handleDownload = useCallback(() => {
    if (!chartResult?.result?.image_base64) {
      toast({
        title: 'No chart available',
        description: 'Generate a chart first',
        variant: 'destructive',
      });
      return;
    }

    // Create download link
    const link = document.createElement('a');
    link.href = `data:image/png;base64,${chartResult.result.image_base64}`;
    link.download = `chart-${Date.now()}.png`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    toast({
      title: 'Download started',
      description: 'Chart downloaded successfully',
    });
  }, [chartResult, toast]);

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5" />
            Mercury Chart Generator
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Chart Type Selection */}
          <div className="space-y-2">
            <Label>Chart Type</Label>
            <Select value={chartType} onValueChange={setChartType}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {CHART_TYPES.map((type) => (
                  <SelectItem key={type.value} value={type.value}>
                    <span className="flex items-center gap-2">
                      <span>{type.icon}</span>
                      <span>{type.label}</span>
                    </span>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Title */}
          <div className="space-y-2">
            <Label htmlFor="title">Chart Title</Label>
            <Input
              id="title"
              placeholder="e.g., Treatment Outcomes"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </div>

          {/* Axis Labels */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="x-label">X-Axis Label</Label>
              <Input
                id="x-label"
                placeholder="e.g., Group"
                value={xLabel}
                onChange={(e) => setXLabel(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="y-label">Y-Axis Label</Label>
              <Input
                id="y-label"
                placeholder="e.g., Pain Score"
                value={yLabel}
                onChange={(e) => setYLabel(e.target.value)}
              />
            </div>
          </div>

          {/* Journal Style */}
          <div className="space-y-2">
            <Label>Journal Style</Label>
            <Select value={journalStyle} onValueChange={setJournalStyle}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {JOURNAL_STYLES.map((style) => (
                  <SelectItem key={style.value} value={style.value}>
                    {style.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Color Palette */}
          <div className="space-y-2">
            <Label>Color Palette</Label>
            <Select value={colorPalette} onValueChange={setColorPalette}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {COLOR_PALETTES.map((palette) => (
                  <SelectItem key={palette.value} value={palette.value}>
                    {palette.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* DPI */}
          <div className="space-y-2">
            <Label>Resolution (DPI)</Label>
            <Select value={String(dpi)} onValueChange={(v) => setDpi(Number(v))}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {DPI_OPTIONS.map((option) => (
                  <SelectItem key={option.value} value={String(option.value)}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Generate Button */}
          <Button
            onClick={handleGenerate}
            disabled={loading || !initialData}
            className="w-full"
          >
            {loading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Generating...
              </>
            ) : (
              <>
                <FileImage className="mr-2 h-4 w-4" />
                Generate Publication Chart
              </>
            )}
          </Button>
        </CardContent>
      </Card>

      {/* Chart Preview */}
      {chartResult && (
        <Card>
          <CardHeader>
            <CardTitle>Generated Chart</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {chartResult.result?.image_base64 && (
              <div className="space-y-4">
                <img
                  src={`data:image/png;base64,${chartResult.result.image_base64}`}
                  alt={chartResult.result.alt_text || 'Generated chart'}
                  className="w-full border rounded-lg shadow-sm"
                />
                {chartResult.result.caption && (
                  <p className="text-sm text-muted-foreground italic">
                    {chartResult.result.caption}
                  </p>
                )}
                <div className="flex gap-2">
                  <Button onClick={handleDownload} variant="outline">
                    <Download className="mr-2 h-4 w-4" />
                    Download PNG
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
