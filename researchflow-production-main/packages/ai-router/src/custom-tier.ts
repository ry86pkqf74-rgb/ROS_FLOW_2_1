/**
 * CUSTOM Tier Configuration for AI Router
 * 
 * Adds support for fine-tuned custom models and LangGraph agents.
 * Priority 2 (between LOCAL and FRONTIER).
 * 
 * Linear Issue: ROS-83
 */

import type { ModelTier, AIProvider, ModelConfig } from './types';

/**
 * Extended Model Tier with CUSTOM
 */
export type ExtendedModelTier = ModelTier | 'CUSTOM';

/**
 * Custom model configuration
 */
export interface CustomModelConfig extends ModelConfig {
  /** Model endpoint URL */
  endpoint: string;
  /** Whether this model uses RAG */
  useRAG: boolean;
  /** Whether this routes to a LangGraph agent */
  useAgents: boolean;
  /** Specific agent to use */
  agentName?: string;
  /** RAG collections to query */
  ragCollections?: string[];
}

/**
 * CUSTOM tier model configurations
 */
export const CUSTOM_MODEL_CONFIGS: Record<string, CustomModelConfig> = {
  'research-refiner': {
    provider: 'local' as AIProvider,
    model: 'research-refiner',
    maxTokens: 8192,
    temperature: 0.3,
    costPerMToken: { input: 0, output: 0 }, // Local = free
    endpoint: 'http://ollama:11434',
    useRAG: true,
    useAgents: false,
    ragCollections: ['research_papers', 'clinical_guidelines', 'ai_feedback_guidance'],
  },
  'manuscript-agent': {
    provider: 'local' as AIProvider,
    model: 'manuscript-agent',
    maxTokens: 8192,
    temperature: 0.3,
    costPerMToken: { input: 0, output: 0 },
    endpoint: 'http://worker:8000/agents',
    useRAG: true,
    useAgents: true,
    agentName: 'ManuscriptAgent',
    ragCollections: ['research_papers', 'ai_feedback_guidance'],
  },
  'stats-agent': {
    provider: 'local' as AIProvider,
    model: 'stats-agent',
    maxTokens: 4096,
    temperature: 0.2,
    costPerMToken: { input: 0, output: 0 },
    endpoint: 'http://worker:8000/agents',
    useRAG: true,
    useAgents: true,
    agentName: 'AnalysisAgent',
    ragCollections: ['statistical_methods', 'ai_feedback_guidance'],
  },
  'dataprep-agent': {
    provider: 'local' as AIProvider,
    model: 'dataprep-agent',
    maxTokens: 4096,
    temperature: 0.2,
    costPerMToken: { input: 0, output: 0 },
    endpoint: 'http://worker:8000/agents',
    useRAG: true,
    useAgents: true,
    agentName: 'DataPrepAgent',
    ragCollections: ['research_papers', 'statistical_methods', 'ai_feedback_guidance'],
  },
  'irb-agent': {
    provider: 'local' as AIProvider,
    model: 'irb-agent',
    maxTokens: 4096,
    temperature: 0.1, // Lower for compliance
    costPerMToken: { input: 0, output: 0 },
    endpoint: 'http://worker:8000/agents',
    useRAG: true,
    useAgents: true,
    agentName: 'IRBAgent',
    ragCollections: ['irb_protocols', 'clinical_guidelines', 'ai_feedback_guidance'],
  },
  'quality-agent': {
    provider: 'local' as AIProvider,
    model: 'quality-agent',
    maxTokens: 4096,
    temperature: 0.3,
    costPerMToken: { input: 0, output: 0 },
    endpoint: 'http://worker:8000/agents',
    useRAG: true,
    useAgents: true,
    agentName: 'QualityAgent',
    ragCollections: ['clinical_guidelines', 'ai_feedback_guidance'],
  },
};

/**
 * Task type to CUSTOM model mapping
 */
export const CUSTOM_TASK_MAPPING: Record<string, string> = {
  // Manuscript tasks → manuscript-agent or research-refiner
  'manuscript_refinement': 'manuscript-agent',
  'abstract_generate': 'manuscript-agent',
  'draft_section': 'research-refiner',
  
  // Statistical tasks → stats-agent
  'statistical_analysis': 'stats-agent',
  'assumption_validation': 'stats-agent',
  'sensitivity_analysis': 'stats-agent',
  
  // Data tasks → dataprep-agent
  'data_validation': 'dataprep-agent',
  'data_cleaning': 'dataprep-agent',
  'outlier_detection': 'dataprep-agent',
  
  // IRB tasks → irb-agent
  'irb_review': 'irb-agent',
  'compliance_check': 'irb-agent',
  'consent_review': 'irb-agent',
  
  // Quality tasks → quality-agent
  'figure_generation': 'quality-agent',
  'table_formatting': 'quality-agent',
  'integrity_check': 'quality-agent',
};

/**
 * CUSTOM tier configuration
 */
export const CUSTOM_TIER_CONFIG = {
  priority: 2, // Between LOCAL (1) and FRONTIER (3)
  timeout: 120000, // 2 minutes
  maxRetries: 2,
  fallbackTier: 'FRONTIER' as ModelTier,
  
  // Feature flags
  features: {
    useRAG: true,
    useAgents: true,
    useFinetuned: true,
    enableCaching: true,
  },
};

/**
 * Check if a task should use CUSTOM tier
 */
export function shouldUseCustomTier(taskType: string): boolean {
  return taskType in CUSTOM_TASK_MAPPING;
}

/**
 * Get CUSTOM model config for a task
 */
export function getCustomModelForTask(taskType: string): CustomModelConfig | null {
  const modelName = CUSTOM_TASK_MAPPING[taskType];
  if (!modelName) return null;
  return CUSTOM_MODEL_CONFIGS[modelName] || null;
}

/**
 * Check if CUSTOM tier is available (all required services running)
 */
export async function isCustomTierAvailable(): Promise<boolean> {
  const workerUrl = process.env.WORKER_URL || 'http://worker:8000';
  const ollamaUrl = process.env.OLLAMA_URL || 'http://ollama:11434';
  
  try {
    // Check worker agents endpoint
    const workerCheck = await fetch(`${workerUrl}/agents/`, {
      method: 'GET',
      signal: AbortSignal.timeout(5000),
    });
    
    // Check Ollama
    const ollamaCheck = await fetch(`${ollamaUrl}/api/tags`, {
      method: 'GET',
      signal: AbortSignal.timeout(5000),
    });
    
    return workerCheck.ok && ollamaCheck.ok;
  } catch {
    return false;
  }
}
