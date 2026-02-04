/**
 * AlertBadge - Severity indicator component
 * 
 * Displays alert badges with different severity levels.
 * Supports animations and pulse effects for critical alerts.
 * 
 * Linear Issue: ROS-61
 * 
 * @module components/insights/AlertBadge
 */

import React from 'react';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import {
  AlertCircle,
  AlertTriangle,
  Info,
  CheckCircle,
  XCircle,
  Bell,
  Zap,
} from 'lucide-react';

// ============================================
// Types
// ============================================

export type AlertSeverity = 'info' | 'success' | 'warning' | 'error' | 'critical';

export interface AlertBadgeProps {
  /** Severity level of the alert */
  severity: AlertSeverity;
  /** Optional label text */
  label?: string;
  /** Show pulse animation for attention */
  pulse?: boolean;
  /** Show icon */
  showIcon?: boolean;
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Tooltip content */
  tooltip?: string;
  /** Custom class name */
  className?: string;
  /** Click handler */
  onClick?: () => void;
}

// ============================================
// Severity Configurations
// ============================================

const severityConfig = {
  info: {
    icon: Info,
    label: 'Info',
    className: 'bg-blue-100 text-blue-800 border-blue-200 dark:bg-blue-900/30 dark:text-blue-300 dark:border-blue-800',
    pulseColor: 'bg-blue-400',
  },
  success: {
    icon: CheckCircle,
    label: 'Success',
    className: 'bg-green-100 text-green-800 border-green-200 dark:bg-green-900/30 dark:text-green-300 dark:border-green-800',
    pulseColor: 'bg-green-400',
  },
  warning: {
    icon: AlertTriangle,
    label: 'Warning',
    className: 'bg-yellow-100 text-yellow-800 border-yellow-200 dark:bg-yellow-900/30 dark:text-yellow-300 dark:border-yellow-800',
    pulseColor: 'bg-yellow-400',
  },
  error: {
    icon: XCircle,
    label: 'Error',
    className: 'bg-red-100 text-red-800 border-red-200 dark:bg-red-900/30 dark:text-red-300 dark:border-red-800',
    pulseColor: 'bg-red-400',
  },
  critical: {
    icon: AlertCircle,
    label: 'Critical',
    className: 'bg-red-600 text-white border-red-700 dark:bg-red-700 dark:text-white dark:border-red-600',
    pulseColor: 'bg-red-500',
  },
};

const sizeConfig = {
  sm: {
    badge: 'text-xs px-1.5 py-0.5',
    icon: 'h-3 w-3',
    pulse: 'h-1.5 w-1.5',
  },
  md: {
    badge: 'text-sm px-2 py-0.5',
    icon: 'h-4 w-4',
    pulse: 'h-2 w-2',
  },
  lg: {
    badge: 'text-base px-2.5 py-1',
    icon: 'h-5 w-5',
    pulse: 'h-2.5 w-2.5',
  },
};

// ============================================
// Component
// ============================================

export function AlertBadge({
  severity,
  label,
  pulse = false,
  showIcon = true,
  size = 'md',
  tooltip,
  className,
  onClick,
}: AlertBadgeProps) {
  const config = severityConfig[severity];
  const sizes = sizeConfig[size];
  const Icon = config.icon;
  const displayLabel = label || config.label;

  const badgeContent = (
    <Badge
      variant="outline"
      className={cn(
        'inline-flex items-center gap-1 font-medium border transition-colors',
        config.className,
        sizes.badge,
        onClick && 'cursor-pointer hover:opacity-80',
        className
      )}
      onClick={onClick}
    >
      {/* Pulse indicator */}
      {pulse && (
        <span className="relative flex">
          <span
            className={cn(
              'absolute inline-flex rounded-full opacity-75 animate-ping',
              config.pulseColor,
              sizes.pulse
            )}
          />
          <span
            className={cn(
              'relative inline-flex rounded-full',
              config.pulseColor,
              sizes.pulse
            )}
          />
        </span>
      )}
      
      {/* Icon */}
      {showIcon && <Icon className={sizes.icon} />}
      
      {/* Label */}
      {displayLabel}
    </Badge>
  );

  if (tooltip) {
    return (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            {badgeContent}
          </TooltipTrigger>
          <TooltipContent>
            <p>{tooltip}</p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    );
  }

  return badgeContent;
}

// ============================================
// Compound Components
// ============================================

export interface AlertBadgeCountProps {
  severity: AlertSeverity;
  count: number;
  maxCount?: number;
  className?: string;
}

export function AlertBadgeCount({
  severity,
  count,
  maxCount = 99,
  className,
}: AlertBadgeCountProps) {
  const config = severityConfig[severity];
  const displayCount = count > maxCount ? `${maxCount}+` : count;

  if (count === 0) return null;

  return (
    <Badge
      variant="outline"
      className={cn(
        'inline-flex items-center justify-center min-w-[1.5rem] h-6 px-1.5 font-medium border',
        config.className,
        className
      )}
    >
      {displayCount}
    </Badge>
  );
}

export interface AlertSummaryProps {
  alerts: {
    info?: number;
    success?: number;
    warning?: number;
    error?: number;
    critical?: number;
  };
  showZero?: boolean;
  className?: string;
}

export function AlertSummary({ alerts, showZero = false, className }: AlertSummaryProps) {
  const severities: AlertSeverity[] = ['critical', 'error', 'warning', 'info', 'success'];

  return (
    <div className={cn('flex items-center gap-1.5', className)}>
      {severities.map((severity) => {
        const count = alerts[severity] || 0;
        if (!showZero && count === 0) return null;
        
        return (
          <AlertBadgeCount
            key={severity}
            severity={severity}
            count={count}
          />
        );
      })}
    </div>
  );
}

// ============================================
// Notification Badge (for headers/navs)
// ============================================

export interface NotificationBadgeProps {
  count: number;
  maxCount?: number;
  severity?: AlertSeverity;
  className?: string;
}

export function NotificationBadge({
  count,
  maxCount = 9,
  severity = 'error',
  className,
}: NotificationBadgeProps) {
  if (count === 0) return null;

  const config = severityConfig[severity];
  const displayCount = count > maxCount ? `${maxCount}+` : count;

  return (
    <span
      className={cn(
        'absolute -top-1 -right-1 flex items-center justify-center',
        'min-w-[1.125rem] h-[1.125rem] px-1 rounded-full',
        'text-[10px] font-bold',
        config.className,
        className
      )}
    >
      {displayCount}
    </span>
  );
}

// ============================================
// Alert Icon (standalone)
// ============================================

export interface AlertIconProps {
  severity: AlertSeverity;
  size?: 'sm' | 'md' | 'lg';
  pulse?: boolean;
  className?: string;
}

export function AlertIcon({ severity, size = 'md', pulse = false, className }: AlertIconProps) {
  const config = severityConfig[severity];
  const sizes = sizeConfig[size];
  const Icon = config.icon;

  const iconColors = {
    info: 'text-blue-500',
    success: 'text-green-500',
    warning: 'text-yellow-500',
    error: 'text-red-500',
    critical: 'text-red-600',
  };

  return (
    <span className={cn('relative inline-flex', className)}>
      {pulse && (
        <span
          className={cn(
            'absolute inset-0 rounded-full opacity-75 animate-ping',
            config.pulseColor
          )}
        />
      )}
      <Icon className={cn(sizes.icon, iconColors[severity])} />
    </span>
  );
}

export default AlertBadge;
