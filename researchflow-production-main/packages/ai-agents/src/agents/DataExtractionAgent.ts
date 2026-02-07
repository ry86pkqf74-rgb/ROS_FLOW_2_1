/**
 * Data Extraction Agent
 *
 * Specialized agent for extracting structured data from clinical documents.
 */

import { getClaudeProvider, type ClaudeRequestOptions } from '@researchflow/ai-router';

import { AGENT_REGISTRY } from '../registry.js';
import type { AgentInput, AgentOutput } from '../types/agent.types.js';

import { BaseAgent } from './BaseAgent.js';


export class DataExtractionAgent extends BaseAgent {
  constructor() {
    super(AGENT_REGISTRY['data-extraction']);
  }

  protected buildPrompt(input: AgentInput): string {
    return `You are a Data Extraction Agent specialized in clinical data extraction.

TASK: Help extract structured data from the provided clinical document.
Focus on:
1. Demographics (age, gender, ethnicity - de-identified)
2. Clinical variables (diagnoses, procedures, medications)
3. Outcomes (primary and secondary endpoints)
4. Temporal data (dates, durations, follow-up periods)

IMPORTANT:
- Flag any potential PHI (Protected Health Information)
- Use standardized medical terminologies where possible
- Provide confidence scores for extracted values

CONTEXT:
${input.context ? JSON.stringify(input.context, null, 2) : 'No additional context'}

QUERY:
${input.query}

Respond with:
1. Extracted variables as structured data
2. Confidence scores for each extraction
3. PHI warnings if any identifiers detected
4. Suggestions for additional data to collect`;
  }

  async execute(input: AgentInput): Promise<AgentOutput> {
    const startTime = Date.now();

    if (!this.validateInput(input)) {
      throw new Error('Invalid input: query is required');
    }

    const prompt = this.buildPrompt(input);

    try {
      // Get Claude provider and make real AI call
      const claudeProvider = getClaudeProvider();
      const options: ClaudeRequestOptions = {
        taskType: 'data-extraction',
        tier: this.config.modelTier as any,
        agentId: 'data-extraction',
        metadata: {
          query: input.query.substring(0, 100),
          hasContext: !!input.context,
        },
      };

      const result = await claudeProvider.complete(prompt, {
        ...options,
        maxTokens: 2048,
        temperature: 0.2, // Lower temperature for consistent data extraction
        systemPrompt: 'You are a clinical data extraction specialist. Extract structured data carefully and flag any potential PHI. Provide confidence scores for each extraction.',
      });

      // Parse and validate JSON response
      let parsedContent: any;
      try {
        parsedContent = JSON.parse(result.text);
      } catch {
        // If JSON parsing fails, wrap the response
        parsedContent = {
          extractedVariables: [],
          confidenceScores: {},
          phiWarnings: [],
          recommendations: [result.text],
          _parseError: 'Response was not valid JSON, raw text included in recommendations',
        };
      }

      return {
        content: JSON.stringify(parsedContent, null, 2),
        citations: [],
        metadata: {
          modelUsed: this.config.modelTier,
          tokensUsed: result.usage.totalTokens,
          phiDetected: false,
          processingTimeMs: Date.now() - startTime,
          costUsd: result.usage.estimatedCostUsd,
        },
      };
    } catch (error) {
      // Fallback to error response on failure
      console.error('DataExtractionAgent AI call failed:', error);

      const fallbackContent = JSON.stringify({
        extractedVariables: [],
        confidenceScores: {},
        phiWarnings: [],
        recommendations: [`Error processing query: ${error instanceof Error ? error.message : 'Unknown error'}. Please try again or check API configuration.`],
        _error: true,
      }, null, 2);

      return {
        content: fallbackContent,
        citations: [],
        metadata: {
          modelUsed: this.config.modelTier,
          tokensUsed: 0,
          phiDetected: false,
          processingTimeMs: Date.now() - startTime,
          error: error instanceof Error ? error.message : 'Unknown error',
        },
      };
    }
  }
}
