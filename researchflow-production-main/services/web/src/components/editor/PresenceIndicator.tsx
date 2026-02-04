/**
 * PresenceIndicator
 *
 * User avatar badges with unique colors, cursor position tooltips,
 * selection range summary, and "X users editing" badge.
 */

import React from 'react';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { Users } from 'lucide-react';
import type { UserPresence } from '@/hooks/use-collaborative-editing';
import { cn } from '@/lib/utils';

export interface PresenceIndicatorProps {
  /** Other users currently in the document (excluding local user) */
  users: UserPresence[];
  /** Optional class for the container */
  className?: string;
  /** Compact mode: only show count badge */
  compact?: boolean;
}

function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/);
  if (parts.length >= 2) {
    return (parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase();
  }
  return name.charAt(0).toUpperCase() || '?';
}

function cursorLabel(user: UserPresence): string {
  if (user.cursor) {
    return `${user.name} — line ${user.cursor.line + 1}, col ${user.cursor.ch + 1}`;
  }
  return user.name;
}

export function PresenceIndicator({ users, className, compact = false }: PresenceIndicatorProps) {
  if (users.length === 0) {
    return (
      <Badge variant="secondary" className={cn('gap-1', className)}>
        <Users className="h-3 w-3" />
        You're the only one editing
      </Badge>
    );
  }

  if (compact) {
    return (
      <Badge variant="secondary" className={cn('gap-1', className)}>
        <Users className="h-3 w-3" />
        {users.length} {users.length === 1 ? 'user' : 'users'} editing
      </Badge>
    );
  }

  return (
    <TooltipProvider>
      <div className={cn('flex items-center gap-2', className)}>
        <Badge variant="secondary" className="gap-1">
          <Users className="h-3 w-3" />
          {users.length} {users.length === 1 ? 'user' : 'users'} editing
        </Badge>
        <div className="flex -space-x-2">
          {users.map((user) => (
            <Tooltip key={user.id}>
              <TooltipTrigger asChild>
                <div className="ring-2 ring-background rounded-full">
                  <Avatar
                    className="h-8 w-8 border-2 border-background flex items-center justify-center text-xs font-semibold text-white"
                    style={{ backgroundColor: user.color }}
                  >
                    <AvatarFallback
                      className="text-xs font-semibold text-white border-0"
                      style={{ backgroundColor: user.color }}
                    >
                      {getInitials(user.name)}
                    </AvatarFallback>
                  </Avatar>
                </div>
              </TooltipTrigger>
              <TooltipContent side="bottom" className="max-w-xs">
                <p className="font-medium">{user.name}</p>
                {user.cursor && (
                  <p className="text-xs text-muted-foreground mt-0.5">
                    Cursor: line {user.cursor.line + 1}, col {user.cursor.ch + 1}
                  </p>
                )}
                {user.selection && (
                  <p className="text-xs text-muted-foreground">
                    Selection: L{user.selection.anchor.line + 1} – L{user.selection.head.line + 1}
                  </p>
                )}
              </TooltipContent>
            </Tooltip>
          ))}
        </div>
      </div>
    </TooltipProvider>
  );
}
