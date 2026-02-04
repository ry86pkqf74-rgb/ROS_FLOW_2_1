/**
 * Manuscript Drafting Agent
 *
 * Specialized agent for drafting manuscript sections.
 * Now integrated with Claude provider via ai-router for real AI responses.
 */

import { BaseAgent } from './BaseAgent.js';
import type { AgentInput, AgentOutput } from '../types/agent.types.js';
import { AGENT_REGISTRY } from '../registry.js';
import { getClaudeProvider, type ClaudeRequestOptions } from '@researchflow/ai-router';

export class ManuscriptDraftingAgent extends BaseAgent {
  constructor() {
    super(AGENT_REGISTRY['manuscript-drafting']);
  }

  protected buildPrompt(input: AgentInput): string {
    return `You are a Manuscript Drafting Agent specialized in scientific writing.

TASK: Help draft or revise manuscript sections following IMRaD structure.
Focus on:
1. Clear, concise scientific writing
2. Logical flow and transitions
3. Appropriate use of citations
4. Active voice where suitable
5. Adherence to target journal style

IMPORTANT:
- Flag any statements that need citation support
- Highlight claims that may need toning down
- Ensure reproducibility in methods descriptions

CONTEXT:
${input.context ? JSON.stringify(input.context, null, 2) : 'No additional context'}

QUERY:
${input.query}

Respond with:
1. Draft text or revision suggestions
2. Comments on improvements made
3. Citations needed (marked as [CITE])
4. Potential issues to address`;
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
        taskType: 'manuscript-drafting',
        tier: this.config.modelTier as any,
        agentId: 'manuscript-drafting',
        metadata: {
          query: input.query.substring(0, 100),
          hasContext: !!input.context,
        },
      };

      const result = await claudeProvider.complete(prompt, {
        ...options,
        maxTokens: 4096,
        temperature: 0.5, // Moderate temperature for creative yet coherent writing
        systemPrompt: 'You are an expert scientific manuscript writing assistant. Provide clear, professional guidance on manuscript drafting with proper structure and citations.',
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
      console.error('ManuscriptDraftingAgent AI call failed:', error);

      const fallbackContent = `## Manuscript Drafting Response

Based on your query: "${input.query.substring(0, 100)}..."

### Writing Guidance

When drafting your manuscript, consider:

1. **Introduction**: Move from broad context to specific research gap
2. **Methods**: Provide sufficient detail for reproducibility
3. **Results**: Present data objectively without interpretation
4. **Discussion**: Interpret findings in context of existing literature

### IMRaD Best Practices
- Use past tense for methods and results
- Use present tense for established facts
- Keep paragraphs focused on single ideas
- Use transitional phrases between sections

### Citations
- Mark claims needing support as [CITE]
- Prefer primary sources over reviews
- Include recent relevant literature

_Error: ${error instanceof Error ? error.message : 'Unknown error'}. Please try again or check API configuration._`;

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
