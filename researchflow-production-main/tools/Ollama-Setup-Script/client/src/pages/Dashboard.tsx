import { useOllamaModels } from "@/hooks/use-ollama";
import { useSessions } from "@/hooks/use-sessions";
import { StatusIndicator } from "@/components/StatusIndicator";
import { ModelCard } from "@/components/ModelCard";
import { Activity, Box, MessageSquare, Cpu, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Link } from "wouter";

function StatCard({ icon: Icon, label, value, subtext }: any) {
  return (
    <div className="bg-card border border-border rounded-xl p-6 shadow-sm flex items-start justify-between">
      <div>
        <p className="text-sm font-medium text-muted-foreground mb-1">{label}</p>
        <h3 className="text-2xl font-bold tracking-tight">{value}</h3>
        {subtext && <p className="text-xs text-muted-foreground mt-1">{subtext}</p>}
      </div>
      <div className="p-3 bg-primary/5 text-primary rounded-lg">
        <Icon className="w-5 h-5" />
      </div>
    </div>
  );
}

export default function Dashboard() {
  const { data: modelsData, isLoading: modelsLoading, isError: modelsError } = useOllamaModels();
  const { data: sessionsData, isLoading: sessionsLoading } = useSessions();

  const modelsCount = modelsData?.models?.length || 0;
  const sessionsCount = sessionsData?.length || 0;
  
  // Calculate total size
  const totalSizeGB = modelsData?.models?.reduce((acc, m) => acc + m.size, 0) 
    ? (modelsData!.models.reduce((acc, m) => acc + m.size, 0) / (1024 * 1024 * 1024)).toFixed(1) 
    : "0";

  return (
    <div className="min-h-screen bg-background p-8 pl-72">
      <header className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Dashboard</h1>
          <p className="text-muted-foreground mt-1">Overview of your local LLM environment</p>
        </div>
        <StatusIndicator />
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-10">
        <StatCard 
          icon={Box} 
          label="Installed Models" 
          value={modelsLoading ? "-" : modelsCount}
          subtext="Ready to use"
        />
        <StatCard 
          icon={MessageSquare} 
          label="Chat Sessions" 
          value={sessionsLoading ? "-" : sessionsCount}
          subtext="Total conversations"
        />
        <StatCard 
          icon={Cpu} 
          label="Total Storage" 
          value={`${totalSizeGB} GB`}
          subtext="Disk usage"
        />
        <StatCard 
          icon={Activity} 
          label="Ollama Status" 
          value={modelsError ? "Offline" : "Active"}
          subtext="Local service"
        />
      </div>

      <div className="mb-6 flex items-center justify-between">
        <h2 className="text-xl font-semibold">Recent Models</h2>
        <Link href="/models">
          <Button variant="ghost" className="gap-2">
            View All <ArrowRight className="w-4 h-4" />
          </Button>
        </Link>
      </div>

      {modelsLoading ? (
        <div className="flex items-center justify-center h-48 bg-muted/10 rounded-xl border border-dashed border-border">
          <p className="text-muted-foreground">Loading models...</p>
        </div>
      ) : modelsCount === 0 ? (
        <div className="flex flex-col items-center justify-center h-48 bg-muted/10 rounded-xl border border-dashed border-border gap-4">
          <p className="text-muted-foreground">No models installed yet.</p>
          <Link href="/models">
            <Button>Go to Models Library</Button>
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {modelsData?.models.slice(0, 3).map((model) => (
            <ModelCard key={model.digest} model={model} />
          ))}
        </div>
      )}
    </div>
  );
}
