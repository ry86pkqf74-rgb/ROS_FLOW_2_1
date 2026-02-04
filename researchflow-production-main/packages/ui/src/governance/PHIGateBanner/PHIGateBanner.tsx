import * as React from 'react';
import { ShieldAlert, ShieldCheck, ShieldQuestion, Lock, Unlock } from 'lucide-react';
import { cn } from '../../utils/cn';

// figma: fileKey=PENDING nodeId=PENDING
// Component contract: RF/Governance/PHIGateBanner

export type PHIStatus = 'blocked' | 'requires-approval' | 'approved' | 'demo-mode';

export interface PHIGateBannerProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Current PHI access status */
  status: PHIStatus;
  /** Name of the approving steward (for approved status) */
  stewardName?: string;
  /** Timestamp of approval */
  approvalTimestamp?: Date;
  /** Current governance mode */
  governanceMode?: 'DEMO' | 'LIVE';
  /** Callback to request access */
  onRequestAccess?: () => void;
  /** Compact display mode */
  compact?: boolean;
}

const statusConfig = {
  'blocked': {
    icon: ShieldAlert,
    title: 'PHI Access Blocked',
    description: 'This content contains Protected Health Information and cannot be accessed in the current context.',
    containerClass: [
      'bg-[var(--semantic-status-error-bg)]',
      'border-[var(--semantic-status-error-border)]',
    ],
    iconClass: 'text-[var(--semantic-governance-phi-blocked)]',
    textClass: 'text-[var(--semantic-status-error-text)]',
  },
  'requires-approval': {
    icon: ShieldQuestion,
    title: 'PHI Access Requires Approval',
    description: 'This content contains PHI. Data steward approval is required before access can be granted.',
    containerClass: [
      'bg-[var(--semantic-status-warning-bg)]',
      'border-[var(--semantic-status-warning-border)]',
    ],
    iconClass: 'text-[var(--semantic-governance-phi-warning)]',
    textClass: 'text-[var(--semantic-status-warning-text)]',
  },
  'approved': {
    icon: ShieldCheck,
    title: 'PHI Access Approved',
    description: 'Access to this PHI has been authorized.',
    containerClass: [
      'bg-[var(--semantic-status-success-bg)]',
      'border-[var(--semantic-status-success-border)]',
    ],
    iconClass: 'text-[var(--semantic-governance-phi-safe)]',
    textClass: 'text-[var(--semantic-status-success-text)]',
  },
  'demo-mode': {
    icon: Lock,
    title: 'Demo Mode - PHI Blocked',
    description: 'The system is running in DEMO mode. PHI access is disabled. Switch to LIVE mode for PHI access.',
    containerClass: [
      'bg-[var(--semantic-governance-demo-bg)]',
      'border-[var(--semantic-governance-demo-border)]',
    ],
    iconClass: 'text-[var(--semantic-governance-demo-badge)]',
    textClass: 'text-[var(--semantic-governance-demo-text)]',
  },
};

export const PHIGateBanner = React.forwardRef<HTMLDivElement, PHIGateBannerProps>(
  (
    {
      className,
      status,
      stewardName,
      approvalTimestamp,
      governanceMode,
      onRequestAccess,
      compact = false,
      ...props
    },
    ref
  ) => {
    const config = statusConfig[status];
    const Icon = config.icon;

    const formatTimestamp = (date: Date) => {
      return new Intl.DateTimeFormat('en-US', {
        dateStyle: 'medium',
        timeStyle: 'short',
      }).format(date);
    };

    return (
      <div
        ref={ref}
        role="alert"
        aria-live="polite"
        className={cn(
          // Base styles
          'relative',
          'border rounded-[var(--radius-lg)]',
          compact ? 'p-3' : 'p-4',
          // Status styles
          config.containerClass,
          className
        )}
        {...props}
      >
        <div className={cn('flex gap-3', compact && 'items-center')}>
          {/* Icon */}
          <div className={cn('flex-shrink-0', config.iconClass)}>
            <Icon className={cn(compact ? 'h-5 w-5' : 'h-6 w-6')} />
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <div className={cn('flex items-center gap-2', !compact && 'mb-1')}>
              <h4 className={cn('font-semibold', config.textClass, compact ? 'text-sm' : 'text-base')}>
                {config.title}
              </h4>
              
              {/* Governance mode badge */}
              {governanceMode && (
                <span
                  className={cn(
                    'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium',
                    governanceMode === 'DEMO'
                      ? 'bg-[var(--semantic-governance-demo-badge)] text-white'
                      : 'bg-[var(--semantic-governance-live-badge)] text-white'
                  )}
                >
                  {governanceMode === 'DEMO' ? <Lock className="h-3 w-3" /> : <Unlock className="h-3 w-3" />}
                  {governanceMode}
                </span>
              )}
            </div>

            {!compact && (
              <p className={cn('text-sm', config.textClass, 'opacity-90')}>
                {config.description}
              </p>
            )}

            {/* Approval details */}
            {status === 'approved' && (stewardName || approvalTimestamp) && !compact && (
              <div className={cn('mt-2 text-xs', config.textClass, 'opacity-75')}>
                {stewardName && <span>Approved by: {stewardName}</span>}
                {stewardName && approvalTimestamp && <span className="mx-2">•</span>}
                {approvalTimestamp && <span>{formatTimestamp(approvalTimestamp)}</span>}
              </div>
            )}

            {/* Request access button */}
            {status === 'requires-approval' && onRequestAccess && !compact && (
              <button
                onClick={onRequestAccess}
                className={cn(
                  'mt-3 inline-flex items-center gap-2',
                  'px-3 py-1.5 rounded-md',
                  'text-sm font-medium',
                  'bg-[var(--semantic-status-warning-icon)] text-white',
                  'hover:opacity-90 transition-opacity',
                  'focus:outline-none focus:ring-2 focus:ring-offset-2'
                )}
              >
                Request Access
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }
);

PHIGateBanner.displayName = 'PHIGateBanner';

export default PHIGateBanner;
