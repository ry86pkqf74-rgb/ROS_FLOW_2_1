import type { Express } from "express";

import { isAuthenticated } from "./replitAuth";
import { authStorage } from "./storage";

// Register auth-specific routes
export function registerAuthRoutes(app: Express): void {
  // Get current authenticated user
  app.get("/api/auth/user", isAuthenticated, async (req: any, res) => {
    if (!process.env.REPL_ID) {
      return res.json({
        id: "anonymous",
        email: "anonymous@localhost",
        firstName: "Local",
        lastName: "User",
        profileImageUrl: null
      });
    }

    try {
      const userId = req.user.claims.sub;
      const user = await authStorage.getUser(userId);
      res.json(user);
    } catch (error) {
      console.error("Error fetching user:", error);
      res.status(500).json({ message: "Failed to fetch user" });
    }
  });
}
