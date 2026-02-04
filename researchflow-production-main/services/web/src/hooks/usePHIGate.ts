/**
 * usePHIGate - Hook for PHI access control and audit logging
 */

import { useState, useEffect, useCallback } from 'react';
import { apiClient } from '@/lib/api/client';

export type GovernanceMode = 'DEMO' | 'LIVE' | 'STANDBY';
type ApprovalStatus = 'none' | 'pending' | 'approved' | 'denied';

interface UsePHIGateReturn {
  governanceMode: GovernanceMode;
  isLoading: boolean;
  hasAccess: boolean;
  requiresApproval: boolean;
  approvalStatus: ApprovalStatus;
  requestApproval: (stageId: number, action: string) => Promise<void>;
  logAccess: (stageId: number, action: string, dataType: string) => void;
  checkPermission: (action: string, dataType: string) => boolean;
}

interface GovernanceResponse {
  mode: GovernanceMode;
}

export function usePHIGate(projectId: string): UsePHIGateReturn {
  const [governanceMode, setGovernanceMode] = useState<GovernanceMode>('DEMO');
  const [isLoading, setIsLoading] = useState(true);
  const [approvalStatus, setApprovalStatus] = useState<ApprovalStatus>('none');
  const [, setPendingApprovals] = useState<Set<string>>(new Set());

  useEffect(() => {
    const fetchGovernanceMode = async () => {
      try {
        const response = await apiClient.get<GovernanceResponse>(
          `/api/projects/${projectId}/governance`
        );
        if (response.data?.mode) {
          setGovernanceMode(response.data.mode);
        }
        try {
          const approvals = await apiClient.get<{ stageId: number; action: string }[]>(
            `/api/projects/${projectId}/approvals/pending`
          );
          if (approvals.data && approvals.data.length > 0) {
            setApprovalStatus('pending');
            setPendingApprovals(new Set(approvals.data.map((a) => `${a.stageId}-${a.action}`)));
          }
        } catch {
          // Project approvals endpoint may not exist
        }
      } catch {
        // Fallback to global governance when project endpoint does not exist
        try {
          const globalRes = await apiClient.get<GovernanceResponse>('/api/governance/mode');
          if (globalRes.data?.mode) {
            const mode = globalRes.data.mode as string;
            setGovernanceMode(
              mode === 'STANDBY' ? 'STANDBY' : mode === 'LIVE' ? 'LIVE' : 'DEMO'
            );
          }
        } catch {
          const stateRes = await apiClient.get<{ mode?: string }>('/api/governance/state');
          if (stateRes.data?.mode) {
            const mode = stateRes.data.mode as string;
            setGovernanceMode(
              mode === 'STANDBY' ? 'STANDBY' : mode === 'LIVE' ? 'LIVE' : 'DEMO'
            );
          }
        } finally {
          setIsLoading(false);
          return;
        }
      } finally {
        setIsLoading(false);
      }
    };

    fetchGovernanceMode();
  }, [projectId]);

  const checkPermission = useCallback(
    (action: string, dataType: string): boolean => {
      if (governanceMode === 'STANDBY') return false;
      if (governanceMode === 'DEMO' && dataType === 'phi') return false;
      if (governanceMode === 'LIVE' && action === 'export') {
        return approvalStatus === 'approved';
      }
      return true;
    },
    [governanceMode, approvalStatus]
  );

  const hasAccess = checkPermission('view', 'phi');
  const requiresApproval = governanceMode === 'LIVE';

  const requestApproval = useCallback(
    async (stageId: number, action: string) => {
      try {
        await apiClient.post(`/api/projects/${projectId}/approvals/request`, {
          stageId,
          action,
          reason: 'PHI export requested',
        });
        setApprovalStatus('pending');
        setPendingApprovals((prev) => new Set(prev).add(`${stageId}-${action}`));
      } catch (error) {
        console.error('Failed to request approval:', error);
        throw error;
      }
    },
    [projectId]
  );

  const logAccess = useCallback(
    (stageId: number, action: string, dataType: string) => {
      apiClient
        .post('/api/audit/log', {
          projectId,
          stageId,
          action,
          dataType,
          timestamp: new Date().toISOString(),
          phiAccess: dataType === 'phi',
        })
        .catch((err) => console.error('Audit log failed:', err));
    },
    [projectId]
  );

  return {
    governanceMode,
    isLoading,
    hasAccess,
    requiresApproval,
    approvalStatus,
    requestApproval,
    logAccess,
    checkPermission,
  };
}
