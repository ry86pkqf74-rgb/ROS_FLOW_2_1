import { useQuery } from '@tanstack/react-query';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { CheckCircle, XCircle, Loader2, Server } from 'lucide-react';

interface ServiceHealth {
  name: string;
  status: 'healthy' | 'unhealthy' | 'starting';
  uptime?: string;
  version?: string;
}

function normalizeStatus(raw: { status?: string } | null, ok: boolean): ServiceHealth['status'] {
  if (!raw || !ok) return 'unhealthy';
  if (raw.status === 'ok') return 'healthy';
  return 'unhealthy';
}

export function DockerStatus() {
  const { data: services, isLoading } = useQuery({
    queryKey: ['system-health'],
    queryFn: async () => {
      const fetchHealth = async (url: string) => {
        try {
          const r = await fetch(url);
          const body = await r.json().catch(() => null);
          return { ok: r.ok, body };
        } catch {
          return { ok: false, body: null };
        }
      };
      const [orchestratorRes, workerRes] = await Promise.all([
        fetchHealth('/api/health'),
        fetchHealth('/api/worker/health'),
      ]);
      const orchestratorOk = orchestratorRes.ok && orchestratorRes.body?.status === 'ok';
      const workerOk = workerRes.ok && workerRes.body?.status === 'ok';
      return [
        {
          name: 'Orchestrator',
          status: normalizeStatus(orchestratorRes.body, orchestratorOk),
          uptime: orchestratorRes.body?.uptime,
          version: orchestratorRes.body?.version,
        },
        {
          name: 'Worker',
          status: normalizeStatus(workerRes.body, workerOk),
          uptime: workerRes.body?.uptime,
          version: workerRes.body?.version,
        },
      ] as ServiceHealth[];
    },
    refetchInterval: 10000,
  });

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'unhealthy':
        return <XCircle className="h-4 w-4 text-red-500" />;
      default:
        return <Loader2 className="h-4 w-4 animate-spin text-yellow-500" />;
    }
  };

  if (isLoading) return <div className="animate-pulse">Checking services...</div>;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Server className="h-5 w-5" />
          System Status
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {services?.map((service) => (
            <div
              key={service.name}
              className="flex items-center justify-between p-2 border rounded"
            >
              <div className="flex items-center gap-2">
                {getStatusIcon(service.status)}
                <span className="font-medium">{service.name}</span>
              </div>
              <Badge variant={service.status === 'healthy' ? 'default' : 'destructive'}>
                {service.status}
              </Badge>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
