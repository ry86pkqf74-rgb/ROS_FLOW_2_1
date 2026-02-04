/**
 * Conference Scout Agent
 *
 * Specialized agent for extracting conference submission guidelines.
 * Now integrated with Claude provider via ai-router for real AI responses.
 */

import { BaseAgent } from './BaseAgent.js';
import type { AgentInput, AgentOutput } from '../types/agent.types.js';
import { AGENT_REGISTRY } from '../registry.js';
import { getClaudeProvider, type ClaudeRequestOptions } from '@researchflow/ai-router';

export class ConferenceScoutAgent extends BaseAgent {
  constructor() {
    super(AGENT_REGISTRY['conference-scout']);
  }

  protected buildPrompt(input: AgentInput): string {
    return `You are a Conference Scout Agent specialized in extracting submission guidelines.

TASK: Analyze the provided conference information and extract:
1. Submission deadlines (abstract, full paper)
2. Word/character limits for abstracts
3. Required sections/format
4. Presentation format (oral, poster, both)
5. Registration requirements

CONTEXT:
${input.context ? JSON.stringify(input.context, null, 2) : 'No additional context'}

QUERY:
${input.query}

Respond ONLY with valid JSON in this exact format (no markdown, no explanation):
{
  "conferenceInfo": {
    "name": "Conference Name",
    "dates": "Conference dates",
    "location": "Location"
  },
  "deadlines": [
    { "type": "abstract", "date": "YYYY-MM-DD", "timezone": "UTC" }
  ],
  "formatRequirements": {
    "abstractWordLimit": 250,
    "fullPaperWordLimit": 5000,
    "requiredSections": ["Introduction", "Methods", "Results", "Conclusions"]
  },
  "presentationTypes": ["oral", "poster"],
  "recommendations": [
    "Specific recommendation based on query"
  ]
}`;
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
        taskType: 'conference-scout',
        tier: this.config.modelTier as any,
        agentId: 'conference-scout',
        metadata: {
          query: input.query.substring(0, 100),
          hasContext: !!input.context,
        },
      };

      const result = await claudeProvider.complete(prompt, {
        ...options,
        maxTokens: 2048,
        temperature: 0.3, // Lower temperature for structured output
        systemPrompt: 'You are a helpful research assistant specializing in academic conference information. Always respond with valid JSON only.',
      });

      // Parse and validate JSON response
      let parsedContent: any;
      try {
        parsedContent = JSON.parse(result.text);
      } catch {
        // If JSON parsing fails, wrap the response
        parsedContent = {
          conferenceInfo: { name: 'Unknown', dates: 'TBD', location: 'TBD' },
          deadlines: [],
          formatRequirements: { abstractWordLimit: 250, fullPaperWordLimit: null, requiredSections: [] },
          presentationTypes: ['oral', 'poster'],
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
      // Fallback to placeholder on error
      console.error('ConferenceScoutAgent AI call failed:', error);

      const fallbackContent = JSON.stringify({
        conferenceInfo: { name: 'Error occurred', dates: 'N/A', location: 'N/A' },
        deadlines: [],
        formatRequirements: { abstractWordLimit: 250, fullPaperWordLimit: null, requiredSections: [] },
        presentationTypes: ['oral', 'poster'],
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
