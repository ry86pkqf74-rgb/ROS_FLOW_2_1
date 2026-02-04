/**
 * Interactive Chart Builder with Plotly
 *
 * Features:
 * - Drag-and-drop variable mapping to axes
 * - Real-time preview with Plotly.js
 * - AI-suggested chart types based on data
 * - Export to SVG/PNG/PDF
 * - Accessibility color modes (colorblind safe)
 */

import React, { useState, useMemo, useCallback, useRef } from 'react';
import Plot from 'react-plotly.js';
import Plotly from 'plotly.js';
import {
  DndContext,
  DragEndEvent,
  useDraggable,
  PointerSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import { VariableDropZone } from './VariableDropZone';
import { ChartStylePanel } from './ChartStylePanel';
import {
  type DataColumn,
  type ChartConfig,
  type ChartStyle,
  type ChartType,
  type AxisMapping,
} from '@/components/stages';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useToast } from '@/hooks/use-toast';
import { Download, Sparkles, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

// Builder-only chart types (violin, kaplan_meier map to Plotly; save as boxplot/line in ChartConfig)
export type BuilderChartType =
  | ChartType
  | 'violin'
  | 'kaplan_meier';

export interface ChartSuggestion {
  id: string;
  chartType: BuilderChartType | ChartType;
  description: string;
  confidence?: number;
  suggestedConfig?: Partial<ChartConfig>;
}

export interface ChartBuilderProps {
  datasetId: string;
  columns: DataColumn[];
  data: Record<string, unknown>[];
  onSaveChart: (chart: ChartConfig) => Promise<void>;
  onGetAISuggestions: () => Promise<ChartSuggestion[]>;
}

const CHART_TYPES: { id: BuilderChartType; name: string; icon: string }[] = [
  { id: 'scatter', name: 'Scatter Plot', icon: '⚬' },
  { id: 'line', name: 'Line Chart', icon: '📈' },
  { id: 'bar', name: 'Bar Chart', icon: '📊' },
  { id: 'box', name: 'Box Plot', icon: '☐' },
  { id: 'histogram', name: 'Histogram', icon: '▥' },
  { id: 'heatmap', name: 'Heatmap', icon: '▦' },
  { id: 'violin', name: 'Violin Plot', icon: '🎻' },
  { id: 'kaplan_meier', name: 'Kaplan-Meier', icon: '📉' },
];

const DEFAULT_STYLE: ChartStyle = {
  title: '',
  width: 800,
  height: 600,
  showGrid: true,
  showDataLabels: false,
  colors: {
    primary: '#3b82f6',
    secondary: '#10b981',
    palette: [
      '#3b82f6',
      '#10b981',
      '#f59e0b',
      '#ef4444',
      '#8b5cf6',
      '#06b6d4',
    ],
    scheme: 'default',
  },
  legend: {
    show: true,
    position: 'right',
  },
  fontFamily: 'Inter, sans-serif',
  fontSize: 12,
  backgroundColor: '#ffffff',
};

const DROP_ZONE_X = 'drop-x-axis';
const DROP_ZONE_Y = 'drop-y-axis';
const DROP_ZONE_COLOR = 'drop-color-by';
const DROP_ZONE_SIZE = 'drop-size-by';

function mapBuilderChartTypeToConfig(t: BuilderChartType): ChartType {
  if (t === 'violin' || t === 'box') return 'boxplot';
  if (t === 'kaplan_meier') return 'line';
  return t as ChartType;
}

function DraggableColumn({
  column,
  isDisabled,
}: {
  column: DataColumn;
  isDisabled?: boolean;
}) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: column.id,
    data: { columnId: column.id },
  });

  return (
    <div
      ref={setNodeRef}
      {...listeners}
      {...attributes}
      className={cn(
        'flex items-center justify-between rounded border bg-background px-2 py-1.5 text-sm cursor-grab active:cursor-grabbing',
        isDragging && 'opacity-50',
        isDisabled && 'cursor-not-allowed opacity-60'
      )}
    >
      <span className="font-medium">{column.name}</span>
      <Badge variant="secondary" className="text-xs">
        {column.type}
      </Badge>
    </div>
  );
}

