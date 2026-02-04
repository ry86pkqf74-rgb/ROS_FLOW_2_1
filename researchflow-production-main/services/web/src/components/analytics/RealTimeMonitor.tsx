/*
Real-Time Analytics Monitor Component
====================================

React component for displaying real-time system health and performance metrics.
Features live updates via WebSocket connection and interactive charts.
*/

import React, { useState, useEffect, useMemo } from 'react';
import { Card, CardHeader, CardContent, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Progress } from '@/components/ui/progress';
import { Button } from '@/components/ui/button';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts';
import { Activity, AlertTriangle, CheckCircle, Clock, Cpu, HardDrive, MemoryStick, TrendingUp, TrendingDown } from 'lucide-react';

// ============================================================================
// Types & Interfaces
// ============================================================================

interface SystemHealth {
  timestamp: string;
  cpu_usage: number;
  memory_usage: number;
  disk_usage: number;
  active_operations: number;
  queue_length: number;
  response_time_avg: number;
  error_rate: number;
}

interface Alert {
  type: string;
  severity: 'warning' | 'critical';
  message: string;
  value: number;
  timestamp: string;
}

interface OperationStats {
  active_operations: number;
  completed_operations: number;
  success_rate: number;
  avg_processing_time: number;
  avg_compression_ratio: number;
}

interface DashboardSummary {
  active_operations: number;
  completed_operations: number;
  success_rate: number;
  avg_processing_time: number;
  system_health_score: number;
  uptime_hours: number;
  total_operations_today: number;
}

interface RealTimeMonitorProps {
  className?: string;
  autoRefresh?: boolean;
  refreshInterval?: number;
}

// ============================================================================
// Real-Time Monitor Component
// ============================================================================

