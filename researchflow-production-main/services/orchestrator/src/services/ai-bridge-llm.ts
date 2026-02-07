/**
 * AI Bridge LLM Provider Execution
 *
 * Real LLM calls for the AI Bridge using env-configured providers.
 * Uses OPENAI_API_KEY and ANTHROPIC_API_KEY from environment (see .env.example).
 * No provider keys are hardcoded.
 */

import { createLogger } from '../utils/logger';

const logger = createLogger('ai-bridge-llm');

export interface BridgeLLMResponse {
  content: string;
  usage: { totalTokens: number; promptTokens: number; completionTokens: number };
  cost: { total: number; input: number; output: number };
  finishReason: string;
}

export interface BridgeLLMOptions {
  maxTokens?: number;
  temperature?: number;
  taskType?: string;
}

// Per-million-token USD pricing (input, output) for cost calculation
const ANTHROPIC_PRICING: Record<string, { input: number; output: number }> = {
  'claude-3-opus-20240229': { input: 15.0, output: 75.0 },
  'claude-3-sonnet-20240229': { input: 3.0, output: 15.0 },
  'claude-3-haiku-20240307': { input: 0.25, output: 1.25 },
  'claude-3-5-sonnet-20241022': { input: 3.0, output: 15.0 },
  'claude-3-5-opus-20240620': { input: 15.0, output: 75.0 },
  'claude-sonnet-4-5-20250929': { input: 3.0, output: 15.0 },
  'claude-opus-4-5-20251101': { input: 15.0, output: 75.0 },
  'claude-haiku-4-5-20251001': { input: 0.25, output: 1.25 },
};

const OPENAI_PRICING: Record<string, { input: number; output: number }> = {
  'gpt-4': { input: 30.0, output: 60.0 },
  'gpt-4-turbo': { input: 10.0, output: 30.0 },
  'gpt-4o': { input: 5.0, output: 15.0 },
  'gpt-4o-mini': { input: 0.15, output: 0.6 },
  'gpt-3.5-turbo': { input: 0.5, output: 1.5 },
};

function getAnthropicCost(model: string, inputTokens: number, outputTokens: number): number {
  const pricing = ANTHROPIC_PRICING[model] ?? ANTHROPIC_PRICING['claude-3-haiku-20240307'];
  return (
    (inputTokens / 1_000_000) * pricing.input +
    (outputTokens / 1_000_000) * pricing.output
  );
}

function getOpenAICost(model: string, inputTokens: number, outputTokens: number): number {
  const pricing = OPENAI_PRICING[model] ?? OPENAI_PRICING['gpt-4'];
  return (
    (inputTokens / 1_000_000) * pricing.input +
    (outputTokens / 1_000_000) * pricing.output
  );
}

function isAnthropicModel(model: string): boolean {
  return /^claude-/i.test(model);
}

function isOpenAIModel(model: string): boolean {
  return /^gpt-/i.test(model);
}

/**
 * Call Anthropic Messages API (non-streaming)
 */
async function callAnthropic(
  prompt: string,
  model: string,
  options: BridgeLLMOptions
): Promise<BridgeLLMResponse> {
  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) {
    throw new Error('ANTHROPIC_API_KEY is not set. Set it in .env for real LLM execution.');
  }

  const maxTokens = options.maxTokens ?? 4096;
  const temperature = Math.min(2, Math.max(0, options.temperature ?? 0.7));

  const response = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': apiKey,
      'anthropic-version': '2023-06-01',
    },
    body: JSON.stringify({
      model,
      max_tokens: maxTokens,
      temperature,
      messages: [{ role: 'user' as const, content: prompt }],
    }),
  });

  if (!response.ok) {
    const text = await response.text();
    logger.warn('Anthropic API error', { status: response.status, body: text });
    throw new Error(`Anthropic API error: ${response.status} ${text}`);
  }

  const data = (await response.json()) as {
    content: Array<{ type: string; text: string }>;
    usage: { input_tokens: number; output_tokens: number };
    stop_reason?: string;
  };

  const content = data.content?.map((b) => b.text).join('') ?? '';
  const promptTokens = data.usage?.input_tokens ?? 0;
  const completionTokens = data.usage?.output_tokens ?? 0;
  const totalTokens = promptTokens + completionTokens;
  const inputCost = getAnthropicCost(model, promptTokens, 0);
  const outputCost = getAnthropicCost(model, 0, completionTokens);
  const totalCost = getAnthropicCost(model, promptTokens, completionTokens);

  return {
    content,
    usage: { totalTokens, promptTokens, completionTokens },
    cost: { total: totalCost, input: inputCost, output: outputCost },
    finishReason: data.stop_reason ?? 'stop',
  };
}

