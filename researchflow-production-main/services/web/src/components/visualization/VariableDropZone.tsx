/**
 * VariableDropZone - DnD target for chart axis/variable mapping
 * Uses @dnd-kit/core useDroppable; displays current mapped column or placeholder.
 */

import React from 'react';
import { useDroppable } from '@dnd-kit/core';
import { cn } from '@/lib/utils';

export interface VariableDropZoneProps {
  id: string;
  label: string;
  currentColumnName: string | null;
  onDrop?: (columnId: string) => void;
  className?: string;
  disabled?: boolean;
}

export function VariableDropZone({
  id,
  label,
  currentColumnName,
  onDrop,
  className,
  disabled = false,
}: VariableDropZoneProps) {
  const { isOver, setNodeRef } = useDroppable({
    id,
    data: { dropZoneId: id, onDrop },
  });

  return (
    <div
      ref={setNodeRef}
      className={cn(
        'rounded-md border-2 border-dashed p-3 min-h-[2.5rem] transition-colors',
        isOver && !disabled && 'border-primary bg-primary/5',
        !currentColumnName && !isOver && 'border-muted-foreground/30 bg-muted/30',
        currentColumnName && 'border-muted bg-muted/50',
        disabled && 'opacity-50 cursor-not-allowed',
        className
      )}
    >
      <span className="text-xs font-medium text-muted-foreground block mb-1">
        {label}
      </span>
      <span className="text-sm font-medium">
        {currentColumnName || 'Drop variable here'}
      </span>
    </div>
  );
}
