import { Loader2, Save } from "lucide-react";
import { useState, useEffect } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useSettings, useUpdateSetting } from "@/hooks/use-settings";


export default function Settings() {
  const { data: settings, isLoading } = useSettings();
  const updateSetting = useUpdateSetting();
  
  // Local state for form
  const [ollamaUrl, setOllamaUrl] = useState("");

  // Sync state when data loads
  useEffect(() => {
    if (settings) {
      const urlSetting = settings.find(s => s.key === "ollama_url");
      if (urlSetting) setOllamaUrl(urlSetting.value);
    }
  }, [settings]);

  const handleSave = () => {
    updateSetting.mutate({ key: "ollama_url", value: ollamaUrl });
  };

  return (
    <div className="min-h-screen bg-background p-8 pl-72">
      <header className="mb-8">
        <h1 className="text-3xl font-bold text-foreground">Settings</h1>
        <p className="text-muted-foreground mt-1">Configure your Ollama connection</p>
      </header>

      <div className="max-w-2xl">
        <Card className="shadow-lg shadow-black/5 border-border">
          <CardHeader>
            <CardTitle>Connection Settings</CardTitle>
            <CardDescription>
              Specify where your Ollama instance is running. Usually this is localhost.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="space-y-2">
              <Label htmlFor="url">Ollama API URL</Label>
              <Input 
                id="url"
                value={isLoading ? "Loading..." : ollamaUrl}
                onChange={(e) => setOllamaUrl(e.target.value)}
                placeholder="http://127.0.0.1:11434"
                className="font-mono bg-muted/30"
              />
              <p className="text-xs text-muted-foreground">
                Ensure this URL is accessible from the server running this app.
              </p>
            </div>

            <Button 
              onClick={handleSave} 
              disabled={updateSetting.isPending || isLoading}
              className="w-full sm:w-auto"
            >
              {updateSetting.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <Save className="w-4 h-4 mr-2" />
                  Save Configuration
                </>
              )}
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
