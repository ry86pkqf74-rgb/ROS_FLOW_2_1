/**
 * Protocol Design Agent Types
 * 
 * TypeScript interfaces for Stage 1 Protocol Design Agent
 * that match the Python PICO implementation.
 */

/**
 * PICO Framework Elements
 * Matches PICOElements in services/worker/src/agents/common/pico.py
 */
export interface PICOElements {
  population: string;
  intervention: string;
  comparator: string;
  outcomes: string[];
  timeframe: string;
}

/**
 * Research Hypotheses
 * Generated from PICO elements
 */
export interface ResearchHypotheses {
  null: string;
  alternative: string;
  comparative: string;
  primary: string;
}

/**
 * Study Types supported by Protocol Design Agent
 */
export type StudyType = 
  | 'randomized_controlled_trial'
  | 'prospective_cohort'
  | 'retrospective_cohort'
  | 'case_control'
  | 'cross_sectional'
  | 'observational';

/**
 * Entry modes for Protocol Design Agent
 */
export type ProtocolEntryMode = 
  | 'quick_entry'     // Natural language description
  | 'pico_direct'     // Structured PICO input
  | 'hypothesis_mode'; // Hypothesis-driven research

/**
 * PICO Quality Assessment
 */
export interface PICOQualityAssessment {
  score: number;
  quality_level: 'poor' | 'fair' | 'good' | 'excellent';
  recommendations: string[];
  strengths: string[];
}

/**
 * Stage 1 Protocol Design Agent Input
 */
export interface ProtocolDesignInput {
  /** Natural language research description */
  research_description?: string;
  
  /** Structured PICO elements (alternative to research_description) */
  pico_elements?: PICOElements;
  
  /** Research hypothesis (alternative entry mode) */
  hypothesis?: string;
  
  /** Maximum improvement iterations */
  max_iterations?: number;
  
  /** Governance mode */
  governance_mode?: 'DEMO' | 'LIVE' | 'STANDBY';
}

/**
 * Stage 1 Protocol Design Agent Output
 * Matches get_stage_output_for_next_stages() return type
 */
export interface ProtocolDesignOutput {
  /** Structured PICO elements */
  pico_elements: PICOElements;
  
  /** Generated research hypotheses */
  hypotheses: ResearchHypotheses;
  
  /** Primary hypothesis for the study */
  primary_hypothesis: string;
  
  /** Detected/recommended study type */
  study_type: StudyType;
  
  /** Study design analysis and recommendations */
  study_design_analysis: string;
  
  /** Complete protocol outline */
  protocol_outline: string;
  
  /** Boolean search query for literature review */
  search_query: string;
  
  /** Stage completion status */
  stage_1_complete: boolean;
  
  /** Agent identifier */
  agent_id: 'protocol_design';
  
  /** Completion timestamp */
  completion_timestamp: string;
  
  /** PICO quality assessment */
  pico_quality?: PICOQualityAssessment;
  
  /** Entry mode used */
  entry_mode?: ProtocolEntryMode;
  
  /** Quality gate score */
  quality_score?: number;
  
  /** Number of improvement iterations */
  iteration_count?: number;
}

/**
 * Stage 1 Agent State for UI display
 */
export interface ProtocolDesignAgentState {
  /** Current execution stage */
  current_stage: number;
  
  /** Entry mode detected/used */
  entry_mode?: ProtocolEntryMode;
  
  /** PICO validation status */
  pico_valid?: boolean;
  
  /** Generated hypotheses */
  hypotheses?: ResearchHypotheses;
  
  /** Study type detection */
  study_type?: StudyType;
  
  /** Protocol outline */
  protocol_outline?: string;
  
  /** Quality gate status */
  gate_status?: 'pending' | 'passed' | 'failed' | 'needs_human';
  
  /** Current output for display */
  current_output?: string;
  
  /** Any errors */
  error?: string;
  
  /** Agent execution messages */
  messages?: Array<{
    id: string;
    role: 'system' | 'user' | 'assistant';
    content: string;
    timestamp: string;
    phi_detected: boolean;
  }>;
}

/**
 * Protocol Design Configuration
 */
export interface ProtocolDesignConfig {
  /** LLM model tier to use */
  model_tier?: 'NANO' | 'MINI' | 'STANDARD' | 'FRONTIER';
  
  /** Maximum execution time in seconds */
  timeout?: number;
  
  /** Maximum improvement iterations */
  max_iterations?: number;
  
  /** PICO quality threshold */
  pico_quality_threshold?: number;
  
  /** Minimum protocol sections required */
  min_protocol_sections?: number;
  
  /** Minimum protocol length */
  min_protocol_length?: number;
  
  /** Enable improvement loop */
  improvement_enabled?: boolean;
}

/**
 * Utility type for Stage 1 artifacts
 */
export interface ProtocolDesignArtifacts {
  pico_framework: PICOElements;
  protocol_outline: string;
  research_hypotheses: ResearchHypotheses;
  search_query: {
    query: string;
    boolean_format: boolean;
    generated_from_pico: boolean;
  };
}

/**
 * Type guard for Protocol Design Output
 */
export function isProtocolDesignOutput(output: unknown): output is ProtocolDesignOutput {
  if (!output || typeof output !== 'object') return false;
  
  const obj = output as Record<string, unknown>;
  
  return (
    typeof obj.stage_1_complete === 'boolean' &&
    obj.stage_1_complete === true &&
    obj.agent_id === 'protocol_design' &&
    typeof obj.pico_elements === 'object' &&
    typeof obj.hypotheses === 'object' &&
    typeof obj.study_type === 'string' &&
    typeof obj.protocol_outline === 'string'
  );
}

/**
 * Type guard for PICO Elements
 */
export function isPICOElements(obj: unknown): obj is PICOElements {
  if (!obj || typeof obj !== 'object') return false;
  
  const pico = obj as Record<string, unknown>;
  
  return (
    typeof pico.population === 'string' &&
    typeof pico.intervention === 'string' &&
    typeof pico.comparator === 'string' &&
    Array.isArray(pico.outcomes) &&
    typeof pico.timeframe === 'string'
  );
}