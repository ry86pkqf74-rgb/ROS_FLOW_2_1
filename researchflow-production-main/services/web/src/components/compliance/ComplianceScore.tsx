import React from 'react';
import { LucideIcon } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { cn } from '@/lib/utils';

interface ComplianceScoreProps {
  title: string;
  score: number;
  icon: LucideIcon;
  color: 'primary' | 'blue' | 'green' | 'purple' | 'red';
}

const colorClasses = {
  primary: 'text-primary bg-primary/10',
  blue: 'text-blue-600 bg-blue-100',
  green: 'text-green-600 bg-green-100',
  purple: 'text-purple-600 bg-purple-100',
  red: 'text-red-600 bg-red-100',
};

export const ComplianceScore: React.FC<ComplianceScoreProps> = ({
  title,
  score,
  icon: Icon,
  color,
}) => {
  const getScoreColor = (s: number) => {
    if (s >= 80) return 'text-green-600';
    if (s >= 60) return 'text-yellow-600';
    return 'text-red-600';
  };

  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-center gap-3">
          <div className={cn('p-2 rounded-lg', colorClasses[color])}>
            <Icon className="h-5 w-5" />
          </div>
          <div className="flex-1">
            <div className="text-sm text-muted-foreground">{title}</div>
            <div className={cn('text-2xl font-bold', getScoreColor(score))}>
              {score}%
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
