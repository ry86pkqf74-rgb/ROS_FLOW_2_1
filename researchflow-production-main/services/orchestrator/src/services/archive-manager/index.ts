/**
 * Archive Manager Bridge Service
 *
 * Provides project archival primitives for downstream automation.
 * This is a bridge-friendly interface: it does not assume a particular DB
 * or storage provider in this module.
 */

export interface ArchiveProjectInput {
  projectId: string;
  /** Optional reason for audit logs */
  reason?: string;
  /** Optional: who initiated archival */
  requestedBy?: string;
  /** Optional: arbitrary metadata */
  metadata?: Record<string, unknown>;
}

export interface ArchiveProjectResult {
  ok: boolean;
  timestamp: string;
  projectId: string;
  status: 'ARCHIVED' | 'NOOP';
  message: string;
}

export interface RestoreProjectInput {
  projectId: string;
  requestedBy?: string;
}

export interface RestoreProjectResult {
  ok: boolean;
  timestamp: string;
  projectId: string;
  status: 'RESTORED' | 'NOOP';
  message: string;
}

/**
 * Bridge method: archiveProject
 *
 * NOTE: This implementation is a placeholder that provides a stable bridge contract.
 * Wire to the real persistence layer (DB/storage) in a follow-up change.
 */
export async function archiveProject(input: ArchiveProjectInput): Promise<ArchiveProjectResult> {
  if (!input?.projectId) {
    throw new Error('projectId is required');
  }

  return {
    ok: true,
    timestamp: new Date().toISOString(),
    projectId: input.projectId,
    status: 'ARCHIVED',
    message: 'Archive requested (no-op implementation). Integrate with storage/persistence to finalize.',
  };
}

/**
 * Bridge method: restoreProject
 */
export async function restoreProject(input: RestoreProjectInput): Promise<RestoreProjectResult> {
  if (!input?.projectId) {
    throw new Error('projectId is required');
  }

  return {
    ok: true,
    timestamp: new Date().toISOString(),
    projectId: input.projectId,
    status: 'RESTORED',
    message: 'Restore requested (no-op implementation). Integrate with storage/persistence to finalize.',
  };
}

const archiveManagerService = { archiveProject, restoreProject };
export default archiveManagerService;
