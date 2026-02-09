/**
 * Express Request type extensions
 * Declares custom properties on the Express Request object
 */

declare global {
  namespace Express {
    interface Request {
      headers?: any;
      body?: any;
      socket?: any;
      ip?: string;
      method?: string;
      originalUrl?: string;
      header?: (name: string) => any;
      rawBody?: any;
      recovery?: any;
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
