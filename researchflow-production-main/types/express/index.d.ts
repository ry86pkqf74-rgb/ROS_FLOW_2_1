/**
 * Express Request type extensions
 * Declares custom properties on the Express Request object
 */

declare global {
  namespace Express {
    interface Request {
      user?: {
        id: string;
        username: string;
        role: string;
        email: string;
        isActive: boolean;
      };
    }
  }
}

export {};
