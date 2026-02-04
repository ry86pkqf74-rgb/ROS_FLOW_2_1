/**
 * useAgentProgress - React Hook for Agent Progress Tracking
 * 
 * Provides real-time WebSocket connection to track LangGraph agent progress.
 * Handles reconnection, status updates, and progress events.
 * 
 * Linear Issue: ROS-85
 */

import { useState, useEffect, useCallback, useRef } from 'react';

export type AgentStatus = 
  | 'idle'
  | 'queued'
  | 'running'
  | 'completed'
  | 'failed'
  | 'connecting'
  | 'disconnected';

export interface AgentProgress {
  stage: string;
  iteration: number;
  totalIterations?: number;
  currentStep?: string;
  qualityScore?: number;
}

export interface AgentResult {
  taskId: string;
  agentName: string;
  success: boolean;
  result?: Record<string, any>;
  artifacts?: Array<{
    type: string;
    content: any;
    createdAt: string;
  }>;
  qualityScore: number;
  iterations: number;
  durationMs: number;
  ragSources: string[];
  error?: string;
}

export interface UseAgentProgressOptions {
  /** Worker WebSocket URL */
  workerUrl?: string;
  /** Auto-reconnect on disconnect */
  autoReconnect?: boolean;
  /** Reconnect interval in ms */
  reconnectInterval?: number;
  /** Maximum reconnect attempts */
  maxReconnectAttempts?: number;
  /** Callback when progress updates */
  onProgress?: (progress: AgentProgress) => void;
  /** Callback when agent completes */
  onComplete?: (result: AgentResult) => void;
  /** Callback on error */
  onError?: (error: string) => void;
}

export interface UseAgentProgressReturn {
  /** Current status */
  status: AgentStatus;
  /** Current progress data */
  progress: AgentProgress | null;
  /** Final result (when completed) */
  result: AgentResult | null;
  /** Error message if failed */
  error: string | null;
  /** Agent name if known */
  agentName: string | null;
  /** Connect to track a task */
  connect: (taskId: string) => void;
  /** Disconnect from tracking */
  disconnect: () => void;
  /** Check if currently connected */
  isConnected: boolean;
  /** Task ID being tracked */
  taskId: string | null;
}

const DEFAULT_WORKER_URL =
  // Vite build-time env
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  (typeof import.meta !== 'undefined' && (import.meta as any).env?.VITE_AGENT_WS_URL) ||
  // Fallbacks for other runtimes/tests
  (process.env as Record<string, string | undefined> | undefined)?.VITE_AGENT_WS_URL ||
  (process.env as Record<string, string | undefined> | undefined)?.NEXT_PUBLIC_WORKER_URL ||
  'ws://localhost:8000';

const DEFAULT_OPTIONS: Required<UseAgentProgressOptions> = {
  workerUrl: DEFAULT_WORKER_URL,
  autoReconnect: true,
  reconnectInterval: 3000,
  maxReconnectAttempts: 5,
  onProgress: () => {},
  onComplete: () => {},
  onError: () => {},
};

export function useAgentProgress(
  options: UseAgentProgressOptions = {}
): UseAgentProgressReturn {
  const opts = { ...DEFAULT_OPTIONS, ...options };
  
  const [status, setStatus] = useState<AgentStatus>('idle');
  const [progress, setProgress] = useState<AgentProgress | null>(null);
  const [result, setResult] = useState<AgentResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [agentName, setAgentName] = useState<string | null>(null);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const pingIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Cleanup function
  const cleanup = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }
    setIsConnected(false);
  }, []);

  // Connect to WebSocket
  const connect = useCallback((newTaskId: string) => {
    cleanup();
    
    setTaskId(newTaskId);
    setStatus('connecting');
    setProgress(null);
    setResult(null);
    setError(null);
    reconnectAttemptsRef.current = 0;

    const wsUrl = `${opts.workerUrl}/agents/ws/${newTaskId}`;
    
    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        setStatus('queued');
        reconnectAttemptsRef.current = 0;

        // Setup ping interval
        pingIntervalRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send('ping');
          }
        }, 25000);
      };

      ws.onmessage = (event) => {
        try {
          // Handle pong
          if (event.data === 'pong') return;

          const message = JSON.parse(event.data);
          
          switch (message.type) {
            case 'status':
              setStatus(message.data?.status || 'running');
              setAgentName(message.data?.agent_name || null);
              if (message.data?.progress) {
                setProgress(message.data.progress);
              }
              break;

            case 'progress':
              setStatus('running');
              const progressData: AgentProgress = {
                stage: message.data?.stage || 'processing',
                iteration: message.data?.iteration || 0,
                totalIterations: message.data?.max_iterations,
                currentStep: message.data?.current_step,
                qualityScore: message.data?.quality_score,
              };
              setProgress(progressData);
              opts.onProgress(progressData);
              break;

            case 'complete':
              setStatus('completed');
              const completeResult: AgentResult = {
                taskId: newTaskId,
                agentName: message.data?.agent_name || agentName || 'unknown',
                success: message.data?.success ?? true,
                result: message.data?.result,
                artifacts: message.data?.artifacts || [],
                qualityScore: message.data?.quality_score || 0,
                iterations: message.data?.iterations || 0,
                durationMs: message.data?.duration_ms || 0,
                ragSources: message.data?.rag_sources || [],
              };
              setResult(completeResult);
              opts.onComplete(completeResult);
              break;

            case 'error':
              setStatus('failed');
              const errorMsg = message.data?.message || 'Unknown error';
              setError(errorMsg);
              opts.onError(errorMsg);
              break;

            case 'keepalive':
              // Ignore keepalives
              break;

            default:
              console.warn('Unknown WebSocket message type:', message.type);
          }
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e);
        }
      };

      ws.onerror = (event) => {
        console.error('WebSocket error:', event);
        setError('Connection error');
      };

      ws.onclose = (event) => {
        setIsConnected(false);
        
        // Don't reconnect if cleanly closed or completed
        if (event.wasClean || status === 'completed' || status === 'failed') {
          setStatus(status === 'completed' || status === 'failed' ? status : 'disconnected');
          return;
        }

        // Auto-reconnect
        if (opts.autoReconnect && reconnectAttemptsRef.current < opts.maxReconnectAttempts) {
          setStatus('connecting');
          reconnectAttemptsRef.current++;
          
          reconnectTimeoutRef.current = setTimeout(() => {
            connect(newTaskId);
          }, opts.reconnectInterval);
        } else {
          setStatus('disconnected');
          setError('Connection lost');
        }
      };
    } catch (e) {
      setStatus('failed');
      setError(e instanceof Error ? e.message : 'Failed to connect');
    }
  }, [opts, cleanup, status, agentName]);

  // Disconnect
  const disconnect = useCallback(() => {
    cleanup();
    setStatus('idle');
    setTaskId(null);
    setProgress(null);
    setResult(null);
    setError(null);
    setAgentName(null);
  }, [cleanup]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      cleanup();
    };
  }, [cleanup]);

  return {
    status,
    progress,
    result,
    error,
    agentName,
    connect,
    disconnect,
    isConnected,
    taskId,
  };
}

export default useAgentProgress;
