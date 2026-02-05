#!/usr/bin/env node
/**
 * Generate WORKER_SERVICE_TOKEN for development
 * 
 * This script generates a mock HS256 JWT for internal service-to-service auth.
 * Only works when ALLOW_MOCK_AUTH=true and AUTH_ALLOW_STATELESS_JWT=true.
 * 
 * Usage:
 *   npx tsx tools/dev/generate-worker-service-token.ts
 *   
 * Or to set directly in .env:
 *   echo "WORKER_SERVICE_TOKEN=$(npx tsx tools/dev/generate-worker-service-token.ts)" >> .env
 */

import jwt from 'jsonwebtoken';
import { jwtConfig } from '../../services/orchestrator/src/config/jwt';

const DEV_SECRET = 'development-secret-key-not-for-production';

// Service principal for internal worker
const payload = {
  // Valid UUID (v4) required by JWTPayloadSchema
  sub: '00000000-0000-4000-8000-000000000001',
  email: 'svc-worker@local.dev',
  role: 'ADMIN',
  iat: Math.floor(Date.now() / 1000),
  exp: Math.floor(Date.now() / 1000) + (30 * 24 * 60 * 60), // 30 days
};

const token = jwt.sign(payload, DEV_SECRET, {
  algorithm: 'HS256',
  issuer: jwtConfig.issuer,
  audience: jwtConfig.audience,
});

// Print ONLY the token (for easy shell capture)
console.log(token);
