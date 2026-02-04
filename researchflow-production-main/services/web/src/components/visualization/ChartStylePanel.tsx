/**
 * ChartStylePanel - Style controls for chart builder
 * Title, dimensions, grid, data labels, color scheme (including accessibility), legend.
 */

import React from 'react';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { cn } from '@/lib/utils';
import type { ChartStyle, ColorConfig, LegendConfig } from '@/components/stages';

const COLOR_SCHEMES: Record<ColorConfig['scheme'], { name: string }> = {
  default: { name: 'Default' },
  viridis: { name: 'Viridis (colorblind safe)' },
  plasma: { name: 'Plasma' },
  blues: { name: 'Blues' },
  greens: { name: 'Greens' },
  custom: { name: 'Custom' },
};

const LEGEND_POSITIONS: { value: LegendConfig['position']; label: string }[] = [
  { value: 'top', label: 'Top' },
  { value: 'bottom', label: 'Bottom' },
  { value: 'left', label: 'Left' },
  { value: 'right', label: 'Right' },
];

export interface ChartStylePanelProps {
  style: ChartStyle;
  onChange: (updates: Partial<ChartStyle>) => void;
  className?: string;
}

export function ChartStylePanel({ style, onChange, className }: ChartStylePanelProps) {
  const colorSchemeOptions = Object.entries(COLOR_SCHEMES).map(([value, { name }]) => ({
    value,
    label: name,
  }));

  return (
    <div className={cn('space-y-4', className)}>
      <div className="space-y-2">
        <Label htmlFor="chart-title">Title</Label>
        <Input
          id="chart-title"
          value={style.title}
          onChange={(e) => onChange({ title: e.target.value })}
          placeholder="Chart title"
        />
      </div>
      <div className="space-y-2">
        <Label htmlFor="chart-subtitle">Subtitle (optional)</Label>
        <Input
          id="chart-subtitle"
          value={style.subtitle ?? ''}
          onChange={(e) => onChange({ subtitle: e.target.value || undefined })}
          placeholder="Subtitle"
        />
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="chart-width">Width</Label>
          <Input
            id="chart-width"
            type="number"
            min={200}
            max={1600}
            value={style.width}
            onChange={(e) => onChange({ width: Number(e.target.value) || 800 })}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="chart-height">Height</Label>
          <Input
            id="chart-height"
            type="number"
            min={200}
            max={1200}
            value={style.height}
            onChange={(e) => onChange({ height: Number(e.target.value) || 600 })}
          />
        </div>
      </div>
      <div className="flex items-center justify-between">
        <Label htmlFor="chart-grid">Show grid</Label>
        <Switch
          id="chart-grid"
          checked={style.showGrid}
          onCheckedChange={(checked) => onChange({ showGrid: checked })}
        />
      </div>
      <div className="flex items-center justify-between">
        <Label htmlFor="chart-datalabels">Show data labels</Label>
        <Switch
          id="chart-datalabels"
          checked={style.showDataLabels}
          onCheckedChange={(checked) => onChange({ showDataLabels: checked })}
        />
      </div>
      <div className="space-y-2">
        <Label>Color scheme</Label>
        <Select
          value={style.colors.scheme}
          onValueChange={(value) =>
            onChange({
              colors: {
                ...style.colors,
                scheme: value as ColorConfig['scheme'],
              },
            })
          }
        >
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {colorSchemeOptions.map((opt) => (
              <SelectItem key={opt.value} value={opt.value}>
                {opt.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <div className="flex items-center justify-between">
        <Label htmlFor="chart-legend">Show legend</Label>
        <Switch
          id="chart-legend"
          checked={style.legend.show}
          onCheckedChange={(checked) =>
            onChange({ legend: { ...style.legend, show: checked } })
          }
        />
      </div>
      {style.legend.show && (
        <div className="space-y-2">
          <Label>Legend position</Label>
          <Select
            value={style.legend.position}
            onValueChange={(value) =>
              onChange({
                legend: { ...style.legend, position: value as LegendConfig['position'] },
              })
            }
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {LEGEND_POSITIONS.map((p) => (
                <SelectItem key={p.value} value={p.value}>
                  {p.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )}
      <div className="space-y-2">
        <Label htmlFor="chart-bg">Background color</Label>
        <Input
          id="chart-bg"
          type="text"
          value={style.backgroundColor}
          onChange={(e) => onChange({ backgroundColor: e.target.value })}
          placeholder="#ffffff"
        />
      </div>
    </div>
  );
}
