/**
 * JWT configuration for production authentication.
 *
 * RS256 (asymmetric) requires JWT_PUBLIC_KEY and JWT_PRIVATE_KEY (PEM strings or paths)
 * in production. In development, keys are required for RS256; do not use symmetric
 * secrets in production.
 */

export const jwtConfig = {
  algorithm: 'RS256' as const,
  issuer: process.env.JWT_ISSUER || 'researchflow',
  audience: process.env.JWT_AUDIENCE || 'researchflow-api',
  expiresIn: '24h',
  refreshExpiresIn: '7d',
};
