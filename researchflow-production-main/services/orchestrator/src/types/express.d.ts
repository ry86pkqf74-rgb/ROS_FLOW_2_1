/**
 * Express Type Augmentation for ResearchFlow Orchestrator
 * 
 * Extends Express Request/Response types with custom properties
 * used throughout the application.
 * 
 * Linear Issue: ROS-59
 */

import { Request, Response, NextFunction } from 'express';

// User type from auth
interface AuthUser {
  id: string;
  email: string;
  name?: string;
  role: 'ADMIN' | 'RESEARCHER' | 'STEWARD' | 'VIEWER';
  organizationId?: string;
  permissions?: string[];
}

// Session type
interface SessionData {
  userId: string;
  organizationId?: string;
  createdAt: number;
  expiresAt: number;
}

declare global {
  namespace Express {
    interface Request {
      // Auth properties
      user?: AuthUser;
      userId?: string;
      organizationId?: string;
      session?: SessionData;
      
      // Request metadata
      requestId?: string;
      correlationId?: string;
      startTime?: number;
      
      // Parsed body types (for JSON APIs)
      body: Record<string, unknown>;
      
      // Query params (typed)
      query: Record<string, string | string[] | undefined>;
      
      // Route params (typed)
      params: Record<string, string>;
      
      // File uploads (multer)
      file?: Express.Multer.File;
      files?: Express.Multer.File[] | { [fieldname: string]: Express.Multer.File[] };
      
      // Custom properties for ResearchFlow
      projectId?: string;
      runId?: string;
      artifactId?: string;
      
      // Governance mode
      governanceMode?: 'demo' | 'live' | 'audit';
      
      // PHI detection
      phiDetected?: boolean;
      phiFields?: string[];
    }

    interface Response {
      // Custom response methods
      sendSuccess: (data: unknown, statusCode?: number) => void;
      sendError: (message: string, statusCode?: number, details?: unknown) => void;
      
      // Locals for template rendering
      locals: {
        user?: AuthUser;
        requestId?: string;
        [key: string]: unknown;
      };
    }
  }
}

// Middleware types
export type AsyncHandler = (
  req: Request,
  res: Response,
  next: NextFunction
) => Promise<void>;

export type ErrorHandler = (
  error: Error,
  req: Request,
  res: Response,
  next: NextFunction
) => void;

// Re-export express types for convenience
export { Request, Response, NextFunction };
