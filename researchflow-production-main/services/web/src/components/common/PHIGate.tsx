/**
 * PHIGate - Wrapper component for PHI-sensitive content
 * Enforces governance mode restrictions and audit logging
 */

import React, { useEffect } from 'react';
import { Shield, AlertTriangle, Lock } from 'lucide-react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { usePHIGate } from '@/hooks/usePHIGate';

export type GovernanceMode = 'DEMO' | 'LIVE' | 'STANDBY';

function getBlockReason(
  mode: GovernanceMode,
  act: string,
  type: string
): string {
  if (mode === 'STANDBY')
    return 'System is in standby mode. All PHI operations are suspended.';
  if (mode === 'DEMO' && type === 'phi')
    return 'Real PHI is not allowed in demo mode.';
  if (mode === 'LIVE' && act === 'export')
    return 'Export requires steward approval.';
  return 'Access denied based on current governance policy.';
}

interface PHIGateProps {
  children: React.ReactNode;
  projectId: string;
  stageId: number;
  action: 'view' | 'edit' | 'export' | 'upload';
  dataType?: 'phi' | 'synthetic' | 'aggregated';
  onAccessGranted?: () => void;
  onAccessDenied?: (reason: string) => void;
  fallback?: React.ReactNode;
}

export const PHIGate: React.FC<PHIGateProps> = ({
  children,
  projectId,
  stageId,
  action,
  dataType = 'phi',
  onAccessGranted,
  onAccessDenied,
  fallback,
}) => {
  const {
    governanceMode,
    isLoading,
    checkPermission,
    requiresApproval,
    approvalStatus,
    requestApproval,
    logAccess,
  } = usePHIGate(projectId);

  const hasAccess = checkPermission(action, dataType);

  useEffect(() => {
    if (isLoading) return;
    if (hasAccess) {
      logAccess(stageId, action, dataType);
      onAccessGranted?.();
    } else {
      onAccessDenied?.(getBlockReason(governanceMode, action, dataType));
    }
  }, [
    isLoading,
    hasAccess,
    governanceMode,
    action,
    dataType,
    stageId,
    logAccess,
    onAccessGranted,
    onAccessDenied,
  ]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  if (governanceMode === 'STANDBY') {
    return (
      <Alert variant="destructive" className="m-4">
        <Lock className="h-4 w-4" />
        <AlertTitle>System in Standby Mode</AlertTitle>
        <AlertDescription>
          All PHI operations are currently suspended. Contact your system
          administrator.
        </AlertDescription>
      </Alert>
    );
  }

  if (governanceMode === 'DEMO' && dataType === 'phi') {
    return (
      <Alert variant="destructive" className="m-4">
        <AlertTriangle className="h-4 w-4" />
        <AlertTitle>PHI Not Allowed in Demo Mode</AlertTitle>
        <AlertDescription>
          Real patient data cannot be processed in demo mode. Please use
          synthetic data or switch to live mode.
        </AlertDescription>
        {fallback}
      </Alert>
    );
  }

  if (
    governanceMode === 'LIVE' &&
    action === 'export' &&
    requiresApproval
  ) {
    if (approvalStatus === 'pending') {
      return (
        <Alert className="m-4 border-yellow-500 bg-yellow-50">
          <Shield className="h-4 w-4 text-yellow-600" />
          <AlertTitle>Approval Pending</AlertTitle>
          <AlertDescription>
            Your export request is awaiting steward approval.
          </AlertDescription>
        </Alert>
      );
    }

    if (approvalStatus === 'none') {
      return (
        <Alert className="m-4 border-blue-500 bg-blue-50">
          <Shield className="h-4 w-4 text-blue-600" />
          <AlertTitle>Steward Approval Required</AlertTitle>
          <AlertDescription className="space-y-2">
            <p>Exporting PHI requires approval from a data steward.</p>
            <Button
              size="sm"
              onClick={() => requestApproval(stageId, action)}
            >
              Request Approval
            </Button>
          </AlertDescription>
        </Alert>
      );
    }
  }

  return <>{children}</>;
};

export default PHIGate;
