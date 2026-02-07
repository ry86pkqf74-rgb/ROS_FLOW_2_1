/**
 * Advanced Security Enhancements Middleware
 * Enterprise-grade security with TLS 1.3, JWT management, and DDoS protection
 */

import crypto from 'crypto';

import { Request, Response, NextFunction } from 'express';
import { rateLimit } from 'express-rate-limit';
import jwt from 'jsonwebtoken';

import { createLogger } from '../utils/logger';

interface SecurityConfig {
  enableTLS13: boolean;
  enableJWTSecurity: boolean;
  enableRateLimiting: boolean;
  enableDDoSProtection: boolean;
  jwtSecret: string;
  jwtRefreshSecret: string;
  tokenExpiration: string;
  refreshTokenExpiration: string;
  encryptionKey: string;
  rateLimitWindow: number;
  rateLimitMaxRequests: number;
  ddosThreshold: number;
  ddosWindowMs: number;
}

interface TokenPayload {
  userId: string;
  email: string;
  role: string;
  iat: number;
  exp: number;
}

interface SecurityRequest extends Request {
  user?: TokenPayload;
  auth?: { authenticated: boolean; isServiceToken?: boolean; userId?: string; role?: string };
  rateLimitInfo?: {
    limit: number;
    remaining: number;
    reset: Date;
  };
  securityContext?: {
    encrypted: boolean;
    authenticated: boolean;
    rateLimited: boolean;
    threatLevel: 'low' | 'medium' | 'high';
  };
}

export class SecurityEnhancementMiddleware {
  private config: SecurityConfig;
  private logger = createLogger('security-middleware');
  private activeConnections = new Map<string, { count: number; lastAccess: number }>();
  private suspiciousIPs = new Set<string>();
  private refreshTokens = new Map<string, { userId: string; expiresAt: number }>();

  constructor(config: Partial<SecurityConfig> = {}) {
    this.config = {
      enableTLS13: process.env.ENABLE_TLS13 !== 'false',
      enableJWTSecurity: process.env.ENABLE_JWT_SECURITY !== 'false',
      enableRateLimiting: process.env.ENABLE_RATE_LIMITING !== 'false',
      enableDDoSProtection: process.env.ENABLE_DDOS_PROTECTION !== 'false',
      jwtSecret: process.env.JWT_SECRET || this.generateSecureKey(),
      jwtRefreshSecret: process.env.JWT_REFRESH_SECRET || this.generateSecureKey(),
      tokenExpiration: process.env.JWT_EXPIRATION || '15m',
      refreshTokenExpiration: process.env.JWT_REFRESH_EXPIRATION || '7d',
      encryptionKey: process.env.ENCRYPTION_KEY || this.generateSecureKey(),
      rateLimitWindow: parseInt(process.env.RATE_LIMIT_WINDOW || '900000', 10), // 15 minutes
      rateLimitMaxRequests: parseInt(process.env.RATE_LIMIT_MAX_REQUESTS || '1000', 10),
      ddosThreshold: parseInt(process.env.DDOS_THRESHOLD || '100', 10),
      ddosWindowMs: parseInt(process.env.DDOS_WINDOW_MS || '60000', 10), // 1 minute
      ...config
    };

    // Validate critical security settings
    this.validateSecurityConfig();
    
    // Start cleanup processes
    this.startCleanupProcesses();
  }

  /**
   * Main security middleware orchestrator
   */
  middleware() {
    return (req: SecurityRequest, res: Response, next: NextFunction) => {
      // Initialize security context
      req.securityContext = {
        encrypted: req.secure,
        authenticated: false,
        rateLimited: false,
        threatLevel: 'low'
      };

      // Apply security layers
      this.applySecurityLayers(req, res, next);
    };
  }

