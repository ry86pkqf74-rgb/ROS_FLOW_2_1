/**
 * Governance Middleware
 *
 * Re-exports authentication and authorization middleware for convenience.
 * Uses unified requireAuth from auth.ts (JWT in production, mock only when ALLOW_MOCK_AUTH=true in dev).
 */

import { requireAuth as authRequireAuth } from './auth';

/**
 * Require authentication middleware
 * Ensures request has valid user context (JWT or dev mock when ALLOW_MOCK_AUTH=true)
 */
export const requireAuth = authRequireAuth;

/**
 * Alias for requireAuth - some routes may use this name
 */
export const requireAuthentication = requireAuth;

export { mockAuthMiddleware, getMockUser, setMockUserRole } from './auth';
