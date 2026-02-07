/**
 * Custom Agent Dispatcher
 * 
 * Routes requests to LangGraph agents and fine-tuned models.
 * Handles RAG context injection and agent orchestration.
 * 
 * Linear Issue: ROS-83
 */

import { EventEmitter } from 'events';

import type { AIRouterRequest as AIRequest, AIRouterResponse as AIResponse } from '../types';

// Define StreamChunk locally since it's not in main types
interface StreamChunk {
  type?: 'content' | 'error' | 'done' | 'metadata';
  content: string;
  done: boolean;
  metadata?: Record<string, unknown>;
}
import {
  CustomModelConfig,
  CUSTOM_MODEL_CONFIGS,
  CUSTOM_TASK_MAPPING,
  getCustomModelForTask,
  isCustomTierAvailable,
} from '../custom-tier';

export interface AgentDispatchRequest {
  taskId: string;
  taskType: string;
  stageId?: number;
  researchId: string;
  input: Record<string, any>;
  context?: string;
  streaming?: boolean;
}

export interface AgentDispatchResponse {
  success: boolean;
  taskId: string;
  agentName?: string;
  result?: Record<string, any>;
  artifacts?: Array<Record<string, any>>;
  qualityScore?: number;
  ragSources?: string[];
  error?: string;
  durationMs?: number;
}

export interface RAGContext {
  query: string;
  collections: string[];
  topK?: number;
  results?: Array<{
    id: string;
    content: string;
    metadata: Record<string, any>;
    score: number;
  }>;
}

export class CustomAgentDispatcher extends EventEmitter {
  private workerUrl: string;
  private ollamaUrl: string;
  private chromaUrl: string;
  private available: boolean = false;
  private lastHealthCheck: number = 0;
  private healthCheckInterval: number = 30000; // 30 seconds

  constructor(config?: {
    workerUrl?: string;
    ollamaUrl?: string;
    chromaUrl?: string;
  }) {
    super();
    this.workerUrl = config?.workerUrl || process.env.WORKER_URL || 'http://worker:8000';
    this.ollamaUrl = config?.ollamaUrl || process.env.OLLAMA_URL || 'http://ollama:11434';
    this.chromaUrl = config?.chromaUrl || process.env.CHROMADB_URL || 'http://chromadb:8000';
  }

  /**
   * Check if custom dispatch is available
   */
  async isAvailable(): Promise<boolean> {
    const now = Date.now();
    if (now - this.lastHealthCheck < this.healthCheckInterval) {
      return this.available;
    }

    this.available = await isCustomTierAvailable();
    this.lastHealthCheck = now;
    return this.available;
  }

  /**
   * Dispatch to appropriate agent or fine-tuned model
   */
  async dispatch(request: AgentDispatchRequest): Promise<AgentDispatchResponse> {
    const startTime = Date.now();
    const modelConfig = getCustomModelForTask(request.taskType);

    if (!modelConfig) {
      return {
        success: false,
        taskId: request.taskId,
        error: `No custom model configured for task type: ${request.taskType}`,
      };
    }

    try {
      // Inject RAG context if configured
      let context = request.context || '';
      if (modelConfig.useRAG && modelConfig.ragCollections?.length) {
        const ragContext = await this.fetchRAGContext({
          query: this.extractQueryFromInput(request.input),
          collections: modelConfig.ragCollections,
          topK: 5,
        });
        context = this.formatRAGContext(ragContext);
      }

      // Route to agent or direct model
      let response: AgentDispatchResponse;
      
      if (modelConfig.useAgents && modelConfig.agentName) {
        response = await this.dispatchToAgent(request, modelConfig, context);
      } else {
        response = await this.dispatchToModel(request, modelConfig, context);
      }

      response.durationMs = Date.now() - startTime;
      return response;

    } catch (error) {
      return {
        success: false,
        taskId: request.taskId,
        error: error instanceof Error ? error.message : 'Unknown error',
        durationMs: Date.now() - startTime,
      };
    }
  }