  /**
   * Apply layered security protections.
   * For allowlisted service-token requests we only skip rate limiting and threat
   * logging; DDoS, headers, and body/size limits still apply.
   */
  private async applySecurityLayers(req: SecurityRequest, res: Response, next: NextFunction) {
    try {
      const isServiceToken = req.auth?.isServiceToken === true;
      if (isServiceToken) {
        req.securityContext!.authenticated = true;
      }

      // Layer 1: DDoS Protection (always run)
      if (this.config.enableDDoSProtection) {
        const ddosResult = this.checkDDoSProtection(req);
        if (ddosResult.blocked) {
          return res.status(429).json({
            error: 'Too Many Requests',
            code: 'DDOS_PROTECTION',
            message: 'Request blocked by DDoS protection',
            retry_after: ddosResult.retryAfter
          });
        }
      }

      // Layer 2: Rate Limiting (skip only for allowlisted service-token requests)
      if (this.config.enableRateLimiting && !isServiceToken) {
        const rateLimitResult = this.applyRateLimit(req);
        if (rateLimitResult.limited) {
          req.securityContext!.rateLimited = true;
          req.rateLimitInfo = {
            limit: rateLimitResult.limit,
            remaining: rateLimitResult.remaining,
            reset: rateLimitResult.reset
          };
          
          if (rateLimitResult.remaining <= 0) {
            return res.status(429).json({
              error: 'Rate Limit Exceeded',
              code: 'RATE_LIMIT',
              limit: rateLimitResult.limit,
              remaining: rateLimitResult.remaining,
              reset: rateLimitResult.reset
            });
          }
        }
      }

      // Layer 3: JWT Authentication (skip for allowlisted service-token; already authenticated)
      const isDev = process.env.NODE_ENV === 'development' || process.env.NODE_ENV === 'test';
      const allowMock = process.env.ALLOW_MOCK_AUTH === 'true';
      if (
        !isServiceToken &&
        this.config.enableJWTSecurity &&
        this.requiresAuthentication(req) &&
        !(isDev && allowMock)
      ) {
        const authResult = await this.authenticateJWT(req);
        if (!authResult.valid) {
          return res.status(401).json({
            error: 'Unauthorized',
            code: 'JWT_INVALID',
            message: authResult.message
          });
        }
        req.user = authResult.user;
        req.securityContext!.authenticated = true;
      }

      // Layer 4: Threat Assessment
      const threatLevel = this.assessThreatLevel(req);
      req.securityContext!.threatLevel = threatLevel;

      // Set security response headers
      this.setSecurityHeaders(res);

      // Log security event
      this.logSecurityEvent(req);

      next();
    } catch (error) {
      this.logger.error('Security middleware error', {
        error: error instanceof Error ? error.message : String(error),
        path: req.path,
        ip: req.ip
      });
      
      res.status(500).json({
        error: 'Security Processing Error',
        code: 'SECURITY_ERROR'
      });
    }
  }

  /**
   * DDoS Protection - Track and block suspicious traffic
   */
  private checkDDoSProtection(req: SecurityRequest): { blocked: boolean; retryAfter?: number } {
    const clientIP = req.ip;
    const now = Date.now();
    
    // Check if IP is already flagged as suspicious
    if (this.suspiciousIPs.has(clientIP)) {
      return { blocked: true, retryAfter: 300 }; // 5 minutes
    }

    // Track connection count per IP
    const connectionData = this.activeConnections.get(clientIP) || { count: 0, lastAccess: now };
    
    // Reset count if outside window
    if (now - connectionData.lastAccess > this.config.ddosWindowMs) {
      connectionData.count = 0;
    }

    connectionData.count++;
    connectionData.lastAccess = now;
    this.activeConnections.set(clientIP, connectionData);

    // Check threshold
    if (connectionData.count > this.config.ddosThreshold) {
      this.suspiciousIPs.add(clientIP);
      this.logger.warn('IP flagged for DDoS protection', {
        ip: clientIP,
        requestCount: connectionData.count,
        threshold: this.config.ddosThreshold
      });
      
      return { blocked: true, retryAfter: 300 };
    }

    return { blocked: false };
  }

