/**
 * InsightsLiveStream - Real-time WebSocket event stream component
 * 
 * Displays live AI invocation events from the InsightsBus Redis stream.
 * Uses WebSocket for real-time updates with automatic reconnection.
 * 
 * Linear Issue: ROS-61
 * 
 * @module components/insights/InsightsLiveStream
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { 
  Play, 
  Pause, 
  Trash2, 
  Wifi, 
  WifiOff,
  Activity,
  Clock,
  Zap
} from 'lucide-react';
import { AlertBadge } from './AlertBadge';
import { MetricSparkline } from './MetricSparkline';
import { cn } from '@/lib/utils';

// ============================================
// Types
// ============================================

export interface InsightEvent {
  id: string;
  timestamp: string;
  type: string;
  governance_mode: 'DEMO' | 'LIVE';
  project_id: string;
  tier: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  run_id?: string;
  stage?: number;
  agent_id?: string;
  latency_ms?: number;
  tokens_used?: number;
  cost_usd?: number;
}

export interface InsightsLiveStreamProps {
  /** WebSocket URL for insights stream */
  wsUrl?: string;
  /** Maximum events to keep in memory */
  maxEvents?: number;
  /** Initial paused state */
  initialPaused?: boolean;
  /** Filter by governance mode */
  governanceFilter?: 'DEMO' | 'LIVE' | 'all';
  /** Custom class name */
  className?: string;
  /** Callback when event received */
  onEvent?: (event: InsightEvent) => void;
}

// ============================================
// Component
// ============================================

