import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { createServer, Server as HttpServer } from "http";
import { WebSocket } from "ws";
import { WebSocketEventServer } from "../server";

describe("WebSocket Server Smoke Test", () => {
  let httpServer: HttpServer;
  let wsServer: WebSocketEventServer;
  let baseUrl: string;

  beforeEach((context) => {
    return new Promise<void>((resolve) => {
      // Create a dummy HTTP server
      httpServer = createServer((req, res) => {
        res.writeHead(200, { "Content-Type": "text/plain" });
        res.end("Test server");
      });

      // Listen on random available port
      httpServer.listen(0, () => {
        const address = httpServer.address();
        const port = typeof address === "object" && address ? address.port : 0;
        baseUrl = `ws://localhost:${port}`;
        resolve();
      });
    });
  });

  afterEach(() => {
    // Ensure cleanup
    if (wsServer) {
      wsServer.shutdown();
    }
    if (httpServer) {
      httpServer.close();
    }
  });

  it("mounts on HTTP server without throwing", () => {
    wsServer = new WebSocketEventServer({ path: "/ws" });

    expect(() => {
      wsServer.initialize(httpServer);
    }).not.toThrow();
  });

  it("accepts a client connection and closes cleanly", async () => {
    wsServer = new WebSocketEventServer({ path: "/ws" });
    wsServer.initialize(httpServer);

    // Open a client connection
    const client = new WebSocket(`${baseUrl}/ws`);

    // Wait for connection to establish
    await new Promise<void>((resolve, reject) => {
      client.on("open", () => resolve());
      client.on("error", reject);
    });

    // Verify connection is open
    expect(client.readyState).toBe(WebSocket.OPEN);

    // Check server stats show connection
    const stats = wsServer.getStats();
    expect(stats.totalConnections).toBe(1);

    // Close client connection
    client.close();

    // Wait for clean close
    await new Promise<void>((resolve) => {
      client.on("close", () => resolve());
    });

    expect(client.readyState).toBe(WebSocket.CLOSED);
  });

  it("shuts down gracefully without throwing", async () => {
    wsServer = new WebSocketEventServer({ path: "/ws" });
    wsServer.initialize(httpServer);

    // Open a client connection
    const client = new WebSocket(`${baseUrl}/ws`);

    await new Promise<void>((resolve, reject) => {
      client.on("open", () => resolve());
      client.on("error", reject);
    });

    // Shutdown server
    expect(() => {
      wsServer.shutdown();
    }).not.toThrow();

    // Wait for client to receive close event
    await new Promise<void>((resolve) => {
      client.on("close", (code, reason) => {
        // Server should send shutdown code
        expect(code).toBe(1001);
        expect(reason.toString()).toBe("Server shutting down");
        resolve();
      });
    });

    // Verify stats after shutdown
    const stats = wsServer.getStats();
    expect(stats.totalConnections).toBe(0);
  });

  it("handles multiple connections and shutdown cleanly", async () => {
    wsServer = new WebSocketEventServer({ path: "/ws" });
    wsServer.initialize(httpServer);

    // Open multiple client connections
    const client1 = new WebSocket(`${baseUrl}/ws`);
    const client2 = new WebSocket(`${baseUrl}/ws`);
    const client3 = new WebSocket(`${baseUrl}/ws`);

    // Wait for all connections to establish
    await Promise.all([
      new Promise<void>((resolve, reject) => {
        client1.on("open", () => resolve());
        client1.on("error", reject);
      }),
      new Promise<void>((resolve, reject) => {
        client2.on("open", () => resolve());
        client2.on("error", reject);
      }),
      new Promise<void>((resolve, reject) => {
        client3.on("open", () => resolve());
        client3.on("error", reject);
      }),
    ]);

    // Verify all connections are tracked
    const stats = wsServer.getStats();
    expect(stats.totalConnections).toBe(3);

    // Shutdown should close all connections
    wsServer.shutdown();

    // Wait for all clients to close
    await Promise.all([
      new Promise<void>((resolve) => client1.on("close", () => resolve())),
      new Promise<void>((resolve) => client2.on("close", () => resolve())),
      new Promise<void>((resolve) => client3.on("close", () => resolve())),
    ]);

    // All connections should be closed
    expect(client1.readyState).toBe(WebSocket.CLOSED);
    expect(client2.readyState).toBe(WebSocket.CLOSED);
    expect(client3.readyState).toBe(WebSocket.CLOSED);
  });
});
