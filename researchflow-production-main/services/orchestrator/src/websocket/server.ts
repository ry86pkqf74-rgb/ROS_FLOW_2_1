/**
 * WebSocket Server - PHI-Safe Event Broadcasting
 *
 * Isolated WebSocket server module that can be mounted by the orchestrator.
 * Handles client connections, subscriptions, and broadcasts PHI-safe protocol events.
 *
 * Features:
 * - Connection management with unique client IDs
 * - Event type subscription filtering
 * - Run/project/manuscript-level filtering
 * - HIPAA mode enforcement
 * - Heartbeat/ping-pong for connection health
 * - Graceful shutdown
 *
 * Not yet wired to orchestrator routes or services - integration will happen in later phase.
 *
 * @module websocket/server
 */

import type { Server as HttpServer } from 'http';
import { WebSocketServer, WebSocket as WsSocket } from 'ws';
import {
  ClientMessage,
  ServerMessage,
  ProtocolEvent,
  isValidClientMessage,
  isValidProtocolEvent,
  isHipaaMode,
  sanitizePayloadForHipaa,
} from './protocol';
import { subscribe as subscribeToEventBus } from './event-bus';

/**
 * Client connection metadata
 */
interface ClientConnection {
  id: string;
  ws: WsSocket;
  isAuthenticated: boolean;
  userId?: string;
  subscribedEventTypes: Set<string>;
  filters: {
    runId?: string;
    projectId?: string;
    manuscriptId?: string;
  };
  lastHeartbeat: number;
  messageCount: number;
}

/**
 * WebSocket server configuration
 */
interface WebSocketServerConfig {
  path?: string;
  heartbeatIntervalMs?: number;
  heartbeatTimeoutMs?: number;
  maxConnections?: number;
}

/**
 * WebSocket Server Class
 */
export class WebSocketEventServer {
  private wss: WebSocketServer | null = null;
  private clients: Map<string, ClientConnection> = new Map();
  private httpServer: HttpServer | null = null;
  private heartbeatInterval: NodeJS.Timeout | null = null;
  private eventBusUnsubscribe: (() => void) | null = null;
  private isShuttingDown = false;

  private readonly config: Required<WebSocketServerConfig>;

  constructor(config: WebSocketServerConfig = {}) {
    this.config = {
      path: config.path || '/ws/events',
      heartbeatIntervalMs: config.heartbeatIntervalMs || 30000, // 30 seconds
      heartbeatTimeoutMs: config.heartbeatTimeoutMs || 60000, // 60 seconds
      maxConnections: config.maxConnections || 10000,
    };
  }

  /**
   * Initialize and mount WebSocket server on HTTP server
   */
  public initialize(httpServer: HttpServer): void {
    if (this.wss) {
      console.warn('[WebSocketEventServer] Already initialized');
      return;
    }

    this.httpServer = httpServer;

    // Create WebSocket server
    this.wss = new WebSocketServer({
      server: httpServer,
      path: this.config.path,
    });

    // Handle new connections
    this.wss.on('connection', (ws: WsSocket, req) => {
      this.handleNewConnection(ws, req);
    });

    // Start heartbeat monitoring
    this.startHeartbeat();

    // Subscribe to EventBus and broadcast protocol events to clients (validate + sanitize in broadcast())
    this.eventBusUnsubscribe = subscribeToEventBus((event) => {
      this.broadcast(event);
    });

    const hipaaStatus = isHipaaMode() ? ' (HIPAA mode enabled)' : '';
    console.log(
      `[WebSocketEventServer] Initialized at ${this.config.path}${hipaaStatus}`
    );
  }

  /**
   * Handle new client connection
   */
  private handleNewConnection(ws: WsSocket, req: any): void {
    // Check connection limit
    if (this.clients.size >= this.config.maxConnections) {
      console.warn('[WebSocketEventServer] Max connections reached, rejecting client');
      ws.close(1008, 'Server at capacity');
      return;
    }

    const clientId = this.generateClientId();
    const connection: ClientConnection = {
      id: clientId,
      ws,
      isAuthenticated: false,
      subscribedEventTypes: new Set(),
      filters: {},
      lastHeartbeat: Date.now(),
      messageCount: 0,
    };

    this.clients.set(clientId, connection);

    console.log(
      `[WebSocketEventServer] Client connected: ${clientId} (total: ${this.clients.size})`
    );

    // Send connection established message
    this.sendToClient(clientId, {
      type: 'connection.established',
      timestamp: new Date().toISOString(),
      payload: {
        clientId,
        serverVersion: '1.0.0',
        hipaaMode: isHipaaMode(),
      },
    });

    // Set up message handler
    ws.on('message', (data) => {
      this.handleClientMessage(clientId, data);
    });

    // Handle errors
    ws.on('error', (error) => {
      console.error(
        `[WebSocketEventServer] Client error (${clientId}):`,
        error.message
      );
    });

    // Handle disconnection
    ws.on('close', () => {
      this.handleDisconnection(clientId);
    });

    // Handle pong (heartbeat response)
    ws.on('pong', () => {
      const client = this.clients.get(clientId);
      if (client) {
        client.lastHeartbeat = Date.now();
      }
    });
  }

