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
/** Max events to keep per job (LTRIM -500 -1) */
const MAX_EVENTS = parseInt(process.env.SSE_STORE_MAX_EVENTS || '500', 10);
/** TTL for list and :done marker (1 hour) */
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

/** Redis list key for Stage 2 SSE events: stage2:sse:${job_id} */
function jobKey(jobId: string): string {
  return `stage2:sse:${jobId}`;
}

/** Terminal marker key when job completes/fails: stage2:sse:${job_id}:done */
function doneKey(jobId: string): string {
  return `stage2:sse:${jobId}:done`;
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
  pipeline.ltrim(key, -MAX_EVENTS, -1);
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
 * Set the terminal marker when job completes or fails.
 * Key: stage2:sse:${job_id}:done, TTL 1 hour.
 */
export async function setDone(jobId: string): Promise<void> {
  const r = getRedis();
  const key = doneKey(jobId);
  await r.set(key, '1', 'EX', TTL_SECONDS);
}

/**
 * Check if the job has reached a terminal state (:done marker exists).
 */
export async function isDone(jobId: string): Promise<boolean> {
  const r = getRedis();
  const key = doneKey(jobId);
  const v = await r.get(key);
  return v !== null;
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
