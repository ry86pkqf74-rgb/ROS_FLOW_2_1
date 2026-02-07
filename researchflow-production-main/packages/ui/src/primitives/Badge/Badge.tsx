import * as React from 'react';

import { cn } from '../../utils/cn';

// figma: fileKey=PENDING nodeId=PENDING
// Component contract: RF/Badge

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  /** Visual style variant */
  variant?: 'default' | 'secondary' | 'success' | 'warning' | 'error' | 'info';
  /** Size of the badge */
  size?: 'sm' | 'md';
  /** Optional dot indicator */
  dot?: boolean;
  /** Pulsing animation for active states */
  pulse?: boolean;
}

const variantStyles = {
  default: [
    'bg-[var(--color-base-gray-100)]',
    'text-[var(--color-base-gray-700)]',
    'border-[var(--color-base-gray-200)]',
  ],
  secondary: [
    'bg-[var(--color-base-primary-100)]',
    'text-[var(--color-base-primary-700)]',
    'border-[var(--color-base-primary-200)]',
  ],
  success: [
    'bg-[var(--semantic-status-success-bg)]',
    'text-[var(--semantic-status-success-text)]',
    'border-[var(--semantic-status-success-border)]',
  ],
  warning: [
    'bg-[var(--semantic-status-warning-bg)]',
    'text-[var(--semantic-status-warning-text)]',
    'border-[var(--semantic-status-warning-border)]',
  ],
  error: [
    'bg-[var(--semantic-status-error-bg)]',
    'text-[var(--semantic-status-error-text)]',
    'border-[var(--semantic-status-error-border)]',
  ],
  info: [
    'bg-[var(--semantic-status-info-bg)]',
    'text-[var(--semantic-status-info-text)]',
    'border-[var(--semantic-status-info-border)]',
  ],
};

const dotColors = {
  default: 'bg-[var(--color-base-gray-500)]',
  secondary: 'bg-[var(--color-base-primary-500)]',
  success: 'bg-[var(--semantic-status-success-icon)]',
  warning: 'bg-[var(--semantic-status-warning-icon)]',
  error: 'bg-[var(--semantic-status-error-icon)]',
  info: 'bg-[var(--semantic-status-info-icon)]',
};

const sizeStyles = {
  sm: 'px-2 py-0.5 text-xs',
  md: 'px-2.5 py-1 text-sm',
};

export const Badge = React.forwardRef<HTMLSpanElement, BadgeProps>(
  (
    {
      className,
      variant = 'default',
      size = 'sm',
      dot = false,
      pulse = false,
      children,
      ...props
    },
    ref
  ) => {
    return (
      <span
        ref={ref}
        className={cn(
          // Base styles
          'inline-flex items-center gap-1.5',
          'font-medium',
          'rounded-full',
          'border',
          // Variant styles
          variantStyles[variant],
          // Size styles
          sizeStyles[size],
          className
        )}
        {...props}
      >
        {dot && (
          <span className="relative flex h-2 w-2">
            {pulse && (
              <span
                className={cn(
                  'absolute inline-flex h-full w-full animate-ping rounded-full opacity-75',
                  dotColors[variant]
                )}
              />
            )}
            <span
              className={cn(
                'relative inline-flex h-2 w-2 rounded-full',
                dotColors[variant]
              )}
            />
          </span>
        )}
        {children}
      </span>
    );
  }
);

Badge.displayName = 'Badge';

export default Badge;
