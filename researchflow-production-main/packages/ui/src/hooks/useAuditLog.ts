import * as React from 'react';

/**
 * Audit action types
 */
export type AuditAction = 
  | 'workflow.created' | 'workflow.started' | 'workflow.completed' | 'workflow.failed'
  | 'phi.accessed' | 'phi.denied' | 'phi.approved'
  | 'document.viewed' | 'document.edited' | 'document.exported'
  | 'model.invoked' | 'model.tier_changed'
  | 'user.login' | 'user.logout';

/**
 * Audit log entry
 */
export interface AuditLogEntry {
  id: string;
  timestamp: string;
  action: AuditAction;
  actor: {
    id: string;
    name: string;
    email: string;
    role: string;
  };
  resource: {
    type: string;
    id: string;
    name: string;
  };
  details: Record<string, unknown>;
  metadata: {
    ip?: string;
    userAgent?: string;
    sessionId?: string;
  };
}

/**
 * Audit log filter options
 */
export interface AuditLogFilters {
  action?: AuditAction;
  actorId?: string;
  resourceType?: string;
  startDate?: string;
  endDate?: string;
}

/**
 * Audit log hook state
 */
export interface UseAuditLogState {
  /** Audit log entries */
  entries: AuditLogEntry[];
  /** Whether data is loading */
  isLoading: boolean;
  /** Error message if any */
  error: string | null;
  /** Current page */
  page: number;
  /** Total number of entries */
  total: number;
  /** Whether there are more pages */
  hasMore: boolean;
}

/**
 * Audit log hook actions
 */
export interface UseAuditLogActions {
  /** Fetch entries with optional filters */
  fetchEntries: (filters?: AuditLogFilters) => Promise<void>;
  /** Load next page */
  loadMore: () => Promise<void>;
  /** Refresh current data */
  refresh: () => Promise<void>;
  /** Export entries */
  exportEntries: (format: 'csv' | 'json') => Promise<string>;
}

/**
 * Audit log hook options
 */
export interface UseAuditLogOptions {
  /** API endpoint */
  apiEndpoint?: string;
  /** Items per page */
  pageSize?: number;
  /** Initial filters */
  initialFilters?: AuditLogFilters;
  /** Auto-fetch on mount */
  autoFetch?: boolean;
}

/**
 * Hook for fetching and managing audit log entries
 * 
 * @example
 * ```tsx
 * function AuditLogViewer() {
 *   const {
 *     entries,
 *     isLoading,
 *     error,
 *     hasMore,
 *     fetchEntries,
 *     loadMore,
 *     exportEntries,
 *   } = useAuditLog({ autoFetch: true });
 *   
 *   return (
 *     <div>
 *       {entries.map(entry => (
 *         <div key={entry.id}>{entry.action}</div>
 *       ))}
 *       {hasMore && <button onClick={loadMore}>Load More</button>}
 *     </div>
 *   );
 * }
 * ```
 */
export function useAuditLog(options: UseAuditLogOptions = {}): UseAuditLogState & UseAuditLogActions {
  const {
    apiEndpoint = '/api/audit/logs',
    pageSize = 20,
    initialFilters = {},
    autoFetch = false,
  } = options;

  const [state, setState] = React.useState<UseAuditLogState>({
    entries: [],
    isLoading: false,
    error: null,
    page: 1,
    total: 0,
    hasMore: false,
  });

  const [filters, setFilters] = React.useState<AuditLogFilters>(initialFilters);

  const fetchEntries = React.useCallback(async (newFilters?: AuditLogFilters) => {
    const activeFilters = newFilters ?? filters;
    if (newFilters) {
      setFilters(newFilters);
    }

    setState(prev => ({ ...prev, isLoading: true, error: null }));

    try {
      const params = new URLSearchParams({
        page: '1',
        limit: pageSize.toString(),
        ...Object.fromEntries(
          Object.entries(activeFilters).filter(([, v]) => v !== undefined)
        ),
      });

      const response = await fetch(`${apiEndpoint}?${params}`);
      
      if (!response.ok) {
        throw new Error('Failed to fetch audit logs');
      }

      const data = await response.json();

      setState({
        entries: data.entries,
        isLoading: false,
        error: null,
        page: data.page,
        total: data.total,
        hasMore: data.hasMore,
      });
    } catch (error) {
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      }));
    }
  }, [apiEndpoint, pageSize, filters]);

  const loadMore = React.useCallback(async () => {
    if (state.isLoading || !state.hasMore) return;

    setState(prev => ({ ...prev, isLoading: true }));

    try {
      const params = new URLSearchParams({
        page: (state.page + 1).toString(),
        limit: pageSize.toString(),
        ...Object.fromEntries(
          Object.entries(filters).filter(([, v]) => v !== undefined)
        ),
      });

      const response = await fetch(`${apiEndpoint}?${params}`);
      
      if (!response.ok) {
        throw new Error('Failed to fetch more audit logs');
      }

      const data = await response.json();

      setState(prev => ({
        entries: [...prev.entries, ...data.entries],
        isLoading: false,
        error: null,
        page: data.page,
        total: data.total,
        hasMore: data.hasMore,
      }));
    } catch (error) {
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      }));
    }
  }, [apiEndpoint, pageSize, filters, state.isLoading, state.hasMore, state.page]);

  const refresh = React.useCallback(async () => {
    await fetchEntries(filters);
  }, [fetchEntries, filters]);

  const exportEntries = React.useCallback(async (format: 'csv' | 'json'): Promise<string> => {
    const response = await fetch(`${apiEndpoint.replace('/logs', '')}/export`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ format, filters }),
    });

    if (!response.ok) {
      throw new Error('Failed to start export');
    }

    const data = await response.json();
    return data.exportId;
  }, [apiEndpoint, filters]);

  // Auto-fetch on mount if enabled
  React.useEffect(() => {
    if (autoFetch) {
      fetchEntries();
    }
  }, [autoFetch]);

  return {
    ...state,
    fetchEntries,
    loadMore,
    refresh,
    exportEntries,
  };
}

export default useAuditLog;
