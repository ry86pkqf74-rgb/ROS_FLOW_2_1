/**
 * PHIBanner - Display current governance mode status
 */

import React from 'react';
import { Shield, FlaskConical, Activity, Pause } from 'lucide-react';
import { cn } from '@/lib/utils';

type GovernanceMode = 'DEMO' | 'LIVE' | 'STANDBY';

interface PHIBannerProps {
  mode: GovernanceMode;
  className?: string;
}

const modeConfig = {
  DEMO: {
    icon: FlaskConical,
    label: 'Demo Mode',
    description: 'Using synthetic data only',
    bgColor: 'bg-blue-100 border-blue-300',
    textColor: 'text-blue-800',
    iconColor: 'text-blue-600',
  },
  LIVE: {
    icon: Activity,
    label: 'Live Mode',
    description: 'PHI access enabled with audit logging',
    bgColor: 'bg-green-100 border-green-300',
    textColor: 'text-green-800',
    iconColor: 'text-green-600',
  },
  STANDBY: {
    icon: Pause,
    label: 'Standby Mode',
    description: 'All PHI operations suspended',
    bgColor: 'bg-red-100 border-red-300',
    textColor: 'text-red-800',
    iconColor: 'text-red-600',
  },
};

export const PHIBanner: React.FC<PHIBannerProps> = ({ mode, className }) => {
  const config = modeConfig[mode];
  const Icon = config.icon;

  return (
    <div
      className={cn(
        'flex items-center gap-3 px-4 py-2 border rounded-lg',
        config.bgColor,
        className
      )}
    >
      <Icon className={cn('h-5 w-5', config.iconColor)} />
      <div className="flex-1">
        <div className={cn('font-medium text-sm', config.textColor)}>
          {config.label}
        </div>
        <div className={cn('text-xs opacity-80', config.textColor)}>
          {config.description}
        </div>
      </div>
      <Shield className={cn('h-4 w-4', config.iconColor)} />
    </div>
  );
};

export default PHIBanner;
