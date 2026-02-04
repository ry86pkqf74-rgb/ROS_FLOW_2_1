import React, { useState, useEffect } from 'react';
import { Shield, Bot, FileText, Clock } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { complianceApi } from '@/api/compliance';

interface TransparencyReportProps {
  projectId: string;
}

interface TransparencyData {
  aiModelsUsed: Array<{ model: string; provider: string; calls: number }>;
  totalAICalls: number;
  averageLatency: number;
  decisionsLogged: number;
}

export const TransparencyReport: React.FC<TransparencyReportProps> = ({
  projectId,
}) => {
  const [data, setData] = useState<TransparencyData | null>(null);

  useEffect(() => {
    complianceApi
      .getTransparencyReport(projectId)
      .then(setData)
      .catch(() => setData(null));
  }, [projectId]);

  if (!data) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Shield className="h-5 w-5" />
          HTI-1 Transparency Report
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-3 gap-4">
          <div className="text-center p-4 bg-muted rounded-lg">
            <Bot className="h-8 w-8 mx-auto mb-2 text-blue-600" />
            <div className="text-2xl font-bold">{data.totalAICalls}</div>
            <div className="text-sm text-muted-foreground">AI Calls</div>
          </div>
          <div className="text-center p-4 bg-muted rounded-lg">
            <Clock className="h-8 w-8 mx-auto mb-2 text-green-600" />
            <div className="text-2xl font-bold">{data.averageLatency}ms</div>
            <div className="text-sm text-muted-foreground">Avg Latency</div>
          </div>
          <div className="text-center p-4 bg-muted rounded-lg">
            <FileText className="h-8 w-8 mx-auto mb-2 text-purple-600" />
            <div className="text-2xl font-bold">{data.decisionsLogged}</div>
            <div className="text-sm text-muted-foreground">Decisions Logged</div>
          </div>
        </div>

        <div>
          <h4 className="font-medium mb-2">AI Models Used</h4>
          <div className="space-y-2">
            {data.aiModelsUsed.map((model, i) => (
              <div
                key={i}
                className="flex justify-between items-center p-2 bg-muted rounded"
              >
                <span>
                  {model.model} ({model.provider})
                </span>
                <span className="text-muted-foreground">{model.calls} calls</span>
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
