import { Cpu, Zap, Sparkles } from 'lucide-react';
import * as React from 'react';

import { cn } from '../../utils/cn';

// figma: fileKey=PENDING nodeId=PENDING
// Component contract: RF/Governance/ModelTierBadge

export type ModelTier = 'NANO' | 'MINI' | 'FRONTIER';

export interface ModelTierBadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  /** Model tier level */
  tier: ModelTier;
  /** Show tier description */
  showDescription?: boolean;
  /** Size of the badge */
  size?: 'sm' | 'md' | 'lg';
  /** Show processing indicator */
  isProcessing?: boolean;
}

const tierConfig = {
  NANO: {
    icon: Cpu,
    label: 'Nano',
    description: 'Fast, cost-efficient processing',
    color: 'bg-[var(--semantic-governance-modeltier-nano)]',
    textColor: 'text-white',
    bgLight: 'bg-[var(--color-base-gray-100)]',
    textDark: 'text-[var(--color-base-gray-700)]',
  },
  MINI: {
    icon: Zap,
    label: 'Mini',
    description: 'Balanced performance and accuracy',
    color: 'bg-[var(--semantic-governance-modeltier-mini)]',
    textColor: 'text-white',
    bgLight: 'bg-[var(--color-base-blue-100)]',
    textDark: 'text-[var(--color-base-blue-700)]',
  },
  FRONTIER: {
    icon: Sparkles,
    label: 'Frontier',
    description: 'Maximum capability for complex tasks',
    color: 'bg-[var(--semantic-governance-modeltier-frontier)]',
    textColor: 'text-white',
    bgLight: 'bg-[var(--color-base-purple-100)]',
    textDark: 'text-[var(--color-base-purple-700)]',
  },
};

const sizeStyles = {
  sm: {
    badge: 'px-2 py-0.5 text-xs gap-1',
    icon: 'h-3 w-3',
  },
  md: {
    badge: 'px-2.5 py-1 text-sm gap-1.5',
    icon: 'h-4 w-4',
  },
  lg: {
    badge: 'px-3 py-1.5 text-base gap-2',
    icon: 'h-5 w-5',
  },
};

export const ModelTierBadge = React.forwardRef<HTMLSpanElement, ModelTierBadgeProps>(
  (
    {
      className,
      tier,
      showDescription = false,
      size = 'md',
      isProcessing = false,
      ...props
    },
    ref
  ) => {
    const config = tierConfig[tier];
    const Icon = config.icon;
    const sizeStyle = sizeStyles[size];

    if (showDescription) {
      return (
        <div
          className={cn(
            'inline-flex items-start gap-3 p-3',
            'rounded-[var(--radius-lg)]',
            config.bgLight,
            className
          )}
        >
          <span
            className={cn(
              'flex items-center justify-center',
              'w-8 h-8 rounded-full',
              config.color,
              config.textColor
            )}
          >
            <Icon className="h-4 w-4" />
          </span>
          <div>
            <div className={cn('font-semibold', config.textDark)}>
              {config.label} Tier
            </div>
            <div className={cn('text-sm opacity-75', config.textDark)}>
              {config.description}
            </div>
          </div>
        </div>
      );
    }

    return (
      <span
        ref={ref}
        className={cn(
          'inline-flex items-center',
          'font-medium rounded-full',
          config.color,
          config.textColor,
          sizeStyle.badge,
          isProcessing && 'animate-pulse',
          className
        )}
        {...props}
      >
        <Icon className={cn(sizeStyle.icon, isProcessing && 'animate-spin')} />
        {config.label}
      </span>
    );
  }
);

ModelTierBadge.displayName = 'ModelTierBadge';

export default ModelTierBadge;
