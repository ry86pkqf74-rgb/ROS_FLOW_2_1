/**
 * AI Providers Module
 *
 * Wrapped AI provider clients with automatic Notion logging.
 */

// Claude / Anthropic
export {
  ClaudeProvider,
  getClaudeProvider,
  claudeComplete,
  type ClaudeRequestOptions,
  type ClaudeResponse,
} from './claude';

// OpenAI
export {
  OpenAIProvider,
  getOpenAIProvider,
  openaiComplete,
  openaiCompleteJSON,
  type OpenAIRequestOptions,
  type OpenAIResponse,
} from './openai';

// Qwen Local (via Ollama)
export {
  QwenLocalProvider,
  LOCAL_ELIGIBLE_TASKS,
  LOCAL_BLOCKED_TASKS,
  shouldUseLocal,
  type QwenLocalConfig,
  type CompletionRequest as QwenCompletionRequest,
  type CompletionResponse as QwenCompletionResponse,
} from './qwen-local';

// Mercury Coder (Inception Labs - Diffusion LLM)
// Ultra-fast diffusion model with realtime mode, FIM, Apply/Edit endpoints
export {
  MercuryCoderProvider,
  getMercuryCoderProvider,
  type MercuryCoderRequestOptions,
  type MercuryResponse,
  type MercuryEndpoint,
  type MercuryModel,
  type MercuryChatMessage,
  type MercuryFIMRequest,
  type MercuryApplyRequest,
  type MercuryEditRequest,
  type MercuryStructuredOutputSchema,
} from './mercury-coder';
