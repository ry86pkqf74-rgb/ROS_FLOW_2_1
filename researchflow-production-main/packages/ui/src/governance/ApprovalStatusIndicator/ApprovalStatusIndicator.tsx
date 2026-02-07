import { 
  Clock, 
  CheckCircle2, 
  XCircle, 
  AlertCircle, 
  User,
  Calendar
} from 'lucide-react';
import * as React from 'react';

import { cn } from '../../utils/cn';

// figma: fileKey=PENDING nodeId=PENDING
// Component contract: RF/Governance/ApprovalStatusIndicator

export type ApprovalStatus = 'pending' | 'approved' | 'denied' | 'expired' | 'revoked';

export interface ApprovalDetails {
  /** Current approval status */
  status: ApprovalStatus;
  /** Who requested approval */
  requestedBy?: string;
  /** When approval was requested */
  requestedAt?: Date;
  /** Who reviewed (approved/denied) */
  reviewedBy?: string;
  /** When review occurred */
  reviewedAt?: Date;
  /** Reason for denial or revocation */
  reason?: string;
  /** When approval expires */
  expiresAt?: Date;
}

export interface ApprovalStatusIndicatorProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Approval details */
  approval: ApprovalDetails;
  /** Display variant */
  variant?: 'badge' | 'card' | 'inline';
  /** Show full details */
  showDetails?: boolean;
  /** Compact mode (badge only) */
  compact?: boolean;
}

const statusConfig = {
  pending: {
    icon: Clock,
    label: 'Pending Approval',
    color: 'text-[var(--semantic-status-warning-icon)]',
    bgColor: 'bg-[var(--semantic-status-warning-bg)]',
    borderColor: 'border-[var(--semantic-status-warning-border)]',
    textColor: 'text-[var(--semantic-status-warning-text)]',
  },
  approved: {
    icon: CheckCircle2,
    label: 'Approved',
    color: 'text-[var(--semantic-status-success-icon)]',
    bgColor: 'bg-[var(--semantic-status-success-bg)]',
    borderColor: 'border-[var(--semantic-status-success-border)]',
    textColor: 'text-[var(--semantic-status-success-text)]',
  },
  denied: {
    icon: XCircle,
    label: 'Denied',
    color: 'text-[var(--semantic-status-error-icon)]',
    bgColor: 'bg-[var(--semantic-status-error-bg)]',
    borderColor: 'border-[var(--semantic-status-error-border)]',
    textColor: 'text-[var(--semantic-status-error-text)]',
  },
  expired: {
    icon: AlertCircle,
    label: 'Expired',
    color: 'text-[var(--semantic-text-muted)]',
    bgColor: 'bg-[var(--semantic-bg-muted)]',
    borderColor: 'border-[var(--semantic-border-default)]',
    textColor: 'text-[var(--semantic-text-secondary)]',
  },
  revoked: {
    icon: XCircle,
    label: 'Revoked',
    color: 'text-[var(--semantic-status-error-icon)]',
    bgColor: 'bg-[var(--semantic-status-error-bg)]',
    borderColor: 'border-[var(--semantic-status-error-border)]',
    textColor: 'text-[var(--semantic-status-error-text)]',
  },
};

const formatDate = (date: Date) => {
  return new Intl.DateTimeFormat('en-US', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date);
};

const formatRelativeTime = (date: Date) => {
  const now = new Date();
  const diff = date.getTime() - now.getTime();
  const diffDays = Math.ceil(diff / (1000 * 60 * 60 * 24));

  if (diffDays < 0) return 'Expired';
  if (diffDays === 0) return 'Expires today';
  if (diffDays === 1) return 'Expires tomorrow';
  return `Expires in ${diffDays} days`;
};