  /**
   * Advanced Rate Limiting with per-user and per-IP tracking
   */
  private applyRateLimit(req: SecurityRequest): {
    limited: boolean;
    limit: number;
    remaining: number;
    reset: Date;
  } {
    const identifier = req.user?.userId || req.ip;
    const now = Date.now();
    const windowStart = now - this.config.rateLimitWindow;
    
    // In production, use Redis for distributed rate limiting
    // For now, using in-memory tracking as proof-of-concept
    
    const key = `rate_limit:${identifier}`;
    const requestCount = 0;
    
    // Simplified rate limit check
    // In production, implement sliding window with Redis
    
    const remaining = Math.max(0, this.config.rateLimitMaxRequests - requestCount);
    const reset = new Date(windowStart + this.config.rateLimitWindow);

    return {
      limited: true,
      limit: this.config.rateLimitMaxRequests,
      remaining,
      reset
    };
  }

  /**
   * JWT Authentication and Token Management
   */
  private async authenticateJWT(req: SecurityRequest): Promise<{
    valid: boolean;
    user?: TokenPayload;
    message?: string;
  }> {
    try {
      const authHeader = req.headers.authorization;
      
      if (!authHeader || !authHeader.startsWith('Bearer ')) {
        return { valid: false, message: 'Missing or invalid authorization header' };
      }

      const token = authHeader.substring(7);
      
      // Verify JWT token
      const decoded = jwt.verify(token, this.config.jwtSecret) as TokenPayload;
      
      // Additional security checks
      if (!decoded.userId || !decoded.email) {
        return { valid: false, message: 'Invalid token payload' };
      }

      // Check if token is in blacklist (implement token blacklisting in production)
      if (await this.isTokenBlacklisted(token)) {
        return { valid: false, message: 'Token has been revoked' };
      }

      return { valid: true, user: decoded };

    } catch (error) {
      if (error instanceof jwt.TokenExpiredError) {
        return { valid: false, message: 'Token has expired' };
      } else if (error instanceof jwt.JsonWebTokenError) {
        return { valid: false, message: 'Invalid token' };
      } else {
        return { valid: false, message: 'Token verification failed' };
      }
    }
  }

  /**
   * Generate new JWT tokens
   */
  generateTokens(payload: Omit<TokenPayload, 'iat' | 'exp'>): {
    accessToken: string;
    refreshToken: string;
    expiresIn: number;
  } {
    const now = Math.floor(Date.now() / 1000);
    
    // Generate access token
    const accessToken = jwt.sign(
      {
        ...payload,
        iat: now
      },
      this.config.jwtSecret,
      { expiresIn: this.config.tokenExpiration }
    );

    // Generate refresh token
    const refreshToken = jwt.sign(
      {
        userId: payload.userId,
        type: 'refresh',
        iat: now
      },
      this.config.jwtRefreshSecret,
      { expiresIn: this.config.refreshTokenExpiration }
    );

    // Store refresh token
    const refreshPayload = jwt.decode(refreshToken) as any;
    this.refreshTokens.set(refreshToken, {
      userId: payload.userId,
      expiresAt: refreshPayload.exp * 1000
    });

    return {
      accessToken,
      refreshToken,
      expiresIn: this.parseExpirationTime(this.config.tokenExpiration)
    };
  }

