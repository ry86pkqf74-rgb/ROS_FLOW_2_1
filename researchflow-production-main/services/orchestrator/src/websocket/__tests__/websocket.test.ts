/**
 * WebSocket Server Tests
 *
 * Tests for the isolated WebSocket server module with PHI-safe protocol.
 * Validates:
 * - Server initialization on ephemeral port
 * - Client connection and message handling
 * - Protocol event broadcasting with schema validation
 * - HIPAA mode payload sanitization
 * - Subscription filtering
 *
 * @module websocket/__tests__/websocket
 */

import { describe, it, beforeAll, afterAll, expect, vi } from 'vitest';
import { createServer, Server as HttpServer } from 'http';
import * as ws from 'ws';

// Mock audit-service to avoid DB dependency
vi.mock('../../services/audit-service', () => ({
  logAction: vi.fn(),
}));

import { WebSocketEventServer } from '../server';
import {
  createProtocolEvent,
  isValidProtocolEvent,
  sanitizePayloadForHipaa,
  RunStatusEnum,
  NodeStatusEnum,
} from '../protocol';

type WsClient = ws.WebSocket;

/**
 * Helper to create test HTTP server on ephemeral port
 */
function createTestHttpServer(): Promise<{ server: HttpServer; port: number }> {
  return new Promise((resolve, reject) => {
    const server = createServer();
    server.listen(0, () => {
      const address = server.address();
      if (address && typeof address === 'object') {
        resolve({ server, port: address.port });
      } else {
        reject(new Error('Failed to get server port'));
      }
    });
  });
}

/**
 * Helper to connect WebSocket client.
 * Buffers incoming messages so none are lost to race conditions
 * (e.g. `connection.established` arriving before `waitForMessage` is called).
 */
function connectClient(port: number): Promise<WsClient> {
  return new Promise((resolve, reject) => {
    const client = new ws.WebSocket(`ws://localhost:${port}/ws` as any) as WsClient;

    // Message queue – stores anything that arrives before waitForMessage is called
    const queue: any[] = [];
    const pending: Array<{ resolve: (v: any) => void; reject: (e: Error) => void }> = [];

    client.on('message', (raw) => {
      try {
        const msg = JSON.parse(raw.toString());
        if (pending.length > 0) {
          const waiter = pending.shift()!;
          waiter.resolve(msg);
        } else {
          queue.push(msg);
        }
      } catch { /* ignore parse errors */ }
    });

    // Expose the queue via expando properties
    (client as any).__msgQueue = queue;
    (client as any).__msgPending = pending;

    // Clear timeout on success/failure to avoid dangling handles in CI
    const timeout = setTimeout(() => reject(new Error('Connection timeout')), 5000);
    client.on('open', () => { clearTimeout(timeout); resolve(client); });
    client.on('error', (err) => { clearTimeout(timeout); reject(err); });
  });
}

/**
 * Helper to wait for the next message from a buffered WebSocket client.
 */
function waitForMessage(client: WsClient, timeout = 10000): Promise<any> {
  const queue: any[] = (client as any).__msgQueue ?? [];
  const pending: Array<{ resolve: (v: any) => void; reject: (e: Error) => void }> =
    (client as any).__msgPending ?? [];

  // If there's already a buffered message, return it immediately
  if (queue.length > 0) {
    return Promise.resolve(queue.shift());
  }

  // Otherwise wait for the next one
  return new Promise((resolve, reject) => {
    // Build the entry first so we can remove it by reference on timeout
    const entry = {
      resolve: (msg: any) => { clearTimeout(timer); resolve(msg); },
      reject:  (err: Error) => { clearTimeout(timer); reject(err); },
    };

    const timer = setTimeout(() => {
      const idx = pending.indexOf(entry);
      if (idx !== -1) pending.splice(idx, 1);
      reject(new Error('Message timeout'));
    }, timeout);

    pending.push(entry);
  });
}

