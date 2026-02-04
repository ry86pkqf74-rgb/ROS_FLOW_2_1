import * as React from 'react';
import { Loader2 } from 'lucide-react';
import { cn } from '../../utils/cn';

// figma: fileKey=PENDING nodeId=PENDING
// Component contract: RF/Button

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  /** Visual style variant */
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'destructive';
  /** Size of the button */
  size?: 'sm' | 'md' | 'lg';
  /** Show loading spinner */
  isLoading?: boolean;
  /** Text shown during loading state */
  loadingText?: string;
  /** Icon to show before children */
  leftIcon?: React.ReactNode;
  /** Icon to show after children */
  rightIcon?: React.ReactNode;
  /** Full width button */
  fullWidth?: boolean;
}

const variantStyles = {
  primary: [
    'bg-[var(--semantic-interactive-primary-default)]',
    'text-white',
    'hover:bg-[var(--semantic-interactive-primary-hover)]',
    'active:bg-[var(--semantic-interactive-primary-active)]',
    'disabled:bg-[var(--semantic-interactive-primary-disabled)]',
    'focus-visible:ring-2 focus-visible:ring-[var(--semantic-interactive-primary-default)] focus-visible:ring-offset-2',
  ],
  secondary: [
    'bg-[var(--semantic-interactive-secondary-default)]',
    'text-[var(--semantic-text-primary)]',
    'hover:bg-[var(--semantic-interactive-secondary-hover)]',
    'active:bg-[var(--semantic-interactive-secondary-active)]',
    'disabled:bg-[var(--semantic-interactive-secondary-disabled)]',
    'border border-[var(--semantic-border-default)]',
  ],
  outline: [
    'bg-transparent',
    'text-[var(--semantic-text-primary)]',
    'border border-[var(--semantic-border-strong)]',
    'hover:bg-[var(--semantic-bg-surface-hover)]',
    'active:bg-[var(--semantic-interactive-secondary-active)]',
  ],
  ghost: [
    'bg-transparent',
    'text-[var(--semantic-text-primary)]',
    'hover:bg-[var(--semantic-bg-surface-hover)]',
    'active:bg-[var(--semantic-interactive-secondary-active)]',
  ],
  destructive: [
    'bg-[var(--semantic-interactive-destructive-default)]',
    'text-white',
    'hover:bg-[var(--semantic-interactive-destructive-hover)]',
    'active:bg-[var(--semantic-interactive-destructive-active)]',
    'disabled:bg-[var(--semantic-interactive-destructive-disabled)]',
    'focus-visible:ring-2 focus-visible:ring-[var(--semantic-interactive-destructive-default)] focus-visible:ring-offset-2',
  ],
};

const sizeStyles = {
  sm: [
    'h-8',
    'px-3',
    'text-sm',
    'rounded-[var(--radius-md)]',
    'gap-1.5',
  ],
  md: [
    'h-10',
    'px-4',
    'text-sm',
    'rounded-[var(--radius-md)]',
    'gap-2',
  ],
  lg: [
    'h-12',
    'px-6',
    'text-base',
    'rounded-[var(--radius-lg)]',
    'gap-2',
  ],
};

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant = 'primary',
      size = 'md',
      isLoading = false,
      loadingText,
      leftIcon,
      rightIcon,
      fullWidth = false,
      disabled,
      children,
      ...props
    },
    ref
  ) => {
    return (
      <button
        ref={ref}
        className={cn(
          // Base styles
          'inline-flex items-center justify-center',
          'font-medium',
          'transition-colors duration-150',
          'focus-visible:outline-none',
          'disabled:pointer-events-none disabled:opacity-50',
          // Variant styles
          variantStyles[variant],
          // Size styles
          sizeStyles[size],
          // Full width
          fullWidth && 'w-full',
          className
        )}
        disabled={disabled || isLoading}
        {...props}
      >
        {isLoading && (
          <Loader2 className="h-4 w-4 animate-spin" />
        )}
        {!isLoading && leftIcon}
        {isLoading && loadingText ? loadingText : children}
        {!isLoading && rightIcon}
      </button>
    );
  }
);

Button.displayName = 'Button';

export default Button;