/**
 * Call OpenAI Chat Completions API (non-streaming)
 */
async function callOpenAI(
  prompt: string,
  model: string,
  options: BridgeLLMOptions
): Promise<BridgeLLMResponse> {
  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) {
    throw new Error('OPENAI_API_KEY is not set. Set it in .env for real LLM execution.');
  }

  const maxTokens = options.maxTokens ?? 4096;
  const temperature = Math.min(2, Math.max(0, options.temperature ?? 0.7));

  const response = await fetch('https://api.openai.com/v1/chat/completions', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      model,
      messages: [{ role: 'user' as const, content: prompt }],
      max_tokens: maxTokens,
      temperature,
    }),
  });

  if (!response.ok) {
    const text = await response.text();
    logger.warn('OpenAI API error', { status: response.status, body: text });
    throw new Error(`OpenAI API error: ${response.status} ${text}`);
  }

  const data = (await response.json()) as {
    choices: Array<{ message?: { content?: string }; finish_reason?: string }>;
    usage?: { prompt_tokens: number; completion_tokens: number; total_tokens: number };
  };

  const content = data.choices?.[0]?.message?.content ?? '';
  const promptTokens = data.usage?.prompt_tokens ?? 0;
  const completionTokens = data.usage?.completion_tokens ?? 0;
  const totalTokens = data.usage?.total_tokens ?? promptTokens + completionTokens;
  const inputCost = (promptTokens / 1_000_000) * (OPENAI_PRICING[model]?.input ?? 5);
  const outputCost = (completionTokens / 1_000_000) * (OPENAI_PRICING[model]?.output ?? 15);
  const totalCost = getOpenAICost(model, promptTokens, completionTokens);

  return {
    content,
    usage: { totalTokens, promptTokens, completionTokens },
    cost: { total: totalCost, input: inputCost, output: outputCost },
    finishReason: data.choices?.[0]?.finish_reason ?? 'stop',
  };
}

/**
 * Execute real LLM call using the appropriate provider based on model id.
 * Uses OPENAI_API_KEY and ANTHROPIC_API_KEY from environment.
 */
export async function callRealLLMProvider(
  prompt: string,
  model: string,
  options: BridgeLLMOptions = {}
): Promise<BridgeLLMResponse> {
  if (isAnthropicModel(model)) {
    return callAnthropic(prompt, model, options);
  }
  if (isOpenAIModel(model)) {
    return callOpenAI(prompt, model, options);
  }
  throw new Error(
    `Unsupported model "${model}" for AI Bridge. Use a claude-* or gpt-* model id from the router.`
  );
}

/**
 * Stream real LLM response from provider and yield content chunks.
 * Yields { type: 'content', content: string } then { type: 'done', response: BridgeLLMResponse }.
 */
export async function* streamRealLLMProvider(
  prompt: string,
  model: string,
  options: BridgeLLMOptions = {}
): AsyncGenerator<
  { type: 'content'; content: string } | { type: 'done'; response: BridgeLLMResponse },
  void,
  unknown
