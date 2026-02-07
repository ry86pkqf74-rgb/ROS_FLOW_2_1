import { ChevronUp, ChevronDown, ChevronsUpDown, Loader2 } from 'lucide-react';
import * as React from 'react';

import { cn } from '../../utils/cn';

// figma: fileKey=PENDING nodeId=PENDING
// Component contract: RF/Table

export type SortDirection = 'asc' | 'desc' | null;

export interface Column<T> {
  /** Unique key for the column */
  key: string;
  /** Column header label */
  header: string;
  /** Accessor function or property key */
  accessor: keyof T | ((row: T) => React.ReactNode);
  /** Is this column sortable? */
  sortable?: boolean;
  /** Column width (CSS value) */
  width?: string;
  /** Align cell content */
  align?: 'left' | 'center' | 'right';
  /** Custom cell renderer */
  cell?: (value: unknown, row: T) => React.ReactNode;
}

export interface TableProps<T> {
  /** Column definitions */
  columns: Column<T>[];
  /** Table data */
  data: T[];
  /** Unique key for each row */
  rowKey: keyof T | ((row: T) => string);
  /** Loading state */
  isLoading?: boolean;
  /** Empty state message */
  emptyMessage?: string;
  /** Error state */
  error?: string;
  /** Current sort column */
  sortColumn?: string;
  /** Current sort direction */
  sortDirection?: SortDirection;
  /** Sort change handler */
  onSort?: (column: string, direction: SortDirection) => void;
  /** Row click handler */
  onRowClick?: (row: T) => void;
  /** Striped rows */
  striped?: boolean;
  /** Compact size */
  compact?: boolean;
  /** Additional class */
  className?: string;
}

export function Table<T>({
  columns,
  data,
  rowKey,
  isLoading = false,
  emptyMessage = 'No data available',
  error,
  sortColumn,
  sortDirection,
  onSort,
  onRowClick,
  striped = false,
  compact = false,
  className,
}: TableProps<T>) {
  const getRowKey = (row: T, index: number): string => {
    if (typeof rowKey === 'function') {
      return rowKey(row);
    }
    return String(row[rowKey] ?? index);
  };

  const getCellValue = (row: T, column: Column<T>): React.ReactNode => {
    const rawValue = typeof column.accessor === 'function'
      ? column.accessor(row)
      : row[column.accessor];

    if (column.cell) {
      return column.cell(rawValue, row);
    }

    return rawValue as React.ReactNode;
  };

  const handleSort = (column: Column<T>) => {
    if (!column.sortable || !onSort) return;

    let newDirection: SortDirection = 'asc';
    if (sortColumn === column.key) {
      if (sortDirection === 'asc') newDirection = 'desc';
      else if (sortDirection === 'desc') newDirection = null;
    }

    onSort(column.key, newDirection);
  };

  const getSortIcon = (column: Column<T>) => {
    if (!column.sortable) return null;

    if (sortColumn !== column.key) {
      return <ChevronsUpDown className="h-4 w-4 opacity-50" />;
    }

    if (sortDirection === 'asc') {
      return <ChevronUp className="h-4 w-4" />;
    }

    if (sortDirection === 'desc') {
      return <ChevronDown className="h-4 w-4" />;
    }

    return <ChevronsUpDown className="h-4 w-4 opacity-50" />;
  };

  const cellPadding = compact ? 'px-3 py-2' : 'px-4 py-3';

  return (
    <div className={cn('relative overflow-auto', className)}>
      <table className="w-full border-collapse">
        {/* Header */}
        <thead>
          <tr className="border-b border-[var(--semantic-border-default)]">
            {columns.map((column) => (
              <th
                key={column.key}
                className={cn(
                  cellPadding,
                  'text-left font-semibold',
                  'text-sm text-[var(--semantic-text-secondary)]',
                  'bg-[var(--semantic-bg-surface-alt)]',
                  column.sortable && 'cursor-pointer select-none',
                  column.sortable && 'hover:bg-[var(--semantic-bg-surface-hover)]',
                  column.align === 'center' && 'text-center',
                  column.align === 'right' && 'text-right'
                )}
                style={{ width: column.width }}
                onClick={() => handleSort(column)}
              >
                <div className={cn(
                  'flex items-center gap-1',
                  column.align === 'center' && 'justify-center',
                  column.align === 'right' && 'justify-end'
                )}>
                  {column.header}
                  {getSortIcon(column)}
                </div>
              </th>
            ))}
          </tr>
        </thead>

        {/* Body */}
        <tbody>
          {/* Loading state */}
          {isLoading && (
            <tr>
              <td colSpan={columns.length} className="text-center py-12">
                <div className="flex items-center justify-center gap-2 text-[var(--semantic-text-muted)]">
                  <Loader2 className="h-5 w-5 animate-spin" />
                  <span>Loading...</span>
                </div>
              </td>
            </tr>
          )}

          {/* Error state */}
          {!isLoading && error && (
            <tr>
              <td colSpan={columns.length} className="text-center py-12">
                <div className="text-[var(--semantic-status-error-text)]">
                  {error}
                </div>
              </td>
            </tr>
          )}

          {/* Empty state */}
          {!isLoading && !error && data.length === 0 && (
            <tr>
              <td colSpan={columns.length} className="text-center py-12">
                <div className="text-[var(--semantic-text-muted)]">
                  {emptyMessage}
                </div>
              </td>
            </tr>
          )}

          {/* Data rows */}
          {!isLoading && !error && data.map((row, rowIndex) => (
            <tr
              key={getRowKey(row, rowIndex)}
              className={cn(
                'border-b border-[var(--semantic-border-muted)]',
                'transition-colors',
                striped && rowIndex % 2 === 1 && 'bg-[var(--semantic-bg-surface-alt)]',
                onRowClick && 'cursor-pointer hover:bg-[var(--semantic-bg-surface-hover)]'
              )}
              onClick={() => onRowClick?.(row)}
            >
              {columns.map((column) => (
                <td
                  key={column.key}
                  className={cn(
                    cellPadding,
                    'text-sm text-[var(--semantic-text-primary)]',
                    column.align === 'center' && 'text-center',
                    column.align === 'right' && 'text-right'
                  )}
                >
                  {getCellValue(row, column)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

Table.displayName = 'Table';

export default Table;
