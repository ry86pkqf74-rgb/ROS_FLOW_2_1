import net from "net";

import { pool } from "../../db";

export async function checkPostgres(): Promise<{ ok: boolean; error?: string }> {
  if (!pool) {
    return { ok: false, error: "No database pool configured" };
  }
  try {
    const client = await pool.connect();
    try {
      await client.query("SELECT 1");
      return { ok: true };
    } finally {
      client.release();
    }
  } catch (error) {
    return { ok: false, error: error instanceof Error ? error.message : "Unknown error" };
  }
}

export async function checkRedis(): Promise<{ ok: boolean; error?: string }> {
  const redisUrl = process.env.REDIS_URL || "redis://redis:6379";
  try {
    const url = new URL(redisUrl);
    const host = url.hostname;
    const port = parseInt(url.port || "6379", 10);

    return new Promise((resolve) => {
      const socket = new net.Socket();
      const timeout = setTimeout(() => {
        socket.destroy();
        resolve({ ok: false, error: "Connection timeout" });
      }, 2000);

      socket.connect(port, host, () => {
        socket.write("*1\r\n$4\r\nPING\r\n");
      });

      socket.on("data", (data) => {
        clearTimeout(timeout);
        const response = data.toString();
        if (response.includes("PONG")) {
          socket.destroy();
          resolve({ ok: true });
        } else {
          socket.destroy();
          resolve({ ok: false, error: `Unexpected response: ${response}` });
        }
      });

      socket.on("error", (err) => {
        clearTimeout(timeout);
        socket.destroy();
        resolve({ ok: false, error: err.message });
      });
    });
  } catch (error) {
    return { ok: false, error: error instanceof Error ? error.message : "Invalid Redis URL" };
  }
}

export async function checkWorker(): Promise<{ ok: boolean; error?: string }> {
  const workerUrl = process.env.WORKER_CALLBACK_URL || "http://worker:8000";
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 2000);

    const response = await fetch(`${workerUrl}/health`, {
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    if (response.ok) {
      return { ok: true };
    }
    return { ok: false, error: `HTTP ${response.status}` };
  } catch (error) {
    if (error instanceof Error && error.name === "AbortError") {
      return { ok: false, error: "Connection timeout" };
    }
    return { ok: false, error: error instanceof Error ? error.message : "Unknown error" };
  }
}