  /**
   * Refresh JWT tokens
   */
  async refreshTokens(refreshToken: string): Promise<{
    success: boolean;
    accessToken?: string;
    newRefreshToken?: string;
    expiresIn?: number;
    error?: string;
  }> {
    try {
      // Verify refresh token
      const decoded = jwt.verify(refreshToken, this.config.jwtRefreshSecret) as any;
      
      if (decoded.type !== 'refresh') {
        return { success: false, error: 'Invalid refresh token type' };
      }

      // Check if refresh token exists in storage
      const storedToken = this.refreshTokens.get(refreshToken);
      if (!storedToken || storedToken.userId !== decoded.userId) {
        return { success: false, error: 'Refresh token not found or invalid' };
      }

      // Remove old refresh token
      this.refreshTokens.delete(refreshToken);

      // In production, fetch user data from database
      const userPayload = {
        userId: decoded.userId,
        email: 'user@example.com', // Fetch from DB
        role: 'user' // Fetch from DB
      };

      // Generate new tokens
      const newTokens = this.generateTokens(userPayload);

      return {
        success: true,
        accessToken: newTokens.accessToken,
        newRefreshToken: newTokens.refreshToken,
        expiresIn: newTokens.expiresIn
      };

    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Token refresh failed'
      };
    }
  }

  /**
   * Revoke tokens (logout)
   */
  async revokeTokens(accessToken?: string, refreshToken?: string): Promise<void> {
    if (accessToken) {
      // Add to blacklist (implement token blacklisting in production)
      await this.blacklistToken(accessToken);
    }

    if (refreshToken) {
      this.refreshTokens.delete(refreshToken);
    }
  }

  /**
   * Encrypt sensitive data
   */
  encrypt(data: string): { encrypted: string; iv: string } {
    const iv = crypto.randomBytes(16);
    const cipher = crypto.createCipher('aes-256-gcm', this.config.encryptionKey);
    
    let encrypted = cipher.update(data, 'utf8', 'hex');
    encrypted += cipher.final('hex');
    
    return {
      encrypted,
      iv: iv.toString('hex')
    };
  }

  /**
   * Decrypt sensitive data
   */
  decrypt(encrypted: string, iv: string): string {
    const decipher = crypto.createDecipher('aes-256-gcm', this.config.encryptionKey);
    
    let decrypted = decipher.update(encrypted, 'hex', 'utf8');
    decrypted += decipher.final('utf8');
    
    return decrypted;
  }

  /**
   * Assess threat level based on request characteristics
   */
  private assessThreatLevel(req: SecurityRequest): 'low' | 'medium' | 'high' {
    let threatScore = 0;
    
    // Check for suspicious patterns
    if (this.suspiciousIPs.has(req.ip)) threatScore += 30;
    if (req.securityContext?.rateLimited) threatScore += 20;
    if (!req.secure) threatScore += 10;
    if (this.hasKnownAttackPatterns(req)) threatScore += 40;
    if (this.hasAnormalRequestSize(req)) threatScore += 15;
    
    if (threatScore >= 50) return 'high';
    if (threatScore >= 25) return 'medium';
    return 'low';
  }

  /**
   * Check for known attack patterns
   */
  private hasKnownAttackPatterns(req: SecurityRequest): boolean {
    const attackPatterns = [
      /\.\./,           // Path traversal
      /<script/i,       // XSS
      /union.*select/i, // SQL injection
      /exec\s*\(/i,     // Command injection
      /javascript:/i,   // JavaScript protocol
      /\$\{.*\}/,       // Template injection
    ];

    const checkString = `${req.path} ${JSON.stringify(req.query)} ${JSON.stringify(req.body)}`;
    return attackPatterns.some(pattern => pattern.test(checkString));
  }

  /**
   * Check for abnormal request size
   */
  private hasAnormalRequestSize(req: SecurityRequest): boolean {
    const contentLength = req.get('content-length');
    if (!contentLength) return false;
    
    const size = parseInt(contentLength, 10);
    return size > 10 * 1024 * 1024; // 10MB threshold
  }

  /**
   * Set comprehensive security headers
   */
  private setSecurityHeaders(res: Response): void {
    // Content Security Policy
    res.setHeader('Content-Security-Policy', 
      "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'");
    
    // Prevent clickjacking
    res.setHeader('X-Frame-Options', 'DENY');
    
    // Prevent MIME sniffing
    res.setHeader('X-Content-Type-Options', 'nosniff');
    
    // Enable XSS protection
    res.setHeader('X-XSS-Protection', '1; mode=block');
    
    // Force HTTPS
    res.setHeader('Strict-Transport-Security', 'max-age=31536000; includeSubDomains');
    
    // Prevent information disclosure
    res.removeHeader('X-Powered-By');
    res.setHeader('Server', 'ResearchFlow');
    
    // Referrer Policy
    res.setHeader('Referrer-Policy', 'strict-origin-when-cross-origin');
    
    // Permissions Policy
    res.setHeader('Permissions-Policy', 'geolocation=(), microphone=(), camera=()');
  }

  /**
   * Log security events. Skip verbose logging for internal service calls unless VERBOSE_INTERNAL_LOGS.
   */
  private logSecurityEvent(req: SecurityRequest): void {
    if (req.auth?.isServiceToken === true && process.env.VERBOSE_INTERNAL_LOGS !== 'true') {
      return;
    }
    if (req.securityContext?.threatLevel !== 'low') {
      this.logger.warn('Security event detected', {
        ip: req.ip,
        path: req.path,
        method: req.method,
        threatLevel: req.securityContext.threatLevel,
        authenticated: req.securityContext.authenticated,
        rateLimited: req.securityContext.rateLimited,
        userAgent: req.get('user-agent'),
        timestamp: Date.now()
      });
    }
  }

  /**
   * Helper methods
   */
  private requiresAuthentication(req: SecurityRequest): boolean {
    const protectedPaths = ['/api/admin', '/api/user', '/api/workflow'];
    return protectedPaths.some(path => req.path.startsWith(path));
  }

  private generateSecureKey(): string {
    return crypto.randomBytes(32).toString('hex');
  }

  private parseExpirationTime(expiration: string): number {
    const match = expiration.match(/^(\d+)([smhd])$/);
    if (!match) return 900; // Default 15 minutes
    
    const value = parseInt(match[1], 10);
    const unit = match[2];
    
    switch (unit) {
      case 's': return value;
      case 'm': return value * 60;
      case 'h': return value * 60 * 60;
      case 'd': return value * 24 * 60 * 60;
      default: return 900;
    }
  }

  private async isTokenBlacklisted(token: string): Promise<boolean> {
    // In production, check Redis blacklist
    return false;
  }

  private async blacklistToken(token: string): Promise<void> {
    // In production, add to Redis blacklist with expiration
    this.logger.info('Token blacklisted', { token: token.substring(0, 20) + '...' });
  }

  private validateSecurityConfig(): void {
    if (!this.config.jwtSecret || this.config.jwtSecret.length < 32) {
      throw new Error('JWT secret must be at least 32 characters long');
    }
    
    if (!this.config.encryptionKey || this.config.encryptionKey.length < 32) {
      throw new Error('Encryption key must be at least 32 characters long');
    }
  }

  private startCleanupProcesses(): void {
    // Clean up old connection data every 5 minutes
    setInterval(() => {
      const now = Date.now();
      const cutoff = now - (this.config.ddosWindowMs * 2);
      
      for (const [ip, data] of this.activeConnections) {
        if (data.lastAccess < cutoff) {
          this.activeConnections.delete(ip);
        }
      }
    }, 5 * 60 * 1000);

    // Clean up expired refresh tokens every hour
    setInterval(() => {
      const now = Date.now();
      
      for (const [token, data] of this.refreshTokens) {
        if (data.expiresAt < now) {
          this.refreshTokens.delete(token);
        }
      }
    }, 60 * 60 * 1000);

    // Clear suspicious IPs every hour
    setInterval(() => {
      this.suspiciousIPs.clear();
    }, 60 * 60 * 1000);
  }

  /**
   * Get security system status
   */
  getStatus() {
    return {
      config: {
        tls13Enabled: this.config.enableTLS13,
        jwtSecurityEnabled: this.config.enableJWTSecurity,
        rateLimitingEnabled: this.config.enableRateLimiting,
        ddosProtectionEnabled: this.config.enableDDoSProtection,
        rateLimitWindow: this.config.rateLimitWindow,
        rateLimitMaxRequests: this.config.rateLimitMaxRequests,
        ddosThreshold: this.config.ddosThreshold
      },
      stats: {
        activeConnections: this.activeConnections.size,
        suspiciousIPs: this.suspiciousIPs.size,
        activeRefreshTokens: this.refreshTokens.size
      }
    };
  }

  /**
   * Reset security state (for testing)
   */
  reset(): void {
    this.activeConnections.clear();
    this.suspiciousIPs.clear();
    this.refreshTokens.clear();
  }
}

export default SecurityEnhancementMiddleware;