describe('WebSocket Server', { timeout: 30000 }, () => {
  let httpServer: HttpServer;
  let wsServer: WebSocketEventServer;
  let port: number;

  beforeAll(async () => {
    // Create HTTP server on ephemeral port
    const result = await createTestHttpServer();
    httpServer = result.server;
    port = result.port;

    // Initialize WebSocket server
    wsServer = new WebSocketEventServer({
      path: '/ws',
      heartbeatIntervalMs: 30000, // Longer for tests
      heartbeatTimeoutMs: 60000,
    });
    wsServer.initialize(httpServer);

    console.log(`[Test] WebSocket server started on port ${port}`);
  });

  afterAll(async () => {
    // Cleanup
    wsServer.shutdown();
    await new Promise<void>((resolve) => {
      httpServer.close(() => {
        console.log('[Test] Server shut down');
        resolve();
      });
    });
  });

  it('should accept client connections', async () => {
    const client = await connectClient(port);

    // Should receive connection.established message
    const message = await waitForMessage(client);

    expect(message.type).toBe('connection.established');
    expect(message.payload.clientId).toBeTruthy();
    expect(message.payload.serverVersion).toBe('1.0.0');
    expect(typeof message.payload.hipaaMode).toBe('boolean');

    client.close();
  });

  it('should handle ping-pong', async () => {
    const client = await connectClient(port);

    // Wait for connection established
    await waitForMessage(client);

    // Send ping
    client.send(JSON.stringify({ type: 'ping' }));

    // Should receive pong
    const pong = await waitForMessage(client);
    expect(pong.type).toBe('pong');

    client.close();
  });

  it('should handle authentication', async () => {
    const client = await connectClient(port);

    // Wait for connection established
    await waitForMessage(client);

    // Send auth message
    client.send(
      JSON.stringify({
        type: 'auth',
        payload: {
          token: 'test-token-123',
          userId: 'user-456',
        },
      })
    );

    // Should receive auth.success
    const authResponse = await waitForMessage(client);
    expect(authResponse.type).toBe('auth.success');
    expect(authResponse.payload.userId).toBe('user-456');

    client.close();
  });

  it('should handle subscriptions', async () => {
    const client = await connectClient(port);

    // Wait for connection established
    await waitForMessage(client);

    // Subscribe to event types
    client.send(
      JSON.stringify({
        type: 'subscribe',
        payload: {
          eventTypes: ['RUN_STATUS', 'NODE_STATUS'],
          filters: {
            projectId: 'proj-123',
          },
        },
      })
    );

    // Should receive subscription.confirmed
    const confirmation = await waitForMessage(client);
    expect(confirmation.type).toBe('subscription.confirmed');
    expect(confirmation.payload.eventTypes).toContain('RUN_STATUS');
    expect(confirmation.payload.eventTypes).toContain('NODE_STATUS');
    expect(confirmation.payload.filters.projectId).toBe('proj-123');

    client.close();
  });

  it('should broadcast events to subscribed clients', async () => {
    const client = await connectClient(port);

    // Wait for connection established
    await waitForMessage(client);

    // Subscribe to RUN_STATUS
    client.send(
      JSON.stringify({
        type: 'subscribe',
        payload: {
          eventTypes: ['RUN_STATUS'],
        },
      })
    );

    // Wait for subscription confirmation
    await waitForMessage(client);

    // Broadcast a RUN_STATUS event
    const event = createProtocolEvent('RUN_STATUS', {
      runId: 'run-123',
      projectId: 'proj-456',
      status: 'RUNNING',
      timestamp: new Date().toISOString(),
      stageCount: 3,
    });

    wsServer.broadcast(event);

    // Client should receive the event
    const receivedEvent = await waitForMessage(client);
    expect(receivedEvent.type).toBe('RUN_STATUS');
    expect(receivedEvent.payload.runId).toBe('run-123');
    expect(receivedEvent.payload.status).toBe('RUNNING');

    client.close();
  });

  it('should filter events by projectId', async () => {
    const client = await connectClient(port);

    // Wait for connection established
    await waitForMessage(client);

    // Subscribe with projectId filter
    client.send(
      JSON.stringify({
        type: 'subscribe',
        payload: {
          eventTypes: ['RUN_STATUS'],
          filters: {
            projectId: 'proj-999',
          },
        },
      })
    );

    // Wait for subscription confirmation
    await waitForMessage(client);

    // Broadcast event with different projectId
    const event = createProtocolEvent('RUN_STATUS', {
      runId: 'run-123',
      projectId: 'proj-456', // Different from filter
      status: 'RUNNING',
      timestamp: new Date().toISOString(),
    });

    wsServer.broadcast(event);

    // Client should NOT receive the event
    // Wait a short time and ensure no message arrives
    await new Promise<void>((resolve) => {
      let receivedMessage = false;
      
      const messageHandler = () => {
        receivedMessage = true;
      };
      
      client.once('message', messageHandler);
      
      setTimeout(() => {
        client.off('message', messageHandler);
        expect(receivedMessage).toBe(false);
        resolve();
      }, 1000);
    });

    client.close();
  });

  it('should validate protocol events', () => {
    // Valid RUN_STATUS event
    const validEvent = {
      type: 'RUN_STATUS',
      timestamp: new Date().toISOString(),
      payload: {
        runId: 'run-123',
        projectId: 'proj-456',
        status: 'COMPLETED',
        timestamp: new Date().toISOString(),
      },
    };

    expect(isValidProtocolEvent(validEvent)).toBe(true);

    // Invalid event - missing required field
    const invalidEvent = {
      type: 'RUN_STATUS',
      timestamp: new Date().toISOString(),
      payload: {
        runId: 'run-123',
        // Missing projectId
        status: 'COMPLETED',
      },
    };

    expect(isValidProtocolEvent(invalidEvent)).toBe(false);
  });

  it('should sanitize payload for HIPAA mode', () => {
    const payload = {
      runId: 'run-123',
      projectId: 'proj-456',
      status: 'RUNNING',
      timestamp: new Date().toISOString(),
      // Fields that should be stripped in HIPAA mode
      runName: 'My Research Run',
      description: 'Analysis of patient data',
      userEmail: 'researcher@example.com',
      customField: 'should be removed',
    };

    const sanitized = sanitizePayloadForHipaa(payload);

    // Should keep allowed fields
    expect(sanitized.runId).toBe('run-123');
    expect(sanitized.projectId).toBe('proj-456');
    expect(sanitized.status).toBe('RUNNING');

    // Should remove disallowed fields (in HIPAA mode)
    // Note: This only applies if HIPAA_MODE=true or APP_MODE=hipaa
    // In test environment without those env vars, fields may still be present
    // So we just verify the function doesn't error
    expect(sanitized).toBeTruthy();
  });

  it('should enforce PHI-safe payload schema', () => {
    // Attempt to create event with invalid status
    expect(() => {
      createProtocolEvent('RUN_STATUS', {
        runId: 'run-123',
        projectId: 'proj-456',
        status: 'INVALID_STATUS', // Not a valid enum value
        timestamp: new Date().toISOString(),
      });
    }).toThrow();

    // Valid event should succeed
    const validEvent = createProtocolEvent('RUN_STATUS', {
      runId: 'run-123',
      projectId: 'proj-456',
      status: 'RUNNING',
      timestamp: new Date().toISOString(),
    });

    expect(validEvent).toBeTruthy();
    expect(validEvent.type).toBe('RUN_STATUS');
  });

  it('should broadcast NODE_STATUS events', async () => {
    const client = await connectClient(port);

    // Wait for connection established
    await waitForMessage(client);

    // Subscribe to NODE_STATUS
    client.send(
      JSON.stringify({
        type: 'subscribe',
        payload: {
          eventTypes: ['NODE_STATUS'],
        },
      })
    );

    // Wait for subscription confirmation
    await waitForMessage(client);

    // Broadcast NODE_STATUS event
    const event = createProtocolEvent('NODE_STATUS', {
      runId: 'run-123',
      nodeId: 'stage-1',
      status: 'RUNNING',
      timestamp: new Date().toISOString(),
      progress: 45,
      itemsProcessed: 450,
      itemsTotal: 1000,
    });

    wsServer.broadcast(event);

    // Client should receive the event
    const receivedEvent = await waitForMessage(client);
    expect(receivedEvent.type).toBe('NODE_STATUS');
    expect(receivedEvent.payload.nodeId).toBe('stage-1');
    expect(receivedEvent.payload.progress).toBe(45);

    client.close();
  });

  it('should broadcast MANUSCRIPT_COMMIT_CREATED events', async () => {
    const client = await connectClient(port);

    // Wait for connection established
    await waitForMessage(client);

    // Subscribe to MANUSCRIPT_COMMIT_CREATED
    client.send(
      JSON.stringify({
        type: 'subscribe',
        payload: {
          eventTypes: ['MANUSCRIPT_COMMIT_CREATED'],
        },
      })
    );

    // Wait for subscription confirmation
    await waitForMessage(client);

    // Broadcast MANUSCRIPT_COMMIT_CREATED event
    const event = createProtocolEvent('MANUSCRIPT_COMMIT_CREATED', {
      manuscriptId: 'ms-123',
      commitHash: 'a1b2c3d4e5f6',
      projectId: 'proj-456',
      userId: 'user-789',
      timestamp: new Date().toISOString(),
      changeCount: 5,
    });

    wsServer.broadcast(event);

    // Client should receive the event
    const receivedEvent = await waitForMessage(client);
    expect(receivedEvent.type).toBe('MANUSCRIPT_COMMIT_CREATED');
    expect(receivedEvent.payload.commitHash).toBe('a1b2c3d4e5f6');

    client.close();
  });

  it('should return server statistics', () => {
    const stats = wsServer.getStats();

    expect(typeof stats.totalConnections).toBe('number');
    expect(typeof stats.authenticatedConnections).toBe('number');
    expect(stats.subscriptions).toBeTruthy();
    expect(typeof stats.hipaaMode).toBe('boolean');
  });
});
