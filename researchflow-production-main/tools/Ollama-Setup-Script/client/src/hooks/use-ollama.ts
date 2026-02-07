import { api, type OllamaModelsResponse } from "@shared/routes";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

import { useToast } from "@/hooks/use-toast";

// Fetch available models from Ollama proxy
export function useOllamaModels() {
  return useQuery({
    queryKey: [api.ollama.models.path],
    queryFn: async () => {
      const res = await fetch(api.ollama.models.path, { credentials: "include" });
      if (!res.ok) {
        // If connection fails, we might want to know to show a specific error
        throw new Error("Could not connect to Ollama service");
      }
      return api.ollama.models.responses[200].parse(await res.json());
    },
    // Check connection periodically
    refetchInterval: 10000, 
    retry: false,
  });
}

// Pull a new model
export function usePullModel() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: async (name: string) => {
      const res = await fetch(api.ollama.pull.path, {
        method: api.ollama.pull.method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
        credentials: "include",
      });

      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.message || "Failed to pull model");
      }
      return api.ollama.pull.responses[200].parse(await res.json());
    },
    onSuccess: (_, name) => {
      toast({
        title: "Model Pull Initiated",
        description: `Successfully started pulling ${name}. This may take a while.`,
      });
      queryClient.invalidateQueries({ queryKey: [api.ollama.models.path] });
    },
    onError: (error) => {
      toast({
        title: "Pull Failed",
        description: error.message,
        variant: "destructive",
      });
    },
  });
}

// Chat with a model
export function useChat() {
  return useMutation({
    mutationFn: async (payload: {
      model: string;
      messages: { role: "user" | "assistant" | "system"; content: string }[];
    }) => {
      const res = await fetch(api.ollama.chat.path, {
        method: api.ollama.chat.method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...payload, stream: false }), // Simple non-streaming for MVP
        credentials: "include",
      });

      if (!res.ok) throw new Error("Chat request failed");
      return await res.json();
    },
  });
}
