import os from 'os';

import { Router, Request, Response } from 'express';
import { Pool } from 'pg';

import { getRedisClient, isCacheAvailable } from '../utils/cache.js';
import { logger } from '../utils/logger.js';
import { asString } from '../utils/asString';


export type HealthStatus = 'OK' | 'DEGRADED' | 'DOWN';

export interface HealthConfig {
  pg?: {
    connectionString?: string;
    statementTimeoutMs?: number;
  };
  redis?: {
    enabled?: boolean;
    pingTimeoutMs?: number;
  };
  serviceNames?: string[];
  gracefulDegradation?: {
    allowRedisDown?: boolean;
    allowDbDown?: boolean;
  };
}

export function createHealthRouter(config: HealthConfig = {}) {
  const router = Router();

  const allowRedisDown = config.gracefulDegradation?.allowRedisDown ?? true;
  const allowDbDown = config.gracefulDegradation?.allowDbDown ?? false;

  async function checkDb() {
    const connectionString = config.pg?.connectionString ?? process.env.DATABASE_URL;
    if (!connectionString) {
      return { ok: false, status: 'UNKNOWN' as const, message: 'DATABASE_URL not set' };
    }

    const pool = new Pool({ connectionString });
    const started = Date.now();
    try {
      const res = await pool.query('SELECT 1 as ok');
      const latencyMs = Date.now() - started;
      return { ok: res?.rows?.[0]?.ok === 1, status: 'OK' as const, latencyMs };
    } catch (err: any) {
      const latencyMs = Date.now() - started;
      return { ok: false, status: 'DOWN' as const, latencyMs, error: err?.message ?? String(err) };
    } finally {
      await pool.end().catch(() => undefined);
    }
  }

  async function checkRedis() {
    if (config.redis?.enabled === false) {
      return { ok: true, status: 'SKIPPED' as const };
    }

    const started = Date.now();
    try {
      const client = await getRedisClient();
      const pong = await client.ping();
      const latencyMs = Date.now() - started;
      return { ok: pong === 'PONG', status: 'OK' as const, latencyMs, cacheAvailable: isCacheAvailable() };
    } catch (err: any) {
      const latencyMs = Date.now() - started;
      return { ok: false, status: 'DOWN' as const, latencyMs, cacheAvailable: false, error: err?.message ?? String(err) };
    }
  }

  function usage() {
    const mem = process.memoryUsage();
    const load = os.loadavg();
    return {
      processUptimeSec: process.uptime(),
      nodeVersion: process.version,
      platform: process.platform,
      cpu: {
        cores: os.cpus().length,
        load1: load[0],
        load5: load[1],
        load15: load[2],
      },
      memory: {
        rss: mem.rss,
        heapTotal: mem.heapTotal,
        heapUsed: mem.heapUsed,
        external: mem.external,
      },
    };
  }

  function aggregateStatus(dbOk: boolean, redisOk: boolean): { status: HealthStatus; degraded: boolean; reasons: string[] } {
    const reasons: string[] = [];
    let status: HealthStatus = 'OK';

    if (!dbOk) {
      reasons.push('db');
      status = allowDbDown ? 'DEGRADED' : 'DOWN';
    }
    if (!redisOk) {
      reasons.push('redis');
      if (status === 'OK') status = allowRedisDown ? 'DEGRADED' : 'DOWN';
      if (status === 'DEGRADED' && !allowRedisDown) status = 'DOWN';
    }

    return { status, degraded: status === 'DEGRADED', reasons };
  }

  router.get('/health', async (_req: Request, res: Response) => {
    const [db, redis] = await Promise.all([checkDb(), checkRedis()]);
    const u = usage();

    const agg = aggregateStatus(db.ok === true, redis.ok === true);
    const httpStatus = agg.status === 'DOWN' ? 503 : 200;

    const payload = {
      status: agg.status,
      degraded: agg.degraded,
      degradedReasons: agg.reasons,
      timestamp: new Date().toISOString(),
      dependencies: {
        db,
        redis,
      },
      usage: u,
    };

    if (agg.status !== 'OK') {
      logger.warn('health_check_degraded', payload as any);
    }

    res.status(httpStatus).json(payload);
  });

  router.get('/health/services/:name', async (req: Request, res: Response) => {
    const name = asString(req.params.name);
    const known = new Set(config.serviceNames ?? []);

    if (known.size && !known.has(name)) {
      return res.status(404).json({
        status: 'DOWN',
        service: name,
        error: 'unknown_service',
        knownServices: Array.from(known),
        timestamp: new Date().toISOString(),
      });
    }

    // For now, orchestrator only has in-process service singletons.
    // Consider UNKNOWN as OK unless dependency layer is down.
    const [db, redis] = await Promise.all([checkDb(), checkRedis()]);
    const agg = aggregateStatus(db.ok === true, redis.ok === true);
    const httpStatus = agg.status === 'DOWN' ? 503 : 200;

    res.status(httpStatus).json({
      status: agg.status,
      service: name,
      degraded: agg.degraded,
      degradedReasons: agg.reasons,
      timestamp: new Date().toISOString(),
      dependencies: { db, redis },
    });
  });

  return router;
}
