/**
 * Service token auth context middleware
 *
 * Runs before security and rate limiters. Detects WORKER_SERVICE_TOKEN only on
 * an explicit allowlist of internal routes; elsewhere the token is ignored so
 * normal auth and protections apply (no global bypass).
 */

import crypto from 'crypto';

import { Request, Response, NextFunction } from 'express';

/** Auth context set by this middleware; security and rate limiters read it. */
export interface AuthContext {
  authenticated: boolean;
  isServiceToken: boolean;
  userId?: string;
  role?: string;
}

declare global {
  namespace Express {
    interface Request {
      auth?: AuthContext;
    }
  }
}

const SERVICE_USER_ID = '00000000-0000-4000-8000-000000000001';

/**
 * Routes where service token is accepted. Method + path (exact).
 * Only add entries after explicit confirmation; default is dispatch only.
 *
 * Path matching: this middleware runs at app level (no mount path), so req.path
 * is the full pathname (e.g. /api/ai/router/dispatch), not relative to a router.
 */
const SERVICE_TOKEN_ALLOWLIST: { method: string; path: string }[] = [
  { method: 'POST', path: '/api/ai/router/dispatch' },
];

function isAllowlisted(method: string, path: string): boolean {
  return SERVICE_TOKEN_ALLOWLIST.some(
    (entry) => entry.method === method && path === entry.path
  );
}

/** Constant-time comparison to avoid leaking token length via timing. */
function secureTokenEqual(a: string, b: string): boolean {
  try {
    const bufA = Buffer.from(a, 'utf8');
    const bufB = Buffer.from(b, 'utf8');
    if (bufA.length !== bufB.length) return false;
    return crypto.timingSafeEqual(bufA, bufB);
  } catch {
    return false;
  }
}

/** Synthetic user for service token: role SERVICE is non-admin; RBAC treats as constrained. */
function getServiceUser(): { id: string; email: string; displayName: string; role: string } {
  return {
    id: SERVICE_USER_ID,
    email: 'service@researchflow.internal',
    displayName: 'Internal Service',
    role: 'SERVICE',
  };
}

/**
 * Middleware: sets req.auth (and req.user for service token) only when
 * Authorization matches WORKER_SERVICE_TOKEN and request is on the allowlist.
 * Otherwise leaves req.auth/req.user unset so normal auth and protections apply.
 */
export function serviceAuthMiddleware(
  req: Request,
  _res: Response,
  next: NextFunction
): void {
  const authHeader = req.headers.authorization;
  const token = authHeader?.startsWith('Bearer ') ? authHeader.slice(7).trim() : undefined;
  const serviceToken = process.env.WORKER_SERVICE_TOKEN;

  req.auth = {
    authenticated: false,
    isServiceToken: false,
  };

  if (!token || !serviceToken || !secureTokenEqual(token, serviceToken)) {
    return next();
  }

  if (!isAllowlisted(req.method, req.path)) {
    return next();
  }

  req.auth = {
    authenticated: true,
    isServiceToken: true,
    userId: SERVICE_USER_ID,
    role: 'SERVICE',
  };
  (req as any).user = getServiceUser();
  next();
}
