/**
 * Qwen3 Local Provider Tests
 *
 * Tests for the local Qwen3-Coder provider including:
 * - Provider initialization and configuration
 * - Health check behavior
 * - Completion requests
 * - Task eligibility (shouldUseLocal)
 * - Error handling and timeouts
 *
 * Last Updated: 2026-01-29
 */

import { describe, it, expect, beforeEach, afterEach, vi, type Mock } from 'vitest';
import {
  QwenLocalProvider,
  shouldUseLocal,
  LOCAL_ELIGIBLE_TASKS,
  type CompletionRequest,
  type QwenLocalConfig,
} from '../src/providers/qwen-local';

// Mock global fetch
const mockFetch = vi.fn();
global.fetch = mockFetch;

// Mock console methods to suppress log output during tests
vi.spyOn(console, 'log').mockImplementation(() => {});
vi.spyOn(console, 'warn').mockImplementation(() => {});

describe('QwenLocalProvider', () => {
  let provider: QwenLocalProvider;

  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
    mockFetch.mockReset();
  });

  afterEach(() => {
    if (provider) {
      provider.shutdown();
    }
    vi.useRealTimers();
  });

  // ===================
  // Constructor Tests
  // ===================

  describe('constructor', () => {
    it('should initialize with default config when no options provided', () => {
      provider = new QwenLocalProvider();
      const config = provider.getConfig();

      expect(config.name).toBe('qwen3-coder-local');
      expect(config.contextWindow).toBe(32768);
      expect(config.maxTokens).toBe(8192);
    });

    it('should override defaults with provided config', () => {
      provider = new QwenLocalProvider({
        name: 'custom-qwen',
        endpoint: 'http://custom:11434',
        model: 'custom-model:latest',
        contextWindow: 16384,
        maxTokens: 4096,
        temperature: 0.5,
      });

      const config = provider.getConfig();
      expect(config.name).toBe('custom-qwen');
      expect(config.contextWindow).toBe(16384);
      expect(config.maxTokens).toBe(4096);
    });
  });

  // ===================
  // Health Check Tests
  // ===================

  describe('checkHealth', () => {
    it('should return true when Ollama responds with available model', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            models: [
              { name: 'ai/qwen3-coder:latest', model: 'ai/qwen3-coder:latest', size: 30000000000 },
            ],
          }),
      });

      provider = new QwenLocalProvider();
      const healthy = await provider.checkHealth();

      expect(healthy).toBe(true);
      expect(provider.isAvailable()).toBe(true);
    });

    it('should return false when model is not in available list', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            models: [{ name: 'llama2:latest', model: 'llama2:latest', size: 7000000000 }],
          }),
      });

      provider = new QwenLocalProvider();
      const healthy = await provider.checkHealth();

      expect(healthy).toBe(false);
      expect(provider.isAvailable()).toBe(false);
    });

    it('should return false when Ollama is not responding', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Connection refused'));

      provider = new QwenLocalProvider();
      const healthy = await provider.checkHealth();

      expect(healthy).toBe(false);
      expect(provider.isAvailable()).toBe(false);
    });

    it('should increment consecutive failures on repeated errors', async () => {
      mockFetch.mockRejectedValue(new Error('Connection refused'));

      provider = new QwenLocalProvider();

      // First failure
      await provider.checkHealth();
      let status = provider.getHealthStatus();
      expect(status.failures).toBe(1);

      // Second failure
      await provider.checkHealth();
      status = provider.getHealthStatus();
      expect(status.failures).toBe(2);

      // Third failure
      await provider.checkHealth();
      status = provider.getHealthStatus();
      expect(status.failures).toBe(3);
    });

    it('should reset consecutive failures on successful check', async () => {
      // First fail
      mockFetch.mockRejectedValueOnce(new Error('Connection refused'));
      provider = new QwenLocalProvider();
      await provider.checkHealth();
      expect(provider.getHealthStatus().failures).toBe(1);

      // Then succeed
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            models: [{ name: 'ai/qwen3-coder:latest', model: 'ai/qwen3-coder:latest', size: 30000000000 }],
          }),
      });
      await provider.checkHealth();
      expect(provider.getHealthStatus().failures).toBe(0);
    });

    it('should handle non-ok HTTP response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
      });

      provider = new QwenLocalProvider();
      const healthy = await provider.checkHealth();

      expect(healthy).toBe(false);
      expect(provider.getHealthStatus().failures).toBe(1);
    });
  });

  // ===================
  // Initialize Tests
  // ===================

  describe('initialize', () => {
    it('should perform initial health check on initialization', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            models: [{ name: 'ai/qwen3-coder:latest', model: 'ai/qwen3-coder:latest', size: 30000000000 }],
          }),
      });

      provider = new QwenLocalProvider();
      await provider.initialize();

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/tags'),
        expect.objectContaining({ method: 'GET' })
      );
      expect(provider.isAvailable()).toBe(true);
    });

    it('should set up periodic health checks', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            models: [{ name: 'ai/qwen3-coder:latest', model: 'ai/qwen3-coder:latest', size: 30000000000 }],
          }),
      });

      provider = new QwenLocalProvider({ healthCheckIntervalMs: 5000 });
      await provider.initialize();

      // Initial call
      expect(mockFetch).toHaveBeenCalledTimes(1);

      // Advance timer by health check interval
      await vi.advanceTimersByTimeAsync(5000);
      expect(mockFetch).toHaveBeenCalledTimes(2);

      // Advance again
      await vi.advanceTimersByTimeAsync(5000);
      expect(mockFetch).toHaveBeenCalledTimes(3);
    });
  });

  // ===================
  // Complete Tests
  // ===================

  describe('complete', () => {
    const sampleRequest: CompletionRequest = {
      messages: [
        { role: 'system', content: 'You are a code reviewer.' },
        { role: 'user', content: 'Review this function.' },
      ],
      temperature: 0.1,
      maxTokens: 1000,
    };

    it('should call Ollama API and return formatted response', async () => {
      // Setup health check response
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            models: [{ name: 'ai/qwen3-coder:latest', model: 'ai/qwen3-coder:latest', size: 30000000000 }],
          }),
      });

      // Setup completion response
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            model: 'ai/qwen3-coder:latest',
            message: { role: 'assistant', content: 'Code looks good!' },
            done: true,
            prompt_eval_count: 50,
            eval_count: 20,
          }),
      });

      provider = new QwenLocalProvider();
      await provider.initialize();

      const response = await provider.complete(sampleRequest);

      expect(response.content).toBe('Code looks good!');
      expect(response.provider).toBe('qwen-local');
      expect(response.cost).toBe(0); // Local = free
      expect(response.usage.promptTokens).toBe(50);
      expect(response.usage.completionTokens).toBe(20);
      expect(response.usage.totalTokens).toBe(70);
    });

    it('should throw error when provider is unhealthy', async () => {
      mockFetch.mockRejectedValue(new Error('Connection refused'));

      provider = new QwenLocalProvider();
      // Make provider unhealthy
      await provider.checkHealth();

      await expect(provider.complete(sampleRequest)).rejects.toThrow(
        'Qwen3 local model is not available'
      );
    });

    it('should retry health check once before failing', async () => {
      // First health check fails
      mockFetch.mockRejectedValueOnce(new Error('Connection refused'));
      // Second health check succeeds
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            models: [{ name: 'ai/qwen3-coder:latest', model: 'ai/qwen3-coder:latest', size: 30000000000 }],
          }),
      });
      // Completion succeeds
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            model: 'ai/qwen3-coder:latest',
            message: { role: 'assistant', content: 'Success!' },
            done: true,
          }),
      });

      provider = new QwenLocalProvider();
      await provider.checkHealth(); // First check fails

      const response = await provider.complete(sampleRequest);
      expect(response.content).toBe('Success!');
    });

    it('should handle API error response', async () => {
      // Health check succeeds
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            models: [{ name: 'ai/qwen3-coder:latest', model: 'ai/qwen3-coder:latest', size: 30000000000 }],
          }),
      });
      // Completion fails
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        text: () => Promise.resolve('Internal server error'),
      });

      provider = new QwenLocalProvider();
      await provider.initialize();

      await expect(provider.complete(sampleRequest)).rejects.toThrow('Qwen3 request failed (500)');
    });

    it('should estimate tokens when not provided by API', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            models: [{ name: 'ai/qwen3-coder:latest', model: 'ai/qwen3-coder:latest', size: 30000000000 }],
          }),
      });

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            model: 'ai/qwen3-coder:latest',
            message: { role: 'assistant', content: 'Response text here.' },
            done: true,
            // No token counts provided
          }),
      });

      provider = new QwenLocalProvider();
      await provider.initialize();

      const response = await provider.complete(sampleRequest);

      // Token estimate: ~4 chars per token
      expect(response.usage.promptTokens).toBeGreaterThan(0);
      expect(response.usage.completionTokens).toBeGreaterThan(0);
    });

    it('should always report zero cost for local inference', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            models: [{ name: 'ai/qwen3-coder:latest', model: 'ai/qwen3-coder:latest', size: 30000000000 }],
          }),
      });

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            model: 'ai/qwen3-coder:latest',
            message: { role: 'assistant', content: 'Response' },
            done: true,
            prompt_eval_count: 1000,
            eval_count: 500,
          }),
      });

      provider = new QwenLocalProvider();
      await provider.initialize();

      const response = await provider.complete(sampleRequest);
      expect(response.cost).toBe(0);
    });
  });

  // ===================
  // Tier & Config Tests
  // ===================

  describe('getTier', () => {
    it('should always return LOCAL', () => {
      provider = new QwenLocalProvider();
      expect(provider.getTier()).toBe('LOCAL');
    });
  });

  describe('getConfig', () => {
    it('should return model configuration', () => {
      provider = new QwenLocalProvider({
        name: 'test-qwen',
        contextWindow: 16000,
        maxTokens: 4000,
      });

      const config = provider.getConfig();
      expect(config).toEqual({
        name: 'test-qwen',
        contextWindow: 16000,
        maxTokens: 4000,
      });
    });
  });

  describe('getHealthStatus', () => {
    it('should return health status object', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            models: [{ name: 'ai/qwen3-coder:latest', model: 'ai/qwen3-coder:latest', size: 30000000000 }],
          }),
      });

      provider = new QwenLocalProvider();
      await provider.checkHealth();

      const status = provider.getHealthStatus();
      expect(status).toHaveProperty('healthy', true);
      expect(status).toHaveProperty('lastCheck');
      expect(status.lastCheck).toBeInstanceOf(Date);
      expect(status).toHaveProperty('failures', 0);
    });
  });

  // ===================
  // Shutdown Tests
  // ===================

  describe('shutdown', () => {
    it('should clear health check interval', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            models: [{ name: 'ai/qwen3-coder:latest', model: 'ai/qwen3-coder:latest', size: 30000000000 }],
          }),
      });

      provider = new QwenLocalProvider({ healthCheckIntervalMs: 1000 });
      await provider.initialize();

      // Verify interval is running
      expect(mockFetch).toHaveBeenCalledTimes(1);
      await vi.advanceTimersByTimeAsync(1000);
      expect(mockFetch).toHaveBeenCalledTimes(2);

      // Shutdown and verify interval stops
      provider.shutdown();
      await vi.advanceTimersByTimeAsync(5000);
      expect(mockFetch).toHaveBeenCalledTimes(2); // No additional calls
    });
  });
});

