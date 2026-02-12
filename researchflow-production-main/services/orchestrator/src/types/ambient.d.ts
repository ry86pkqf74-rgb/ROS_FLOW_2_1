/**
 * Ambient Type Declarations for External Modules
 * Linear Issue: ROS-59
 */

// ChromaDB — vector store client (used by @researchflow/vector-store)
declare module 'chromadb' {
  export interface CollectionMetadata {
    [key: string]: string | number | boolean;
  }

  export interface AddParams {
    ids: string[];
    embeddings?: number[][];
    documents?: string[];
    metadatas?: Array<Record<string, any>>;
  }

  export interface QueryParams {
    queryEmbeddings: number[][];
    nResults?: number;
    where?: Record<string, any>;
    include?: IncludeEnum[];
  }

  export interface QueryResponse {
    ids: string[][];
    embeddings: number[][][] | null;
    documents: (string | null)[][] | null;
    metadatas: (Record<string, any> | null)[][] | null;
    distances: number[][] | null;
  }

  export interface GetParams {
    ids?: string[];
    where?: Record<string, any>;
    include?: IncludeEnum[];
  }

  export interface GetResponse {
    ids: string[];
    embeddings: number[][] | null;
    documents: (string | null)[] | null;
    metadatas: (Record<string, any> | null)[] | null;
  }

  export interface Collection {
    name: string;
    metadata?: CollectionMetadata;
    add(params: AddParams): Promise<void>;
    query(params: QueryParams): Promise<QueryResponse>;
    get(params?: GetParams): Promise<GetResponse>;
    delete(params: { ids: string[] }): Promise<void>;
    update(params: { ids: string[]; embeddings?: number[][]; documents?: string[]; metadatas?: Array<Record<string, any>> }): Promise<void>;
    count(): Promise<number>;
  }

  export type IncludeEnum = 'documents' | 'metadatas' | 'embeddings' | 'distances';

  export class ChromaClient {
    constructor(params?: {
      path?: string;
      auth?: { provider: string; credentials: string } | undefined;
      tenant?: string;
      database?: string;
    });
    getOrCreateCollection(params: { name: string; metadata?: CollectionMetadata }): Promise<Collection>;
    deleteCollection(params: { name: string }): Promise<void>;
    listCollections(): Promise<Collection[]>;
    heartbeat(): Promise<number>;
  }

  export default ChromaClient;
}

// Socket.IO — real-time collaboration server
declare module 'socket.io' {
  export interface ServerOptions {
    cors?: { origin: string | string[]; methods?: string[] };
    path?: string;
    transports?: string[];
  }

  export interface Socket {
    id: string;
    data: Record<string, any>;
    join(room: string): void;
    leave(room: string): void;
    to(room: string): { emit(event: string, ...args: any[]): void };
    emit(event: string, ...args: any[]): void;
    on(event: string, listener: (...args: any[]) => void): void;
    disconnect(close?: boolean): void;
  }

  export class Server {
    constructor(httpServer?: any, opts?: Partial<ServerOptions>);
    sockets: { sockets: Map<string, Socket> };
    engine: { on(event: string, listener: (...args: any[]) => void): void };
    on(event: string, listener: (...args: any[]) => void): this;
    emit(event: string, ...args: any[]): boolean;
    close(fn?: (err?: Error) => void): void;
  }
}

// OpenAI
declare module 'openai' {
  export default class OpenAI {
    constructor(config?: any);
    chat: { completions: { create(params: any): Promise<any> } };
    images: { generate(params: any): Promise<any> };
    audio: {
      transcriptions: { create(params: any): Promise<any> };
      speech: { create(params: any): Promise<any> };
    };
    embeddings: {
      create(params: {
        model: string;
        input: string | string[];
        encoding_format?: string;
        dimensions?: number;
      }): Promise<{
        data: Array<{ embedding: number[]; index: number; object: string }>;
        model: string;
        object: string;
        usage: { prompt_tokens: number; total_tokens: number };
      }>;
    };
  }
  export interface ChatCompletionMessageParam {
    role: 'system' | 'user' | 'assistant';
    content: string;
  }
}

