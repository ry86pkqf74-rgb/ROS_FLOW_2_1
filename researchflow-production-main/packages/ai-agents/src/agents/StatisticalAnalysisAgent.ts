/**
 * Statistical Analysis Agent
 *
 * Specialized agent for guiding statistical analysis.
 */

import { getClaudeProvider, type ClaudeRequestOptions } from '@researchflow/ai-router';

import { AGENT_REGISTRY } from '../registry.js';
import type { AgentInput, AgentOutput } from '../types/agent.types.js';

import { BaseAgent } from './BaseAgent.js';


export class StatisticalAnalysisAgent extends BaseAgent {
  constructor() {
    super(AGENT_REGISTRY['statistical-analysis']);
  }

  protected buildPrompt(input: AgentInput): string {
    return `You are a Statistical Analysis Agent with expertise in clinical research methodology.

TASK: Provide guidance on statistical analysis for clinical research.
Focus on:
1. Appropriate statistical test selection
2. Sample size and power considerations
3. Assumption checking
4. Effect size interpretation
5. Multiple comparison corrections

CONTEXT:
${input.context ? JSON.stringify(input.context, null, 2) : 'No additional context'}

QUERY:
${input.query}

Respond with:
1. Recommended statistical approach
2. Justification citing established methods
3. Assumptions to verify
4. Expected outputs and interpretation guidance
5. Potential limitations and alternatives`;
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
        taskType: 'statistical-analysis',
        tier: this.config.modelTier as any,
        agentId: 'statistical-analysis',
        metadata: {
          query: input.query.substring(0, 100),
          hasContext: !!input.context,
        },
      };

      const result = await claudeProvider.complete(prompt, {
        ...options,
        maxTokens: 2048,
        temperature: 0.3, // Lower temperature for methodical guidance
        systemPrompt: 'You are an expert in clinical research statistics and methodology. Provide detailed, scientifically-grounded guidance on statistical analysis.',
      });

      const content = result.text;

      return {
        content,
        citations: this.extractCitations(content),
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
      console.error('StatisticalAnalysisAgent AI call failed:', error);

      const fallbackContent = `## Statistical Analysis Guidance

Based on your query: "${input.query.substring(0, 100)}..."

### Error Occurred
Unable to retrieve AI-powered recommendations at this time. Please try again or check API configuration.

### Fallback Guidance - Common Statistical Methods for Clinical Research
- **Comparison of groups**: t-test, ANOVA, Mann-Whitney, Kruskal-Wallis
- **Correlation**: Pearson, Spearman, partial correlation
- **Regression**: Linear, logistic, Cox proportional hazards
- **Survival**: Kaplan-Meier, log-rank test

### Key Considerations
1. Define primary and secondary endpoints clearly
2. Consider baseline characteristics adjustment
3. Pre-specify analysis plan before unblinding

_Note: ${error instanceof Error ? error.message : 'Unknown error'}_`;

      return {
        content: fallbackContent,
        citations: this.extractCitations(fallbackContent),
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