  /**
   * Handle incoming message from client
   */
  private handleClientMessage(clientId: string, data: any): void {
    const client = this.clients.get(clientId);
    if (!client) return;

    client.messageCount++;

    try {
      const message = JSON.parse(data.toString());

      // Validate message format
      if (!isValidClientMessage(message)) {
        this.sendError(clientId, 'INVALID_MESSAGE', 'Invalid message format');
        return;
      }

      // Route message based on type
      switch (message.type) {
        case 'ping':
          this.handlePing(clientId);
          break;

        case 'auth':
          this.handleAuth(clientId, message);
          break;

        case 'subscribe':
          this.handleSubscribe(clientId, message);
          break;

        case 'unsubscribe':
          this.handleUnsubscribe(clientId, message);
          break;

        default:
          this.sendError(clientId, 'UNKNOWN_MESSAGE_TYPE', 'Unknown message type');
      }
    } catch (error) {
      console.error(
        `[WebSocketEventServer] Failed to process message from ${clientId}:`,
        error
      );
      this.sendError(
        clientId,
        'MESSAGE_PARSE_ERROR',
        'Failed to parse message'
      );
    }
  }

  /**
   * Handle ping message
   */
  private handlePing(clientId: string): void {
    this.sendToClient(clientId, {
      type: 'pong',
      timestamp: new Date().toISOString(),
      payload: {},
    });
  }

  /**
   * Handle authentication message
   * Note: Actual JWT validation would be done here in production
   */
  private handleAuth(clientId: string, message: any): void {
    const client = this.clients.get(clientId);
    if (!client) return;

    const { token, userId } = message.payload;

    // TODO: Validate JWT token when integrating with orchestrator auth
    // For now, accept any token for testing
    if (token) {
      client.isAuthenticated = true;
      client.userId = userId;

      this.sendToClient(clientId, {
        type: 'auth.success',
        timestamp: new Date().toISOString(),
        payload: {
          userId,
        },
      });

      console.log(
        `[WebSocketEventServer] Client authenticated: ${clientId} (user: ${userId})`
      );
    } else {
      this.sendToClient(clientId, {
        type: 'auth.failed',
        timestamp: new Date().toISOString(),
        payload: {
          message: 'Invalid or missing token',
        },
      });
    }
  }

  /**
   * Handle subscription message
   */
  private handleSubscribe(clientId: string, message: any): void {
    const client = this.clients.get(clientId);
    if (!client) return;

    const { eventTypes, filters } = message.payload;

    // Add event types to subscription set
    for (const eventType of eventTypes) {
      client.subscribedEventTypes.add(eventType);
    }

    // Update filters if provided
    if (filters) {
      client.filters = {
        ...client.filters,
        ...filters,
      };
    }

    // Send confirmation
    this.sendToClient(clientId, {
      type: 'subscription.confirmed',
      timestamp: new Date().toISOString(),
      payload: {
        eventTypes: Array.from(client.subscribedEventTypes),
        filters: client.filters,
      },
    });

    console.log(
      `[WebSocketEventServer] Client ${clientId} subscribed to: ${eventTypes.join(', ')}`
    );
  }

  /**
   * Handle unsubscribe message
   */
  private handleUnsubscribe(clientId: string, message: any): void {
    const client = this.clients.get(clientId);
    if (!client) return;

    const { eventTypes } = message.payload;

    // Remove event types from subscription set
    for (const eventType of eventTypes) {
      client.subscribedEventTypes.delete(eventType);
    }

    // Send confirmation
    this.sendToClient(clientId, {
      type: 'subscription.confirmed',
      timestamp: new Date().toISOString(),
      payload: {
        eventTypes: Array.from(client.subscribedEventTypes),
        filters: client.filters,
      },
    });

    console.log(
      `[WebSocketEventServer] Client ${clientId} unsubscribed from: ${eventTypes.join(', ')}`
    );
  }

  /**
   * Handle client disconnection
   */
  private handleDisconnection(clientId: string): void {
    this.clients.delete(clientId);
    console.log(
      `[WebSocketEventServer] Client disconnected: ${clientId} (total: ${this.clients.size})`
    );
  }

