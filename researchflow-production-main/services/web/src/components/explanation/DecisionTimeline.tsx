/**
 * DecisionTimeline - Timeline view of statistical audit decisions/events
 * Renders a vertical timeline with timestamp, title, description, type.
 */

import React from 'react';
import { format } from 'date-fns';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

export interface DecisionEvent {
  id: string;
  timestamp: string;
  title: string;
  description?: string;
  type?: string;
}

export interface DecisionTimelineProps {
  events: DecisionEvent[];
  className?: string;
}

export function DecisionTimeline({ events, className }: DecisionTimelineProps) {
  if (events.length === 0) {
    return (
      <div className={cn('text-sm text-muted-foreground py-8 text-center', className)}>
        No decision events in this analysis.
      </div>
    );
  }

  const sorted = [...events].sort(
    (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
  );

  return (
    <div className={cn('relative', className)}>
      <div className="absolute left-4 top-0 bottom-0 w-px bg-border" aria-hidden />
      <ul className="space-y-6">
        {sorted.map((event) => (
          <li key={event.id} className="relative flex gap-4 pl-10">
            <span
              className="absolute left-2.5 h-3 w-3 rounded-full bg-primary border-2 border-background"
              aria-hidden
            />
            <Card className="flex-1">
              <CardContent className="p-4">
                <div className="flex flex-wrap items-center gap-2 mb-1">
                  <time
                    dateTime={event.timestamp}
                    className="text-xs text-muted-foreground"
                  >
                    {format(new Date(event.timestamp), 'PPp')}
                  </time>
                  {event.type && (
                    <Badge variant="secondary" className="text-xs">
                      {event.type}
                    </Badge>
                  )}
                </div>
                <h4 className="font-medium text-sm">{event.title}</h4>
                {event.description && (
                  <p className="text-sm text-muted-foreground mt-1">
                    {event.description}
                  </p>
                )}
              </CardContent>
            </Card>
          </li>
        ))}
      </ul>
    </div>
  );
}
