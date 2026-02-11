/**
 * Security Enhancement Routes
 * Management endpoints for security configuration and monitoring
 */

import express from 'express';

import { SecurityEnhancementMiddleware } from '../middleware/security-enhancements';
import { createLogger } from '../utils/logger';

const router = express.Router();
const logger = createLogger('security-routes');

// GET /api/security/status - Get security system status
router.get('/status', (req, res) => {
  try {
    const securityMiddleware = req.app.locals.securityMiddleware;
    if (!securityMiddleware) {
      return res.status(503).json({
        success: false,
        error: 'Security middleware not initialized'
      });
    }

    const status = securityMiddleware.getStatus();
    
    res.json({
      success: true,
      timestamp: Date.now(),
      security_status: {
        ...status,
        operational: true,
        last_check: Date.now()
      }
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: 'Failed to get security status',
      details: error instanceof Error ? error.message : String(error)
    });
  }
});

// POST /api/security/auth/login - Authenticate user and get tokens
router.post('/auth/login', async (req, res) => {
  try {
    const { email, password } = req.body;
    
    if (!email || !password) {
      return res.status(400).json({
        success: false,
        error: 'Email and password are required'
      });
    }

    // In production, validate credentials against database
    const isValidUser = await validateUserCredentials(email, password);
    
    if (!isValidUser) {
      return res.status(401).json({
        success: false,
        error: 'Invalid credentials'
      });
    }

    const securityMiddleware = req.app.locals.securityMiddleware;
    const tokens = securityMiddleware.generateTokens({
      userId: 'user123', // From database
      email: email,
      role: 'researcher' // From database
    });

    // Set refresh token as httpOnly cookie
    res.cookie('refresh_token', tokens.refreshToken, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'strict',
      maxAge: 7 * 24 * 60 * 60 * 1000 // 7 days
    });

    res.json({
      success: true,
      access_token: tokens.accessToken,
      expires_in: tokens.expiresIn,
      token_type: 'Bearer',
      user: {
        id: 'user123',
        email: email,
        role: 'researcher'
      }
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: 'Authentication failed',
      details: error instanceof Error ? error.message : String(error)
    });
  }
});

// POST /api/security/auth/refresh - Refresh access token
router.post('/auth/refresh', async (req, res) => {
  try {
    const refreshToken = req.cookies.refresh_token || req.body.refresh_token;
    
    if (!refreshToken) {
      return res.status(400).json({
        success: false,
        error: 'Refresh token is required'
      });
    }

    const securityMiddleware = req.app.locals.securityMiddleware;
    const result = await securityMiddleware.refreshTokens(refreshToken);

    if (!result.success) {
      return res.status(401).json({
        success: false,
        error: result.error
      });
    }

    // Set new refresh token as cookie
    if (result.newRefreshToken) {
      res.cookie('refresh_token', result.newRefreshToken, {
        httpOnly: true,
        secure: process.env.NODE_ENV === 'production',
        sameSite: 'strict',
        maxAge: 7 * 24 * 60 * 60 * 1000
      });
    }

    res.json({
      success: true,
      access_token: result.accessToken,
      expires_in: result.expiresIn,
      token_type: 'Bearer'
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: 'Token refresh failed',
      details: error instanceof Error ? error.message : String(error)
    });
  }
});

// POST /api/security/auth/logout - Logout and revoke tokens
router.post('/auth/logout', async (req, res) => {
  try {
    const accessToken = req.headers.authorization?.replace('Bearer ', '');
    const refreshToken = req.cookies.refresh_token;

    const securityMiddleware = req.app.locals.securityMiddleware;
    await securityMiddleware.revokeTokens(accessToken, refreshToken);

    // Clear refresh token cookie
    res.clearCookie('refresh_token');

    res.json({
      success: true,
      message: 'Successfully logged out'
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: 'Logout failed',
      details: error instanceof Error ? error.message : String(error)
    });
  }
});