  /**
   * Broadcast protocol event to subscribed clients
   */
  public broadcast(event: ProtocolEvent): void {
    if (!isValidProtocolEvent(event)) {
      console.warn('[WebSocketEventServer] Invalid protocol event, skipping broadcast');
      return;
    }

    // Sanitize payload for HIPAA if needed
    const sanitizedPayload = sanitizePayloadForHipaa(event.payload as Record<string, any>);
    const sanitizedEvent = {
      ...event,
      payload: sanitizedPayload,
    } as ProtocolEvent;

    let sentCount = 0;

    for (const [clientId, client] of this.clients.entries()) {
      // Check if client is subscribed to this event type
      if (!client.subscribedEventTypes.has(event.type)) {
        continue;
      }

      // Apply filters
      if (!this.matchesFilters(client, sanitizedEvent)) {
        continue;
      }

      // Send to client
      this.sendToClient(clientId, sanitizedEvent);
      sentCount++;
    }

    if (sentCount > 0) {
      console.debug(
        `[WebSocketEventServer] Broadcast ${event.type} to ${sentCount} clients`
      );
    }
  }

  /**
   * Check if event matches client filters
   */
  private matchesFilters(client: ClientConnection, event: ProtocolEvent): boolean {
    const payload = event.payload as any;

    // Check runId filter
    if (client.filters.runId && payload.runId !== client.filters.runId) {
      return false;
    }

    // Check projectId filter
    if (client.filters.projectId && payload.projectId !== client.filters.projectId) {
      return false;
    }

    // Check manuscriptId filter
    if (client.filters.manuscriptId && payload.manuscriptId !== client.filters.manuscriptId) {
      return false;
    }

    return true;
  }

  /**
   * Send message to specific client
   */
  private sendToClient(clientId: string, message: ServerMessage): void {
    const client = this.clients.get(clientId);
    if (!client || client.ws.readyState !== WsSocket.OPEN) {
      return;
    }

    try {
      client.ws.send(JSON.stringify(message));
    } catch (error) {
      console.error(
        `[WebSocketEventServer] Failed to send message to ${clientId}:`,
        error
      );
    }
  }

  /**
   * Send error message to client
   */
  private sendError(clientId: string, code: string, message: string): void {
    this.sendToClient(clientId, {
      type: 'error',
      timestamp: new Date().toISOString(),
      payload: { code, message },
    });
  }

  /**
   * Start heartbeat monitoring
   */
  private startHeartbeat(): void {
    this.heartbeatInterval = setInterval(() => {
      const now = Date.now();
      const staleClients: string[] = [];

      for (const [clientId, client] of this.clients) {
        // Check for stale connections
        if (now - client.lastHeartbeat > this.config.heartbeatTimeoutMs) {
          staleClients.push(clientId);
        } else if (client.ws.readyState === WsSocket.OPEN) {
          // Send ping to active clients (ws library specific)
          try {
            (client.ws as any).ping();
          } catch (error) {
            console.error(`[WebSocketEventServer] Failed to ping ${clientId}:`, error);
          }
        }
      }

      // Close stale connections
      for (const clientId of staleClients) {
        const client = this.clients.get(clientId);
        if (client) {
          console.warn(
            `[WebSocketEventServer] Closing stale connection: ${clientId}`
          );
          client.ws.close(1000, 'Heartbeat timeout');
        }
      }
    }, this.config.heartbeatIntervalMs);
  }

  /**
   * Get server statistics
   */
  public getStats(): {
    totalConnections: number;
    authenticatedConnections: number;
    subscriptions: Record<string, number>;
    hipaaMode: boolean;
  } {
    let authenticatedCount = 0;
    const subscriptionCounts: Record<string, number> = {};

    for (const client of this.clients.values()) {
      if (client.isAuthenticated) {
        authenticatedCount++;
      }

      for (const eventType of client.subscribedEventTypes) {
        subscriptionCounts[eventType] = (subscriptionCounts[eventType] || 0) + 1;
      }
    }

    return {
      totalConnections: this.clients.size,
      authenticatedConnections: authenticatedCount,
      subscriptions: subscriptionCounts,
      hipaaMode: isHipaaMode(),
    };
  }

  /**
   * Graceful shutdown
   */
  public shutdown(): void {
    this.isShuttingDown = true;

    console.log('[WebSocketEventServer] Shutting down...');

    // Unsubscribe from EventBus to avoid leaks
    if (this.eventBusUnsubscribe) {
      this.eventBusUnsubscribe();
      this.eventBusUnsubscribe = null;
    }

    // Stop heartbeat
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }

    // Close all client connections
    for (const client of this.clients.values()) {
      if (client.ws.readyState === WsSocket.OPEN) {
        client.ws.close(1001, 'Server shutting down');
      }
    }

    // Close WebSocket server
    if (this.wss) {
      this.wss.close(() => {
        console.log('[WebSocketEventServer] Server closed');
      });
      this.wss = null;
    }

    this.clients.clear();
  }

  /**
   * Generate unique client ID
   */
  private generateClientId(): string {
    return `ws_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }
}

/**
 * Singleton instance for easy import
 */
export const websocketServer = new WebSocketEventServer();

export default websocketServer;
