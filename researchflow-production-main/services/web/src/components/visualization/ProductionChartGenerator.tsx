/**
 * Enhanced Production Chart Generator
 * 
 * Features:
 * - Full backend integration with visualization service
 * - Real-time cache indicators and performance metrics
 * - Journal style selection with backend capabilities
 * - Comprehensive error handling with recovery suggestions
 * - Quality profiles for different use cases
 * - Chart type selection with backend validation
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useVisualization, type ChartGenerationRequest, type ChartGenerationResponse } from '../../hooks/useVisualization';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  Loader2, 
  AlertCircle, 
  CheckCircle, 
  Clock, 
  Zap, 
  Database,
  Download,
  RefreshCw,
  TrendingUp,
  Settings,
  Sparkles
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface QualityProfile {
  id: string;
  name: string;
  description: string;
  dpi: number;
  format: string;
  optimizations: string[];
}

const QUALITY_PROFILES: QualityProfile[] = [
  {
    id: 'draft',
    name: 'Draft',
    description: 'Fast generation for exploratory analysis',
    dpi: 72,
    format: 'png',
    optimizations: ['fast_render', 'reduced_quality']
  },
  {
    id: 'presentation',
    name: 'Presentation',
    description: 'High quality for presentations and reports',
    dpi: 150,
    format: 'png',
    optimizations: ['balanced_quality', 'moderate_size']
  },
  {
    id: 'publication',
    name: 'Publication',
    description: 'Maximum quality for journal submissions',
    dpi: 300,
    format: 'svg',
    optimizations: ['max_quality', 'vector_output']
  }
];

// Sample data for demonstration
const SAMPLE_DATA = {
  bar_chart: {
    categories: ['Group A', 'Group B', 'Group C', 'Group D'],
    values: [23, 45, 56, 78],
    colors: ['#3b82f6', '#10b981', '#f59e0b', '#ef4444']
  },
  line_chart: {
    x_values: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
    y_values: [10, 15, 13, 17, 20, 18, 22, 25, 23, 28],
    trend_line: true
  },
  scatter_plot: {
    x_values: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
    y_values: [2, 5, 3, 8, 7, 6, 9, 12, 10, 15],
    size_values: [10, 15, 20, 25, 30, 35, 40, 45, 50, 55]
  },
  box_plot: {
    groups: ['Control', 'Treatment A', 'Treatment B'],
    data: {
      'Control': [12, 15, 18, 20, 22, 25, 28],
      'Treatment A': [18, 22, 25, 28, 30, 32, 35],
      'Treatment B': [25, 28, 30, 33, 35, 38, 42]
    }
  }
};

export default function ProductionChartGenerator() {
  const { 
    generateChart, 
    getCapabilities, 
    loading, 
    error, 
    capabilities,
    clearError,
    health,
    getHealth 
  } = useVisualization();

  // Chart configuration state
  const [chartType, setChartType] = useState<string>('bar_chart');
  const [journalStyle, setJournalStyle] = useState<string>('nature');
  const [qualityProfile, setQualityProfile] = useState<string>('presentation');
  const [researchId, setResearchId] = useState<string>('demo-research-001');
  const [chartTitle, setChartTitle] = useState<string>('Sample Chart');
  const [customData, setCustomData] = useState<string>('');

  // Results state
  const [lastResponse, setLastResponse] = useState<ChartGenerationResponse | null>(null);
  const [generationHistory, setGenerationHistory] = useState<ChartGenerationResponse[]>([]);

  // Performance tracking
  const [performanceStats, setPerformanceStats] = useState({
    totalGenerated: 0,
    averageTime: 0,
    cacheHits: 0,
    errorCount: 0
  });

  // Load capabilities and health on mount
  useEffect(() => {
    getCapabilities().catch(console.warn);
    getHealth().catch(console.warn);
  }, [getCapabilities, getHealth]);

  // Update performance stats when new response comes in
  useEffect(() => {
    if (lastResponse) {
      setPerformanceStats(prev => ({
        totalGenerated: prev.totalGenerated + 1,
        averageTime: Math.round(
          (prev.averageTime * prev.totalGenerated + lastResponse.duration_ms) / 
          (prev.totalGenerated + 1)
        ),
        cacheHits: prev.cacheHits + (lastResponse.cached ? 1 : 0),
        errorCount: prev.errorCount
      }));
    }
  }, [lastResponse]);

  const selectedProfile = useMemo(
    () => QUALITY_PROFILES.find(p => p.id === qualityProfile) || QUALITY_PROFILES[1],
    [qualityProfile]
  );

  const currentSampleData = useMemo(
    () => SAMPLE_DATA[chartType as keyof typeof SAMPLE_DATA] || SAMPLE_DATA.bar_chart,
    [chartType]
  );

  const handleGenerateChart = useCallback(async () => {
    clearError();
    
    try {
      // Prepare chart data
      let data = currentSampleData;
      
      // If custom data is provided, try to parse it
      if (customData.trim()) {
        try {
          data = JSON.parse(customData);
        } catch (e) {
          console.warn('Invalid custom data JSON, using sample data');
        }
      }

      const request: ChartGenerationRequest = {
        chart_type: chartType,
        data,
        config: {
          journal_style: journalStyle,
          quality_profile: qualityProfile,
          dpi: selectedProfile.dpi,
          format: selectedProfile.format,
          title: chartTitle,
          optimizations: selectedProfile.optimizations
        },
        research_id: researchId,
        metadata: {
          generated_at: new Date().toISOString(),
          frontend_version: '1.0.0',
          user_profile: qualityProfile
        }
      };

      const response = await generateChart(request);
      setLastResponse(response);
      setGenerationHistory(prev => [response, ...prev.slice(0, 9)]); // Keep last 10

    } catch (err) {
      setPerformanceStats(prev => ({
        ...prev,
        errorCount: prev.errorCount + 1
      }));
      console.error('Chart generation failed:', err);
    }
  }, [
    chartType,
    journalStyle,
    qualityProfile,
    researchId,
    chartTitle,
    customData,
    currentSampleData,
    selectedProfile,
    generateChart,
    clearError
  ]);

  const handleDownload = useCallback((format: 'png' | 'svg' | 'pdf') => {
    if (!lastResponse?.result.image_base64) return;

    const link = document.createElement('a');
    link.download = `${chartTitle.replace(/\s+/g, '_')}.${format}`;
    link.href = `data:image/${format === 'svg' ? 'svg+xml' : format};base64,${lastResponse.result.image_base64}`;
    link.click();
  }, [lastResponse, chartTitle]);

  const getStatusIcon = (cached?: boolean, duration?: number) => {
    if (cached) return <Zap className="h-4 w-4 text-yellow-500" />;
    if (duration && duration < 1000) return <CheckCircle className="h-4 w-4 text-green-500" />;
    if (duration && duration > 3000) return <Clock className="h-4 w-4 text-orange-500" />;
    return <CheckCircle className="h-4 w-4 text-green-500" />;
  };

  return (
    <div className="container mx-auto p-6 max-w-7xl">
      <div className="flex flex-col lg:flex-row gap-6">
        {/* Configuration Panel */}
        <div className="lg:w-96 space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Settings className="h-5 w-5" />
                Chart Configuration
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="chart-type">Chart Type</Label>
                <Select value={chartType} onValueChange={setChartType}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {capabilities?.chart_types?.map(type => (
                      <SelectItem key={type} value={type}>
                        {type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                      </SelectItem>
                    )) || (
                      <>
                        <SelectItem value="bar_chart">Bar Chart</SelectItem>
                        <SelectItem value="line_chart">Line Chart</SelectItem>
                        <SelectItem value="scatter_plot">Scatter Plot</SelectItem>
                        <SelectItem value="box_plot">Box Plot</SelectItem>
                      </>
                    )}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="journal-style">Journal Style</Label>
                <Select value={journalStyle} onValueChange={setJournalStyle}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {capabilities?.journal_styles?.map(style => (
                      <SelectItem key={style} value={style}>
                        {style.toUpperCase()}
                      </SelectItem>
                    )) || (
                      <>
                        <SelectItem value="nature">Nature</SelectItem>
                        <SelectItem value="jama">JAMA</SelectItem>
                        <SelectItem value="nejm">NEJM</SelectItem>
                      </>
                    )}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="quality-profile">Quality Profile</Label>
                <Select value={qualityProfile} onValueChange={setQualityProfile}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {QUALITY_PROFILES.map(profile => (
                      <SelectItem key={profile.id} value={profile.id}>
                        {profile.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">
                  {selectedProfile.description}
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="chart-title">Chart Title</Label>
                <Input
                  id="chart-title"
                  value={chartTitle}
                  onChange={(e) => setChartTitle(e.target.value)}
                  placeholder="Enter chart title"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="research-id">Research ID</Label>
                <Input
                  id="research-id"
                  value={researchId}
                  onChange={(e) => setResearchId(e.target.value)}
                  placeholder="research-001"
                />
              </div>

              <Separator />

              <Button 
                onClick={handleGenerateChart} 
                disabled={loading}
                className="w-full"
                size="lg"
              >
                {loading ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Generating...
                  </>
                ) : (
                  <>
                    <Sparkles className="h-4 w-4 mr-2" />
                    Generate Chart
                  </>
                )}
              </Button>
            </CardContent>
          </Card>

          {/* Performance Stats */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <TrendingUp className="h-5 w-5" />
                Performance Stats
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <div className="font-semibold">{performanceStats.totalGenerated}</div>
                  <div className="text-muted-foreground">Charts Generated</div>
                </div>
                <div>
                  <div className="font-semibold">{performanceStats.averageTime}ms</div>
                  <div className="text-muted-foreground">Avg Generation Time</div>
                </div>
                <div>
                  <div className="font-semibold">{performanceStats.cacheHits}</div>
                  <div className="text-muted-foreground">Cache Hits</div>
                </div>
                <div>
                  <div className="font-semibold">
                    {performanceStats.totalGenerated > 0 
                      ? Math.round((performanceStats.cacheHits / performanceStats.totalGenerated) * 100)
                      : 0}%
                  </div>
                  <div className="text-muted-foreground">Cache Rate</div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* System Health */}
          {health && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Database className="h-5 w-5" />
                  System Health
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2 text-sm">
                  <div className="flex items-center justify-between">
                    <span>Worker</span>
                    <Badge variant={health.components.worker.status === 'healthy' ? 'default' : 'destructive'}>
                      {health.components.worker.status}
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Database</span>
                    <Badge variant={health.components.database.healthy ? 'default' : 'destructive'}>
                      {health.components.database.healthy ? 'healthy' : 'unhealthy'}
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Cache</span>
                    <Badge variant={health.components.cache.status === 'healthy' ? 'default' : 'destructive'}>
                      {health.components.cache.status}
                    </Badge>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Main Content Area */}
        <div className="flex-1 space-y-4">
          {/* Error Display */}
          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription className="flex flex-col gap-2">
                <div className="font-semibold">{error.error}</div>
                <div>{error.message}</div>
                {error.suggestions && error.suggestions.length > 0 && (
                  <div>
                    <div className="font-medium mb-1">Suggestions:</div>
                    <ul className="list-disc list-inside space-y-1">
                      {error.suggestions.map((suggestion, index) => (
                        <li key={index} className="text-sm">{suggestion}</li>
                      ))}
                    </ul>
                  </div>
                )}
                <Button 
                  variant="outline" 
                  size="sm" 
                  onClick={clearError}
                  className="self-start mt-2"
                >
                  Dismiss
                </Button>
              </AlertDescription>
            </Alert>
          )}

          <Tabs defaultValue="result" className="w-full">
            <TabsList className="grid w-full grid-cols-4">
              <TabsTrigger value="result">Chart Result</TabsTrigger>
              <TabsTrigger value="data">Sample Data</TabsTrigger>
              <TabsTrigger value="custom">Custom Data</TabsTrigger>
              <TabsTrigger value="history">History</TabsTrigger>
            </TabsList>

            <TabsContent value="result" className="space-y-4">
              {lastResponse ? (
                <Card>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <CardTitle className="flex items-center gap-2">
                        {getStatusIcon(lastResponse.cached, lastResponse.duration_ms)}
                        {lastResponse.result.caption || chartTitle}
                      </CardTitle>
                      <div className="flex items-center gap-2">
                        {lastResponse.cached && (
                          <Badge variant="secondary" className="text-xs">
                            <Zap className="h-3 w-3 mr-1" />
                            Cached
                          </Badge>
                        )}
                        <Badge variant="outline" className="text-xs">
                          {lastResponse.duration_ms}ms
                        </Badge>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      {/* Chart Image */}
                      <div className="border rounded-lg overflow-hidden">
                        <img
                          src={`data:image/${lastResponse.result.format};base64,${lastResponse.result.image_base64}`}
                          alt={lastResponse.result.alt_text}
                          className="w-full h-auto"
                          style={{ 
                            maxWidth: lastResponse.result.width,
                            maxHeight: lastResponse.result.height 
                          }}
                        />
                      </div>

                      {/* Chart Details */}
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                        <div>
                          <div className="font-semibold">Format</div>
                          <div className="text-muted-foreground">{lastResponse.result.format.toUpperCase()}</div>
                        </div>
                        <div>
                          <div className="font-semibold">Dimensions</div>
                          <div className="text-muted-foreground">
                            {lastResponse.result.width} × {lastResponse.result.height}
                          </div>
                        </div>
                        <div>
                          <div className="font-semibold">DPI</div>
                          <div className="text-muted-foreground">{lastResponse.result.dpi}</div>
                        </div>
                        <div>
                          <div className="font-semibold">Generation Time</div>
                          <div className="text-muted-foreground">{lastResponse.duration_ms}ms</div>
                        </div>
                      </div>

                      {/* Download Options */}
                      <div className="flex gap-2">
                        <Button 
                          variant="outline" 
                          size="sm"
                          onClick={() => handleDownload('png')}
                        >
                          <Download className="h-4 w-4 mr-2" />
                          PNG
                        </Button>
                        <Button 
                          variant="outline" 
                          size="sm"
                          onClick={() => handleDownload('svg')}
                        >
                          <Download className="h-4 w-4 mr-2" />
                          SVG
                        </Button>
                        <Button 
                          variant="outline" 
                          size="sm"
                          onClick={() => handleDownload('pdf')}
                        >
                          <Download className="h-4 w-4 mr-2" />
                          PDF
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ) : (
                <Card>
                  <CardContent className="flex flex-col items-center justify-center h-64 text-center">
                    <Sparkles className="h-12 w-12 text-muted-foreground mb-4" />
                    <h3 className="text-lg font-semibold mb-2">Ready to Generate</h3>
                    <p className="text-muted-foreground mb-4">
                      Configure your chart settings and click "Generate Chart" to see the results
                    </p>
                  </CardContent>
                </Card>
              )}
            </TabsContent>

            <TabsContent value="data" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>Sample Data for {chartType.replace('_', ' ')}</CardTitle>
                </CardHeader>
                <CardContent>
                  <pre className="bg-muted p-4 rounded-lg text-sm overflow-auto">
                    {JSON.stringify(currentSampleData, null, 2)}
                  </pre>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="custom" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>Custom Data (JSON)</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <Textarea
                      placeholder="Enter custom JSON data..."
                      value={customData}
                      onChange={(e) => setCustomData(e.target.value)}
                      className="font-mono text-sm"
                      rows={12}
                    />
                    <p className="text-xs text-muted-foreground">
                      Enter custom JSON data to override the sample data. Leave empty to use sample data.
                    </p>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="history" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>Generation History</CardTitle>
                </CardHeader>
                <CardContent>
                  {generationHistory.length > 0 ? (
                    <div className="space-y-2">
                      {generationHistory.map((response, index) => (
                        <div 
                          key={response.request_id} 
                          className="flex items-center justify-between p-3 border rounded-lg"
                        >
                          <div className="flex items-center gap-3">
                            {getStatusIcon(response.cached, response.duration_ms)}
                            <div>
                              <div className="font-medium text-sm">
                                {response.result.caption || 'Generated Chart'}
                              </div>
                              <div className="text-xs text-muted-foreground">
                                {new Date(response.result.metadata.generated_at || Date.now()).toLocaleString()}
                              </div>
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            {response.cached && (
                              <Badge variant="secondary" className="text-xs">
                                Cached
                              </Badge>
                            )}
                            <Badge variant="outline" className="text-xs">
                              {response.duration_ms}ms
                            </Badge>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-8 text-muted-foreground">
                      No charts generated yet
                    </div>
                  )}
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  );
}