export const RealTimeMonitor: React.FC<RealTimeMonitorProps> = ({
  className = '',
  autoRefresh = true,
  refreshInterval = 5000
}) => {
  // State management
  const [healthData, setHealthData] = useState<SystemHealth | null>(null);
  const [healthHistory, setHealthHistory] = useState<SystemHealth[]>([]);
  const [operationStats, setOperationStats] = useState<OperationStats | null>(null);
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [websocket, setWebsocket] = useState<WebSocket | null>(null);

  // WebSocket connection management
  useEffect(() => {
    if (!autoRefresh) return;

    const connectWebSocket = () => {
      try {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/api/analytics/ws/realtime`;
        const ws = new WebSocket(wsUrl);

        ws.onopen = () => {
          setIsConnected(true);
          setError(null);
          console.log('Analytics WebSocket connected');
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            handleWebSocketMessage(data);
          } catch (e) {
            console.error('Failed to parse WebSocket message:', e);
          }
        };

        ws.onclose = () => {
          setIsConnected(false);
          // Attempt reconnection after delay
          setTimeout(connectWebSocket, 5000);
        };

        ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          setError('WebSocket connection failed');
        };

        setWebsocket(ws);
      } catch (e) {
        console.error('Failed to create WebSocket:', e);
        setError('Failed to establish real-time connection');
      }
    };

    connectWebSocket();

    return () => {
      if (websocket) {
        websocket.close();
      }
    };
  }, [autoRefresh]);

  // Handle WebSocket messages
  const handleWebSocketMessage = (data: any) => {
    switch (data.type) {
      case 'initial':
        // Initial dashboard data
        if (data.data.summary) setSummary(data.data.summary);
        if (data.data.system_health?.current) setHealthData(data.data.system_health.current);
        if (data.data.system_health?.history) setHealthHistory(data.data.system_health.history);
        if (data.data.operation_metrics) setOperationStats(data.data.operation_metrics);
        if (data.data.alerts) setAlerts(data.data.alerts);
        setIsLoading(false);
        break;

      case 'health_update':
        // Real-time health update
        const newHealth = data.data;
        setHealthData(newHealth);
        setHealthHistory(prev => [...prev.slice(-19), newHealth]); // Keep last 20 points
        break;

      case 'alert':
        // New alert
        setAlerts(prev => [data.data, ...prev.slice(0, 9)]); // Keep last 10 alerts
        break;
    }
  };

  // Fetch initial data (fallback for non-WebSocket)
  useEffect(() => {
    if (!autoRefresh || websocket) return;

    const fetchData = async () => {
      try {
        setIsLoading(true);
        const [healthRes, summaryRes, alertsRes, operationsRes] = await Promise.all([
          fetch('/api/analytics/health'),
          fetch('/api/analytics/dashboard/summary'),
          fetch('/api/analytics/dashboard/alerts'),
          fetch('/api/analytics/operations/stats')
        ]);

        if (healthRes.ok) {
          const healthData = await healthRes.json();
          setHealthData(healthData.health);
        }

        if (summaryRes.ok) {
          const summaryData = await summaryRes.json();
          setSummary(summaryData.summary);
        }

        if (alertsRes.ok) {
          const alertsData = await alertsRes.json();
          setAlerts(alertsData.alerts);
        }

        if (operationsRes.ok) {
          const operationsData = await operationsRes.json();
          setOperationStats(operationsData.statistics);
        }

        setError(null);
      } catch (e) {
        setError('Failed to fetch analytics data');
        console.error('Analytics data fetch error:', e);
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();

    if (autoRefresh && !websocket) {
      const interval = setInterval(fetchData, refreshInterval);
      return () => clearInterval(interval);
    }
  }, [autoRefresh, refreshInterval, websocket]);

  // Chart data preparation
  const chartData = useMemo(() => {
    return healthHistory.map((health, index) => ({
      time: new Date(health.timestamp).toLocaleTimeString(),
      cpu: health.cpu_usage,
      memory: health.memory_usage,
      responseTime: health.response_time_avg * 1000, // Convert to ms
      errorRate: health.error_rate
    }));
  }, [healthHistory]);

  // Get status color for metrics
  const getStatusColor = (value: number, thresholds: { warning: number; critical: number }) => {
    if (value >= thresholds.critical) return 'destructive';
    if (value >= thresholds.warning) return 'warning';
    return 'default';
  };

  // Get trend icon
  const getTrendIcon = (current: number, previous: number) => {
    if (current > previous * 1.05) return <TrendingUp className="h-4 w-4 text-red-500" />;
    if (current < previous * 0.95) return <TrendingDown className="h-4 w-4 text-green-500" />;
    return <Activity className="h-4 w-4 text-gray-500" />;
  };

  if (isLoading) {
    return (
      <div className={`real-time-monitor ${className}`}>
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <span className="ml-2">Loading analytics data...</span>
        </div>
      </div>
    );
  }

  if (error && !healthData) {
    return (
      <div className={`real-time-monitor ${className}`}>
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className={`real-time-monitor space-y-4 ${className}`}>
      {/* Header with connection status */}
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Real-Time Monitor</h2>
        <div className="flex items-center space-x-2">
          <Badge variant={isConnected ? 'default' : 'secondary'}>
            {isConnected ? (
              <>
                <CheckCircle className="h-3 w-3 mr-1" />
                Live
              </>
            ) : (
              <>
                <Clock className="h-3 w-3 mr-1" />
                Updating...
              </>
            )}
          </Badge>
          {error && (
            <Badge variant="destructive">
              <AlertTriangle className="h-3 w-3 mr-1" />
              Connection Issue
            </Badge>
          )}
        </div>
      </div>

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center space-x-2">
                <Activity className="h-5 w-5 text-blue-500" />
                <div>
                  <p className="text-sm text-gray-600">Active Operations</p>
                  <p className="text-2xl font-bold">{summary.active_operations}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4">
              <div className="flex items-center space-x-2">
                <CheckCircle className="h-5 w-5 text-green-500" />
                <div>
                  <p className="text-sm text-gray-600">Success Rate</p>
                  <p className="text-2xl font-bold">{summary.success_rate.toFixed(1)}%</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4">
              <div className="flex items-center space-x-2">
                <Clock className="h-5 w-5 text-orange-500" />
                <div>
                  <p className="text-sm text-gray-600">Avg Processing</p>
                  <p className="text-2xl font-bold">{summary.avg_processing_time.toFixed(2)}s</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4">
              <div className="flex items-center space-x-2">
                <TrendingUp className="h-5 w-5 text-purple-500" />
                <div>
                  <p className="text-sm text-gray-600">Health Score</p>
                  <p className="text-2xl font-bold">{summary.system_health_score.toFixed(0)}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* System Health Metrics */}
      {healthData && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center text-sm">
                <Cpu className="h-4 w-4 mr-2" />
                CPU Usage
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span>{healthData.cpu_usage.toFixed(1)}%</span>
                  <Badge variant={getStatusColor(healthData.cpu_usage, { warning: 70, critical: 85 })}>
                    {healthData.cpu_usage > 85 ? 'Critical' : healthData.cpu_usage > 70 ? 'Warning' : 'Normal'}
                  </Badge>
                </div>
                <Progress value={healthData.cpu_usage} />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center text-sm">
                <MemoryStick className="h-4 w-4 mr-2" />
                Memory Usage
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span>{healthData.memory_usage.toFixed(1)}%</span>
                  <Badge variant={getStatusColor(healthData.memory_usage, { warning: 75, critical: 90 })}>
                    {healthData.memory_usage > 90 ? 'Critical' : healthData.memory_usage > 75 ? 'Warning' : 'Normal'}
                  </Badge>
                </div>
                <Progress value={healthData.memory_usage} />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center text-sm">
                <HardDrive className="h-4 w-4 mr-2" />
                Disk Usage
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span>{healthData.disk_usage.toFixed(1)}%</span>
                  <Badge variant={getStatusColor(healthData.disk_usage, { warning: 80, critical: 95 })}>
                    {healthData.disk_usage > 95 ? 'Critical' : healthData.disk_usage > 80 ? 'Warning' : 'Normal'}
                  </Badge>
                </div>
                <Progress value={healthData.disk_usage} />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Performance Charts */}
      {chartData.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <Card>
            <CardHeader>
              <CardTitle>System Performance</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="time" />
                  <YAxis />
                  <Tooltip />
                  <Line type="monotone" dataKey="cpu" stroke="#3b82f6" name="CPU %" strokeWidth={2} />
                  <Line type="monotone" dataKey="memory" stroke="#10b981" name="Memory %" strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Response Time & Errors</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="time" />
                  <YAxis yAxisId="left" />
                  <YAxis yAxisId="right" orientation="right" />
                  <Tooltip />
                  <Line 
                    yAxisId="left" 
                    type="monotone" 
                    dataKey="responseTime" 
                    stroke="#f59e0b" 
                    name="Response Time (ms)" 
                    strokeWidth={2} 
                  />
                  <Line 
                    yAxisId="right" 
                    type="monotone" 
                    dataKey="errorRate" 
                    stroke="#ef4444" 
                    name="Error Rate %" 
                    strokeWidth={2} 
                  />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Active Alerts */}
      {alerts.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <AlertTriangle className="h-5 w-5 mr-2" />
              Active Alerts ({alerts.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {alerts.slice(0, 5).map((alert, index) => (
                <Alert key={index} variant={alert.severity === 'critical' ? 'destructive' : 'default'}>
                  <AlertTriangle className="h-4 w-4" />
                  <AlertDescription className="flex justify-between">
                    <span>{alert.message}</span>
                    <span className="text-xs text-gray-500">
                      {new Date(alert.timestamp).toLocaleTimeString()}
                    </span>
                  </AlertDescription>
                </Alert>
              ))}
              {alerts.length > 5 && (
                <p className="text-sm text-gray-500 text-center">
                  ... and {alerts.length - 5} more alerts
                </p>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Refresh Controls */}
      <div className="flex justify-end">
        <Button
          variant="outline"
          size="sm"
          onClick={() => window.location.reload()}
        >
          Refresh Dashboard
        </Button>
      </div>
    </div>
  );
};

export default RealTimeMonitor;