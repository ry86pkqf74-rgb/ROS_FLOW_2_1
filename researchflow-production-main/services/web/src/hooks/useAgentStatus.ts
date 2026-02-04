import { useEffect, useRef, useCallback, useState } from 'react';
import type { AgentPhase } from '../components/ai/AgentStatus';

/**
 * Agent Status Message from WebSocket
 */
interface AgentStatusMessage {
  type: 'status' | 'progress' | 'phase' | 'error' | 'ping';
  status?: 'idle' | 'running' | 'paused' | 'completed' | 'failed';
  phase?: AgentPhase;
  progress?: number;
  message?: string;
  timestamp?: string;
}

/**
 * Hook State
 */
interface AgentStatusState {
  status: 'idle' | 'running' | 'paused' | 'completed' | 'failed';
  phase: AgentPhase;
  progress: number;
  error: string | null;
  isConnected: boolean;
  lastUpdate: Date | null;
}

/**
 * Configuration for the WebSocket connection
 */
interface UseAgentStatusConfig {
  wsUrl?: string;
  autoConnect?: boolean;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  heartbeatInterval?: number;
  onError?: (error: Error) => void;
  onPhaseChange?: (phase: AgentPhase) => void;
}

const DEFAULT_WS_URL =
  process.env.REACT_APP_AGENT_WS_URL ||
  `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/api/agent/ws`;

const DEFAULT_RECONNECT_INTERVAL = 3000; // 3 seconds
const DEFAULT_MAX_RECONNECT_ATTEMPTS = 10;
const DEFAULT_HEARTBEAT_INTERVAL = 30000; // 30 seconds

/**
 * Custom hook for managing agent status via WebSocket
 *
 * Features:
 * - Real-time status updates from the agent
 * - Phase tracking through execution pipeline
 * - Automatic reconnection with exponential backoff
 * - Heartbeat monitoring to detect stale connections
 * - Type-safe message handling
 *
 * @param config Configuration options
 * @returns Current agent status and connection state
 *
 * @example
 * ```tsx
 * const { status, phase, progress, error, isConnected } = useAgentStatus({
 *   wsUrl: 'wss://api.example.com/agent/ws',
 *   onPhaseChange: (phase) => console.log(`Now in ${phase} phase`)
 * });
 * ```
 */