export function InsightsLiveStream({
  wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/api/insights/stream`,
  maxEvents = 100,
  initialPaused = false,
  governanceFilter = 'all',
  className,
  onEvent,
}: InsightsLiveStreamProps) {
  // State
  const [events, setEvents] = useState<InsightEvent[]>([]);
  const [isPaused, setIsPaused] = useState(initialPaused);
  const [isConnected, setIsConnected] = useState(false);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const [latencyHistory, setLatencyHistory] = useState<number[]>([]);
  
  // Refs
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttempts = useRef(0);

  // ============================================
  // WebSocket Connection
  // ============================================

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    try {
      const ws = new WebSocket(wsUrl);
      
      ws.onopen = () => {
        setIsConnected(true);
        setConnectionError(null);
        reconnectAttempts.current = 0;
        console.log('[InsightsLiveStream] Connected to WebSocket');
      };

      ws.onmessage = (message) => {
        if (isPaused) return;

        try {
          const event: InsightEvent = JSON.parse(message.data);
          
          // Apply governance filter
          if (governanceFilter !== 'all' && event.governance_mode !== governanceFilter) {
            return;
          }

          // Update events list
          setEvents(prev => {
            const updated = [event, ...prev].slice(0, maxEvents);
            return updated;
          });

          // Track latency
          if (event.latency_ms) {
            setLatencyHistory(prev => [...prev.slice(-29), event.latency_ms!]);
          }

          // Callback
          onEvent?.(event);
        } catch (err) {
          console.error('[InsightsLiveStream] Failed to parse event:', err);
        }
      };

      ws.onerror = (error) => {
        console.error('[InsightsLiveStream] WebSocket error:', error);
        setConnectionError('Connection error');
      };

      ws.onclose = () => {
        setIsConnected(false);
        console.log('[InsightsLiveStream] WebSocket closed');
        
        // Exponential backoff reconnect
        const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000);
        reconnectAttempts.current++;
        
        reconnectTimeoutRef.current = setTimeout(() => {
          if (!isPaused) connect();
        }, delay);
      };

      wsRef.current = ws;
    } catch (err) {
      setConnectionError('Failed to connect');
      console.error('[InsightsLiveStream] Connection failed:', err);
    }
  }, [wsUrl, isPaused, governanceFilter, maxEvents, onEvent]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  // ============================================
  // Lifecycle
  // ============================================

  useEffect(() => {
    if (!isPaused) {
      connect();
    }
    return () => disconnect();
  }, [connect, disconnect, isPaused]);

  // ============================================
  // Handlers
  // ============================================

  const handleTogglePause = () => {
    setIsPaused(prev => !prev);
    if (isPaused) {
      connect();
    } else {
      disconnect();
    }
  };

  const handleClear = () => {
    setEvents([]);
    setLatencyHistory([]);
  };

  // ============================================
  // Computed Values
  // ============================================

  const stats = {
    total: events.length,
    completed: events.filter(e => e.status === 'completed').length,
    failed: events.filter(e => e.status === 'failed').length,
    avgLatency: latencyHistory.length > 0 
      ? Math.round(latencyHistory.reduce((a, b) => a + b, 0) / latencyHistory.length)
      : 0,
  };

  // ============================================
  // Render
  // ============================================

  return (
    <Card className={cn('flex flex-col h-full', className)}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-lg">
            <Activity className="h-5 w-5" />
            Live Insights Stream
          </CardTitle>
          
          <div className="flex items-center gap-2">
            {/* Connection Status */}
            <Badge 
              variant={isConnected ? 'default' : 'destructive'}
              className="gap-1"
            >
              {isConnected ? (
                <>
                  <Wifi className="h-3 w-3" />
                  Connected
                </>
              ) : (
                <>
                  <WifiOff className="h-3 w-3" />
                  {connectionError || 'Disconnected'}
                </>
              )}
            </Badge>
            
            {/* Controls */}
            <Button
              variant="outline"
              size="sm"
              onClick={handleTogglePause}
              className="gap-1"
            >
              {isPaused ? (
                <>
                  <Play className="h-4 w-4" />
                  Resume
                </>
              ) : (
                <>
                  <Pause className="h-4 w-4" />
                  Pause
                </>
              )}
            </Button>
            
            <Button
              variant="outline"
              size="sm"
              onClick={handleClear}
              className="gap-1"
            >
              <Trash2 className="h-4 w-4" />
              Clear
            </Button>
          </div>
        </div>

        {/* Stats Bar */}
        <div className="flex items-center gap-4 mt-2 text-sm text-muted-foreground">
          <div className="flex items-center gap-1">
            <Zap className="h-4 w-4" />
            <span>{stats.total} events</span>
          </div>
          <div className="flex items-center gap-1">
            <Badge variant="outline" className="text-green-600">
              {stats.completed} completed
            </Badge>
          </div>
          {stats.failed > 0 && (
            <div className="flex items-center gap-1">
              <Badge variant="destructive">
                {stats.failed} failed
              </Badge>
            </div>
          )}
          <div className="flex items-center gap-1">
            <Clock className="h-4 w-4" />
            <span>Avg: {stats.avgLatency}ms</span>
          </div>
          
          {/* Latency Sparkline */}
          {latencyHistory.length > 0 && (
            <MetricSparkline 
              data={latencyHistory} 
              label="Latency"
              color="blue"
              className="ml-auto"
            />
          )}
        </div>
      </CardHeader>

      <CardContent className="flex-1 overflow-hidden p-0">
        <ScrollArea className="h-full p-4">
          {events.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-32 text-muted-foreground">
              <Activity className="h-8 w-8 mb-2 opacity-50" />
              <p>Waiting for events...</p>
              {isPaused && (
                <p className="text-sm mt-1">Stream is paused</p>
              )}
            </div>
          ) : (
            <div className="space-y-2">
              {events.map((event) => (
                <EventCard key={event.id} event={event} />
              ))}
            </div>
          )}
        </ScrollArea>
      </CardContent>
    </Card>
  );
}

// ============================================
// Event Card Sub-component
// ============================================

interface EventCardProps {
  event: InsightEvent;
}

function EventCard({ event }: EventCardProps) {
  const statusColors = {
    pending: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
    running: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
    completed: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
    failed: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
  };

  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString();
  };

  return (
    <div className={cn(
      'p-3 rounded-lg border bg-card transition-all',
      event.status === 'failed' && 'border-red-200 dark:border-red-800'
    )}>
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <Badge variant="outline" className={statusColors[event.status]}>
              {event.status}
            </Badge>
            <Badge variant="secondary">
              {event.governance_mode}
            </Badge>
            {event.tier && (
              <Badge variant="outline">
                {event.tier}
              </Badge>
            )}
            {event.status === 'failed' && (
              <AlertBadge severity="error" />
            )}
          </div>
          
          <div className="text-sm text-muted-foreground">
            <span className="font-mono text-xs">{event.id.slice(0, 12)}...</span>
            {event.agent_id && (
              <span className="ml-2">Agent: {event.agent_id}</span>
            )}
            {event.stage !== undefined && (
              <span className="ml-2">Stage: {event.stage}</span>
            )}
          </div>
        </div>

        <div className="text-right text-sm">
          <div className="text-muted-foreground">
            {formatTime(event.timestamp)}
          </div>
          {event.latency_ms && (
            <div className="font-mono text-xs">
              {event.latency_ms}ms
            </div>
          )}
          {event.tokens_used && (
            <div className="text-xs text-muted-foreground">
              {event.tokens_used.toLocaleString()} tokens
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default InsightsLiveStream;
