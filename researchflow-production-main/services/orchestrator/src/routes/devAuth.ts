import type { User as CoreUser } from "@researchflow/core";
import { Router, Request, Response, NextFunction } from "express";

import { jwt } from "../../lib/crypto-deps.js";
import { jwtConfig } from "../config/jwt.js";

function devAuthEnabled() {
  return !process.env.REPL_ID && process.env.ENABLE_DEV_AUTH === "true";
}

/**
 * Mock user for development when ALLOW_MOCK_AUTH=true
 */
const mockUser: CoreUser = {
  id: 'user-dev-001',
  email: 'steward@researchflow.dev',
  name: 'Development Steward',
  role: 'STEWARD',
  createdAt: new Date('2024-01-01'),
  isActive: true
};

/**
 * Global middleware that sets req.user for all requests in dev mode
 * when ALLOW_MOCK_AUTH=true. Applied before all routes.
 */
export function devAuthMiddleware(req: Request, res: Response, next: NextFunction): void {
  const isDev = process.env.NODE_ENV === 'development' || process.env.NODE_ENV === 'test' || !process.env.NODE_ENV;
  const allowMock = process.env.ALLOW_MOCK_AUTH === 'true';

  if (isDev && allowMock && !req.user) {
    req.user = mockUser;
  }

  next();
}

function signDevToken(userId: string) {
  const payload = {
    sub: userId,
    userId,
    role: "researcher",
  };

  // Match authService dev fallback behavior
  return jwt.sign(payload, "development-secret-key-not-for-production", {
    expiresIn: jwtConfig.expiresIn,
    issuer: jwtConfig.issuer,
    audience: jwtConfig.audience,
  });
}

const router = Router();

/**
 * Dev-only login for Playwright/CI.
 * Enabled only when REPL_ID is NOT set AND ENABLE_DEV_AUTH=true.
 *
 * Uses X-Dev-User-Id to issue an access token that the web app stores in localStorage.
 */
router.post("/login", async (req, res) => {
  if (!devAuthEnabled()) {
    return res.status(404).json({ error: "Not found" });
  }

  const userId = String(req.header("X-Dev-User-Id") || "").trim();
  if (!userId) {
    return res.status(400).json({ error: "Missing X-Dev-User-Id" });
  }

  const accessToken = signDevToken(userId);

  // Web expects: { accessToken, user, message } (see services/web/src/hooks/use-auth.ts)
  return res.json({
    message: "Dev login successful",
    accessToken,
    user: {
      id: userId,
      email: "e2e-test@researchflow.local",
      role: "researcher",
    },
  });
});

export default router;