export function InteractiveChartBuilder({
  datasetId,
  columns,
  data,
  onSaveChart,
  onGetAISuggestions,
}: ChartBuilderProps) {
  const { toast } = useToast();
  const plotRef = useRef<HTMLDivElement>(null);

  const [chartType, setChartType] = useState<BuilderChartType>('scatter');
  const [xAxis, setXAxis] = useState<string | null>(null);
  const [yAxis, setYAxis] = useState<string | null>(null);
  const [colorBy, setColorBy] = useState<string | null>(null);
  const [sizeBy, setSizeBy] = useState<string | null>(null);
  const [styleOptions, setStyleOptions] = useState<ChartStyle>(DEFAULT_STYLE);
  const [suggestions, setSuggestions] = useState<ChartSuggestion[]>([]);
  const [loadingSuggestions, setLoadingSuggestions] = useState(false);
  const [saving, setSaving] = useState(false);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 8 },
    })
  );

  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      const { active, over } = event;
      if (!over) return;
      const columnId = active.id as string;
      const zoneId = over.id as string;
      if (zoneId === DROP_ZONE_X) setXAxis(columnId);
      else if (zoneId === DROP_ZONE_Y) setYAxis(columnId);
      else if (zoneId === DROP_ZONE_COLOR) setColorBy(columnId);
      else if (zoneId === DROP_ZONE_SIZE) setSizeBy(columnId);
    },
    []
  );

  const getColumnName = useCallback(
    (id: string | null) => (id ? columns.find((c) => c.id === id)?.name ?? null : null),
    [columns]
  );

  const clearMapping = useCallback((zone: 'x' | 'y' | 'color' | 'size') => {
    if (zone === 'x') setXAxis(null);
    else if (zone === 'y') setYAxis(null);
    else if (zone === 'color') setColorBy(null);
    else if (zone === 'size') setSizeBy(null);
  }, []);

  const palette = styleOptions.colors.palette?.length
    ? styleOptions.colors.palette
    : DEFAULT_STYLE.colors.palette;

  const plotlyData = useMemo(() => {
    const xCol = xAxis ? (data.map((r) => r[xAxis]) as (string | number)[]) : [];
    const yCol = yAxis ? (data.map((r) => r[yAxis]) as (string | number)[]) : [];

    if (chartType === 'heatmap') {
      if (!xAxis || !yAxis) return [];
      const xUniq = [...new Set(xCol as string[])];
      const yUniq = [...new Set(yCol as string[])];
      const z: number[][] = yUniq.map(() => xUniq.map(() => 0));
      const numCol = columns.find((c) => c.id === yAxis);
      const valCol = columns.find((c) => c.id !== xAxis && c.id !== yAxis && c.type === 'numeric');
      const valKey = valCol?.id ?? yAxis;
      const vals = data.map((r) => Number(r[valKey]) ?? 0);
      let idx = 0;
      for (let j = 0; j < yUniq.length; j++) {
        for (let i = 0; i < xUniq.length; i++) {
          z[j][i] = vals[idx++] ?? 0;
        }
      }
      return [
        {
          type: 'heatmap',
          x: xUniq,
          y: yUniq,
          z,
          colorscale: 'Viridis',
        },
      ];
    }

    if (chartType === 'histogram') {
      const numCol = yAxis ? (data.map((r) => r[yAxis]) as number[]) : [];
      return [
        {
          type: 'histogram',
          x: numCol.filter((v) => typeof v === 'number' && !Number.isNaN(v)),
          marker: { color: palette[0] },
        },
      ];
    }

    if (chartType === 'box' || chartType === 'violin') {
      const groupCol = colorBy ? (data.map((r) => String(r[colorBy])) as string[]) : [];
      const yVals = yAxis ? (data.map((r) => r[yAxis]) as number[]) : [];
      const groups = [...new Set(groupCol)];
      if (groups.length === 0) {
        return [
          {
            type: chartType === 'violin' ? 'violin' : 'box',
            y: yVals.filter((v) => typeof v === 'number' && !Number.isNaN(v)),
            marker: { color: palette[0] },
          },
        ];
      }
      return groups.map((g, i) => {
        const mask = groupCol.map((c) => c === g);
        const ySub = yVals.filter((_, j) => mask[j]);
        return {
          type: chartType === 'violin' ? 'violin' : 'box',
          name: g,
          y: ySub.filter((v) => typeof v === 'number' && !Number.isNaN(v)),
          marker: { color: palette[i % palette.length] },
        };
      });
    }

    if (chartType === 'kaplan_meier') {
      const timeCol = xAxis ? (data.map((r) => Number(r[xAxis])) as number[]) : [];
      const eventCol = yAxis ? (data.map((r) => Number(r[yAxis])) as number[]) : [];
      const groupCol = colorBy ? (data.map((r) => String(r[colorBy])) as string[]) : [];
      const groups = [...new Set(groupCol)];
      if (groups.length === 0) {
        const sorted = timeCol
          .map((t, i) => ({ t, e: eventCol[i] ?? 0 }))
          .sort((a, b) => a.t - b.t);
        let s = 1;
        const y: number[] = [];
        sorted.forEach(({ t, e }) => {
          y.push(s);
          if (e) s *= 1 - 1 / (sorted.length || 1);
        });
        return [
          {
            type: 'scatter',
            mode: 'lines+markers',
            x: sorted.map((d) => d.t),
            y,
            line: { shape: 'hv' },
            marker: { color: palette[0] },
          },
        ];
      }
      return groups.map((g, i) => {
        const mask = groupCol.map((c) => c === g);
        const tSub = timeCol.filter((_, j) => mask[j]);
        const eSub = eventCol.filter((_, j) => mask[j]);
        const sorted = tSub
          .map((t, j) => ({ t, e: eSub[j] ?? 0 }))
          .sort((a, b) => a.t - b.t);
        let s = 1;
        const y: number[] = [];
        sorted.forEach(({ e }) => {
          y.push(s);
          if (e) s *= 1 - 1 / Math.max(sorted.length, 1);
        });
        return {
          type: 'scatter',
          mode: 'lines+markers',
          name: g,
          x: sorted.map((d) => d.t),
          y,
          line: { shape: 'hv' },
          marker: { color: palette[i % palette.length] },
        };
      });
    }

    if (chartType === 'bar') {
      const xVals = xAxis ? (data.map((r) => String(r[xAxis])) as string[]) : [];
      const yVals = yAxis ? (data.map((r) => Number(r[yAxis])) as number[]) : [];
      return [
        {
          type: 'bar',
          x: xVals,
          y: yVals,
          marker: { color: palette[0] },
        },
      ];
    }

    if (chartType === 'line') {
      const xVals = xAxis ? (data.map((r) => r[xAxis]) as (string | number)[]) : [];
      const yVals = yAxis ? (data.map((r) => Number(r[yAxis])) as number[]) : [];
      const groupCol = colorBy ? (data.map((r) => String(r[colorBy])) as string[]) : [];
      const groups = [...new Set(groupCol)];
      if (groups.length <= 1) {
        return [
          {
            type: 'scatter',
            mode: 'lines+markers',
            x: xVals,
            y: yVals,
            marker: { color: palette[0] },
          },
        ];
      }
      return groups.map((g, i) => {
        const mask = groupCol.map((c) => c === g);
        return {
          type: 'scatter',
          mode: 'lines+markers',
          name: g,
          x: xVals.filter((_, j) => mask[j]),
          y: yVals.filter((_, j) => mask[j]),
          marker: { color: palette[i % palette.length] },
        };
      });
    }

    // scatter
    const xVals = xAxis ? (data.map((r) => r[xAxis]) as (string | number)[]) : [];
    const yVals = yAxis ? (data.map((r) => Number(r[yAxis])) as number[]) : [];
    const colorVals = colorBy ? (data.map((r) => String(r[colorBy])) as string[]) : [];
    const sizeVals = sizeBy ? (data.map((r) => Number(r[sizeBy]) ?? 10) as number[]) : 10;
    const groups = colorBy ? [...new Set(colorVals)] : [];
    if (groups.length <= 1) {
      return [
        {
          type: 'scatter',
          mode: 'markers',
          x: xVals,
          y: yVals,
          marker: {
            size: sizeVals,
            color: palette[0],
          },
        },
      ];
    }
    return groups.map((g, i) => {
      const mask = colorVals.map((c) => c === g);
      return {
        type: 'scatter',
        mode: 'markers',
        name: g,
        x: xVals.filter((_, j) => mask[j]),
        y: yVals.filter((_, j) => mask[j]),
        marker: {
          size: Array.isArray(sizeVals) ? sizeVals.filter((_, j) => mask[j]) : sizeVals,
          color: palette[i % palette.length],
        },
      };
    });
  }, [
    chartType,
    xAxis,
    yAxis,
    colorBy,
    sizeBy,
    data,
    columns,
    palette,
  ]);

  const plotlyLayout = useMemo(
    () => ({
      title: styleOptions.title || undefined,
      font: {
        family: styleOptions.fontFamily,
        size: styleOptions.fontSize,
      },
      paper_bgcolor: styleOptions.backgroundColor,
      plot_bgcolor: styleOptions.backgroundColor,
      width: styleOptions.width,
      height: styleOptions.height,
      showlegend: styleOptions.legend.show,
      legend: {
        orientation: styleOptions.legend.position === 'left' || styleOptions.legend.position === 'right' ? 'v' : 'h',
        x: styleOptions.legend.position === 'right' ? 1.02 : styleOptions.legend.position === 'left' ? -0.02 : 0.5,
        y: styleOptions.legend.position === 'top' ? 1.02 : styleOptions.legend.position === 'bottom' ? -0.2 : 0.5,
      },
      xaxis: {
        showgrid: styleOptions.showGrid,
        title: columns.find((c) => c.id === xAxis)?.name ?? undefined,
      },
      yaxis: {
        showgrid: styleOptions.showGrid,
        title: columns.find((c) => c.id === yAxis)?.name ?? undefined,
      },
      margin: { t: 50, r: 50, b: 50, l: 50 },
    }),
    [styleOptions, xAxis, yAxis, columns]
  );

  const handleExport = useCallback(
    async (format: 'svg' | 'png') => {
      const el = document.getElementById('plotly-chart-export') ?? plotRef.current;
      if (!el) {
        toast({ title: 'Export failed', description: 'Chart not ready', variant: 'destructive' });
        return;
      }
      try {
        await Plotly.downloadImage(el as HTMLElement, {
          format,
          filename: `chart-${datasetId}-${Date.now()}`,
          width: styleOptions.width,
          height: styleOptions.height,
        });
        toast({ title: 'Export complete', description: `Chart saved as ${format.toUpperCase()}.` });
      } catch (e) {
        toast({
          title: 'Export failed',
          description: e instanceof Error ? e.message : 'Unknown error',
          variant: 'destructive',
        });
      }
    },
    [datasetId, styleOptions.width, styleOptions.height, toast]
  );

  const handleExportPdf = useCallback(() => {
    toast({
      title: 'PDF export',
      description: 'Use Print (Ctrl/Cmd+P) and "Save as PDF" for best results.',
    });
    window.print();
  }, [toast]);

  const handleSaveChart = useCallback(async () => {
    setSaving(true);
    try {
      const config: ChartConfig = {
        id: `chart-${Date.now()}`,
        name: styleOptions.title || 'Untitled Chart',
        chartType: mapBuilderChartTypeToConfig(chartType),
        xAxis: { columnId: xAxis } as AxisMapping,
        yAxis: { columnId: yAxis } as AxisMapping,
        groupBy: colorBy,
        colorBy: colorBy ?? null,
        sizeBy: sizeBy ?? null,
        aggregation: 'none',
        style: styleOptions,
      };
      await onSaveChart(config);
      toast({ title: 'Chart saved', description: 'Chart configuration saved.' });
    } catch (e) {
      toast({
        title: 'Save failed',
        description: e instanceof Error ? e.message : 'Unknown error',
        variant: 'destructive',
      });
    } finally {
      setSaving(false);
    }
  }, [
    chartType,
    xAxis,
    yAxis,
    colorBy,
    sizeBy,
    styleOptions,
    onSaveChart,
    toast,
  ]);

  const handleGetSuggestions = useCallback(async () => {
    setLoadingSuggestions(true);
    try {
      const list = await onGetAISuggestions();
      setSuggestions(list);
      toast({ title: 'Suggestions loaded', description: `${list.length} chart suggestions.` });
    } catch (e) {
      toast({
        title: 'Suggestions failed',
        description: e instanceof Error ? e.message : 'Unknown error',
        variant: 'destructive',
      });
    } finally {
      setLoadingSuggestions(false);
    }
  }, [onGetAISuggestions, toast]);

  const applySuggestion = useCallback((s: ChartSuggestion) => {
    if (s.suggestedConfig) {
      if (s.suggestedConfig.chartType) setChartType(s.suggestedConfig.chartType as BuilderChartType);
      if (s.suggestedConfig.xAxis?.columnId) setXAxis(s.suggestedConfig.xAxis.columnId);
      if (s.suggestedConfig.yAxis?.columnId) setYAxis(s.suggestedConfig.yAxis.columnId);
      if (s.suggestedConfig.colorBy !== undefined) setColorBy(s.suggestedConfig.colorBy);
      if (s.suggestedConfig.sizeBy !== undefined) setSizeBy(s.suggestedConfig.sizeBy);
      if (s.suggestedConfig.style) setStyleOptions((prev) => ({ ...prev, ...s.suggestedConfig!.style }));
    }
    if (s.chartType) setChartType(s.chartType as BuilderChartType);
  }, []);

  return (
    <div className="flex flex-col gap-4 lg:flex-row lg:gap-6">
      <DndContext sensors={sensors} onDragEnd={handleDragEnd}>
        <aside className="flex flex-col gap-4 w-full lg:w-80 shrink-0">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">Variables</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <ScrollArea className="h-[180px]">
                <div className="space-y-1 pr-2">
                  {columns.map((col) => (
                    <DraggableColumn key={col.id} column={col} />
                  ))}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">Map to chart</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <VariableDropZone
                id={DROP_ZONE_X}
                label="X-Axis"
                currentColumnName={getColumnName(xAxis)}
              />
              <VariableDropZone
                id={DROP_ZONE_Y}
                label="Y-Axis"
                currentColumnName={getColumnName(yAxis)}
              />
              {(chartType === 'scatter' || chartType === 'line' || chartType === 'bar') && (
                <>
                  <VariableDropZone
                    id={DROP_ZONE_COLOR}
                    label="Color by"
                    currentColumnName={getColumnName(colorBy)}
                  />
                  {chartType === 'scatter' && (
                    <VariableDropZone
                      id={DROP_ZONE_SIZE}
                      label="Size by"
                      currentColumnName={getColumnName(sizeBy)}
                    />
                  )}
                </>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">Chart type</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2">
                {CHART_TYPES.map((t) => (
                  <Button
                    key={t.id}
                    variant={chartType === t.id ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => setChartType(t.id)}
                  >
                    <span className="mr-1">{t.icon}</span>
                    {t.name}
                  </Button>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">Style</CardTitle>
            </CardHeader>
            <CardContent>
              <ChartStylePanel style={styleOptions} onChange={setStyleOptions} />
            </CardContent>
          </Card>

          <div className="flex flex-wrap gap-2">
            <Button onClick={handleSaveChart} disabled={saving}>
              {saving ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
              Save chart
            </Button>
            <Button variant="outline" onClick={() => handleExport('png')}>
              <Download className="h-4 w-4 mr-2" />
              PNG
            </Button>
            <Button variant="outline" onClick={() => handleExport('svg')}>
              <Download className="h-4 w-4 mr-2" />
              SVG
            </Button>
            <Button variant="outline" onClick={handleExportPdf}>
              <Download className="h-4 w-4 mr-2" />
              PDF
            </Button>
          </div>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center gap-2">
                <Sparkles className="h-4 w-4" />
                AI suggestions
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <Button
                variant="outline"
                size="sm"
                className="w-full"
                onClick={handleGetSuggestions}
                disabled={loadingSuggestions}
              >
                {loadingSuggestions ? (
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                ) : (
                  <Sparkles className="h-4 w-4 mr-2" />
                )}
                Get suggestions
              </Button>
              <ScrollArea className="h-[120px]">
                <div className="space-y-1 pr-2">
                  {suggestions.map((s) => (
                    <button
                      key={s.id}
                      type="button"
                      className="w-full text-left rounded border p-2 text-xs hover:bg-muted"
                      onClick={() => applySuggestion(s)}
                    >
                      <span className="font-medium">{s.chartType}</span>
                      <p className="text-muted-foreground truncate">{s.description}</p>
                    </button>
                  ))}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>
        </aside>

        <Card className="flex-1 min-w-0">
          <CardContent className="p-4">
            <div ref={plotRef}>
              <Plot
                divId="plotly-chart-export"
                data={plotlyData}
                layout={plotlyLayout}
                config={{ responsive: true }}
                style={{ width: '100%', minHeight: 400 }}
                useResizeHandler
              />
            </div>
          </CardContent>
        </Card>
      </DndContext>
    </div>
  );
}
