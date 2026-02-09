/**
 * Edit Sessions API
 * Phase 3: HITL edit sessions — draft → submit → approve/reject → merge.
 */

import { Router, Request, Response } from 'express';
import * as z from 'zod';

import { requireAuth } from '../middleware/auth';
import * as EditSessionService from '../services/edit-session.service';

const router = Router();

const createSchema = z.object({
  branch_id: z.string().uuid(),
  manuscript_id: z.string().uuid(),
});

const submitSchema = z.object({});
const approveSchema = z.object({});
const rejectSchema = z.object({
  reason: z.string().max(2000).optional(),
});
const mergeSchema = z.object({});

/**
 * POST /api/edit-sessions
 * Create a new edit session (draft) for a branch.
 */
router.post('/', requireAuth, async (req: Request, res: Response) => {
  try {
    const parsed = createSchema.safeParse(req.body);
    if (!parsed.success) {
      return res.status(400).json({ error: 'Invalid input', details: parsed.error.flatten() });
    }
    const userId = (req as any).user?.id;
    const session = await EditSessionService.createEditSession({
      branchId: parsed.data.branch_id,
      manuscriptId: parsed.data.manuscript_id,
      createdBy: userId,
    });
    return res.status(201).json(session);
  } catch (err: any) {
    if (err.message?.includes('already exists')) return res.status(409).json({ error: err.message });
    return res.status(500).json({ error: err?.message ?? 'Failed to create edit session' });
  }
});

/**
 * GET /api/edit-sessions/branch/:branchId
 * Must be before /:sessionId to avoid "branch" being captured as sessionId.
 */
router.get('/branch/:branchId', requireAuth, async (req: Request, res: Response) => {
  try {
    const session = await EditSessionService.getEditSessionByBranchId(req.params.branchId);
    if (!session) return res.status(404).json({ error: 'Edit session not found' });
    return res.json(session);
  } catch (err: any) {
    return res.status(500).json({ error: err?.message ?? 'Failed to get edit session' });
  }
});

/**
 * GET /api/edit-sessions/manuscript/:manuscriptId
 * Must be before /:sessionId to avoid "manuscript" being captured as sessionId.
 */
router.get('/manuscript/:manuscriptId', requireAuth, async (req: Request, res: Response) => {
  try {
    const sessions = await EditSessionService.listEditSessionsByManuscript(req.params.manuscriptId);
    return res.json(sessions);
  } catch (err: any) {
    return res.status(500).json({ error: err?.message ?? 'Failed to list edit sessions' });
  }
});

/**
 * GET /api/edit-sessions/:sessionId
 */
router.get('/:sessionId', requireAuth, async (req: Request, res: Response) => {
  try {
    const session = await EditSessionService.getEditSession(req.params.sessionId);
    if (!session) return res.status(404).json({ error: 'Edit session not found' });
    return res.json(session);
  } catch (err: any) {
    return res.status(500).json({ error: err?.message ?? 'Failed to get edit session' });
  }
});

/**
 * POST /api/edit-sessions/:sessionId/submit
 * Transition draft → submitted.
 */
router.post('/:sessionId/submit', requireAuth, async (req: Request, res: Response) => {
  try {
    const parsed = submitSchema.safeParse(req.body);
    if (!parsed.success) {
      return res.status(400).json({ error: 'Invalid input', details: parsed.error.flatten() });
    }
    const userId = (req as any).user?.id;
    const session = await EditSessionService.submitEditSession(req.params.sessionId, userId);
    return res.json(session);
  } catch (err: any) {
    if (err.message?.startsWith('Cannot submit')) return res.status(400).json({ error: err.message });
    if (err.message === 'Edit session not found') return res.status(404).json({ error: err.message });
    return res.status(500).json({ error: err?.message ?? 'Failed to submit edit session' });
  }
});

/**
 * POST /api/edit-sessions/:sessionId/approve
 * Transition submitted → approved.
 */
router.post('/:sessionId/approve', requireAuth, async (req: Request, res: Response) => {
  try {
    const parsed = approveSchema.safeParse(req.body);
    if (!parsed.success) {
      return res.status(400).json({ error: 'Invalid input', details: parsed.error.flatten() });
    }
    const userId = (req as any).user?.id;
    const session = await EditSessionService.approveEditSession(req.params.sessionId, userId);
    return res.json(session);
  } catch (err: any) {
    if (err.message?.startsWith('Cannot approve')) return res.status(400).json({ error: err.message });
    if (err.message === 'Edit session not found') return res.status(404).json({ error: err.message });
    return res.status(500).json({ error: err?.message ?? 'Failed to approve edit session' });
  }
});

/**
 * POST /api/edit-sessions/:sessionId/reject
 * Transition submitted → rejected.
 */
router.post('/:sessionId/reject', requireAuth, async (req: Request, res: Response) => {
  try {
    const parsed = rejectSchema.safeParse(req.body ?? {});
    if (!parsed.success) {
      return res.status(400).json({ error: 'Invalid input', details: parsed.error.flatten() });
    }
    const userId = (req as any).user?.id;
    const session = await EditSessionService.rejectEditSession(req.params.sessionId, {
      rejectedBy: userId,
      reason: parsed.data.reason,
    });
    return res.json(session);
  } catch (err: any) {
    if (err.message?.startsWith('Cannot reject')) return res.status(400).json({ error: err.message });
    if (err.message === 'Edit session not found') return res.status(404).json({ error: err.message });
    return res.status(500).json({ error: err?.message ?? 'Failed to reject edit session' });
  }
});

/**
 * POST /api/edit-sessions/:sessionId/merge
 * Transition approved → merged. Optionally performs branch merge into main (caller can do merge separately).
 */
router.post('/:sessionId/merge', requireAuth, async (req: Request, res: Response) => {
  try {
    const parsed = mergeSchema.safeParse(req.body ?? {});
    if (!parsed.success) {
      return res.status(400).json({ error: 'Invalid input', details: parsed.error.flatten() });
    }
    const userId = (req as any).user?.id;
    const session = await EditSessionService.mergeEditSession(req.params.sessionId, userId);
    return res.json(session);
  } catch (err: any) {
    if (err.message?.startsWith('Cannot merge')) return res.status(400).json({ error: err.message });
    if (err.message === 'Edit session not found') return res.status(404).json({ error: err.message });
    return res.status(500).json({ error: err?.message ?? 'Failed to merge edit session' });
  }
});

export default router;
