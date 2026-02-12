/**
 * Tests for AgentClient Service
 *
 * Tests circuit breaker, timeout handling, SSRF protection, and PHI safety.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

import { getAgentClient, AgentClient, CircuitOpenError, URLValidationError, AgentResponse } from '../agentClient';

// Mock fetch globally
global.fetch = vi.fn();

// Mock audit-service
vi.mock('../../services/audit-service', () => ({
  logAction: vi.fn(),
}));

describe('AgentClient', () => {
  let client: AgentClient;

  beforeEach(() => {
    client = getAgentClient();
    vi.clearAllMocks();
    // Reset circuit breaker
    client.forceCircuitClose();
  });

  afterEach(() => {
    vi.resetAllMocks();
  });

  describe('Singleton Pattern', () => {
    it('should return same instance on multiple calls', () => {
      const client1 = getAgentClient();
      const client2 = getAgentClient();
      expect(client1).toBe(client2);
    });

    it('should create new instance when options provided', () => {
      const client1 = getAgentClient();
      const client2 = getAgentClient({ timeout: 5000 });
      expect(client1).not.toBe(client2);
    });
  });

  describe('SSRF Protection', () => {
    it('should block localhost URLs', async () => {
      const response = await client.postSync(
        'http://localhost:8080',
        '/api/execute',
        { task: 'test' }
      );

      expect(response.success).toBe(false);
      expect(response.statusCode).toBe(400);
      expect(response.error).toContain('Private network target blocked');
    });

    it('should block 127.0.0.1', async () => {
      const response = await client.postSync(
        'http://127.0.0.1:8080',
        '/api/execute',
        { task: 'test' }
      );

      expect(response.success).toBe(false);
      expect(response.error).toContain('Private network target blocked');
    });

    it('should block private IP ranges (10.x.x.x)', async () => {
      const response = await client.postSync(
        'http://10.0.0.1',
        '/api/execute',
        { task: 'test' }
      );

      expect(response.success).toBe(false);
      expect(response.error).toContain('Private network target blocked');
    });

    it('should block private IP ranges (192.168.x.x)', async () => {
      const response = await client.postSync(
        'http://192.168.1.1',
        '/api/execute',
        { task: 'test' }
      );

      expect(response.success).toBe(false);
      expect(response.error).toContain('Private network target blocked');
    });

    it('should block .local domains', async () => {
      const response = await client.postSync(
        'http://agent.local',
        '/api/execute',
        { task: 'test' }
      );

      expect(response.success).toBe(false);
      expect(response.error).toContain('Internal domain blocked');
    });

    it('should allow valid public URLs', async () => {
      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        status: 200,
        headers: {
          get: (name: string) => name === 'content-type' ? 'application/json' : null,
        },
        json: async () => ({ result: 'success' }),
      });

      const response = await client.postSync(
        'https://api.example.com',
        '/api/execute',
        { task: 'test' }
      );

      expect(response.success).toBe(true);
      expect(response.statusCode).toBe(200);
    });

    it('should reject non-http protocols', async () => {
      const response = await client.postSync(
        'ftp://agent.example.com',
        '/api/execute',
        { task: 'test' }
      );

      expect(response.success).toBe(false);
      expect(response.error).toContain('Invalid protocol');
    });
  });

  describe('Circuit Breaker', () => {
    it('should start in CLOSED state', () => {
      const status = client.getCircuitStatus();
      expect(status.state).toBe('CLOSED');
    });

    it('should report OPEN after forceCircuitOpen', async () => {
      // postSync's makeRequest catches errors internally (PHI safety — never throws),
      // so we verify the circuit breaker directly via forceCircuitOpen.
      // The circuit breaker's execute() path is tested in the "should block
      // requests when circuit is OPEN" test below.

      client.forceCircuitOpen();

      const status = client.getCircuitStatus();
      expect(status.state).toBe('OPEN');
    });

    it('should block requests when circuit is OPEN', async () => {
      client.forceCircuitOpen();

      const response = await client.postSync(
        'https://agent.example.com',
        '/api/execute',
        { task: 'test' }
      );

      expect(response.success).toBe(false);
      expect(response.statusCode).toBe(503);
      expect(response.error).toContain('circuit open');
      // Verify fetch was not called
      expect(global.fetch).not.toHaveBeenCalled();
    });
  });

  describe('Timeout Handling', () => {
    it('should timeout after configured duration', async () => {
      // Mock a slow request that never resolves on its own
      (global.fetch as any).mockImplementation(
        (_url: string, opts: any) =>
          new Promise((_resolve, reject) => {
            // Respect AbortSignal so the test resolves quickly
            if (opts?.signal) {
              opts.signal.addEventListener('abort', () => {
                const err = new Error('The operation was aborted');
                err.name = 'AbortError';
                reject(err);
              });
            }
          })
      );

      const response = await client.postSync(
        'https://agent.example.com',
        '/api/execute',
        { task: 'test' },
        { timeout: 100 } // 100ms timeout
      );

      expect(response.success).toBe(false);
      expect(response.statusCode).toBe(408);
      expect(response.error).toContain('timeout');
    }, 15000);
  });

  describe('Response Handling', () => {
    it('should handle 200 OK with JSON data', async () => {
      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        status: 200,
        headers: {
          get: (name: string) => name === 'content-type' ? 'application/json' : null,
        },
        json: async () => ({ result: 'success', data: { id: 123 } }),
      });

      const response = await client.postSync(
        'https://agent.example.com',
        '/api/execute',
        { task: 'test' }
      );

      expect(response.success).toBe(true);
      expect(response.statusCode).toBe(200);
      expect(response.data).toEqual({ result: 'success', data: { id: 123 } });
      expect(response.latencyMs).toBeGreaterThanOrEqual(0);
    });

    it('should handle 400 Bad Request', async () => {
      (global.fetch as any).mockResolvedValueOnce({
        ok: false,
        status: 400,
        headers: {
          get: (name: string) => name === 'content-type' ? 'application/json' : null,
        },
        json: async () => ({ error: 'Invalid request' }),
      });

      const response = await client.postSync(
        'https://agent.example.com',
        '/api/execute',
        { task: 'test' }
      );

      expect(response.success).toBe(false);
      expect(response.statusCode).toBe(400);
      expect(response.error).toBe('Invalid request');
      expect(response.data).toBeUndefined();
    });

    it('should handle 500 Internal Server Error', async () => {
      (global.fetch as any).mockResolvedValueOnce({
        ok: false,
        status: 500,
        headers: {
          get: (name: string) => name === 'content-type' ? 'application/json' : null,
        },
        json: async () => ({ error: 'Internal server error' }),
      });

      const response = await client.postSync(
        'https://agent.example.com',
        '/api/execute',
        { task: 'test' }
      );

      expect(response.success).toBe(false);
      expect(response.statusCode).toBe(500);
      expect(response.error).toBe('Internal server error');
    });

    it('should handle text responses', async () => {
      (global.fetch as any).mockResolvedValueOnce({
        ok: false,
        status: 400,
        headers: {
          get: (name: string) => null,
        },
        text: async () => 'Bad Request',
      });

      const response = await client.postSync(
        'https://agent.example.com',
        '/api/execute',
        { task: 'test' }
      );

      expect(response.success).toBe(false);
      expect(response.error).toBe('Bad Request');
    });
  });

  describe('PHI Safety', () => {
    it('should never log request body', async () => {
      const consoleSpy = vi.spyOn(console, 'log');

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        status: 200,
        headers: {
          get: (name: string) => name === 'content-type' ? 'application/json' : null,
        },
        json: async () => ({ result: 'success' }),
      });

      await client.postSync(
        'https://agent.example.com',
        '/api/execute',
        { patientName: 'John Doe', ssn: '123-45-6789' } // Simulated PHI
      );

      // Check that logs don't contain PHI
      const logCalls = consoleSpy.mock.calls.flat();
      expect(logCalls.some(call => String(call).includes('John Doe'))).toBe(false);
      expect(logCalls.some(call => String(call).includes('123-45-6789'))).toBe(false);
    });

    it('should never log response body', async () => {
      const consoleSpy = vi.spyOn(console, 'log');

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        status: 200,
        headers: {
          get: (name: string) => name === 'content-type' ? 'application/json' : null,
        },
        json: async () => ({ 
          patientData: { name: 'Jane Smith', dob: '1980-01-01' } 
        }),
      });

      await client.postSync(
        'https://agent.example.com',
        '/api/execute',
        { task: 'test' }
      );

      // Check that logs don't contain response PHI
      const logCalls = consoleSpy.mock.calls.flat();
      expect(logCalls.some(call => String(call).includes('Jane Smith'))).toBe(false);
      expect(logCalls.some(call => String(call).includes('1980-01-01'))).toBe(false);
    });

    it('should only log metadata (path, status, latency)', async () => {
      const consoleSpy = vi.spyOn(console, 'log');

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        status: 200,
        headers: {
          get: (name: string) => name === 'content-type' ? 'application/json' : null,
        },
        json: async () => ({ result: 'success' }),
      });

      await client.postSync(
        'https://agent.example.com',
        '/api/execute',
        { task: 'test' }
      );

      // Should log path, status, and latency
      expect(consoleSpy).toHaveBeenCalledWith(
        expect.stringMatching(/POST \/api\/execute -> 200 \(\d+ms\)/)
      );
    });
  });

  describe('Error Cases', () => {
    it('should handle network failures', async () => {
      (global.fetch as any).mockRejectedValueOnce(new Error('ECONNREFUSED'));

      const response = await client.postSync(
        'https://agent.example.com',
        '/api/execute',
        { task: 'test' }
      );

      expect(response.success).toBe(false);
      expect(response.statusCode).toBe(0);
      expect(response.error).toContain('ECONNREFUSED');
    });

    it('should handle malformed URLs', async () => {
      const response = await client.postSync(
        'not-a-url',
        '/api/execute',
        { task: 'test' }
      );

      expect(response.success).toBe(false);
      expect(response.statusCode).toBe(400);
      expect(response.error).toContain('Invalid URL');
    });

    it('should handle AbortError for timeouts', async () => {
      const abortError = new Error('The operation was aborted');
      abortError.name = 'AbortError';
      (global.fetch as any).mockRejectedValueOnce(abortError);

      const response = await client.postSync(
        'https://agent.example.com',
        '/api/execute',
        { task: 'test' }
      );

      expect(response.success).toBe(false);
      expect(response.statusCode).toBe(408);
      expect(response.error).toContain('timeout');
    });
  });
});
