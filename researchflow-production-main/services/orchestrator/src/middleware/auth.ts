/**
 * Authentication Middleware
 *
 * Production: always verifies JWT (RS256) via authService.
 * Development: uses mock user only when NODE_ENV=development AND ALLOW_MOCK_AUTH=true;
 * otherwise verifies JWT.
 */

import type { User as CoreUser } from '@researchflow/core';
import { Request, Response, NextFunction } from 'express';

import { requireAuth as authServiceRequireAuth } from '../services/authService.js';

// Mock user for development when ALLOW_MOCK_AUTH=true
const mockUser: CoreUser = {
  id: 'user-dev-001',
  email: 'steward@researchflow.dev',
  name: 'Development Steward',
  role: 'STEWARD',
  createdAt: new Date('2024-01-01'),
  isActive: true
};

declare global {
  namespace Express {
    interface User extends CoreUser {}
  }
}

/**
 * Unified requireAuth: production always JWT; development mock only when ALLOW_MOCK_AUTH=true.
 */
export function requireAuth(req: Request, res: Response, next: NextFunction): void {
  const isDev = process.env.NODE_ENV === 'development' || process.env.NODE_ENV === 'test';
  const allowMock = process.env.ALLOW_MOCK_AUTH === 'true';

  if (isDev && allowMock) {
    req.user = mockUser;
    next();
    return;
  }

  authServiceRequireAuth(req, res, next);
}

/**
 * Mock authentication middleware (development only when ALLOW_MOCK_AUTH=true).
 * Exported for tests. Prefer requireAuth for route protection.
 */
export function mockAuthMiddleware(
  req: Request,
  res: Response,
  next: NextFunction
): void {
  const isDev = process.env.NODE_ENV === 'development' || process.env.NODE_ENV === 'test';
  const allowMock = process.env.ALLOW_MOCK_AUTH === 'true';

  if (isDev && allowMock) {
    req.user = mockUser;
    next();
    return;
  }

  if (process.env.NODE_ENV === 'production') {
    res.status(401).json({
      error: 'Authentication required',
      code: 'AUTH_REQUIRED',
      message: 'Invalid or expired token'
    });
    return;
  }

  authServiceRequireAuth(req, res, next);
}

export function getMockUser(): CoreUser {
  return { ...mockUser };
}

export function setMockUserRole(role: CoreUser['role']): void {
  mockUser.role = role;
}
