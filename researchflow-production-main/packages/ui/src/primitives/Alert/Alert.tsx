import * as React from 'react';
import { AlertCircle, CheckCircle2, Info, AlertTriangle, X } from 'lucide-react';
import { cn } from '../../utils/cn';

// figma: fileKey=PENDING nodeId=PENDING
// Component contract: RF/Alert

export interface AlertProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Visual style variant */
  variant?: 'info' | 'success' | 'warning' | 'error';
  /** Alert title */
  title?: string;
  /** Allow dismissing the alert */
  dismissible?: boolean;
  /** Callback when dismissed */
  onDismiss?: () => void;
  /** Icon override */
  icon?: React.ReactNode;
}

const variantStyles = {
  info: {
    container: [
      'bg-[var(--semantic-status-info-bg)]',
      'border-[var(--semantic-status-info-border)]',
      'text-[var(--semantic-status-info-text)]',
    ],
    icon: 'text-[var(--semantic-status-info-icon)]',
    IconComponent: Info,
  },
  success: {
    container: [
      'bg-[var(--semantic-status-success-bg)]',
      'border-[var(--semantic-status-success-border)]',
      'text-[var(--semantic-status-success-text)]',
    ],
    icon: 'text-[var(--semantic-status-success-icon)]',
    IconComponent: CheckCircle2,
  },
  warning: {
    container: [
      'bg-[var(--semantic-status-warning-bg)]',
      'border-[var(--semantic-status-warning-border)]',
      'text-[var(--semantic-status-warning-text)]',
    ],
    icon: 'text-[var(--semantic-status-warning-icon)]',
    IconComponent: AlertTriangle,
  },
  error: {
    container: [
      'bg-[var(--semantic-status-error-bg)]',
      'border-[var(--semantic-status-error-border)]',
      'text-[var(--semantic-status-error-text)]',
    ],
    icon: 'text-[var(--semantic-status-error-icon)]',
    IconComponent: AlertCircle,
  },
};

export const Alert = React.forwardRef<HTMLDivElement, AlertProps>(
  (
    {
      className,
      variant = 'info',
      title,
      dismissible = false,
      onDismiss,
      icon,
      children,
      ...props
    },
    ref
  ) => {
    const { container, icon: iconColor, IconComponent } = variantStyles[variant];

    return (
      <div
        ref={ref}
        role="alert"
        className={cn(
          // Base styles
          'relative flex gap-3',
          'p-4',
          'border rounded-[var(--radius-lg)]',
          // Variant styles
          container,
          className
        )}
        {...props}
      >
        {/* Icon */}
        <div className={cn('flex-shrink-0', iconColor)}>
          {icon || <IconComponent className="h-5 w-5" />}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {title && (
            <h5 className="font-medium mb-1">{title}</h5>
          )}
          <div className="text-sm">{children}</div>
        </div>

        {/* Dismiss button */}
        {dismissible && (
          <button
            type="button"
            onClick={onDismiss}
            className={cn(
              'flex-shrink-0',
              'p-1 -m-1',
              'rounded-md',
              'opacity-70 hover:opacity-100',
              'transition-opacity',
              'focus:outline-none focus:ring-2 focus:ring-offset-2',
              iconColor
            )}
            aria-label="Dismiss"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>
    );
  }
);

Alert.displayName = 'Alert';

export default Alert;
