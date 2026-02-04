import { formatDistanceToNow } from "date-fns";
import { Box, HardDrive, Clock, Trash2, Terminal } from "lucide-react";
import { type OllamaModel } from "@shared/schema";
import { Button } from "@/components/ui/button";

interface ModelCardProps {
  model: OllamaModel;
}

export function ModelCard({ model }: ModelCardProps) {
  const sizeInGB = (model.size / (1024 * 1024 * 1024)).toFixed(2);
  
  return (
    <div className="group relative bg-card hover:bg-muted/20 border border-border rounded-xl p-5 transition-all duration-200 hover:shadow-lg hover:shadow-primary/5 hover:-translate-y-0.5">
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-primary/5 text-primary flex items-center justify-center border border-primary/10">
            <Box className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-display font-semibold text-lg leading-tight">{model.name}</h3>
            <p className="text-xs text-muted-foreground mt-0.5 font-mono">{model.details.family} family</p>
          </div>
        </div>
        
        {/* Placeholder for future delete functionality */}
        <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity">
          <Trash2 className="w-4 h-4" />
        </Button>
      </div>

      <div className="grid grid-cols-2 gap-3 mb-4">
        <div className="flex items-center gap-2 text-xs text-muted-foreground bg-muted/30 p-2 rounded-md">
          <HardDrive className="w-3.5 h-3.5" />
          <span>{sizeInGB} GB</span>
        </div>
        <div className="flex items-center gap-2 text-xs text-muted-foreground bg-muted/30 p-2 rounded-md">
          <Clock className="w-3.5 h-3.5" />
          <span>{formatDistanceToNow(new Date(model.modified_at))} ago</span>
        </div>
        <div className="flex items-center gap-2 text-xs text-muted-foreground bg-muted/30 p-2 rounded-md col-span-2">
          <Terminal className="w-3.5 h-3.5" />
          <span className="truncate font-mono">{model.digest.substring(0, 12)}...</span>
        </div>
      </div>
      
      <div className="flex items-center gap-2 mt-4 pt-4 border-t border-border/50">
         <span className="text-[10px] uppercase tracking-wider font-semibold text-muted-foreground/60 bg-muted/50 px-2 py-0.5 rounded-full">
            {model.details.quantization_level}
         </span>
         <span className="text-[10px] uppercase tracking-wider font-semibold text-muted-foreground/60 bg-muted/50 px-2 py-0.5 rounded-full">
            {model.details.format}
         </span>
      </div>
    </div>
  );
}
