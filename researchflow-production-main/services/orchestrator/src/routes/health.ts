import { Router, type Request, type Response } from "express";
import { checkPostgres, checkRedis, checkWorker } from "../utils/healthChecks";

const router = Router();

router.get("/health", (_req: Request, res: Response) => {
  res.json({ status: "ok", timestamp: new Date().toISOString() });
});

router.get("/health/ready", async (_req: Request, res: Response) => {
  try {
    const [dbCheck, redisCheck, workerCheck] = await Promise.all([
      checkPostgres(),
      checkRedis(),
      checkWorker(),
    ]);

    const checks = {
      database: dbCheck.ok ? "ok" : `failed: ${dbCheck.error}`,
      redis: redisCheck.ok ? "ok" : `failed: ${redisCheck.error}`,
      worker: workerCheck.ok ? "ok" : `failed: ${workerCheck.error}`,
    };

    const allOk = dbCheck.ok && redisCheck.ok && workerCheck.ok;

    if (allOk) {
      res.json({ status: "ready", checks });
    } else {
      res.status(503).json({ status: "not_ready", checks, error: "One or more checks failed" });
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    res.status(503).json({ status: "not_ready", error: message });
  }
});

router.get("/worker", async (_req: Request, res: Response) => {
  try {
    const workerCheck = await checkWorker();
    if (workerCheck.ok) {
      res.json({ status: "ok", worker: "reachable" });
    } else {
      res.status(503).json({ status: "not_ok", worker: "unreachable", error: workerCheck.error });
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    res.status(503).json({ status: "not_ok", worker: "unreachable", error: message });
  }
});

export default router;
