/**
 * AI Bridge Connection Pool
 * 
 * Manages HTTP connections and request queuing for optimal performance
 */

import axios, { AxiosInstance } from 'axios';
import { createLogger } from '../utils/logger';
import http from 'http';
import https from 'https';

const logger = createLogger('ai-bridge-pool');

interface ConnectionPoolConfig {
  maxConnections: number;
  keepAliveTimeout: number;
  timeout: number;
  retryAttempts: number;
  retryDelay: number;
}

interface PooledRequest {
  id: string;
  url: string;
  data: any;
  resolve: (value: any) => void;
  reject: (error: any) => void;
  priority: number;
  timestamp: number;
}

class AIBridgeConnectionPool {
  private client: AxiosInstance;
  private requestQueue: PooledRequest[] = [];
  private activeRequests = 0;
  private config: ConnectionPoolConfig;
  
  constructor(config: Partial<ConnectionPoolConfig> = {}) {
    this.config = {
      maxConnections: 5,
      keepAliveTimeout: 30000,
      timeout: 60000,
      retryAttempts: 3,
      retryDelay: 1000,
      ...config
    };
    
    this.client = axios.create({
      timeout: this.config.timeout,
      maxRedirects: 3,
      headers: {
        'Connection': 'keep-alive',
        'Keep-Alive': `timeout=${this.config.keepAliveTimeout / 1000}`,
      },
      // Enable connection pooling
      httpAgent: new http.Agent({
        keepAlive: true,
        maxSockets: this.config.maxConnections,
        timeout: this.config.keepAliveTimeout,
      }),
      httpsAgent: new https.Agent({
        keepAlive: true,
        maxSockets: this.config.maxConnections,
        timeout: this.config.keepAliveTimeout,
      }),
    });
    
    // Start queue processor
    this.processQueue();
  }
  
  /**
   * Add request to the pool with priority handling
   */
  async request(
    url: string,
    data: any,
    priority: number = 0
  ): Promise<any> {
    return new Promise((resolve, reject) => {
      const request: PooledRequest = {
        id: `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        url,
        data,
        resolve,
        reject,
        priority,
        timestamp: Date.now(),
      };
      
      // Insert by priority (higher priority first)
      const insertIndex = this.requestQueue.findIndex(
        req => req.priority < priority
      );
      
      if (insertIndex === -1) {
        this.requestQueue.push(request);
      } else {
        this.requestQueue.splice(insertIndex, 0, request);
      }
      
      logger.debug(`Request queued: ${request.id} (priority: ${priority}, queue: ${this.requestQueue.length})`);
    });
  }
  
  /**
   * Process the request queue
   */
  private async processQueue() {
    setInterval(async () => {
      if (this.requestQueue.length === 0 || this.activeRequests >= this.config.maxConnections) {
        return;
      }
      
      const request = this.requestQueue.shift();
      if (!request) return;
      
      this.activeRequests++;
      
      try {
        const result = await this.executeRequest(request);
        request.resolve(result);
      } catch (error) {
        request.reject(error);
      } finally {
        this.activeRequests--;
      }
    }, 100); // Check every 100ms
  }
  
  /**
   * Execute individual request with retry logic
   */
  private async executeRequest(request: PooledRequest): Promise<any> {
    let lastError: any;
    
    for (let attempt = 1; attempt <= this.config.retryAttempts; attempt++) {
      try {
        logger.debug(`Executing request: ${request.id} (attempt ${attempt})`);
        
        const startTime = Date.now();
        const response = await this.client.post(request.url, request.data);
        const duration = Date.now() - startTime;
        
        logger.debug(`Request completed: ${request.id} (${duration}ms)`);
        return response;
        
      } catch (error: any) {
        lastError = error;
        
        // Don't retry client errors (4xx)
        if (error.response && error.response.status >= 400 && error.response.status < 500) {
          throw error;
        }
        
        if (attempt < this.config.retryAttempts) {
          const delay = this.config.retryDelay * Math.pow(2, attempt - 1);
          logger.warn(`Request failed: ${request.id} (attempt ${attempt}), retrying in ${delay}ms`);
          await this.sleep(delay);
        }
      }
    }
    
    logger.error(`Request failed after ${this.config.retryAttempts} attempts: ${request.id}`);
    throw lastError;
  }
  
  /**
   * Get pool statistics
   */
  getStats() {
    // Clean up old requests (older than 5 minutes)
    const fiveMinutesAgo = Date.now() - 5 * 60 * 1000;
    this.requestQueue = this.requestQueue.filter(req => req.timestamp > fiveMinutesAgo);
    
    return {
      activeRequests: this.activeRequests,
      queuedRequests: this.requestQueue.length,
      maxConnections: this.config.maxConnections,
      utilization: (this.activeRequests / this.config.maxConnections) * 100,
      avgWaitTime: this.calculateAverageWaitTime(),
    };
  }
  
  /**
   * Calculate average wait time for queued requests
   */
  private calculateAverageWaitTime(): number {
    if (this.requestQueue.length === 0) return 0;
    
    const now = Date.now();
    const totalWaitTime = this.requestQueue.reduce(
      (sum, req) => sum + (now - req.timestamp),
      0
    );
    
    return totalWaitTime / this.requestQueue.length;
  }
  
  /**
   * Utility sleep function
   */
  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
  
  /**
   * Close the connection pool
   */
  async close() {
    // Reject all pending requests
    this.requestQueue.forEach(req => {
      req.reject(new Error('Connection pool closed'));
    });
    this.requestQueue = [];
    
    // Note: axios doesn't have an explicit close method
    // Connections will be closed when the process exits
    logger.info('Connection pool closed');
  }
}

// Singleton instance
let connectionPool: AIBridgeConnectionPool | null = null;

export function getConnectionPool(): AIBridgeConnectionPool {
  if (!connectionPool) {
    connectionPool = new AIBridgeConnectionPool({
      maxConnections: parseInt(process.env.AI_BRIDGE_MAX_CONNECTIONS || '5'),
      keepAliveTimeout: parseInt(process.env.AI_BRIDGE_KEEPALIVE_TIMEOUT || '30000'),
      timeout: parseInt(process.env.AI_BRIDGE_REQUEST_TIMEOUT || '60000'),
      retryAttempts: parseInt(process.env.AI_BRIDGE_RETRY_ATTEMPTS || '3'),
      retryDelay: parseInt(process.env.AI_BRIDGE_RETRY_DELAY || '1000'),
    });
  }
  
  return connectionPool;
}

export function closeConnectionPool() {
  if (connectionPool) {
    connectionPool.close();
    connectionPool = null;
  }
}

export { AIBridgeConnectionPool };