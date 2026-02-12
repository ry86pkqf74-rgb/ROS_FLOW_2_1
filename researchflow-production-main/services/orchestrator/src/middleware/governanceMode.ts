/**
 * Governance Mode Middleware
 *
 * Controls access to operations based on the current governance mode.
 * - DEMO: Simulated data only, uploads/exports blocked
 * - LIVE: All operations allowed
 *
 * Priority: P0 - CRITICAL
 */

import { Request, Response, NextFunction } from 'express';

import { getGovernanceState } from '../routes/governance.js';

export type GovernanceMode = 'DEMO' | 'LIVE';

export async function getGovernanceMode(): Promise<GovernanceMode> {
  const state = await getGovernanceState();
  return state.mode as GovernanceMode;
}

export function requireLiveMode(operationType: string) {
  return async (req: Request, res: Response, next: NextFunction): Promise<void> => {
    const mode = await getGovernanceMode();

    if (mode === 'DEMO') {
      res.status(403).json({
        error: 'Operation blocked in DEMO mode',
        code: 'DEMO_MODE_RESTRICTED',
        operation: operationType
      });
      return;
    }

    next();
  };
}

export function requireDemoSafe(operationType: string) {
  return async (req: Request, res: Response, next: NextFunction): Promise<void> => {
    const mode = await getGovernanceMode();

    if (mode === 'DEMO') {
      res.status(403).json({
        error: 'Operation blocked in DEMO mode',
        code: 'DEMO_MODE_RESTRICTED',
        operation: operationType
      });
      return;
    }

    next();
  };
}