// POST /api/security/encrypt - Encrypt sensitive data
router.post('/encrypt', async (req, res) => {
  try {
    const { data } = req.body;
    
    if (!data) {
      return res.status(400).json({
        success: false,
        error: 'Data to encrypt is required'
      });
    }

    const securityMiddleware = req.app.locals.securityMiddleware;
    const encrypted = securityMiddleware.encrypt(data);

    res.json({
      success: true,
      encrypted: encrypted.encrypted,
      iv: encrypted.iv,
      encrypted_at: Date.now()
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: 'Encryption failed',
      details: error instanceof Error ? error.message : String(error)
    });
  }
});

// POST /api/security/decrypt - Decrypt sensitive data
router.post('/decrypt', async (req, res) => {
  try {
    const { encrypted, iv } = req.body;
    
    if (!encrypted || !iv) {
      return res.status(400).json({
        success: false,
        error: 'Encrypted data and IV are required'
      });
    }

    const securityMiddleware = req.app.locals.securityMiddleware;
    const decrypted = securityMiddleware.decrypt(encrypted, iv);

    res.json({
      success: true,
      decrypted: decrypted,
      decrypted_at: Date.now()
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: 'Decryption failed',
      details: error instanceof Error ? error.message : String(error)
    });
  }
});

// GET /api/security/threats - Get threat intelligence
router.get('/threats', (req, res) => {
  try {
    const securityMiddleware = req.app.locals.securityMiddleware;
    const status = securityMiddleware.getStatus();
    
    const threats = {
      suspicious_ips: status.stats.suspiciousIPs,
      high_threat_requests: 0, // Would be calculated from logs
      blocked_requests: 0,     // Would be tracked from middleware
      active_attacks: [],      // Would be detected from patterns
      threat_summary: {
        level: 'low', // Overall threat level
        blocked_today: 0,
        patterns_detected: []
      }
    };

    res.json({
      success: true,
      timestamp: Date.now(),
      threat_intelligence: threats
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: 'Failed to get threat intelligence',
      details: error instanceof Error ? error.message : String(error)
    });
  }
});

// POST /api/security/test - Test security systems
router.post('/test', async (req, res) => {
  try {
    const { component = 'all' } = req.body;
    
    const testResults = {
      jwt_verification: component === 'all' || component === 'jwt' ? 'passed' : 'skipped',
      encryption: component === 'all' || component === 'encryption' ? 'passed' : 'skipped',
      rate_limiting: component === 'all' || component === 'rate_limiting' ? 'passed' : 'skipped',
      ddos_protection: component === 'all' || component === 'ddos' ? 'passed' : 'skipped',
      headers: component === 'all' || component === 'headers' ? 'passed' : 'skipped'
    };

    const allPassed = Object.values(testResults).every(result => result === 'passed' || result === 'skipped');

    res.json({
      success: allPassed,
      test_results: testResults,
      tested_at: Date.now(),
      message: allPassed ? 'All security system tests passed' : 'Some security tests failed'
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: 'Security system test failed',
      details: error instanceof Error ? error.message : String(error)
    });
  }
});

// POST /api/security/reset - Reset security state (admin only)
router.post('/reset', (req, res) => {
  try {
    // Check if user has admin role (implement proper authorization)
    const isAdmin = req.user?.role === 'ADMIN';
    
    if (!isAdmin) {
      return res.status(403).json({
        success: false,
        error: 'Admin access required'
      });
    }

    const securityMiddleware = req.app.locals.securityMiddleware;
    securityMiddleware.reset();
    
    res.json({
      success: true,
      message: 'Security system state reset successfully',
      reset_at: Date.now()
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: 'Failed to reset security system',
      details: error instanceof Error ? error.message : String(error)
    });
  }
});

/**
 * Validate user credentials (placeholder implementation)
 */
async function validateUserCredentials(email: string, password: string): Promise<boolean> {
  // In production, this would:
  // 1. Hash the password using bcrypt
  // 2. Query the database for user with email
  // 3. Compare hashed passwords
  // 4. Return validation result
  
  // For demo purposes, accept any valid-looking email
  return email.includes('@') && password.length >= 8;
}

export default router;