  /**
   * Dispatch to LangGraph agent via worker
   */
  private async dispatchToAgent(
    request: AgentDispatchRequest,
    config: CustomModelConfig,
    context: string,
  ): Promise<AgentDispatchResponse> {
    const agentRequest = {
      task_id: request.taskId,
      stage_id: request.stageId || this.inferStageFromTask(request.taskType),
      research_id: request.researchId,
      input_data: {
        ...request.input,
        rag_context: context,
      },
      agent_name: config.agentName,
    };

    const response = await fetch(`${this.workerUrl}/agents/run/sync`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(agentRequest),
      signal: AbortSignal.timeout(120000), // 2 minute timeout
    });

    if (!response.ok) {
      throw new Error(`Agent request failed: ${response.status}`);
    }

    const result = await response.json();

    return {
      success: result.status === 'completed',
      taskId: request.taskId,
      agentName: config.agentName,
      result: result.result?.result,
      artifacts: result.result?.artifacts,
      qualityScore: result.result?.quality_score,
      ragSources: result.result?.rag_sources,
      error: result.error,
    };
  }

  /**
   * Dispatch to fine-tuned Ollama model
   */
  private async dispatchToModel(
    request: AgentDispatchRequest,
    config: CustomModelConfig,
    context: string,
  ): Promise<AgentDispatchResponse> {
    const prompt = this.buildPrompt(request, config, context);

    const response = await fetch(`${this.ollamaUrl}/api/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: config.model,
        prompt: prompt,
        stream: false,
        options: {
          temperature: config.temperature,
          num_predict: config.maxTokens,
        },
      }),
      signal: AbortSignal.timeout(60000),
    });

    if (!response.ok) {
      throw new Error(`Ollama request failed: ${response.status}`);
    }

    const result = await response.json();

    // Try to parse structured output
    let parsedResult: Record<string, any>;
    try {
      const jsonMatch = result.response.match(/```json\n?([\s\S]*?)\n?```/);
      if (jsonMatch) {
        parsedResult = JSON.parse(jsonMatch[1]);
      } else if (result.response.includes('{')) {
        const start = result.response.indexOf('{');
        const end = result.response.lastIndexOf('}') + 1;
        parsedResult = JSON.parse(result.response.slice(start, end));
      } else {
        parsedResult = { output: result.response };
      }
    } catch {
      parsedResult = { output: result.response };
    }

    return {
      success: true,
      taskId: request.taskId,
      result: parsedResult,
      qualityScore: 0.8, // Default for direct model calls
    };
  }

  /**
   * Stream dispatch for real-time responses
   */
  async *dispatchStream(
    request: AgentDispatchRequest
  ): AsyncGenerator<StreamChunk> {
    const modelConfig = getCustomModelForTask(request.taskType);

    if (!modelConfig) {
      yield {
        type: 'error',
        content: `No custom model for task: ${request.taskType}`,
      };
      return;
    }

    // RAG context
    let context = request.context || '';
    if (modelConfig.useRAG && modelConfig.ragCollections?.length) {
      const ragContext = await this.fetchRAGContext({
        query: this.extractQueryFromInput(request.input),
        collections: modelConfig.ragCollections,
        topK: 5,
      });
      context = this.formatRAGContext(ragContext);
      
      yield {
        type: 'rag',
        content: `Retrieved ${ragContext.results?.length || 0} documents`,
        metadata: { sources: ragContext.results?.map(r => r.id) },
      };
    }

    // Stream from Ollama
    const prompt = this.buildPrompt(request, modelConfig, context);
    
    const response = await fetch(`${this.ollamaUrl}/api/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: modelConfig.model,
        prompt: prompt,
        stream: true,
        options: {
          temperature: modelConfig.temperature,
          num_predict: modelConfig.maxTokens,
        },
      }),
    });

    if (!response.ok || !response.body) {
      yield { type: 'error', content: `Stream failed: ${response.status}`, done: false };
      return;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n').filter(Boolean);

        for (const line of lines) {
          try {
            const json = JSON.parse(line);
            if (json.response) {
              yield { type: 'content', content: json.response };
            }
            if (json.done) {
              yield { type: 'done', content: '' };
            }
          } catch {
            // Skip invalid JSON lines
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  }

  /**
   * Fetch context from ChromaDB
   */
  private async fetchRAGContext(config: RAGContext): Promise<RAGContext> {
    const results: RAGContext['results'] = [];

    for (const collection of config.collections) {
      try {
        const response = await fetch(`${this.workerUrl}/agents/rag/search`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            query: config.query,
            collection: collection,
            top_k: config.topK || 5,
          }),
          signal: AbortSignal.timeout(10000),
        });

        if (response.ok) {
          const data = await response.json();
          results.push(...(data.results || []));
        }
      } catch (error) {
        console.warn(`RAG fetch failed for ${collection}:`, error);
      }
    }

    // Sort by score and deduplicate
    const sorted = results
      .sort((a, b) => b.score - a.score)
      .slice(0, config.topK || 5);

    return { ...config, results: sorted };
  }

  /**
   * Format RAG results as context string
   */
  private formatRAGContext(context: RAGContext): string {
    if (!context.results?.length) {
      return 'No relevant context found.';
    }

    const formatted = context.results.map((r, i) => {
      const source = r.metadata?.source || `Document ${i + 1}`;
      return `[${source}]\n${r.content.slice(0, 1000)}`;
    });

    return `## Relevant Context\n\n${formatted.join('\n\n---\n\n')}`;
  }

  /**
   * Build prompt for model
   */
  private buildPrompt(
    request: AgentDispatchRequest,
    config: CustomModelConfig,
    context: string,
  ): string {
    const systemPrompt = this.getSystemPrompt(request.taskType);
    const inputStr = JSON.stringify(request.input, null, 2);

    return `<|begin_of_text|><|start_header_id|>system<|end_header_id|>

${systemPrompt}<|eot_id|><|start_header_id|>user<|end_header_id|>

## Task
${request.taskType}

## Input
${inputStr}

${context ? `## Context\n${context}` : ''}

Please provide your response in JSON format.<|eot_id|><|start_header_id|>assistant<|end_header_id|>

`;
  }

  /**
   * Get system prompt for task type
   */
  private getSystemPrompt(taskType: string): string {
    const prompts: Record<string, string> = {
      manuscript_refinement: 'You are an expert scientific editor. Refine manuscripts for clarity and accuracy.',
      statistical_analysis: 'You are a biostatistician. Provide rigorous statistical analysis with proper interpretation.',
      data_validation: 'You are a data quality specialist. Validate data and identify issues.',
      irb_review: 'You are an IRB compliance expert. Review protocols for regulatory compliance.',
      figure_generation: 'You are a scientific visualization expert. Generate publication-quality figure specifications.',
    };
    return prompts[taskType] || 'You are a research assistant. Complete the requested task accurately.';
  }

  /**
   * Extract search query from input
   */
  private extractQueryFromInput(input: Record<string, any>): string {
    // Try common fields
    if (input.query) return input.query;
    if (input.topic) return input.topic;
    if (input.title) return input.title;
    if (input.abstract) return input.abstract.slice(0, 200);
    if (input.content) return input.content.slice(0, 200);
    
    // Fallback: stringify first few fields
    return Object.values(input).slice(0, 3).join(' ').slice(0, 200);
  }

  /**
   * Infer workflow stage from task type
   */
  private inferStageFromTask(taskType: string): number {
    const stageMap: Record<string, number> = {
      data_validation: 1,
      data_cleaning: 3,
      statistical_analysis: 7,
      figure_generation: 10,
      table_formatting: 11,
      irb_review: 13,
      manuscript_refinement: 15,
      abstract_generate: 19,
    };
    return stageMap[taskType] || 1;
  }
}

// Singleton export
let dispatcher: CustomAgentDispatcher | null = null;

export function getCustomDispatcher(): CustomAgentDispatcher {
  if (!dispatcher) {
    dispatcher = new CustomAgentDispatcher();
  }
  return dispatcher;
}
