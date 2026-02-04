import { useOllamaModels } from "@/hooks/use-ollama";
import { ModelCard } from "@/components/ModelCard";
import { PullModelDialog } from "@/components/PullModelDialog";
import { StatusIndicator } from "@/components/StatusIndicator";
import { Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import { useState } from "react";

export default function Models() {
  const { data, isLoading, isError } = useOllamaModels();
  const [search, setSearch] = useState("");

  const filteredModels = data?.models?.filter(m => 
    m.name.toLowerCase().includes(search.toLowerCase()) ||
    m.details.family.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="min-h-screen bg-background p-8 pl-72">
      <header className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Models Library</h1>
          <p className="text-muted-foreground mt-1">Manage your local LLM collection</p>
        </div>
        <div className="flex items-center gap-4">
          <StatusIndicator />
          <PullModelDialog />
        </div>
      </header>

      <div className="flex items-center gap-4 mb-8">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input 
            placeholder="Search installed models..." 
            className="pl-9 bg-card border-border"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-48 bg-card animate-pulse rounded-xl border border-border" />
          ))}
        </div>
      ) : isError ? (
        <div className="flex flex-col items-center justify-center py-20 bg-destructive/5 border border-destructive/20 rounded-xl">
          <h3 className="text-lg font-semibold text-destructive mb-2">Connection Failed</h3>
          <p className="text-muted-foreground max-w-md text-center">
            Could not connect to Ollama. Please ensure the service is running locally on your configured port (default 11434).
          </p>
        </div>
      ) : filteredModels?.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 bg-muted/10 border border-dashed border-border rounded-xl">
          <p className="text-muted-foreground">No models found matching your search.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredModels?.map((model) => (
            <ModelCard key={model.digest} model={model} />
          ))}
        </div>
      )}
    </div>
  );
}
