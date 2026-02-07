import { Download, Loader2 } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { usePullModel } from "@/hooks/use-ollama";

export function PullModelDialog() {
  const [open, setOpen] = useState(false);
  const [modelName, setModelName] = useState("");
  const pullMutation = usePullModel();

  const handlePull = async () => {
    if (!modelName.trim()) return;
    try {
      await pullMutation.mutateAsync(modelName);
      setOpen(false);
      setModelName("");
    } catch (e) {
      // Error handled in hook
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button className="gap-2 shadow-lg shadow-primary/20">
          <Download className="w-4 h-4" />
          Pull Model
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Pull New Model</DialogTitle>
          <DialogDescription>
            Enter the tag of the model you want to pull from the Ollama library (e.g., "llama3", "mistral").
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Input
              placeholder="Model name (e.g. llama3:latest)"
              value={modelName}
              onChange={(e) => setModelName(e.target.value)}
              className="font-mono text-sm"
            />
            <p className="text-xs text-muted-foreground">
              Large models may take several minutes to download depending on your connection.
            </p>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button 
            onClick={handlePull} 
            disabled={!modelName || pullMutation.isPending}
            className="gap-2"
          >
            {pullMutation.isPending ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Starting...
              </>
            ) : (
              "Pull Model"
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