> {
  const maxTokens = options.maxTokens ?? 4096;
  const temperature = Math.min(2, Math.max(0, options.temperature ?? 0.7));

  if (isAnthropicModel(model)) {
    const apiKey = process.env.ANTHROPIC_API_KEY;
    if (!apiKey) {
      throw new Error('ANTHROPIC_API_KEY is not set. Set it in .env for streaming.');
    }

    const response = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': apiKey,
        'anthropic-version': '2023-06-01',
      },
      body: JSON.stringify({
        model,
        max_tokens: maxTokens,
        temperature,
        messages: [{ role: 'user' as const, content: prompt }],
        stream: true,
      }),
    });

    if (!response.ok) {
      const text = await response.text();
      throw new Error(`Anthropic stream error: ${response.status} ${text}`);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('No response body for Anthropic stream');
    }

    const decoder = new TextDecoder();
    let buffer = '';
    let fullContent = '';
    let inputTokens = 0;
    let outputTokens = 0;

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() ?? '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const raw = line.slice(6);
            if (raw === '[DONE]') continue;
            try {
              const event = JSON.parse(raw) as {
                type?: string;
                delta?: { type?: string; text?: string };
                message?: { usage?: { input_tokens?: number; output_tokens?: number } };
              };
              if (event.type === 'content_block_delta' && event.delta?.text) {
                fullContent += event.delta.text;
                yield { type: 'content', content: event.delta.text };
              }
              if (event.message?.usage) {
                inputTokens = event.message.usage.input_tokens ?? inputTokens;
                outputTokens = event.message.usage.output_tokens ?? outputTokens;
              }
            } catch {
              // ignore parse errors for non-JSON lines
            }
          }
        }
      }

      const totalTokens = inputTokens + outputTokens;
      const totalCost = getAnthropicCost(model, inputTokens, outputTokens);
      const inputCost = getAnthropicCost(model, inputTokens, 0);
      const outputCost = getAnthropicCost(model, 0, outputTokens);

      yield {
        type: 'done',
        response: {
          content: fullContent,
          usage: {
            totalTokens,
            promptTokens: inputTokens,
            completionTokens: outputTokens,
          },
          cost: { total: totalCost, input: inputCost, output: outputCost },
          finishReason: 'end_turn',
        },
      };
    } finally {
      reader.releaseLock();
    }
    return;
  }

  if (isOpenAIModel(model)) {
    const apiKey = process.env.OPENAI_API_KEY;
    if (!apiKey) {
      throw new Error('OPENAI_API_KEY is not set. Set it in .env for streaming.');
    }

    const response = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${apiKey}`,
      },
      body: JSON.stringify({
        model,
        messages: [{ role: 'user' as const, content: prompt }],
        max_tokens: maxTokens,
        temperature,
        stream: true,
      }),
    });

    if (!response.ok) {
      const text = await response.text();
      throw new Error(`OpenAI stream error: ${response.status} ${text}`);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('No response body for OpenAI stream');
    }

    const decoder = new TextDecoder();
    let buffer = '';
    let fullContent = '';
    let promptTokens = 0;
    let completionTokens = 0;

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() ?? '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const raw = line.slice(6).trim();
            if (raw === '[DONE]') continue;
            try {
              const event = JSON.parse(raw) as {
                choices?: Array<{
                  delta?: { content?: string };
                  finish_reason?: string;
                }>;
                usage?: { prompt_tokens?: number; completion_tokens?: number; total_tokens?: number };
              };
              const delta = event.choices?.[0]?.delta?.content;
              if (delta) {
                fullContent += delta;
                yield { type: 'content', content: delta };
              }
              if (event.usage) {
                promptTokens = event.usage.prompt_tokens ?? promptTokens;
                completionTokens = event.usage.completion_tokens ?? completionTokens;
              }
            } catch {
              // ignore
            }
          }
        }
      }

      const totalTokens = promptTokens + completionTokens;
      const totalCost = getOpenAICost(model, promptTokens, completionTokens);
      const inputCost = (promptTokens / 1_000_000) * (OPENAI_PRICING[model]?.input ?? 5);
      const outputCost = (completionTokens / 1_000_000) * (OPENAI_PRICING[model]?.output ?? 15);

      yield {
        type: 'done',
        response: {
          content: fullContent,
          usage: { totalTokens, promptTokens, completionTokens },
          cost: { total: totalCost, input: inputCost, output: outputCost },
          finishReason: 'stop',
        },
      };
    } finally {
      reader.releaseLock();
    }
    return;
  }

  throw new Error(
    `Unsupported model "${model}" for streaming. Use a claude-* or gpt-* model id.`
  );
}
