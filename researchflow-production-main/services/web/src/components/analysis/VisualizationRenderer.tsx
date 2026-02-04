/**
 * Visualization Renderer
 *
 * Renders statistical visualizations including Q-Q plots, histograms, boxplots,
 * scatter plots, and other diagnostic charts.
 */

import React, { useState, useMemo } from 'react';
import { BarChart3, Download, Eye, EyeOff, Maximize2, Settings, Grid3X3, List } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Separator } from '@/components/ui/separator';

import { Visualization } from '@/types/statistical-analysis';

// Import chart components from recharts or similar charting library
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ScatterChart,
  Scatter,
  BarChart,
  Bar,
  Histogram
} from 'recharts';

interface VisualizationRendererProps {
  /** Array of visualizations to render */
  visualizations: Visualization[];
  /** Display preferences */
  preferences?: {
    types?: Visualization['type'][];
    showAll?: boolean;
    gridCols?: number;
  };
  /** Called when visualization is exported */
  onExport?: (visualization: Visualization, format: 'png' | 'svg' | 'pdf') => void;
}

interface VisualizationCardProps {
  visualization: Visualization;
  onExport?: (format: 'png' | 'svg' | 'pdf') => void;
}

// Q-Q Plot Component
function QQPlot({ data, title }: { data: any; title: string }) {
  const qqData = useMemo(() => {
    if (!data?.observed || !data?.theoretical) return [];
    
    return data.observed.map((obs: number, index: number) => ({
      theoretical: data.theoretical[index],
      observed: obs,
      inRange: Math.abs(obs - data.theoretical[index]) <= (data.confidence_bands?.[index] || Infinity)
    }));
  }, [data]);

  return (
    <ResponsiveContainer width="100%" height={400}>
      <ScatterChart data={qqData}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis 
          dataKey="theoretical" 
          label={{ value: 'Theoretical Quantiles', position: 'insideBottom', offset: -10 }}
        />
        <YAxis 
          dataKey="observed" 
          label={{ value: 'Sample Quantiles', angle: -90, position: 'insideLeft' }}
        />
        <Tooltip 
          formatter={(value, name) => [Number(value).toFixed(3), name]}
          labelFormatter={(label) => `Theoretical: ${Number(label).toFixed(3)}`}
        />
        
        {/* Scatter points */}
        <Scatter 
          dataKey="observed" 
          fill="#2563eb" 
          fillOpacity={0.7}
          stroke="#1d4ed8"
          strokeWidth={1}
        />
        
        {/* Reference line */}
        <Line 
          dataKey="theoretical" 
          stroke="#dc2626" 
          strokeWidth={2}
          strokeDasharray="5,5"
          dot={false}
        />
      </ScatterChart>
    </ResponsiveContainer>
  );
}

// Histogram Component
function HistogramChart({ data, title }: { data: any; title: string }) {
  const histogramData = useMemo(() => {
    if (!data?.bins || !data?.counts) return [];
    
    return data.bins.map((bin: number, index: number) => ({
      bin: bin.toFixed(2),
      count: data.counts[index],
      density: data.density?.[index] || 0
    }));
  }, [data]);

  return (
    <ResponsiveContainer width="100%" height={400}>
      <BarChart data={histogramData}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis 
          dataKey="bin" 
          label={{ value: 'Value', position: 'insideBottom', offset: -10 }}
        />
        <YAxis 
          label={{ value: 'Frequency', angle: -90, position: 'insideLeft' }}
        />
        <Tooltip />
        <Bar dataKey="count" fill="#2563eb" fillOpacity={0.7} />
        
        {/* Normal curve overlay if provided */}
        {data.normal_curve && (
          <Line 
            dataKey="normal_curve" 
            stroke="#dc2626" 
            strokeWidth={2}
            dot={false}
            type="monotone"
          />
        )}
      </BarChart>
    </ResponsiveContainer>
  );
}

