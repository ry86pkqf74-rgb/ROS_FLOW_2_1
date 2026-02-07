/**
 * AI Bridge LLM service tests.
 * Verifies real provider execution path and non-mock response shape.
 */

import assert from 'node:assert';
import { describe, it, beforeEach, afterEach } from 'node:test';

import { callRealLLMProvider } from '../ai-bridge-llm';

const originalFetch = globalThis.fetch;

describe('ai-bridge-llm', () => {
  afterEach(() => {
    globalThis.fetch = originalFetch;
    delete process.env.ANTHROPIC_API_KEY;
    delete process.env.OPENAI_API_KEY;
  });

  describe('callRealLLMProvider', () => {
    it('returns non-mock response shape (content, usage, cost, finishReason)', async () => {
      process.env.ANTHROPIC_API_KEY = 'sk-ant-test';

      globalThis.fetch = async (url: string | URL) => {
        if (String(url).includes('anthropic.com')) {
          return new Response(
            JSON.stringify({
              content: [{ type: 'text', text: 'Real provider response for test.' }],
              usage: { input_tokens: 5, output_tokens: 8 },
              stop_reason: 'end_turn',
            }),
            { status: 200, headers: { 'Content-Type': 'application/json' } }
          );
        }
        return new Response('', { status: 404 });
      };

      const out = await callRealLLMProvider('Hello', 'claude-3-haiku-20240307', {
        maxTokens: 64,
        temperature: 0,
      });

      assert.strictEqual(typeof out.content, 'string');
      assert.ok(out.content.length > 0);
      assert.ok(!out.content.includes('AI Bridge Mock Response'), 'response must be non-mock');
      assert.strictEqual(out.content, 'Real provider response for test.');

      assert.strictEqual(out.usage.totalTokens, 13);
      assert.strictEqual(out.usage.promptTokens, 5);
      assert.strictEqual(out.usage.completionTokens, 8);

      assert.strictEqual(typeof out.cost.total, 'number');
      assert.strictEqual(typeof out.cost.input, 'number');
      assert.strictEqual(typeof out.cost.output, 'number');

      assert.strictEqual(out.finishReason, 'end_turn');
    });

    it('throws when no provider key is set', async () => {
      await assert.rejects(
        () => callRealLLMProvider('Hi', 'claude-3-haiku-20240307', {}),
        /ANTHROPIC_API_KEY is not set/
      );
    });

    it('throws for unsupported model', async () => {
      process.env.ANTHROPIC_API_KEY = 'sk-ant-test';
      await assert.rejects(
        () => callRealLLMProvider('Hi', 'unknown-model-123', {}),
        /Unsupported model/
      );
    });
  });
});
