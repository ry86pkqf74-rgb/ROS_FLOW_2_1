/**
 * Visualization Dashboard
 * 
 * Real-time monitoring and analytics dashboard for the visualization system.
 * Features:
 * - System performance metrics and charts
 * - Cache hit rates and performance analytics
 * - Error rate monitoring and alerts
 * - User activity insights and trends
 * - System health monitoring
 * - Queue depth and worker status
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useVisualization, type DashboardMetrics, type VisualizationHealth } from '@/hooks/useVisualization';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Activity,
  BarChart3,
  Clock,
  Database,
  RefreshCw,
  TrendingUp,
  TrendingDown,
  Users,
  Zap,
  AlertTriangle,
  CheckCircle,
  Settings,
  Monitor,
  HardDrive,
  Cpu,
  Timer,
  FileImage,
  Palette,
  Shield,
  Download
} from 'lucide-react';
import { cn } from '@/lib/utils';
import Plot from 'react-plotly.js';

interface SystemAlert {
  id: string;
  type: 'warning' | 'error' | 'info';
  message: string;
  timestamp: string;
  component: string;
}

interface MetricsHistory {
  timestamp: string;
  chartsGenerated: number;
  averageTime: number;
  cacheHitRate: number;
  errorRate: number;
  queueDepth: number;
}

export default function VisualizationDashboard() {
  const { 
    getDashboardMetrics, 
    getHealth, 
    clearCache,
    metrics, 
    health, 
    loading 
  } = useVisualization();

  // State management
  const [metricsHistory, setMetricsHistory] = useState<MetricsHistory[]>([]);
  const [alerts, setAlerts] = useState<SystemAlert[]>([]);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [refreshInterval] = useState(30000); // 30 seconds
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  // Load initial data
  useEffect(() => {
    loadDashboardData();
  }, []);

  // Auto-refresh functionality
  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(() => {
      loadDashboardData();
    }, refreshInterval);

    return () => clearInterval(interval);
  }, [autoRefresh, refreshInterval]);

  const loadDashboardData = useCallback(async () => {
    try {
      const [metricsData, healthData] = await Promise.all([
        getDashboardMetrics(),
        getHealth()
      ]);
      
      // Update metrics history
      if (metricsData) {
        const newHistoryPoint: MetricsHistory = {
          timestamp: new Date().toISOString(),
          chartsGenerated: metricsData.chartsGenerated24h,
          averageTime: metricsData.averageGenerationTime,
          cacheHitRate: metricsData.cacheHitRate * 100,
          errorRate: metricsData.errorRate * 100,
          queueDepth: metricsData.queueDepth
        };
        
        setMetricsHistory(prev => [...prev.slice(-50), newHistoryPoint]); // Keep last 50 points
      }

      // Generate alerts based on metrics
      if (metricsData && healthData) {
        const newAlerts: SystemAlert[] = [];
        
        if (metricsData.errorRate > 0.1) {
          newAlerts.push({
            id: `error-rate-${Date.now()}`,
            type: 'error',
            message: `High error rate: ${(metricsData.errorRate * 100).toFixed(1)}%`,
            timestamp: new Date().toISOString(),
            component: 'generator'
          });
        }
        
        if (metricsData.averageGenerationTime > 10000) {
          newAlerts.push({
            id: `slow-generation-${Date.now()}`,
            type: 'warning',
            message: `Slow chart generation: ${metricsData.averageGenerationTime}ms average`,
            timestamp: new Date().toISOString(),
            component: 'performance'
          });
        }
        
        if (metricsData.queueDepth > 10) {
          newAlerts.push({
            id: `queue-depth-${Date.now()}`,
            type: 'warning',
            message: `High queue depth: ${metricsData.queueDepth} pending jobs`,
            timestamp: new Date().toISOString(),
            component: 'queue'
          });
        }

        if (!healthData.components.worker.status || healthData.components.worker.status !== 'healthy') {
          newAlerts.push({
            id: `worker-unhealthy-${Date.now()}`,
            type: 'error',
            message: 'Visualization worker is unhealthy',
            timestamp: new Date().toISOString(),
            component: 'worker'
          });
        }

        setAlerts(prev => {
          // Remove old alerts and add new ones
          const filtered = prev.filter(alert => 
            Date.now() - new Date(alert.timestamp).getTime() < 300000 // Keep alerts for 5 minutes
          );
          return [...filtered, ...newAlerts];
        });
      }
      
      setLastUpdated(new Date());
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
    }
  }, [getDashboardMetrics, getHealth]);

  // Chart data for metrics visualization
  const performanceChartData = useMemo(() => {
    if (metricsHistory.length === 0) return [];

    const timestamps = metricsHistory.map(m => new Date(m.timestamp));
    
    return [
      {
        name: 'Generation Time (ms)',
        x: timestamps,
        y: metricsHistory.map(m => m.averageTime),
        type: 'scatter',
        mode: 'lines+markers',
        line: { color: '#3b82f6' },
        yaxis: 'y'
      },
      {
        name: 'Cache Hit Rate (%)',
        x: timestamps,
        y: metricsHistory.map(m => m.cacheHitRate),
        type: 'scatter',
        mode: 'lines+markers',
        line: { color: '#10b981' },
        yaxis: 'y2'
      }
    ];
  }, [metricsHistory]);

  const queueChartData = useMemo(() => {
    if (metricsHistory.length === 0) return [];

    const timestamps = metricsHistory.map(m => new Date(m.timestamp));
    
    return [
      {
        name: 'Queue Depth',
        x: timestamps,
        y: metricsHistory.map(m => m.queueDepth),
        type: 'scatter',
        mode: 'lines+markers',
        line: { color: '#f59e0b' },
        fill: 'tonexty'
      }
    ];
  }, [metricsHistory]);

  const chartTypesData = useMemo(() => {
    if (!metrics?.topChartTypes) return [];

    return [
      {
        type: 'pie',
        values: metrics.topChartTypes.map(t => t.count),
        labels: metrics.topChartTypes.map(t => t.type.replace('_', ' ')),
        hole: 0.4,
        marker: {
          colors: ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6']
        }
      }
    ];
  }, [metrics]);

  const handleClearCache = useCallback(async () => {
    try {
      await clearCache();
    } catch (error) {
      console.error('Failed to clear cache:', error);
    }
  }, [clearCache]);

  const getHealthBadge = (status: string | boolean, label: string) => {
    const isHealthy = status === 'healthy' || status === true;
    return (
      <div className="flex items-center justify-between">
        <span className="text-sm">{label}</span>
        <Badge variant={isHealthy ? 'default' : 'destructive'}>
          {isHealthy ? 'Healthy' : 'Unhealthy'}
        </Badge>
      </div>
    );
  };

  const MetricCard = ({ 
    title, 
    value, 
    subtitle, 
    icon: Icon, 
    trend, 
    color = 'default' 
  }: {
    title: string;
    value: string | number;
    subtitle?: string;
    icon: any;
    trend?: 'up' | 'down' | 'stable';
    color?: 'default' | 'success' | 'warning' | 'danger';
  }) => {
    const colorClasses = {
      default: 'text-blue-600',
      success: 'text-green-600',
      warning: 'text-orange-600',
      danger: 'text-red-600'
    };

    return (
      <Card>
        <CardContent className="p-6">
          <div className="flex items-center justify-between">
            <div className="space-y-1">
              <p className="text-sm font-medium text-muted-foreground">{title}</p>
              <div className="flex items-center gap-2">
                <p className="text-2xl font-bold">{value}</p>
                {trend && (
                  <div className={cn(
                    "flex items-center text-xs",
                    trend === 'up' ? 'text-green-600' : trend === 'down' ? 'text-red-600' : 'text-gray-600'
                  )}>
                    {trend === 'up' ? (
                      <TrendingUp className="h-3 w-3" />
                    ) : trend === 'down' ? (
                      <TrendingDown className="h-3 w-3" />
                    ) : null}
                  </div>
                )}
              </div>
              {subtitle && (
                <p className="text-xs text-muted-foreground">{subtitle}</p>
              )}
            </div>
            <div className={cn("p-3 rounded-full bg-muted", colorClasses[color])}>
              <Icon className="h-6 w-6" />
            </div>
          </div>
        </CardContent>
      </Card>
    );
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Visualization Dashboard</h1>
          <p className="text-muted-foreground">
            System performance and analytics
          </p>
        </div>
        <div className="flex items-center gap-2">
          {lastUpdated && (
            <span className="text-sm text-muted-foreground">
              Last updated: {lastUpdated.toLocaleTimeString()}
            </span>
          )}
          <Button
            variant="outline"
            onClick={loadDashboardData}
            disabled={loading}
          >
            <RefreshCw className={cn("h-4 w-4 mr-2", loading && "animate-spin")} />
            Refresh
          </Button>
          <Button
            variant={autoRefresh ? 'default' : 'outline'}
            onClick={() => setAutoRefresh(!autoRefresh)}
          >
            <Activity className="h-4 w-4 mr-2" />
            Auto Refresh
          </Button>
        </div>
      </div>

      {/* Alerts */}
      {alerts.length > 0 && (
        <div className="space-y-2">
          {alerts.slice(-3).map(alert => (
            <Alert key={alert.id} variant={alert.type === 'error' ? 'destructive' : 'default'}>
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                <span className="font-medium">{alert.component}:</span> {alert.message}
              </AlertDescription>
            </Alert>
          ))}
        </div>
      )}

      {/* Overview Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard
          title="Charts Generated (24h)"
          value={metrics?.chartsGenerated24h || 0}
          icon={BarChart3}
          color="success"
        />
        <MetricCard
          title="Average Generation Time"
          value={`${metrics?.averageGenerationTime || 0}ms`}
          icon={Timer}
          color={metrics && metrics.averageGenerationTime > 5000 ? 'warning' : 'default'}
        />
        <MetricCard
          title="Cache Hit Rate"
          value={`${Math.round((metrics?.cacheHitRate || 0) * 100)}%`}
          icon={Zap}
          color={metrics && metrics.cacheHitRate > 0.5 ? 'success' : 'warning'}
        />
        <MetricCard
          title="Error Rate"
          value={`${Math.round((metrics?.errorRate || 0) * 100)}%`}
          icon={AlertTriangle}
          color={metrics && metrics.errorRate > 0.05 ? 'danger' : 'success'}
        />
      </div>

      <Tabs defaultValue="performance" className="space-y-4">
        <TabsList>
          <TabsTrigger value="performance">Performance</TabsTrigger>
          <TabsTrigger value="usage">Usage Analytics</TabsTrigger>
          <TabsTrigger value="system">System Health</TabsTrigger>
          <TabsTrigger value="maintenance">Maintenance</TabsTrigger>
        </TabsList>

        <TabsContent value="performance" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Performance Chart */}
            <Card>
              <CardHeader>
                <CardTitle>Performance Metrics</CardTitle>
              </CardHeader>
              <CardContent>
                {performanceChartData.length > 0 ? (
                  <Plot
                    data={performanceChartData}
                    layout={{
                      height: 300,
                      margin: { t: 30, r: 30, b: 50, l: 50 },
                      showlegend: true,
                      xaxis: { title: 'Time' },
                      yaxis: { title: 'Generation Time (ms)', side: 'left' },
                      yaxis2: { title: 'Cache Hit Rate (%)', side: 'right', overlaying: 'y' }
                    }}
                    config={{ responsive: true, displayModeBar: false }}
                    style={{ width: '100%' }}
                  />
                ) : (
                  <div className="h-[300px] flex items-center justify-center text-muted-foreground">
                    No performance data available
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Queue Depth Chart */}
            <Card>
              <CardHeader>
                <CardTitle>Queue Depth</CardTitle>
              </CardHeader>
              <CardContent>
                {queueChartData.length > 0 ? (
                  <Plot
                    data={queueChartData}
                    layout={{
                      height: 300,
                      margin: { t: 30, r: 30, b: 50, l: 50 },
                      showlegend: false,
                      xaxis: { title: 'Time' },
                      yaxis: { title: 'Jobs in Queue' }
                    }}
                    config={{ responsive: true, displayModeBar: false }}
                    style={{ width: '100%' }}
                  />
                ) : (
                  <div className="h-[300px] flex items-center justify-center text-muted-foreground">
                    No queue data available
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Current Performance Stats */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Clock className="h-5 w-5" />
                  Current Status
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex justify-between">
                  <span>Active Jobs:</span>
                  <Badge variant="outline">{metrics?.activeJobs || 0}</Badge>
                </div>
                <div className="flex justify-between">
                  <span>Queue Depth:</span>
                  <Badge variant={metrics && metrics.queueDepth > 5 ? 'secondary' : 'outline'}>
                    {metrics?.queueDepth || 0}
                  </Badge>
                </div>
                <div className="flex justify-between">
                  <span>Success Rate:</span>
                  <Badge variant="default">
                    {Math.round((metrics?.successRate || 0) * 100)}%
                  </Badge>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <HardDrive className="h-5 w-5" />
                  Resource Usage
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span>Memory Usage</span>
                    <span>{Math.round((metrics?.memoryUsage || 0) * 100)}%</span>
                  </div>
                  <Progress value={(metrics?.memoryUsage || 0) * 100} />
                </div>
                <div className="flex justify-between">
                  <span>Avg Image Size:</span>
                  <span>{(metrics?.averageImageSize || 0) > 1024 * 1024 
                    ? `${((metrics?.averageImageSize || 0) / (1024 * 1024)).toFixed(1)}MB`
                    : `${((metrics?.averageImageSize || 0) / 1024).toFixed(0)}KB`}</span>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <AlertTriangle className="h-5 w-5" />
                  Issues
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex justify-between">
                  <span>Timeouts:</span>
                  <Badge variant={metrics && metrics.timeouts > 0 ? 'destructive' : 'outline'}>
                    {metrics?.timeouts || 0}
                  </Badge>
                </div>
                <div className="flex justify-between">
                  <span>Error Rate:</span>
                  <Badge variant={metrics && metrics.errorRate > 0.05 ? 'destructive' : 'default'}>
                    {Math.round((metrics?.errorRate || 0) * 100)}%
                  </Badge>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="usage" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Chart Types Distribution */}
            <Card>
              <CardHeader>
                <CardTitle>Chart Types Distribution</CardTitle>
              </CardHeader>
              <CardContent>
                {chartTypesData.length > 0 ? (
                  <Plot
                    data={chartTypesData}
                    layout={{
                      height: 400,
                      margin: { t: 30, r: 30, b: 30, l: 30 },
                      showlegend: true
                    }}
                    config={{ responsive: true, displayModeBar: false }}
                    style={{ width: '100%' }}
                  />
                ) : (
                  <div className="h-[400px] flex items-center justify-center text-muted-foreground">
                    No usage data available
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Journal Styles Usage */}
            <Card>
              <CardHeader>
                <CardTitle>Journal Styles Usage</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {metrics?.topJournalStyles?.map(style => (
                  <div key={style.style} className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span>{style.style.toUpperCase()}</span>
                      <span>{style.count} ({style.percentage.toFixed(1)}%)</span>
                    </div>
                    <Progress value={style.percentage} />
                  </div>
                )) || (
                  <div className="text-center py-8 text-muted-foreground">
                    No style usage data available
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="system" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* System Health */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Monitor className="h-5 w-5" />
                  System Health
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {health ? (
                  <>
                    <div className="flex items-center justify-between">
                      <span className="text-sm">Overall Status</span>
                      <Badge variant={health.status === 'healthy' ? 'default' : 'destructive'}>
                        {health.status}
                      </Badge>
                    </div>
                    <Separator />
                    {getHealthBadge(health.components.worker.status, 'Worker Service')}
                    {getHealthBadge(health.components.database.healthy, 'Database')}
                    {getHealthBadge(health.components.cache.status, 'Cache Service')}
                    {getHealthBadge(health.components.metrics.healthy, 'Metrics Collection')}
                  </>
                ) : (
                  <div className="text-center py-4 text-muted-foreground">
                    Health data not available
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Configuration */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Settings className="h-5 w-5" />
                  Configuration
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {health?.configuration ? (
                  <>
                    <div className="flex justify-between">
                      <span className="text-sm">Cache Enabled</span>
                      <Badge variant={health.configuration.cacheEnabled ? 'default' : 'outline'}>
                        {health.configuration.cacheEnabled ? 'Yes' : 'No'}
                      </Badge>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm">Rate Limiting</span>
                      <Badge variant={health.configuration.rateLimitEnabled ? 'default' : 'outline'}>
                        {health.configuration.rateLimitEnabled ? 'Enabled' : 'Disabled'}
                      </Badge>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm">Max Data Points</span>
                      <span className="text-sm">{health.configuration.maxDataPoints?.toLocaleString()}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm">Max Concurrent Jobs</span>
                      <span className="text-sm">{health.configuration.maxConcurrentJobs}</span>
                    </div>
                  </>
                ) : (
                  <div className="text-center py-4 text-muted-foreground">
                    Configuration data not available
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="maintenance" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Cache Management</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span>Cache Hit Rate</span>
                    <span>{Math.round((metrics?.cacheHitRate || 0) * 100)}%</span>
                  </div>
                  <Progress value={(metrics?.cacheHitRate || 0) * 100} />
                </div>
                <Button 
                  variant="outline" 
                  onClick={handleClearCache}
                  className="w-full"
                >
                  <Database className="h-4 w-4 mr-2" />
                  Clear Cache
                </Button>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>System Actions</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <Button variant="outline" className="w-full justify-start">
                  <Download className="h-4 w-4 mr-2" />
                  Export System Logs
                </Button>
                <Button variant="outline" className="w-full justify-start">
                  <Settings className="h-4 w-4 mr-2" />
                  View Configuration
                </Button>
                <Button variant="outline" className="w-full justify-start">
                  <Monitor className="h-4 w-4 mr-2" />
                  System Diagnostics
                </Button>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}