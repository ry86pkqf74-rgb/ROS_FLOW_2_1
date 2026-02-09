import { Router } from 'express';

import auditRouter from './audit';

const router = Router();

// Mounts to /internal/audit/*
router.use('/audit', auditRouter);

export default router;

