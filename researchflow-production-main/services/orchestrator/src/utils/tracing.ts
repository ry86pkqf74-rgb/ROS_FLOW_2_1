import { randomUUID } from 'crypto';
import type { Request, Response, NextFunction } from 'express';
import { logger } from './logger.js';

export const TRACE_HEADER = 'x-correlation-id';

export interface TraceContext {
  correlationId: string;
  startedAtMs: number;
}

declare global {
  // eslint-disable-next-line no-var
  var __rfTrace: { correlationId: string } | undefined;
}

export function generateCorrelationId(): string {
  return randomUUID();
}

export function getCorrelationIdFromHeaders(req: Request): string | undefined {
  const v = req.header(TRACE_HEADER);
  return v || undefined;
}

export function tracingMiddleware(req: Request, res: Response, next: NextFunction) {
  const correlationId = getCorrelationIdFromHeaders(req) ?? generateCorrelationId();
  const startedAtMs = Date.now();

  (req as any).trace = { correlationId, startedAtMs } satisfies TraceContext;

  res.setHeader(TRACE_HEADER, correlationId);

  res.on('finish', () => {
    const durationMs = Date.now() - startedAtMs;
    logger.info('request', {
      correlationId,
      method: req.method,
      path: req.originalUrl,
      status: res.statusCode,
      durationMs,
    });
  });

  next();
}

export function getTraceContext(req: Request): TraceContext {
  const t = (req as any).trace as TraceContext | undefined;
  return t ?? { correlationId: generateCorrelationId(), startedAtMs: Date.now() };
}

export function buildTraceHeaders(req: Request): Record<string, string> {
  const { correlationId } = getTraceContext(req);
  return { [TRACE_HEADER]: correlationId };
}

export async function traceServiceCall<T>(
  req: Request,
  serviceName: string,
  methodName: string,
  fn: () => Promise<T>,
): Promise<T> {
  const { correlationId } = getTraceContext(req);
  const start = Date.now();

  try {
    const result = await fn();
    const durationMs = Date.now() - start;
    logger.info('service_call', { correlationId, serviceName, methodName, ok: true, durationMs });
    return result;
  } catch (err) {
    const durationMs = Date.now() - start;
    logger.error('service_call', {
      correlationId,
      serviceName,
      methodName,
      ok: false,
      durationMs,
      error: (err as any)?.message ?? String(err),
    });
    throw err;
  }
}
