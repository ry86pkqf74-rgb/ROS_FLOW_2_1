import type { AITaskType, ModelTier } from '@researchflow/ai-router';

export interface PhaseAgentDefinition {
  id: string;
  name: string;
  description: string;
  modelTier: ModelTier;
  phiScanRequired: boolean;
  maxTokens: number;
  taskType: AITaskType;
  knowledgeBase?: 'research_papers' | 'clinical_guidelines' | 'irb_protocols' | 'statistical_methods';
  stageHints?: string[];
}

const AGENT_REGISTRY: Record<string, PhaseAgentDefinition> = {
  'data-extraction': {
    id: 'data-extraction',
    name: 'Data Extraction Agent',
    description: 'Extracts structured data from clinical documents',
    modelTier: 'MINI',
    phiScanRequired: true,
    maxTokens: 4096,
    taskType: 'classify',
    knowledgeBase: 'research_papers',
    stageHints: ['entity extraction', 'table parsing'],
  },
  'data-validation': {
    id: 'data-validation',
    name: 'Data Validation Agent',
    description: 'Validates and cleans extracted data',
    modelTier: 'MINI',
    phiScanRequired: true,
    maxTokens: 2048,
    taskType: 'policy_check',
    knowledgeBase: 'clinical_guidelines',
    stageHints: ['consistency checks', 'schema validation'],
  },
  'variable-identification': {
    id: 'variable-identification',
    name: 'Variable Identification Agent',
    description: 'Identifies key variables for analysis',
    modelTier: 'STANDARD',
    phiScanRequired: false,
    maxTokens: 4096,
    taskType: 'summarize',
    knowledgeBase: 'research_papers',
    stageHints: ['covariates', 'outcomes'],
  },
  'cohort-definition': {
    id: 'cohort-definition',
    name: 'Cohort Definition Agent',
    description: 'Helps define study cohorts and inclusion/exclusion criteria',
    modelTier: 'STANDARD',
    phiScanRequired: true,
    maxTokens: 4096,
    taskType: 'protocol_reasoning',
    knowledgeBase: 'clinical_guidelines',
    stageHints: ['eligibility', 'IRB alignment'],
  },
  'statistical-analysis': {
    id: 'statistical-analysis',
    name: 'Statistical Analysis Agent',
    description: 'Guides statistical analysis and interprets results',
    modelTier: 'FRONTIER',
    phiScanRequired: false,
    maxTokens: 8192,
    taskType: 'complex_synthesis',
    knowledgeBase: 'statistical_methods',
    stageHints: ['models', 'p-values', 'effect sizes'],
  },
  'descriptive-stats': {
    id: 'descriptive-stats',
    name: 'Descriptive Statistics Agent',
    description: 'Generates summary statistics and visualizations',
    modelTier: 'MINI',
    phiScanRequired: false,
    maxTokens: 2048,
    taskType: 'template_fill',
    knowledgeBase: 'statistical_methods',
  },
  'model-builder': {
    id: 'model-builder',
    name: 'Model Building Agent',
    description: 'Assists with statistical model construction',
    modelTier: 'FRONTIER',
    phiScanRequired: false,
    maxTokens: 8192,
    taskType: 'protocol_reasoning',
    knowledgeBase: 'statistical_methods',
  },
  'results-interpreter': {
    id: 'results-interpreter',
    name: 'Results Interpreter Agent',
    description: 'Interprets statistical results and effect sizes',
    modelTier: 'STANDARD',
    phiScanRequired: false,
    maxTokens: 4096,
    taskType: 'summarize',
    knowledgeBase: 'statistical_methods',
  },
  'manuscript-drafting': {
    id: 'manuscript-drafting',
    name: 'Manuscript Drafting Agent',
    description: 'Drafts manuscript sections following IMRaD structure',
    modelTier: 'FRONTIER',
    phiScanRequired: true,
    maxTokens: 16384,
    taskType: 'draft_section',
    knowledgeBase: 'research_papers',
    stageHints: ['IMRaD', 'journal style'],
  },
  'introduction-writer': {
    id: 'introduction-writer',
    name: 'Introduction Writer Agent',
    description: 'Crafts introductions with literature context',
    modelTier: 'FRONTIER',
    phiScanRequired: false,
    maxTokens: 8192,
    taskType: 'draft_section',
    knowledgeBase: 'research_papers',
  },
  'methods-writer': {
    id: 'methods-writer',
    name: 'Methods Writer Agent',
    description: 'Writes detailed, reproducible methods sections',
    modelTier: 'STANDARD',
    phiScanRequired: false,
    maxTokens: 8192,
    taskType: 'draft_section',
    knowledgeBase: 'research_papers',
  },
  'results-writer': {
    id: 'results-writer',
    name: 'Results Writer Agent',
    description: 'Transforms statistical output into clear narrative',
    modelTier: 'STANDARD',
    phiScanRequired: false,
    maxTokens: 8192,
    taskType: 'draft_section',
    knowledgeBase: 'research_papers',
  },
  'discussion-writer': {
    id: 'discussion-writer',
    name: 'Discussion Writer Agent',
    description: 'Writes balanced discussions with implications',
    modelTier: 'FRONTIER',
    phiScanRequired: false,
    maxTokens: 8192,
    taskType: 'complex_synthesis',
    knowledgeBase: 'research_papers',
  },
  'conference-scout': {
    id: 'conference-scout',
    name: 'Conference Scout Agent',
    description: 'Extracts submission guidelines and deadlines',
    modelTier: 'MINI',
    phiScanRequired: false,
    maxTokens: 2048,
    taskType: 'extract_metadata',
    knowledgeBase: 'research_papers',
  },
  'abstract-generator': {
    id: 'abstract-generator',
    name: 'Abstract Generator Agent',
    description: 'Generates conference abstracts within word limits',
    modelTier: 'STANDARD',
    phiScanRequired: true,
    maxTokens: 4096,
    taskType: 'abstract_generate',
    knowledgeBase: 'research_papers',
  },
  'poster-designer': {
    id: 'poster-designer',
    name: 'Poster Design Agent',
    description: 'Helps organize content for research posters',
    modelTier: 'MINI',
    phiScanRequired: false,
    maxTokens: 4096,
    taskType: 'template_fill',
    knowledgeBase: 'research_papers',
  },
  'presentation-prep': {
    id: 'presentation-prep',
    name: 'Presentation Prep Agent',
    description: 'Assists with slide content and speaker notes',
    modelTier: 'STANDARD',
    phiScanRequired: false,
    maxTokens: 4096,
    taskType: 'summarize',
    knowledgeBase: 'research_papers',
  },
  'research-brief': {
    id: 'research-brief',
    name: 'Research Brief Agent',
    description: 'Generates research topic overviews',
    modelTier: 'MINI',
    phiScanRequired: false,
    maxTokens: 2048,
    taskType: 'summarize',
    knowledgeBase: 'research_papers',
  },
};

