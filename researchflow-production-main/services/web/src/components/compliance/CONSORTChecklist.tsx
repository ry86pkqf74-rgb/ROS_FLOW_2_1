import React from 'react';
import { CheckCircle, Circle, AlertCircle, MinusCircle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

interface ChecklistItem {
  id: string;
  section: string;
  item: string;
  status: 'complete' | 'partial' | 'missing' | 'na';
  notes?: string;
  linkedSection?: string;
}

interface CONSORTChecklistProps {
  items: ChecklistItem[];
  projectId: string;
}

const statusConfig = {
  complete: { icon: CheckCircle, color: 'text-green-600', bg: 'bg-green-100' },
  partial: { icon: AlertCircle, color: 'text-yellow-600', bg: 'bg-yellow-100' },
  missing: { icon: Circle, color: 'text-red-600', bg: 'bg-red-100' },
  na: { icon: MinusCircle, color: 'text-gray-400', bg: 'bg-gray-100' },
};

export const CONSORTChecklist: React.FC<CONSORTChecklistProps> = ({
  items,
  projectId,
}) => {
  const groupedItems = items.reduce((acc, item) => {
    if (!acc[item.section]) acc[item.section] = [];
    acc[item.section].push(item);
    return acc;
  }, {} as Record<string, ChecklistItem[]>);

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            CONSORT-AI Checklist
            <Badge variant="outline">
              {items.filter((i) => i.status === 'complete').length}/{items.length}{' '}
              Complete
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {Object.entries(groupedItems).map(([section, sectionItems]) => (
            <div key={section}>
              <h3 className="font-semibold mb-2">{section}</h3>
              <div className="space-y-2">
                {sectionItems.map((item) => {
                  const config = statusConfig[item.status];
                  const Icon = config.icon;
                  return (
                    <div
                      key={item.id}
                      className={cn(
                        'flex items-start gap-3 p-2 rounded-lg',
                        config.bg
                      )}
                    >
                      <Icon className={cn('h-5 w-5 mt-0.5', config.color)} />
                      <div className="flex-1">
                        <div className="text-sm">{item.item}</div>
                        {item.notes && (
                          <div className="text-xs text-muted-foreground mt-1">
                            {item.notes}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
};
