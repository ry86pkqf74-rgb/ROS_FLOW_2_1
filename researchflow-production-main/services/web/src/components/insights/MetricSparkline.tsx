/**
 * MetricSparkline - Mini inline chart component
 * 
 * Displays a small sparkline chart for metric visualization.
 * Supports multiple colors and hover tooltips.
 * 
 * Linear Issue: ROS-61
 * 
 * @module components/insights/MetricSparkline
 */

import React, { useMemo } from 'react';
import { cn } from '@/lib/utils';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';

// ============================================
// Types
// ============================================

export interface MetricSparklineProps {
  /** Array of numeric values to display */
  data: number[];
  /** Label for the metric */
  label?: string;
  /** Color theme */
  color?: 'blue' | 'green' | 'red' | 'yellow' | 'purple' | 'gray';
  /** Width of the sparkline */
  width?: number;
  /** Height of the sparkline */
  height?: number;
  /** Show min/max labels */
  showMinMax?: boolean;
  /** Show current value */
  showValue?: boolean;
  /** Unit suffix for values */
  unit?: string;
  /** Custom class name */
  className?: string;
}

// ============================================
// Color Palettes
// ============================================

const colorPalettes = {
  blue: {
    stroke: '#3b82f6',
    fill: 'rgba(59, 130, 246, 0.1)',
    dot: '#2563eb',
  },
  green: {
    stroke: '#22c55e',
    fill: 'rgba(34, 197, 94, 0.1)',
    dot: '#16a34a',
  },
  red: {
    stroke: '#ef4444',
    fill: 'rgba(239, 68, 68, 0.1)',
    dot: '#dc2626',
  },
  yellow: {
    stroke: '#eab308',
    fill: 'rgba(234, 179, 8, 0.1)',
    dot: '#ca8a04',
  },
  purple: {
    stroke: '#a855f7',
    fill: 'rgba(168, 85, 247, 0.1)',
    dot: '#9333ea',
  },
  gray: {
    stroke: '#6b7280',
    fill: 'rgba(107, 114, 128, 0.1)',
    dot: '#4b5563',
  },
};

// ============================================
// Component
// ============================================

export function MetricSparkline({
  data,
  label,
  color = 'blue',
  width = 80,
  height = 24,
  showMinMax = false,
  showValue = true,
  unit = '',
  className,
}: MetricSparklineProps) {
  // Compute path and stats
  const { path, areaPath, stats } = useMemo(() => {
    if (data.length < 2) {
      return { path: '', areaPath: '', stats: { min: 0, max: 0, current: 0, avg: 0 } };
    }

    const min = Math.min(...data);
    const max = Math.max(...data);
    const range = max - min || 1;
    const current = data[data.length - 1];
    const avg = data.reduce((a, b) => a + b, 0) / data.length;

    // Padding
    const padding = 2;
    const chartWidth = width - padding * 2;
    const chartHeight = height - padding * 2;

    // Generate points
    const points = data.map((value, index) => {
      const x = padding + (index / (data.length - 1)) * chartWidth;
      const y = padding + chartHeight - ((value - min) / range) * chartHeight;
      return { x, y };
    });

    // Create line path
    const linePath = points
      .map((point, i) => `${i === 0 ? 'M' : 'L'} ${point.x.toFixed(2)} ${point.y.toFixed(2)}`)
      .join(' ');

    // Create area path (for fill)
    const area = [
      `M ${points[0].x.toFixed(2)} ${(height - padding).toFixed(2)}`,
      ...points.map(p => `L ${p.x.toFixed(2)} ${p.y.toFixed(2)}`),
      `L ${points[points.length - 1].x.toFixed(2)} ${(height - padding).toFixed(2)}`,
      'Z',
    ].join(' ');

    return {
      path: linePath,
      areaPath: area,
      stats: { min, max, current, avg },
    };
  }, [data, width, height]);

  const palette = colorPalettes[color];

  // Format value for display
  const formatValue = (value: number): string => {
    if (value >= 1000) {
      return `${(value / 1000).toFixed(1)}k${unit}`;
    }
    return `${Math.round(value)}${unit}`;
  };

  if (data.length < 2) {
    return (
      <div className={cn('flex items-center gap-1 text-muted-foreground', className)}>
        <span className="text-xs">{label}</span>
        <span className="text-xs">--</span>
      </div>
    );
  }

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <div className={cn('flex items-center gap-2', className)}>
            {label && (
              <span className="text-xs text-muted-foreground">{label}</span>
            )}
            
            <svg
              width={width}
              height={height}
              className="overflow-visible"
              style={{ cursor: 'default' }}
            >
              {/* Area fill */}
              <path
                d={areaPath}
                fill={palette.fill}
              />
              
              {/* Line */}
              <path
                d={path}
                fill="none"
                stroke={palette.stroke}
                strokeWidth={1.5}
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              
              {/* Current value dot */}
              {data.length > 0 && (
                <circle
                  cx={width - 2}
                  cy={2 + (height - 4) - ((stats.current - stats.min) / (stats.max - stats.min || 1)) * (height - 4)}
                  r={2.5}
                  fill={palette.dot}
                />
              )}
            </svg>

            {showValue && (
              <span 
                className="text-xs font-mono tabular-nums"
                style={{ color: palette.stroke }}
              >
                {formatValue(stats.current)}
              </span>
            )}
          </div>
        </TooltipTrigger>
        
        <TooltipContent side="top" className="text-xs">
          <div className="space-y-1">
            {label && <div className="font-medium">{label}</div>}
            <div className="grid grid-cols-2 gap-x-4 gap-y-0.5">
              <span className="text-muted-foreground">Current:</span>
              <span className="font-mono">{formatValue(stats.current)}</span>
              <span className="text-muted-foreground">Avg:</span>
              <span className="font-mono">{formatValue(stats.avg)}</span>
              {showMinMax && (
                <>
                  <span className="text-muted-foreground">Min:</span>
                  <span className="font-mono">{formatValue(stats.min)}</span>
                  <span className="text-muted-foreground">Max:</span>
                  <span className="font-mono">{formatValue(stats.max)}</span>
                </>
              )}
            </div>
            <div className="text-muted-foreground pt-1 border-t">
              {data.length} data points
            </div>
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

// ============================================
// Variants
// ============================================

export interface MetricSparklineGroupProps {
  metrics: Array<{
    data: number[];
    label: string;
    color?: MetricSparklineProps['color'];
    unit?: string;
  }>;
  className?: string;
}

export function MetricSparklineGroup({ metrics, className }: MetricSparklineGroupProps) {
  return (
    <div className={cn('flex items-center gap-4', className)}>
      {metrics.map((metric, index) => (
        <MetricSparkline
          key={`${metric.label}-${index}`}
          data={metric.data}
          label={metric.label}
          color={metric.color}
          unit={metric.unit}
        />
      ))}
    </div>
  );
}

export default MetricSparkline;
