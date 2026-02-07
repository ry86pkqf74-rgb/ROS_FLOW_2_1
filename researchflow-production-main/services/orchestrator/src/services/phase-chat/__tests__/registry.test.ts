import { describe, expect, it } from 'vitest';
import {
  getAgentById,
  getAgentsForStage,
  listAgents,
  STAGE_TO_AGENTS,
  type PhaseAgentDefinition,
} from '../registry';

describe('Phase Chat Registry', () => {
  describe('RAG Agents', () => {
    it('should have rag-ingest agent properly configured', () => {
      const agent = getAgentById('rag-ingest');
      
      expect(agent).toBeDefined();
      expect(agent?.id).toBe('rag-ingest');
      expect(agent?.name).toBe('RAG Ingest Agent');
      expect(agent?.taskType).toBe('extract_metadata');
      expect(agent?.modelTier).toBe('MINI');
      expect(agent?.phiScanRequired).toBe(true);
      expect(agent?.maxTokens).toBeGreaterThanOrEqual(2048);
      expect(agent?.knowledgeBase).toBeDefined();
      expect(agent?.stageHints).toContain('chunking');
    });

    it('should have rag-retrieve agent properly configured', () => {
      const agent = getAgentById('rag-retrieve');
      
      expect(agent).toBeDefined();
      expect(agent?.id).toBe('rag-retrieve');
      expect(agent?.name).toBe('RAG Retrieve Agent');
      expect(agent?.taskType).toBe('summarize');
      expect(agent?.modelTier).toBe('MINI');
      expect(agent?.phiScanRequired).toBe(false);
      expect(agent?.maxTokens).toBeGreaterThanOrEqual(4096);
      expect(agent?.knowledgeBase).toBeDefined();
      expect(agent?.stageHints).toContain('semantic search');
    });

    it('should include rag-ingest in Stage 1 for data ingestion', () => {
      const stage1Agents = STAGE_TO_AGENTS[1];
      expect(stage1Agents).toContain('rag-ingest');
    });

    it('should include rag-retrieve in Stage 10 for results synthesis', () => {
      const stage10Agents = STAGE_TO_AGENTS[10];
      expect(stage10Agents).toContain('rag-retrieve');
    });
  });

  describe('Verify Agent', () => {
    it('should have verify agent properly configured', () => {
      const agent = getAgentById('verify');
      
      expect(agent).toBeDefined();
      expect(agent?.id).toBe('verify');
      expect(agent?.name).toBe('Verify Agent');
      expect(agent?.taskType).toBe('policy_check');
      expect(agent?.modelTier).toBe('FRONTIER');
      expect(agent?.phiScanRequired).toBe(true);
      expect(agent?.maxTokens).toBeGreaterThanOrEqual(8192);
      expect(agent?.knowledgeBase).toBe('clinical_guidelines');
      expect(agent?.stageHints).toContain('QC');
    });

    it('should include verify in Stage 10 for QC', () => {
      const stage10Agents = STAGE_TO_AGENTS[10];
      expect(stage10Agents).toContain('verify');
    });
  });

  describe('Stage 10 Integration', () => {
    it('should have all required agents for results synthesis and QC', () => {
      const stage10Agents = STAGE_TO_AGENTS[10];
      
      expect(stage10Agents).toContain('results-interpreter');
      expect(stage10Agents).toContain('model-builder');
      expect(stage10Agents).toContain('rag-retrieve');
      expect(stage10Agents).toContain('verify');
    });

    it('should return valid agent definitions for Stage 10', () => {
      const agents = getAgentsForStage(10);
      
      expect(agents.length).toBeGreaterThan(0);
      expect(agents.every((a) => a?.id)).toBe(true);
      
      const agentIds = agents.map((a) => a.id);
      expect(agentIds).toContain('rag-retrieve');
      expect(agentIds).toContain('verify');
    });
  });

  describe('Registry Integrity', () => {
    it('should have all agents defined in STAGE_TO_AGENTS exist in AGENT_REGISTRY', () => {
      const allStageAgents = Object.values(STAGE_TO_AGENTS).flat();
      const uniqueAgentIds = [...new Set(allStageAgents)];
      
      uniqueAgentIds.forEach((agentId) => {
        const agent = getAgentById(agentId);
        expect(agent, `Agent ${agentId} should exist in registry`).toBeDefined();
      });
    });

    it('should have valid modelTier values for all agents', () => {
      const agents = listAgents();
      const validTiers = ['MINI', 'STANDARD', 'FRONTIER'];
      
      agents.forEach((agent) => {
        expect(validTiers, `Agent ${agent.id} has invalid modelTier`).toContain(
          agent.modelTier
        );
      });
    });

    it('should have valid taskType values for all agents', () => {
      const agents = listAgents();
      const validTaskTypes = [
        'classify',
        'policy_check',
        'summarize',
        'protocol_reasoning',
        'complex_synthesis',
        'template_fill',
        'draft_section',
        'extract_metadata',
        'abstract_generate',
      ];
      
      agents.forEach((agent) => {
        expect(validTaskTypes, `Agent ${agent.id} has invalid taskType`).toContain(
          agent.taskType
        );
      });
    });

    it('should have maxTokens within reasonable bounds', () => {
      const agents = listAgents();
      
      agents.forEach((agent) => {
        expect(agent.maxTokens).toBeGreaterThan(0);
        expect(agent.maxTokens).toBeLessThanOrEqual(32768);
      });
    });

    it('should have valid knowledgeBase values when specified', () => {
      const agents = listAgents();
      const validKnowledgeBases = [
        'research_papers',
        'clinical_guidelines',
        'irb_protocols',
        'statistical_methods',
      ];
      
      agents.forEach((agent) => {
        if (agent.knowledgeBase) {
          expect(
            validKnowledgeBases,
            `Agent ${agent.id} has invalid knowledgeBase`
          ).toContain(agent.knowledgeBase);
        }
      });
    });
  });

  describe('Agent Retrieval Functions', () => {
    it('should return undefined for non-existent agent', () => {
      const agent = getAgentById('non-existent-agent');
      expect(agent).toBeUndefined();
    });

    it('should return empty array for non-existent stage', () => {
      const agents = getAgentsForStage(999);
      expect(agents).toEqual([]);
    });

    it('should list all agents', () => {
      const agents = listAgents();
      expect(agents.length).toBeGreaterThan(0);
      
      // Verify key agents are present
      const agentIds = agents.map((a) => a.id);
      expect(agentIds).toContain('rag-ingest');
      expect(agentIds).toContain('rag-retrieve');
      expect(agentIds).toContain('verify');
      expect(agentIds).toContain('data-extraction');
      expect(agentIds).toContain('manuscript-drafting');
    });
  });

  describe('PHI Scanning Configuration', () => {
    it('should require PHI scan for agents handling sensitive data', () => {
      const sensitiveAgents = [
        'data-extraction',
        'data-validation',
        'cohort-definition',
        'rag-ingest',
        'verify',
        'manuscript-drafting',
        'abstract-generator',
      ];
      
      sensitiveAgents.forEach((agentId) => {
        const agent = getAgentById(agentId);
        expect(
          agent?.phiScanRequired,
          `Agent ${agentId} should require PHI scan`
        ).toBe(true);
      });
    });

    it('should not require PHI scan for retrieval-only agents', () => {
      const retrievalAgent = getAgentById('rag-retrieve');
      expect(retrievalAgent?.phiScanRequired).toBe(false);
    });
  });
});