// PostgreSQL
declare module 'pg' {
  export class Pool {
    constructor(config?: any);
    query(text: string, values?: any[]): Promise<any>;
    connect(): Promise<any>;
    end(): Promise<void>;
  }
}

// Drizzle
declare module 'drizzle-orm/node-postgres' {
  export function drizzle(client: any, config?: any): any;
}

declare module 'drizzle-orm/pg-core' {
  export const pgTable: any;
  export const varchar: any;
  export const text: any;
  export const integer: any;
  export const boolean: any;
  export const timestamp: any;
  export const jsonb: any;
  export const serial: any;
}

// CORS
declare module 'cors' {
  const cors: any;
  export = cors;
}

// Dotenv
declare module 'dotenv' {
  export function config(options?: any): any;
}

// UUID
declare module 'uuid' {
  export function v4(): string;
  export function v1(): string;
  export function validate(uuid: string): boolean;
}

// WebSocket
declare module 'ws' {
  import { EventEmitter } from 'events';
  export class WebSocket extends EventEmitter {
    constructor(address: string | URL, options?: any);
    constructor(address: string | URL, protocols?: string | string[], options?: any);
    static OPEN: number;
    static CLOSED: number;
    readonly OPEN: number;
    readonly CLOSED: number;
    readyState: number;
    send(data: any, cb?: any): void;
    close(code?: number, reason?: string): void;
    ping(data?: any, mask?: boolean, cb?: any): void;
    terminate(): void;
  }
  export namespace WebSocket {
    type RawData = any;
    type Data = any;
  }
  export class WebSocketServer extends EventEmitter {
    constructor(options: any);
    clients: Set<WebSocket>;
    close(cb?: any): void;
    handleUpgrade(request: any, socket: any, head: any, cb: (client: WebSocket) => void): void;
  }
  export default WebSocket;
}

// Passport & Auth
declare module 'passport' {
  const passport: any;
  export = passport;
}

declare module 'express-session' {
  const session: any;
  export = session;
}

declare module 'connect-pg-simple' {
  const connectPgSimple: any;
  export = connectPgSimple;
}

declare module 'memoizee' {
  const memoizee: any;
  export = memoizee;
}

declare module 'openid-client' {
  export const Issuer: any;
}

declare module 'openid-client/passport' {
  export const Strategy: any;
}

// Utilities
declare module 'p-limit' {
  const pLimit: any;
  export = pLimit;
}

declare module 'p-retry' {
  const pRetry: any;
  export = pRetry;
}

declare module 'nanoid' {
  export function nanoid(size?: number): string;
  export function customAlphabet(alphabet: string, size?: number): any;
}

// Vite plugins
declare module 'vite' {
  export type PluginOption = any;
  export const defineConfig: any;
}

declare module '@vitejs/plugin-react' {
  const react: any;
  export default react;
}

declare module '@replit/vite-plugin-runtime-error-modal' {
  const plugin: any;
  export default plugin;
}

declare module '@replit/vite-plugin-cartographer' {
  const plugin: any;
  export default plugin;
}

declare module '@replit/vite-plugin-dev-banner' {
  const plugin: any;
  export default plugin;
}

// ioredis
declare module 'ioredis' {
  export default class Redis {
    constructor(url?: string, options?: any);
    get(key: string): Promise<string | null>;
    set(key: string, value: string, ...args: any[]): Promise<any>;
    del(key: string): Promise<number>;
    publish(channel: string, message: string): Promise<number>;
    subscribe(channel: string): Promise<void>;
    on(event: string, handler: any): this;
    quit(): Promise<void>;
    // List operations
    llen(key: string): Promise<number>;
    lrange(key: string, start: number, stop: number): Promise<string[]>;
    rpush(key: string, ...values: string[]): Promise<number>;
    ltrim(key: string, start: number, stop: number): Promise<string>;
    expire(key: string, seconds: number): Promise<number>;
    setex(key: string, seconds: number, value: string): Promise<any>;
    flushdb(...args: any[]): Promise<any>;
    getBuffer(key: string): Promise<any>;
    keys(pattern: string): Promise<string[]>;
    info(...args: any[]): Promise<any>;
    dbsize(): Promise<number>;
    ttl(key: string): Promise<number>;
    memory(...args: any[]): Promise<any>;
    // Streams/health helpers (permissive typing)
    xadd(...args: any[]): Promise<any>;
    xgroup(...args: any[]): Promise<any>;
    xreadgroup(...args: any[]): Promise<any>;
    xack(...args: any[]): Promise<any>;
    xpending(...args: any[]): Promise<any>;
    xclaim(...args: any[]): Promise<any>;
    xrange(...args: any[]): Promise<any>;
    xinfo(...args: any[]): Promise<any>;
    ping(...args: any[]): Promise<any>;
    pipeline(): RedisPipeline;
  }
  export interface RedisPipeline {
    rpush(key: string, ...values: string[]): this;
    ltrim(key: string, start: number, stop: number): this;
    expire(key: string, seconds: number): this;
    xadd(...args: any[]): this;
    exec(): Promise<Array<[Error | null, any]>>;
  }
}

