/**
 * SSE Event Store
 *
 * Persists SSE events to Redis lists keyed by job_id.
 * Used to replay events for late-joining SSE subscribers
 * and to provide an ordered audit trail of agent streaming output.
 *
 * Milestone 2, Step 9: SSE end-to-end for Stage 2
 */

import Redis from 'ioredis';

const REDIS_URL = process.env.REDIS_URL || 'redis://localhost:6379';
const MAX_EVENTS = parseInt(process.env.SSE_STORE_MAX_EVENTS || '500', 10);
const TTL_SECONDS = parseInt(process.env.SSE_STORE_TTL_SECONDS || '3600', 10);

/** Stored SSE event with sequence metadata */
export interface StoredSSEEvent {
  seq: number;
  ts: string;
  event?: string;
  data: unknown;
}

let redis: Redis | null = null;

function getRedis(): Redis {
  if (!redis) {
    redis = new Redis(REDIS_URL, {
      maxRetriesPerRequest: 3,
      retryStrategy(times) {
        return Math.min(times * 200, 2000);
      },
    });
    redis.on('error', (err) => {
      console.error('[SSEEventStore] Redis error:', err.message);
    });
  }
  return redis;
}

function jobKey(jobId: string): string {
  return `sse:events:${jobId}`;
}

/**
 * Push an SSE event to the store for a given job.
 * Returns the sequence number assigned to the event.
 */
export async function pushEvent(
  jobId: string,
  event: { event?: string; data: unknown }
): Promise<number> {
  const r = getRedis();
  const key = jobKey(jobId);
  const len = await r.llen(key);

  const stored: StoredSSEEvent = {
    seq: len,
    ts: new Date().toISOString(),
    event: event.event,
    data: event.data,
  };

  const pipeline = r.pipeline();
  pipeline.rpush(key, JSON.stringify(stored));
  if (len + 1 > MAX_EVENTS) {
    pipeline.ltrim(key, -MAX_EVENTS, -1);
  }
  pipeline.expire(key, TTL_SECONDS);
  await pipeline.exec();

  return stored.seq;
}

/**
 * Get stored events starting from a sequence number.
 */
export async function getEvents(
  jobId: string,
  fromSeq: number = 0
): Promise<StoredSSEEvent[]> {
  const r = getRedis();
  const raw = await r.lrange(jobKey(jobId), fromSeq, -1);
  return raw.map((s) => JSON.parse(s) as StoredSSEEvent);
}

/**
 * Get the count of stored events for a job.
 */
export async function getEventCount(jobId: string): Promise<number> {
  const r = getRedis();
  return r.llen(jobKey(jobId));
}

/**
 * Close the Redis connection used by this module.
 */
export async function closeSSEEventStore(): Promise<void> {
  if (redis) {
    await redis.quit();
    redis = null;
  }
}
