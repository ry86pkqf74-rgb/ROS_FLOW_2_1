import { AlertCircle, CheckCircle2, Eye, EyeOff } from 'lucide-react';
import * as React from 'react';

import { cn } from '../../utils/cn';

// figma: fileKey=PENDING nodeId=PENDING
// Component contract: RF/Input

export interface InputProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'size'> {
  /** Label for the input */
  label?: string;
  /** Helper text below input */
  helperText?: string;
  /** Error message (shows error state when present) */
  error?: string;
  /** Success state */
  success?: boolean;
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Left icon/element */
  leftElement?: React.ReactNode;
  /** Right icon/element */
  rightElement?: React.ReactNode;
  /** Show password toggle for password inputs */
  showPasswordToggle?: boolean;
  /** Full width */
  fullWidth?: boolean;
}

const sizeStyles = {
  sm: {
    input: 'h-8 text-sm px-3',
    label: 'text-xs',
    helper: 'text-xs',
  },
  md: {
    input: 'h-10 text-sm px-3',
    label: 'text-sm',
    helper: 'text-xs',
  },
  lg: {
    input: 'h-12 text-base px-4',
    label: 'text-base',
    helper: 'text-sm',
  },
};

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  (
    {
      className,
      label,
      helperText,
      error,
      success,
      size = 'md',
      leftElement,
      rightElement,
      showPasswordToggle,
      fullWidth = false,
      type,
      disabled,
      id,
      ...props
    },
    ref
  ) => {
    const [showPassword, setShowPassword] = React.useState(false);
    const inputId = id || React.useId();
    const helperId = `${inputId}-helper`;
    const errorId = `${inputId}-error`;

    const isPassword = type === 'password';
    const inputType = isPassword && showPassword ? 'text' : type;

    const hasError = Boolean(error);
    const hasRightElement = rightElement || (isPassword && showPasswordToggle) || hasError || success;

    const styles = sizeStyles[size];

    return (
      <div className={cn('flex flex-col gap-1.5', fullWidth && 'w-full')}>
        {/* Label */}
        {label && (
          <label
            htmlFor={inputId}
            className={cn(
              'font-medium',
              'text-[var(--semantic-text-primary)]',
              styles.label,
              disabled && 'opacity-50'
            )}
          >
            {label}
          </label>
        )}

        {/* Input wrapper */}
        <div className="relative">
          {/* Left element */}
          {leftElement && (
            <div className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--semantic-text-muted)]">
              {leftElement}
            </div>
          )}

          {/* Input */}
          <input
            ref={ref}
            id={inputId}
            type={inputType}
            disabled={disabled}
            aria-invalid={hasError}
            aria-describedby={cn(
              helperText && helperId,
              hasError && errorId
            ) || undefined}
            className={cn(
              // Base styles
              'w-full',
              'rounded-[var(--radius-md)]',
              'border',
              'bg-[var(--semantic-bg-surface)]',
              'text-[var(--semantic-text-primary)]',
              'placeholder:text-[var(--semantic-text-placeholder)]',
              'transition-colors duration-150',
              'focus:outline-none focus:ring-2 focus:ring-offset-0',
              // Size
              styles.input,
              // Padding adjustments for elements
              leftElement && 'pl-10',
              hasRightElement && 'pr-10',
              // States
              !hasError && !success && [
                'border-[var(--semantic-border-default)]',
                'hover:border-[var(--semantic-border-strong)]',
                'focus:border-[var(--semantic-border-focus)]',
                'focus:ring-[var(--semantic-border-focus)]/20',
              ],
              hasError && [
                'border-[var(--semantic-status-error-icon)]',
                'focus:border-[var(--semantic-status-error-icon)]',
                'focus:ring-[var(--semantic-status-error-icon)]/20',
              ],
              success && !hasError && [
                'border-[var(--semantic-status-success-icon)]',
                'focus:border-[var(--semantic-status-success-icon)]',
                'focus:ring-[var(--semantic-status-success-icon)]/20',
              ],
              // Disabled
              disabled && 'opacity-50 cursor-not-allowed bg-[var(--semantic-bg-muted)]',
              className
            )}
            {...props}
          />

          {/* Right element / Status icons */}
          <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-2">
            {hasError && (
              <AlertCircle className="h-4 w-4 text-[var(--semantic-status-error-icon)]" />
            )}
            {success && !hasError && (
              <CheckCircle2 className="h-4 w-4 text-[var(--semantic-status-success-icon)]" />
            )}
            {isPassword && showPasswordToggle && (
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="text-[var(--semantic-text-muted)] hover:text-[var(--semantic-text-secondary)] focus:outline-none"
                tabIndex={-1}
                aria-label={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            )}
            {rightElement && !hasError && !success && rightElement}
          </div>
        </div>

        {/* Helper text or Error */}
        {(helperText || error) && (
          <p
            id={hasError ? errorId : helperId}
            className={cn(
              styles.helper,
              hasError
                ? 'text-[var(--semantic-status-error-text)]'
                : 'text-[var(--semantic-text-muted)]'
            )}
          >
            {error || helperText}
          </p>
        )}
      </div>
    );
  }
);

Input.displayName = 'Input';

export default Input;