export const useAgentStatus = (config: UseAgentStatusConfig = {}): AgentStatusState & {
  connect: () => void;
  disconnect: () => void;
} => {
  const {
    wsUrl = DEFAULT_WS_URL,
    autoConnect = true,
    reconnectInterval = DEFAULT_RECONNECT_INTERVAL,
    maxReconnectAttempts = DEFAULT_MAX_RECONNECT_ATTEMPTS,
    heartbeatInterval = DEFAULT_HEARTBEAT_INTERVAL,
    onError,
    onPhaseChange,
  } = config;

  // State management
  const [state, setState] = useState<AgentStatusState>({
    status: 'idle',
    phase: 'DataPrep',
    progress: 0,
    error: null,
    isConnected: false,
    lastUpdate: null,
  });

  // Refs for connection management
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();
  const heartbeatTimeoutRef = useRef<NodeJS.Timeout>();
  const heartbeatIntervalRef = useRef<NodeJS.Timeout>();
  const previousPhaseRef = useRef<AgentPhase>('DataPrep');

  /**
   * Clear all timeouts
   */
  const clearTimeouts = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    if (heartbeatTimeoutRef.current) {
      clearTimeout(heartbeatTimeoutRef.current);
    }
    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current);
    }
  }, []);

  /**
   * Handle incoming WebSocket messages
   */
  const handleMessage = useCallback(
    (event: MessageEvent) => {
      try {
        const message: AgentStatusMessage = JSON.parse(event.data);

        setState((prevState) => {
          const newState = { ...prevState };

          switch (message.type) {
            case 'status':
              if (message.status) {
                newState.status = message.status;
                // Clear error on status update
                if (message.status !== 'failed') {
                  newState.error = null;
                }
              }
              break;

            case 'phase':
              if (message.phase && message.phase !== prevState.phase) {
                newState.phase = message.phase;
                previousPhaseRef.current = message.phase;
                // Notify about phase change
                onPhaseChange?.(message.phase);
              }
              break;

            case 'progress':
              if (message.progress !== undefined) {
                newState.progress = Math.min(100, Math.max(0, message.progress));
              }
              break;

            case 'error':
              newState.error = message.message || 'Unknown error occurred';
              newState.status = 'failed';
              // Notify error callback
              if (onError) {
                onError(new Error(newState.error));
              }
              break;

            case 'ping':
              // Heartbeat ping, just acknowledge
              break;
          }

          newState.lastUpdate = new Date();
          return newState;
        });

        // Reset heartbeat timer on message
        if (heartbeatTimeoutRef.current) {
          clearTimeout(heartbeatTimeoutRef.current);
        }
        heartbeatTimeoutRef.current = setTimeout(() => {
          // No message received within heartbeat interval
          setState((prev) => ({
            ...prev,
            isConnected: false,
            error: 'Connection timeout - attempting to reconnect',
          }));
          wsRef.current?.close();
        }, heartbeatInterval + 5000); // Give 5s buffer
      } catch (error) {
        const errorMsg =
          error instanceof Error ? error.message : 'Failed to parse message';
        setState((prev) => ({
          ...prev,
          error: errorMsg,
        }));
        if (onError) {
          onError(
            error instanceof Error ? error : new Error(errorMsg)
          );
        }
      }
    },
    [heartbeatInterval, onError, onPhaseChange]
  );

  /**
   * Attempt to connect to WebSocket
   */
  const connect = useCallback(() => {
    // Prevent multiple simultaneous connection attempts
    if (wsRef.current && wsRef.current.readyState === WebSocket.CONNECTING) {
      return;
    }

    try {
      wsRef.current = new WebSocket(wsUrl);

      wsRef.current.onopen = () => {
        reconnectAttemptsRef.current = 0;
        setState((prev) => ({
          ...prev,
          isConnected: true,
          error: null,
        }));

        // Start heartbeat monitoring
        heartbeatIntervalRef.current = setInterval(() => {
          if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(
              JSON.stringify({ type: 'ping' })
            );
          }
        }, heartbeatInterval);
      };

      wsRef.current.onmessage = handleMessage;

      wsRef.current.onerror = (event) => {
        const errorMsg = `WebSocket error: ${event.type}`;
        setState((prev) => ({
          ...prev,
          error: errorMsg,
          isConnected: false,
        }));
        if (onError) {
          onError(new Error(errorMsg));
        }
      };

      wsRef.current.onclose = () => {
        clearTimeouts();
        setState((prev) => ({
          ...prev,
          isConnected: false,
        }));

        // Attempt to reconnect with exponential backoff
        if (
          autoConnect &&
          reconnectAttemptsRef.current < maxReconnectAttempts
        ) {
          reconnectAttemptsRef.current++;
          const backoffDelay =
            reconnectInterval * Math.pow(1.5, reconnectAttemptsRef.current - 1);

          reconnectTimeoutRef.current = setTimeout(
            () => connect(),
            Math.min(backoffDelay, 30000) // Cap at 30 seconds
          );
        }
      };
    } catch (error) {
      const errorMsg =
        error instanceof Error ? error.message : 'Failed to create WebSocket';
      setState((prev) => ({
        ...prev,
        error: errorMsg,
        isConnected: false,
      }));
      if (onError) {
        onError(
          error instanceof Error ? error : new Error(errorMsg)
        );
      }
    }
  }, [
    wsUrl,
    autoConnect,
    reconnectInterval,
    maxReconnectAttempts,
    heartbeatInterval,
    handleMessage,
    onError,
    clearTimeouts,
  ]);

  /**
   * Disconnect from WebSocket
   */
  const disconnect = useCallback(() => {
    clearTimeouts();
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setState((prev) => ({
      ...prev,
      isConnected: false,
    }));
  }, [clearTimeouts]);

  /**
   * Auto-connect on mount
   */
  useEffect(() => {
    if (autoConnect) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [autoConnect, connect, disconnect]);

  return {
    ...state,
    connect,
    disconnect,
  };
};

export default useAgentStatus;
