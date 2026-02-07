import * as React from 'react';

import { cn } from '../../utils/cn';

// figma: fileKey=PENDING nodeId=PENDING
// Component contract: RF/Tabs

export interface Tab {
  /** Unique identifier */
  id: string;
  /** Tab label */
  label: string;
  /** Optional icon */
  icon?: React.ReactNode;
  /** Disabled state */
  disabled?: boolean;
  /** Badge/count to show */
  badge?: React.ReactNode;
}

export interface TabsProps {
  /** Tab definitions */
  tabs: Tab[];
  /** Currently active tab ID */
  activeTab: string;
  /** Tab change handler */
  onChange: (tabId: string) => void;
  /** Tab style variant */
  variant?: 'underline' | 'pills' | 'enclosed';
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Full width tabs */
  fullWidth?: boolean;
  /** Additional class for the tab list */
  className?: string;
  /** Accessible label for the tab list */
  ariaLabel?: string;
}

export interface TabPanelProps {
  /** Tab ID this panel belongs to */
  tabId: string;
  /** Currently active tab ID */
  activeTab: string;
  /** Panel content */
  children: React.ReactNode;
  /** Additional class */
  className?: string;
}

const sizeStyles = {
  sm: {
    tab: 'px-3 py-1.5 text-sm',
    icon: 'h-4 w-4',
  },
  md: {
    tab: 'px-4 py-2 text-sm',
    icon: 'h-4 w-4',
  },
  lg: {
    tab: 'px-5 py-2.5 text-base',
    icon: 'h-5 w-5',
  },
};

export const Tabs: React.FC<TabsProps> = ({
  tabs,
  activeTab,
  onChange,
  variant = 'underline',
  size = 'md',
  fullWidth = false,
  className,
  ariaLabel = 'Tabs',
}) => {
  const tabRefs = React.useRef<Map<string, HTMLButtonElement>>(new Map());
  const styles = sizeStyles[size];

  const handleKeyDown = (event: React.KeyboardEvent, currentIndex: number) => {
    const enabledTabs = tabs.filter(t => !t.disabled);
    const currentEnabledIndex = enabledTabs.findIndex(t => t.id === tabs[currentIndex].id);

    let nextIndex: number | null = null;

    switch (event.key) {
      case 'ArrowLeft':
        nextIndex = currentEnabledIndex > 0 
          ? currentEnabledIndex - 1 
          : enabledTabs.length - 1;
        break;
      case 'ArrowRight':
        nextIndex = currentEnabledIndex < enabledTabs.length - 1 
          ? currentEnabledIndex + 1 
          : 0;
        break;
      case 'Home':
        nextIndex = 0;
        break;
      case 'End':
        nextIndex = enabledTabs.length - 1;
        break;
      default:
        return;
    }

    if (nextIndex !== null) {
      event.preventDefault();
      const nextTab = enabledTabs[nextIndex];
      tabRefs.current.get(nextTab.id)?.focus();
      onChange(nextTab.id);
    }
  };

  const getTabStyles = (tab: Tab, isActive: boolean) => {
    const baseStyles = [
      'relative',
      'inline-flex items-center gap-2',
      'font-medium',
      'transition-colors duration-150',
      'focus:outline-none focus:ring-2 focus:ring-[var(--semantic-border-focus)] focus:ring-offset-2',
      styles.tab,
    ];

    if (tab.disabled) {
      return cn(baseStyles, 'opacity-50 cursor-not-allowed');
    }

    switch (variant) {
      case 'underline':
        return cn(
          baseStyles,
          'border-b-2 -mb-px',
          isActive
            ? 'border-[var(--semantic-interactive-primary-default)] text-[var(--semantic-interactive-primary-default)]'
            : 'border-transparent text-[var(--semantic-text-secondary)] hover:text-[var(--semantic-text-primary)] hover:border-[var(--semantic-border-default)]'
        );

      case 'pills':
        return cn(
          baseStyles,
          'rounded-full',
          isActive
            ? 'bg-[var(--semantic-interactive-primary-default)] text-white'
            : 'text-[var(--semantic-text-secondary)] hover:text-[var(--semantic-text-primary)] hover:bg-[var(--semantic-bg-surface-hover)]'
        );

      case 'enclosed':
        return cn(
          baseStyles,
          'rounded-t-[var(--radius-md)]',
          'border border-b-0',
          isActive
            ? 'border-[var(--semantic-border-default)] bg-[var(--semantic-bg-surface)] text-[var(--semantic-text-primary)] -mb-px'
            : 'border-transparent text-[var(--semantic-text-secondary)] hover:text-[var(--semantic-text-primary)]'
        );

      default:
        return baseStyles;
    }
  };

  return (
    <div
      role="tablist"
      aria-label={ariaLabel}
      className={cn(
        'flex',
        fullWidth && 'w-full',
        variant === 'underline' && 'border-b border-[var(--semantic-border-default)]',
        variant === 'enclosed' && 'border-b border-[var(--semantic-border-default)]',
        className
      )}
    >
      {tabs.map((tab, index) => {
        const isActive = tab.id === activeTab;

        return (
          <button
            key={tab.id}
            ref={(el) => {
              if (el) tabRefs.current.set(tab.id, el);
            }}
            role="tab"
            type="button"
            id={`tab-${tab.id}`}
            aria-selected={isActive}
            aria-controls={`panel-${tab.id}`}
            tabIndex={isActive ? 0 : -1}
            disabled={tab.disabled}
            onClick={() => !tab.disabled && onChange(tab.id)}
            onKeyDown={(e) => handleKeyDown(e, index)}
            className={cn(
              getTabStyles(tab, isActive),
              fullWidth && 'flex-1 justify-center'
            )}
          >
            {tab.icon && (
              <span className={cn(styles.icon, 'flex-shrink-0')}>
                {tab.icon}
              </span>
            )}
            {tab.label}
            {tab.badge && (
              <span className="flex-shrink-0">
                {tab.badge}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
};

Tabs.displayName = 'Tabs';

export const TabPanel: React.FC<TabPanelProps> = ({
  tabId,
  activeTab,
  children,
  className,
}) => {
  const isActive = tabId === activeTab;

  return (
    <div
      role="tabpanel"
      id={`panel-${tabId}`}
      aria-labelledby={`tab-${tabId}`}
      hidden={!isActive}
      tabIndex={0}
      className={cn(
        'focus:outline-none',
        isActive && 'animate-in fade-in duration-200',
        className
      )}
    >
      {isActive && children}
    </div>
  );
};

TabPanel.displayName = 'TabPanel';

export default Tabs;