export const STAGE_DESCRIPTIONS: Record<number, string> = {
  1: 'Data ingestion and cleaning',
  2: 'Data validation and de-duplication',
  3: 'Variable identification and mapping',
  4: 'Cohort definition and eligibility',
  5: 'Data quality verification',
  6: 'Descriptive statistics and profiling',
  7: 'Statistical analysis design',
  8: 'Model building and tuning',
  9: 'Results interpretation',
  10: 'Results synthesis and QC',
  11: 'Manuscript drafting (Introduction)',
  12: 'Manuscript drafting (Methods)',
  13: 'Manuscript drafting (Results)',
  14: 'Manuscript drafting (Discussion)',
  15: 'Abstract generation',
  16: 'Poster and presentation preparation',
  17: 'Submission planning',
  18: 'Compliance and IRB checks',
  19: 'Final QA',
  20: 'Production handoff',
};

export const STAGE_TO_AGENTS: Record<number, string[]> = {
  1: ['data-extraction'],
  2: ['data-validation', 'data-extraction'],
  3: ['variable-identification', 'data-extraction'],
  4: ['cohort-definition', 'variable-identification'],
  5: ['data-validation', 'cohort-definition'],
  6: ['descriptive-stats', 'statistical-analysis'],
  7: ['statistical-analysis', 'model-builder'],
  8: ['model-builder', 'statistical-analysis'],
  9: ['results-interpreter', 'statistical-analysis'],
  10: ['results-interpreter', 'model-builder'],
  11: ['introduction-writer', 'manuscript-drafting'],
  12: ['methods-writer', 'manuscript-drafting'],
  13: ['results-writer', 'manuscript-drafting'],
  14: ['discussion-writer', 'manuscript-drafting'],
  15: ['abstract-generator', 'research-brief'],
  16: ['poster-designer', 'presentation-prep'],
  17: ['conference-scout', 'presentation-prep'],
  18: ['cohort-definition', 'data-validation'],
  19: ['results-interpreter', 'data-validation'],
  20: ['manuscript-drafting', 'research-brief'],
};

export function getAgentsForStage(stage: number): PhaseAgentDefinition[] {
  const agentIds = STAGE_TO_AGENTS[stage] || [];
  return agentIds.map((id) => AGENT_REGISTRY[id]).filter(Boolean);
}

export function getAgentById(agentId: string): PhaseAgentDefinition | undefined {
  return AGENT_REGISTRY[agentId];
}

export function listAgents(): PhaseAgentDefinition[] {
  return Object.values(AGENT_REGISTRY);
}

