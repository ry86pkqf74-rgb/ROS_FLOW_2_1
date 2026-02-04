import { z } from 'zod';
import { insertSettingSchema, insertChatSessionSchema, insertMessageSchema, chatSessions, messages, settings } from './schema';

export const errorSchemas = {
  validation: z.object({
    message: z.string(),
    field: z.string().optional(),
  }),
  notFound: z.object({
    message: z.string(),
  }),
  internal: z.object({
    message: z.string(),
  }),
};

// Ollama API types
const ollamaModelSchema = z.object({
  name: z.string(),
  modified_at: z.string(),
  size: z.number(),
  digest: z.string(),
  details: z.object({
    format: z.string(),
    family: z.string(),
    families: z.array(z.string()).nullable(),
    parameter_size: z.string(),
    quantization_level: z.string(),
  }),
});

export const api = {
  // === OLLAMA PROXY ROUTES ===
  ollama: {
    models: {
      method: 'GET' as const,
      path: '/api/ollama/models',
      responses: {
        200: z.object({ models: z.array(ollamaModelSchema) }),
        500: errorSchemas.internal,
      },
    },
    pull: {
      method: 'POST' as const,
      path: '/api/ollama/pull',
      input: z.object({ name: z.string() }),
      responses: {
        200: z.object({ status: z.string() }), // Streamed responses handled differently usually, but simple ack here
        400: errorSchemas.validation,
        500: errorSchemas.internal,
      },
    },
    chat: {
      method: 'POST' as const,
      path: '/api/ollama/chat',
      input: z.object({
        model: z.string(),
        messages: z.array(z.object({
          role: z.enum(['user', 'assistant', 'system']),
          content: z.string(),
        })),
        stream: z.boolean().optional(),
      }),
      responses: {
        200: z.any(), // Returns stream or JSON
        500: errorSchemas.internal,
      },
    },
  },

  // === SETTINGS ROUTES ===
  settings: {
    list: {
      method: 'GET' as const,
      path: '/api/settings',
      responses: {
        200: z.array(z.custom<typeof settings.$inferSelect>()),
      },
    },
    update: {
      method: 'POST' as const,
      path: '/api/settings',
      input: z.object({ key: z.string(), value: z.string() }),
      responses: {
        200: z.custom<typeof settings.$inferSelect>(),
        400: errorSchemas.validation,
      },
    },
  },

  // === CHAT HISTORY ROUTES ===
  sessions: {
    list: {
      method: 'GET' as const,
      path: '/api/sessions',
      responses: {
        200: z.array(z.custom<typeof chatSessions.$inferSelect>()),
      },
    },
    create: {
      method: 'POST' as const,
      path: '/api/sessions',
      input: insertChatSessionSchema,
      responses: {
        201: z.custom<typeof chatSessions.$inferSelect>(),
        400: errorSchemas.validation,
      },
    },
    get: {
      method: 'GET' as const,
      path: '/api/sessions/:id',
      responses: {
        200: z.custom<typeof chatSessions.$inferSelect & { messages: typeof messages.$inferSelect[] }>(),
        404: errorSchemas.notFound,
      },
    },
    delete: {
      method: 'DELETE' as const,
      path: '/api/sessions/:id',
      responses: {
        204: z.void(),
        404: errorSchemas.notFound,
      },
    },
  },
  messages: {
    create: {
      method: 'POST' as const,
      path: '/api/sessions/:id/messages',
      input: insertMessageSchema.omit({ sessionId: true }),
      responses: {
        201: z.custom<typeof messages.$inferSelect>(),
        400: errorSchemas.validation,
      },
    },
  },
};

export function buildUrl(path: string, params?: Record<string, string | number>): string {
  let url = path;
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (url.includes(`:${key}`)) {
        url = url.replace(`:${key}`, String(value));
      }
    });
  }
  return url;
}

// Type helpers
export type Setting = z.infer<typeof api.settings.update.responses[200]>;
export type OllamaModelsResponse = z.infer<typeof api.ollama.models.responses[200]>;