// Box Plot Component
function BoxPlot({ data, title }: { data: any; title: string }) {
  // For box plots, we'll create a custom SVG visualization
  // since recharts doesn't have native box plot support
  
  const boxplotData = useMemo(() => {
    if (!data?.groups) return [];
    
    return data.groups.map((group: any) => ({
      name: group.name,
      min: group.min,
      q1: group.q1,
      median: group.median,
      q3: group.q3,
      max: group.max,
      outliers: group.outliers || []
    }));
  }, [data]);

  return (
    <div className="w-full h-96 flex items-center justify-center">
      <svg width="100%" height="100%" viewBox="0 0 400 300">
        {boxplotData.map((group, index) => {
          const x = 50 + index * 80;
          const scale = 200; // Height scaling factor
          const bottom = 250;
          
          // Calculate positions
          const minY = bottom - (group.min / scale);
          const q1Y = bottom - (group.q1 / scale);
          const medianY = bottom - (group.median / scale);
          const q3Y = bottom - (group.q3 / scale);
          const maxY = bottom - (group.max / scale);
          
          return (
            <g key={index}>
              {/* Box */}
              <rect
                x={x - 15}
                y={q3Y}
                width={30}
                height={q1Y - q3Y}
                fill="#2563eb"
                fillOpacity={0.3}
                stroke="#2563eb"
                strokeWidth={1}
              />
              
              {/* Median line */}
              <line
                x1={x - 15}
                y1={medianY}
                x2={x + 15}
                y2={medianY}
                stroke="#dc2626"
                strokeWidth={2}
              />
              
              {/* Whiskers */}
              <line x1={x} y1={q1Y} x2={x} y2={minY} stroke="#2563eb" />
              <line x1={x} y1={q3Y} x2={x} y2={maxY} stroke="#2563eb" />
              <line x1={x - 5} y1={minY} x2={x + 5} y2={minY} stroke="#2563eb" />
              <line x1={x - 5} y1={maxY} x2={x + 5} y2={maxY} stroke="#2563eb" />
              
              {/* Outliers */}
              {group.outliers.map((outlier: number, outIndex: number) => (
                <circle
                  key={outIndex}
                  cx={x}
                  cy={bottom - (outlier / scale)}
                  r={2}
                  fill="#dc2626"
                />
              ))}
              
              {/* Group label */}
              <text
                x={x}
                y={280}
                textAnchor="middle"
                fontSize="12"
                fill="#374151"
              >
                {group.name}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

// Scatter Plot Component
function ScatterPlot({ data, title }: { data: any; title: string }) {
  const scatterData = useMemo(() => {
    if (!data?.x || !data?.y) return [];
    
    return data.x.map((x: number, index: number) => ({
      x,
      y: data.y[index],
      group: data.groups?.[index] || 'default'
    }));
  }, [data]);

  // Group data by category if groups are provided
  const groupedData = useMemo(() => {
    const groups = new Map();
    scatterData.forEach(point => {
      if (!groups.has(point.group)) {
        groups.set(point.group, []);
      }
      groups.get(point.group).push(point);
    });
    return Array.from(groups.entries());
  }, [scatterData]);

  const colors = ['#2563eb', '#dc2626', '#16a34a', '#ca8a04', '#9333ea'];

  return (
    <ResponsiveContainer width="100%" height={400}>
      <ScatterChart>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis 
          type="number"
          dataKey="x"
          label={{ value: data.xLabel || 'X Variable', position: 'insideBottom', offset: -10 }}
        />
        <YAxis 
          type="number"
          dataKey="y"
          label={{ value: data.yLabel || 'Y Variable', angle: -90, position: 'insideLeft' }}
        />
        <Tooltip 
          formatter={(value, name) => [Number(value).toFixed(3), name]}
        />
        <Legend />
        
        {groupedData.map(([groupName, points], index) => (
          <Scatter
            key={groupName}
            name={groupName}
            data={points}
            fill={colors[index % colors.length]}
            fillOpacity={0.7}
          />
        ))}
        
        {/* Regression line if provided */}
        {data.regression_line && (
          <Line
            data={data.regression_line}
            dataKey="y"
            stroke="#dc2626"
            strokeWidth={2}
            dot={false}
            type="linear"
          />
        )}
      </ScatterChart>
    </ResponsiveContainer>
  );
}

// Bar Chart Component
function BarPlot({ data, title }: { data: any; title: string }) {
  const barData = useMemo(() => {
    if (!data?.categories || !data?.values) return [];
    
    return data.categories.map((category: string, index: number) => ({
      category,
      value: data.values[index],
      error: data.errors?.[index] || 0
    }));
  }, [data]);

  return (
    <ResponsiveContainer width="100%" height={400}>
      <BarChart data={barData}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="category" />
        <YAxis 
          label={{ value: data.yLabel || 'Value', angle: -90, position: 'insideLeft' }}
        />
        <Tooltip />
        <Bar dataKey="value" fill="#2563eb" fillOpacity={0.7} />
      </BarChart>
    </ResponsiveContainer>
  );
}

// Forest Plot Component for effect sizes
function ForestPlot({ data, title }: { data: any; title: string }) {
  if (!data?.studies || !Array.isArray(data.studies)) return null;

  return (
    <div className="w-full h-96">
      <svg width="100%" height="100%" viewBox="0 0 500 300">
        {/* Title */}
        <text x={250} y={20} textAnchor="middle" fontSize="16" fontWeight="bold">
          {title}
        </text>
        
        {/* Vertical reference line at null effect */}
        <line
          x1={250}
          y1={40}
          x2={250}
          y2={260}
          stroke="#666"
          strokeDasharray="2,2"
        />
        
        {data.studies.map((study: any, index: number) => {
          const y = 60 + index * 30;
          const effectSize = study.effect_size || 0;
          const lowerCI = study.ci_lower || effectSize - 0.5;
          const upperCI = study.ci_upper || effectSize + 0.5;
          
          // Scale positions (assuming effect sizes between -3 and 3)
          const scale = 60; // pixels per unit
          const center = 250;
          const effectX = center + effectSize * scale;
          const lowerX = center + lowerCI * scale;
          const upperX = center + upperCI * scale;
          
          return (
            <g key={index}>
              {/* Study name */}
              <text x={20} y={y + 5} fontSize="12" fill="#374151">
                {study.name || `Study ${index + 1}`}
              </text>
              
              {/* Confidence interval line */}
              <line
                x1={lowerX}
                y1={y}
                x2={upperX}
                y2={y}
                stroke="#2563eb"
                strokeWidth={2}
              />
              
              {/* CI bounds */}
              <line x1={lowerX} y1={y - 5} x2={lowerX} y2={y + 5} stroke="#2563eb" strokeWidth={2} />
              <line x1={upperX} y1={y - 5} x2={upperX} y2={y + 5} stroke="#2563eb" strokeWidth={2} />
              
              {/* Effect size point */}
              <circle
                cx={effectX}
                cy={y}
                r={4}
                fill="#2563eb"
                stroke="#fff"
                strokeWidth={1}
              />
              
              {/* Effect size value */}
              <text x={450} y={y + 5} fontSize="11" fill="#374151">
                {effectSize.toFixed(2)} [{lowerCI.toFixed(2)}, {upperCI.toFixed(2)}]
              </text>
            </g>
          );
        })}
        
        {/* X-axis labels */}
        <text x={100} y={285} textAnchor="middle" fontSize="12" fill="#666">
          Favours Control
        </text>
        <text x={400} y={285} textAnchor="middle" fontSize="12" fill="#666">
          Favours Treatment
        </text>
      </svg>
    </div>
  );
}

// Individual Visualization Card
function VisualizationCard({ visualization, onExport }: VisualizationCardProps) {
  const [isFullscreen, setIsFullscreen] = useState(false);

  const renderChart = () => {
    switch (visualization.type) {
      case 'qq-plot':
        return <QQPlot data={visualization.data} title={visualization.title} />;
      case 'histogram':
        return <HistogramChart data={visualization.data} title={visualization.title} />;
      case 'boxplot':
        return <BoxPlot data={visualization.data} title={visualization.title} />;
      case 'scatter':
        return <ScatterPlot data={visualization.data} title={visualization.title} />;
      case 'bar':
        return <BarPlot data={visualization.data} title={visualization.title} />;
      case 'forest-plot':
        return <ForestPlot data={visualization.data} title={visualization.title} />;
      default:
        // Fallback for base64 encoded images
        if (visualization.imageBase64) {
          return (
            <img 
              src={`data:image/png;base64,${visualization.imageBase64}`}
              alt={visualization.title}
              className="w-full h-96 object-contain"
            />
          );
        }
        return (
          <div className="w-full h-96 flex items-center justify-center text-gray-500">
            <div className="text-center">
              <BarChart3 className="h-16 w-16 mx-auto mb-4 opacity-50" />
              <p>Unsupported visualization type: {visualization.type}</p>
            </div>
          </div>
        );
    }
  };

  return (
    <Card className="h-full">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-lg">{visualization.title}</CardTitle>
            <Badge variant="outline" className="text-xs mt-1">
              {visualization.type}
            </Badge>
          </div>
          <div className="flex gap-1">
            <Dialog open={isFullscreen} onOpenChange={setIsFullscreen}>
              <DialogTrigger asChild>
                <Button variant="ghost" size="sm">
                  <Maximize2 className="h-4 w-4" />
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-4xl max-h-[90vh] overflow-auto">
                <DialogHeader>
                  <DialogTitle>{visualization.title}</DialogTitle>
                </DialogHeader>
                <div className="mt-4">
                  {renderChart()}
                </div>
              </DialogContent>
            </Dialog>
            
            {onExport && (
              <Select onValueChange={(format: 'png' | 'svg' | 'pdf') => onExport(format)}>
                <SelectTrigger className="w-20 h-8">
                  <Download className="h-4 w-4" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="png">PNG</SelectItem>
                  <SelectItem value="svg">SVG</SelectItem>
                  <SelectItem value="pdf">PDF</SelectItem>
                </SelectContent>
              </Select>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {renderChart()}
      </CardContent>
    </Card>
  );
}

export function VisualizationRenderer({ 
  visualizations, 
  preferences = {},
  onExport 
}: VisualizationRendererProps) {
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [visibleTypes, setVisibleTypes] = useState<Set<Visualization['type']>>(
    new Set(preferences.types || ['histogram', 'boxplot', 'qq-plot', 'scatter', 'bar'])
  );

  // Filter visualizations based on preferences
  const filteredVisualizations = useMemo(() => {
    if (preferences.showAll) return visualizations;
    return visualizations.filter(viz => visibleTypes.has(viz.type));
  }, [visualizations, visibleTypes, preferences.showAll]);

  // Get unique visualization types
  const availableTypes = useMemo(() => {
    return [...new Set(visualizations.map(viz => viz.type))];
  }, [visualizations]);

  // Toggle visualization type visibility
  const toggleType = (type: Visualization['type']) => {
    setVisibleTypes(prev => {
      const newSet = new Set(prev);
      if (newSet.has(type)) {
        newSet.delete(type);
      } else {
        newSet.add(type);
      }
      return newSet;
    });
  };

  if (visualizations.length === 0) {
    return (
      <Card>
        <CardContent className="py-12 text-center">
          <BarChart3 className="h-16 w-16 mx-auto mb-4 text-gray-400" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">No Visualizations Available</h3>
          <p className="text-gray-500">
            No charts were generated for this analysis. This may be normal depending on the test type.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Controls */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg">Visualizations ({filteredVisualizations.length})</CardTitle>
            <div className="flex items-center gap-4">
              {/* Type filters */}
              <div className="flex flex-wrap gap-2">
                {availableTypes.map(type => (
                  <div key={type} className="flex items-center gap-2">
                    <Checkbox 
                      checked={visibleTypes.has(type)}
                      onCheckedChange={() => toggleType(type)}
                    />
                    <Label className="text-sm capitalize">
                      {type.replace('-', ' ')}
                    </Label>
                  </div>
                ))}
              </div>

              <Separator orientation="vertical" className="h-6" />

              {/* View mode toggle */}
              <div className="flex gap-1">
                <Button
                  variant={viewMode === 'grid' ? 'default' : 'ghost'}
                  size="sm"
                  onClick={() => setViewMode('grid')}
                >
                  <Grid3X3 className="h-4 w-4" />
                </Button>
                <Button
                  variant={viewMode === 'list' ? 'default' : 'ghost'}
                  size="sm"
                  onClick={() => setViewMode('list')}
                >
                  <List className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </div>
        </CardHeader>
      </Card>

      {/* Visualizations Grid/List */}
      <div className={
        viewMode === 'grid' 
          ? `grid gap-6 ${
              preferences.gridCols === 1 ? 'grid-cols-1' :
              preferences.gridCols === 2 ? 'grid-cols-1 lg:grid-cols-2' :
              'grid-cols-1 lg:grid-cols-2 xl:grid-cols-3'
            }`
          : 'space-y-6'
      }>
        {filteredVisualizations.map((visualization, index) => (
          <VisualizationCard
            key={`${visualization.type}-${index}`}
            visualization={visualization}
            onExport={onExport ? (format) => onExport(visualization, format) : undefined}
          />
        ))}
      </div>

      {filteredVisualizations.length === 0 && (
        <Card>
          <CardContent className="py-8 text-center">
            <EyeOff className="h-12 w-12 mx-auto mb-4 text-gray-400" />
            <h3 className="text-lg font-semibold text-gray-900 mb-2">No Visualizations Selected</h3>
            <p className="text-gray-500">
              Enable visualization types using the checkboxes above to see charts.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

export default VisualizationRenderer;