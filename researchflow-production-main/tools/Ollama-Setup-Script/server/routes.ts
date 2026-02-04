import type { Express } from "express";
import { createServer, type Server } from "http";
import { storage } from "./storage";
import { api } from "@shared/routes";
import { z } from "zod";

export async function registerRoutes(
  httpServer: Server,
  app: Express
): Promise<Server> {

  // === SEED DATA ===
  const ollamaUrl = await storage.getSetting('ollama_url');
  if (!ollamaUrl) {
    await storage.updateSetting('ollama_url', 'http://127.0.0.1:11434');
  }

  // === PROXY HELPERS ===
  async function getOllamaBaseUrl() {
    const setting = await storage.getSetting('ollama_url');
    return setting?.value || 'http://127.0.0.1:11434';
  }

  // === OLLAMA PROXY ROUTES ===
  
  app.get(api.ollama.models.path, async (req, res) => {
    try {
      const baseUrl = await getOllamaBaseUrl();
      const response = await fetch(`${baseUrl}/api/tags`);
      if (!response.ok) throw new Error(`Ollama API error: ${response.statusText}`);
      const data = await response.json();
      res.json(data);
    } catch (error: any) {
      res.status(500).json({ message: error.message || 'Failed to fetch models' });
    }
  });

  app.post(api.ollama.pull.path, async (req, res) => {
    try {
      const input = api.ollama.pull.input.parse(req.body);
      const baseUrl = await getOllamaBaseUrl();
      
      // We start the pull. 
      // Note: Ollama pull is streaming. For MVP we might just trigger it and return OK.
      // But the client might want to show progress. 
      // For now, let's proxy the request and pipe the response if possible, 
      // or just return success and let the client handle long polling/status?
      // Simple approach: Trigger fetch and pipe response.
      
      const response = await fetch(`${baseUrl}/api/pull`, {
        method: 'POST',
        body: JSON.stringify({ name: input.name, stream: false }), // stream: false waits for completion? Might timeout.
        // If stream: true, we need to pipe.
      });

      if (!response.ok) throw new Error(`Ollama API error: ${response.statusText}`);
      
      // If we use stream: false, it waits until done.
      const data = await response.json();
      res.json(data);

    } catch (error: any) {
       if (error instanceof z.ZodError) {
        return res.status(400).json({
          message: error.errors[0].message,
          field: error.errors[0].path.join('.'),
        });
      }
      res.status(500).json({ message: error.message || 'Failed to pull model' });
    }
  });

  app.post(api.ollama.chat.path, async (req, res) => {
    try {
      const input = api.ollama.chat.input.parse(req.body);
      const baseUrl = await getOllamaBaseUrl();

      const response = await fetch(`${baseUrl}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: input.model,
          messages: input.messages,
          stream: input.stream ?? false, 
        }),
      });

      if (!response.ok) throw new Error(`Ollama API error: ${response.statusText}`);

      if (input.stream) {
        // Pipe the stream
        res.setHeader('Content-Type', 'application/x-ndjson');
        if (response.body) {
          // @ts-ignore - native fetch body is readable stream
          const reader = response.body.getReader();
          const decoder = new TextDecoder();
          
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            const chunk = decoder.decode(value);
            res.write(chunk);
          }
          res.end();
        }
      } else {
        const data = await response.json();
        res.json(data);
      }

    } catch (error: any) {
      res.status(500).json({ message: error.message || 'Failed to chat' });
    }
  });

  // === SETTINGS ROUTES ===

  app.get(api.settings.list.path, async (req, res) => {
    // For now we only have one setting, but generic list is fine
    const s = await storage.getSetting('ollama_url');
    res.json(s ? [s] : []);
  });

  app.post(api.settings.update.path, async (req, res) => {
    try {
      const input = api.settings.update.input.parse(req.body);
      const setting = await storage.updateSetting(input.key, input.value);
      res.json(setting);
    } catch (error: any) {
      if (error instanceof z.ZodError) {
        return res.status(400).json({ message: error.message });
      }
      res.status(500).json({ message: 'Failed to update setting' });
    }
  });

  // === SESSION ROUTES ===

  app.get(api.sessions.list.path, async (req, res) => {
    const sessions = await storage.getChatSessions();
    res.json(sessions);
  });

  app.post(api.sessions.create.path, async (req, res) => {
    try {
      const input = api.sessions.create.input.parse(req.body);
      const session = await storage.createChatSession(input);
      res.status(201).json(session);
    } catch (error: any) {
      res.status(400).json({ message: 'Invalid input' });
    }
  });

  app.get(api.sessions.get.path, async (req, res) => {
    const id = Number(req.params.id);
    const session = await storage.getChatSession(id);
    if (!session) return res.status(404).json({ message: 'Session not found' });
    
    const messages = await storage.getMessages(id);
    res.json({ ...session, messages });
  });

  app.delete(api.sessions.delete.path, async (req, res) => {
    const id = Number(req.params.id);
    // Check exist
    const session = await storage.getChatSession(id);
    if (!session) return res.status(404).json({ message: 'Session not found' });
    
    await storage.deleteChatSession(id);
    res.status(204).send();
  });

  // === MESSAGE ROUTES ===

  app.post(api.messages.create.path, async (req, res) => {
    try {
      const sessionId = Number(req.params.id);
      const input = api.messages.create.input.parse(req.body);
      const message = await storage.createMessage({ ...input, sessionId });
      res.status(201).json(message);
    } catch (error) {
      res.status(400).json({ message: 'Invalid input' });
    }
  });

  return httpServer;
}
