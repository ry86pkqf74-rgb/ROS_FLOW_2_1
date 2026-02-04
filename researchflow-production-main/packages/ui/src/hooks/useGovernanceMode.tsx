import * as React from 'react';

/**
 * Governance mode type
 */
export type GovernanceMode = 'DEMO' | 'LIVE';

/**
 * Governance mode context value
 */
export interface GovernanceModeContextValue {
  /** Current governance mode */
  mode: GovernanceMode;
  /** Whether the mode is currently being switched */
  isSwitching: boolean;
  /** Switch to a different mode */
  switchMode: (newMode: GovernanceMode) => Promise<void>;
  /** Whether PHI access is enabled (only in LIVE mode) */
  isPHIEnabled: boolean;
}

const GovernanceModeContext = React.createContext<GovernanceModeContextValue | null>(null);

/**
 * Governance mode provider props
 */
export interface GovernanceModeProviderProps {
  children: React.ReactNode;
  /** Initial mode (defaults to DEMO) */
  initialMode?: GovernanceMode;
  /** API endpoint for mode switching */
  apiEndpoint?: string;
  /** Callback when mode changes */
  onModeChange?: (newMode: GovernanceMode) => void;
}

/**
 * Provider component for governance mode
 * 
 * @example
 * ```tsx
 * <GovernanceModeProvider initialMode="DEMO">
 *   <App />
 * </GovernanceModeProvider>
 * ```
 */
export function GovernanceModeProvider({
  children,
  initialMode = 'DEMO',
  apiEndpoint = '/api/governance/mode',
  onModeChange,
}: GovernanceModeProviderProps) {
  const [mode, setMode] = React.useState<GovernanceMode>(initialMode);
  const [isSwitching, setIsSwitching] = React.useState(false);

  const switchMode = React.useCallback(async (newMode: GovernanceMode) => {
    if (newMode === mode) return;
    
    setIsSwitching(true);
    
    try {
      const response = await fetch(apiEndpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode: newMode }),
      });
      
      if (!response.ok) {
        throw new Error('Failed to switch governance mode');
      }
      
      setMode(newMode);
      onModeChange?.(newMode);
    } catch (error) {
      console.error('Governance mode switch failed:', error);
      throw error;
    } finally {
      setIsSwitching(false);
    }
  }, [mode, apiEndpoint, onModeChange]);

  const value = React.useMemo<GovernanceModeContextValue>(() => ({
    mode,
    isSwitching,
    switchMode,
    isPHIEnabled: mode === 'LIVE',
  }), [mode, isSwitching, switchMode]);

  return (
    <GovernanceModeContext.Provider value={value}>
      {children}
    </GovernanceModeContext.Provider>
  );
}

/**
 * Hook to access governance mode context
 * 
 * @example
 * ```tsx
 * function MyComponent() {
 *   const { mode, isPHIEnabled, switchMode } = useGovernanceMode();
 *   
 *   return (
 *     <div>
 *       <p>Current mode: {mode}</p>
 *       <p>PHI enabled: {isPHIEnabled ? 'Yes' : 'No'}</p>
 *       <button onClick={() => switchMode('LIVE')}>Switch to LIVE</button>
 *     </div>
 *   );
 * }
 * ```
 */
export function useGovernanceMode(): GovernanceModeContextValue {
  const context = React.useContext(GovernanceModeContext);
  
  if (!context) {
    throw new Error('useGovernanceMode must be used within a GovernanceModeProvider');
  }
  
  return context;
}

export default useGovernanceMode;
