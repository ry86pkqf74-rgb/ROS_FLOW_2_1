import { pgTable, text, serial, timestamp, boolean, jsonb } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod";

// === TABLE DEFINITIONS ===

// Settings to store configuration like Ollama URL
export const settings = pgTable("settings", {
  id: serial("id").primaryKey(),
  key: text("key").notNull().unique(), // e.g., 'ollama_url'
  value: text("value").notNull(),
  updatedAt: timestamp("updated_at").defaultNow(),
});

// Chat sessions for testing models
export const chatSessions = pgTable("chat_sessions", {
  id: serial("id").primaryKey(),
  title: text("title").notNull().default("New Chat"),
  model: text("model").notNull(), // The model used for this session
  createdAt: timestamp("created_at").defaultNow(),
});

// Messages within a chat session
export const messages = pgTable("messages", {
  id: serial("id").primaryKey(),
  sessionId: serial("session_id").references(() => chatSessions.id),
  role: text("role").notNull(), // 'user', 'assistant', 'system'
  content: text("content").notNull(),
  createdAt: timestamp("created_at").defaultNow(),
});

// === SCHEMAS ===

export const insertSettingSchema = createInsertSchema(settings).omit({ id: true, updatedAt: true });
export const insertChatSessionSchema = createInsertSchema(chatSessions).omit({ id: true, createdAt: true });
export const insertMessageSchema = createInsertSchema(messages).omit({ id: true, createdAt: true });

// === EXPLICIT TYPES ===

export type Setting = typeof settings.$inferSelect;
export type InsertSetting = z.infer<typeof insertSettingSchema>;

export type ChatSession = typeof chatSessions.$inferSelect;
export type InsertChatSession = z.infer<typeof insertChatSessionSchema>;

export type Message = typeof messages.$inferSelect;
export type InsertMessage = z.infer<typeof insertMessageSchema>;

// Request types
export type CreateChatSessionRequest = { model: string; title?: string };
export type CreateMessageRequest = { sessionId: number; role: 'user' | 'assistant' | 'system'; content: string };
export type UpdateSettingRequest = { key: string; value: string };

// Ollama specific types (not stored in DB, but used in API)
export interface OllamaModel {
  name: string;
  modified_at: string;
  size: number;
  digest: string;
  details: {
    format: string;
    family: string;
    families: string[] | null;
    parameter_size: string;
    quantization_level: string;
  };
}

export interface OllamaModelResponse {
  models: OllamaModel[];
}

export interface PullModelRequest {
  name: string;
}