// Anthropic
declare module '@anthropic-ai/sdk' {
  export default class Anthropic {
    constructor(config?: any);
    messages: { create(params: any): Promise<any> };
  }
}

// Multer
declare module 'multer' {
  const multer: any;
  export = multer;
}

// More modules
declare module 'axios' { const axios: any; export default axios; export const create: any; }
declare module 'body-parser' { const bp: any; export = bp; }
declare module 'helmet' { const helmet: any; export = helmet; }
declare module 'jsonwebtoken' { export const sign: any; export const verify: any; export const decode: any; }
declare module 'express-rate-limit' { const rateLimit: any; export default rateLimit; }
declare module 'rate-limit-redis' { const store: any; export default store; }
declare module 'node-fetch' { const fetch: any; export default fetch; }
declare module 'form-data' { export default class FormData { append(k: string, v: any): void; } }
declare module 'archiver' { const archiver: any; export = archiver; }
declare module 'bottleneck' {
  export default class Bottleneck {
    constructor(opts?: any);
    schedule<T>(opts: Record<string, any>, fn: () => Promise<T>): Promise<T>;
    schedule<T>(fn: () => Promise<T>): Promise<T>;
    on(event: string, callback: (...args: any[]) => void): void;
    once(event: string, callback: (...args: any[]) => void): void;
    stop(options?: { dropWaitingJobs?: boolean }): Promise<void>;
    counts(): { RECEIVED: number; QUEUED: number; RUNNING: number; EXECUTING: number; DONE: number; RESERVOIR: number };
  }
}
declare module 'prom-client' { export const Registry: any; export const Counter: any; export const Gauge: any; export const Histogram: any; export const collectDefaultMetrics: any; }
declare module 'redis' {
  export type RedisClientType = any;
  export const createClient: any;
}
declare module 'drizzle-orm' { export const eq: any; export const and: any; export const or: any; export const desc: any; export const asc: any; export const gt: any; export const lt: any; export const gte: any; export const lte: any; export const sql: any; export const inArray: any; }

// Internal workspace packages
declare module '@researchflow/ai-router' { export const routeToModel: any; export const getModelConfig: any; }
declare module '@researchflow/ai-router/*' { const mod: any; export = mod; }
// @researchflow/manuscript-engine — resolved via tsconfig paths; ambient override removed (PR151)
// declare module '@researchflow/manuscript-engine' { export const ManuscriptService: any; }
// declare module '@researchflow/manuscript-engine/*' { const mod: any; export = mod; }
declare module '@researchflow/notion-integration' { export const NotionClient: any; }
declare module '@researchflow/cursor-integration' { const mod: any; export = mod; }
declare module '@researchflow/cursor-integration/*' { const mod: any; export = mod; }

// Local modules
declare module '../lib/db' { export const db: any; export const pool: any; }
declare module '../lib/db.js' { export const db: any; export const pool: any; }
declare module '../../lib/db' { export const db: any; export const pool: any; }
declare module '../../lib/db.js' { export const db: any; export const pool: any; }
declare module '../config' { const config: any; export default config; }
declare module './branch-persistence.service' { export class BranchPersistenceService { static getInstance(): any; } }