export const ApprovalStatusIndicator = React.forwardRef<HTMLDivElement, ApprovalStatusIndicatorProps>(
  (
    {
      className,
      approval,
      variant = 'badge',
      showDetails = false,
      compact = false,
      ...props
    },
    ref
  ) => {
    const config = statusConfig[approval.status];
    const Icon = config.icon;

    // Badge variant - simple status indicator
    if (variant === 'badge') {
      return (
        <span
          ref={ref as React.Ref<HTMLSpanElement>}
          className={cn(
            'inline-flex items-center gap-1.5',
            'font-medium rounded-full',
            'border',
            config.bgColor,
            config.borderColor,
            config.textColor,
            compact ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-sm',
            className
          )}
          {...props}
        >
          <Icon className={cn(compact ? 'h-3 w-3' : 'h-4 w-4', config.color)} />
          {config.label}
        </span>
      );
    }

    // Inline variant - minimal inline display
    if (variant === 'inline') {
      return (
        <span
          ref={ref as React.Ref<HTMLSpanElement>}
          className={cn(
            'inline-flex items-center gap-1.5',
            'text-sm',
            config.textColor,
            className
          )}
          {...props}
        >
          <Icon className={cn('h-4 w-4', config.color)} />
          <span className="font-medium">{config.label}</span>
          {approval.reviewedBy && (
            <span className="text-[var(--semantic-text-muted)]">
              by {approval.reviewedBy}
            </span>
          )}
        </span>
      );
    }

    // Card variant - full details display
    return (
      <div
        ref={ref}
        className={cn(
          'rounded-[var(--radius-lg)]',
          'border p-4',
          config.bgColor,
          config.borderColor,
          className
        )}
        {...props}
      >
        {/* Header */}
        <div className="flex items-center gap-2 mb-3">
          <Icon className={cn('h-5 w-5', config.color)} />
          <span className={cn('font-semibold', config.textColor)}>
            {config.label}
          </span>
        </div>

        {/* Details */}
        {showDetails && (
          <div className="space-y-2 text-sm">
            {/* Requested info */}
            {approval.requestedBy && (
              <div className="flex items-center gap-2 text-[var(--semantic-text-secondary)]">
                <User className="h-4 w-4 text-[var(--semantic-text-muted)]" />
                <span>Requested by {approval.requestedBy}</span>
                {approval.requestedAt && (
                  <span className="text-[var(--semantic-text-muted)]">
                    • {formatDate(approval.requestedAt)}
                  </span>
                )}
              </div>
            )}

            {/* Reviewed info */}
            {approval.reviewedBy && (
              <div className="flex items-center gap-2 text-[var(--semantic-text-secondary)]">
                <User className="h-4 w-4 text-[var(--semantic-text-muted)]" />
                <span>
                  {approval.status === 'approved' ? 'Approved' : 'Reviewed'} by {approval.reviewedBy}
                </span>
                {approval.reviewedAt && (
                  <span className="text-[var(--semantic-text-muted)]">
                    • {formatDate(approval.reviewedAt)}
                  </span>
                )}
              </div>
            )}

            {/* Expiration info */}
            {approval.expiresAt && approval.status === 'approved' && (
              <div className="flex items-center gap-2 text-[var(--semantic-text-secondary)]">
                <Calendar className="h-4 w-4 text-[var(--semantic-text-muted)]" />
                <span>{formatRelativeTime(approval.expiresAt)}</span>
                <span className="text-[var(--semantic-text-muted)]">
                  • {formatDate(approval.expiresAt)}
                </span>
              </div>
            )}

            {/* Denial/revocation reason */}
            {approval.reason && (approval.status === 'denied' || approval.status === 'revoked') && (
              <div className={cn('mt-2 p-2 rounded-md', 'bg-white/50')}>
                <span className="font-medium">Reason: </span>
                {approval.reason}
              </div>
            )}
          </div>
        )}
      </div>
    );
  }
);

ApprovalStatusIndicator.displayName = 'ApprovalStatusIndicator';

export default ApprovalStatusIndicator;
