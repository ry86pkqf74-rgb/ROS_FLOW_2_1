import { useOllamaModels } from "@/hooks/use-ollama";
import { cn } from "@/lib/utils";

export function StatusIndicator() {
  const { isError, isLoading } = useOllamaModels();
  
  const status = isLoading ? "connecting" : isError ? "offline" : "online";
  
  return (
    <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-card border border-border shadow-sm">
      <div className={cn(
        "w-2 h-2 rounded-full",
        status === "online" && "bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.4)]",
        status === "offline" && "bg-destructive shadow-[0_0_8px_rgba(239,68,68,0.4)]",
        status === "connecting" && "bg-yellow-500 animate-pulse"
      )} />
      <span className="text-xs font-medium text-muted-foreground">
        {status === "online" ? "Ollama Connected" : status === "offline" ? "Disconnected" : "Connecting..."}
      </span>
    </div>
  );
}