// ===================
// shouldUseLocal Tests
// ===================

describe('shouldUseLocal', () => {
  describe('task eligibility', () => {
    it('should return true for eligible code tasks', () => {
      expect(shouldUseLocal('code_review')).toBe(true);
      expect(shouldUseLocal('code_refactor')).toBe(true);
      expect(shouldUseLocal('lint_fix')).toBe(true);
      expect(shouldUseLocal('unit_test_generation')).toBe(true);
      expect(shouldUseLocal('docstring_generation')).toBe(true);
    });

    it('should return false for non-eligible tasks', () => {
      expect(shouldUseLocal('phi_scan')).toBe(false);
      expect(shouldUseLocal('policy_check')).toBe(false);
      expect(shouldUseLocal('protocol_reasoning')).toBe(false);
      expect(shouldUseLocal('unknown_task')).toBe(false);
    });
  });

  describe('audit requirements', () => {
    it('should return false when requiresAudit is true', () => {
      expect(shouldUseLocal('code_review', { requiresAudit: true })).toBe(false);
      expect(shouldUseLocal('lint_fix', { requiresAudit: true })).toBe(false);
    });

    it('should return true for eligible tasks without audit requirement', () => {
      expect(shouldUseLocal('code_review', { requiresAudit: false })).toBe(true);
    });
  });

  describe('preferLocal option', () => {
    it('should return false when preferLocal is false', () => {
      expect(shouldUseLocal('code_review', { preferLocal: false })).toBe(false);
    });

    it('should return true when preferLocal is true (default)', () => {
      expect(shouldUseLocal('code_review', { preferLocal: true })).toBe(true);
      expect(shouldUseLocal('code_review')).toBe(true); // Default
    });
  });

  describe('token limits', () => {
    it('should return false when estimated tokens exceed limit', () => {
      expect(shouldUseLocal('code_review', { estimatedTokens: 30000 })).toBe(false);
      expect(shouldUseLocal('code_review', { estimatedTokens: 25000 })).toBe(false);
    });

    it('should return true when estimated tokens within limit', () => {
      expect(shouldUseLocal('code_review', { estimatedTokens: 20000 })).toBe(true);
      expect(shouldUseLocal('code_review', { estimatedTokens: 10000 })).toBe(true);
    });
  });

  describe('combined options', () => {
    it('should return false if any disqualifying condition is met', () => {
      // Audit required overrides eligibility
      expect(
        shouldUseLocal('code_review', {
          requiresAudit: true,
          preferLocal: true,
          estimatedTokens: 1000,
        })
      ).toBe(false);

      // Prefer not local overrides eligibility
      expect(
        shouldUseLocal('code_review', {
          requiresAudit: false,
          preferLocal: false,
          estimatedTokens: 1000,
        })
      ).toBe(false);

      // Token limit overrides eligibility
      expect(
        shouldUseLocal('code_review', {
          requiresAudit: false,
          preferLocal: true,
          estimatedTokens: 50000,
        })
      ).toBe(false);
    });

    it('should return true only when all conditions are met', () => {
      expect(
        shouldUseLocal('code_review', {
          requiresAudit: false,
          preferLocal: true,
          estimatedTokens: 10000,
        })
      ).toBe(true);
    });
  });
});

// ===================
// LOCAL_ELIGIBLE_TASKS Tests
// ===================

describe('LOCAL_ELIGIBLE_TASKS', () => {
  it('should contain expected code-related tasks', () => {
    const expectedTasks = [
      'code_review',
      'code_refactor',
      'lint_fix',
      'syntax_check',
      'documentation',
      'docstring_generation',
      'unit_test_generation',
      'code_explanation',
      'type_annotation',
      'variable_rename',
      'extract_function',
      'simplify_conditional',
      'remove_dead_code',
      'add_error_handling',
      'convert_syntax',
    ];

    expectedTasks.forEach((task) => {
      expect(LOCAL_ELIGIBLE_TASKS.has(task)).toBe(true);
    });
  });

  it('should NOT contain PHI-sensitive tasks', () => {
    const blockedTasks = ['phi_scan', 'policy_check', 'protocol_reasoning', 'complex_synthesis'];

    blockedTasks.forEach((task) => {
      expect(LOCAL_ELIGIBLE_TASKS.has(task)).toBe(false);
    });
  });

  it('should be a Set for efficient lookup', () => {
    expect(LOCAL_ELIGIBLE_TASKS).toBeInstanceOf(Set);
  });
});
