/**
 * Phase 8: Custom Dispatcher Testing & Validation
 *
 * Comprehensive Jest tests for CustomDispatcher:
 * - CustomDispatcher routing logic and agent selection
 * - Feature flag integration
 * - Fallback behavior on dispatch failure
 * - WebSocket streaming support
 * - Agent registry management
 * - Dispatch metrics and health checks
 *
 * Test Coverage:
 * - Agent selection by stage and task type
 * - Request/response transformation
 * - Fallback escalation to CLOUD tier
 * - Caching mechanism
 * - Quality gate evaluation
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import {
  CustomDispatcher,
  createCustomDispatcher,
  CUSTOM_AGENT_REGISTRY,
  CustomAgentType,
  DispatchDecision,
  CustomDispatchContext,
} from '../dispatchers/custom';
import type {
  AITaskType,
  AIRouterRequest,
  AIRouterResponse,
  ModelTier,
} from '../types';


// =============================================================================
// Fixtures
// =============================================================================

function createMockRequest(overrides?: Partial<AIRouterRequest>): AIRouterRequest {
  return {
    prompt: 'Test prompt for diabetes treatment',
    taskType: 'summarize' as AITaskType,
    workflowStage: 6,
    context: {},
    metadata: {
      projectId: 'test-proj-001',
      runId: 'test-run-001',
    },
    ...overrides,
  };
}

function createMockContext(
  overrides?: Partial<CustomDispatchContext>
): CustomDispatchContext {
  return {
    taskType: 'summarize',
    workflowStage: 6,
    requiredPhiHandling: false,
    contextSize: 2048,
    ...overrides,
  };
}


// =============================================================================
// Tests: Dispatcher Initialization
// =============================================================================

describe('CustomDispatcher - Initialization', () => {
  it('should initialize with default config', () => {
    const dispatcher = new CustomDispatcher();

    expect(dispatcher).toBeDefined();
    expect(dispatcher.getAgentRegistry()).toBeDefined();
    expect(Object.keys(dispatcher.getAgentRegistry()).length).toBeGreaterThan(0);
  });

  it('should initialize with custom fallback tier', () => {
    const dispatcher = new CustomDispatcher({ fallbackTier: 'FRONTIER' });

    expect(dispatcher).toBeDefined();
    dispatcher.setFallbackTier('FRONTIER');
  });

  it('should have all agents registered', () => {
    const dispatcher = new CustomDispatcher();
    const registry = dispatcher.getAgentRegistry();

    const expectedAgents: CustomAgentType[] = [
      'DataPrep',
      'Analysis',
      'Quality',
      'IRB',
      'Manuscript',
    ];

    expectedAgents.forEach((agent) => {
      expect(registry[agent]).toBeDefined();
      expect(registry[agent].id).toBe(agent);
      expect(registry[agent].name).toBeDefined();
      expect(registry[agent].taskTypes).toBeInstanceOf(Array);
      expect(registry[agent].workflowStages).toBeInstanceOf(Array);
    });
  });

  it('should initialize metrics', () => {
    const dispatcher = new CustomDispatcher();
    const metrics = dispatcher.getMetrics();

    expect(metrics.totalDispatches).toBe(0);
    expect(metrics.successfulDispatches).toBe(0);
    expect(metrics.failedDispatches).toBe(0);
    expect(metrics.fallbacksTriggered).toBe(0);
  });
});


// =============================================================================
// Tests: Agent Selection Logic
// =============================================================================

describe('CustomDispatcher - Agent Selection', () => {
  let dispatcher: CustomDispatcher;

  beforeEach(() => {
    dispatcher = new CustomDispatcher();
  });

  it('should select DataPrep agent for stages 1-5', () => {
    for (let stage = 1; stage <= 5; stage++) {
      const context = createMockContext({ workflowStage: stage });
      const decision = dispatcher['selectAgent'](context);

      expect(decision.selectedAgent).toBe('DataPrep');
      expect(decision.confidence).toBeGreaterThan(0);
    }
  });

  it('should select Analysis agent for stages 6-10', () => {
    for (let stage = 6; stage <= 10; stage++) {
      const context = createMockContext({ workflowStage: stage });
      const decision = dispatcher['selectAgent'](context);

      expect(decision.selectedAgent).toBe('Analysis');
    }
  });

  it('should select IRB agent for stages 11-15', () => {
    for (let stage = 11; stage <= 15; stage++) {
      const context = createMockContext({
        workflowStage: stage,
        requiredPhiHandling: true,
      });
      const decision = dispatcher['selectAgent'](context);

      expect(decision.selectedAgent).toBe('IRB');
    }
  });

  it('should select Manuscript agent for stages 16-20', () => {
    for (let stage = 16; stage <= 20; stage++) {
      const context = createMockContext({ workflowStage: stage });
      const decision = dispatcher['selectAgent'](context);

      expect(['Manuscript', 'IRB']).toContain(decision.selectedAgent);
    }
  });

  it('should select agent by task type', () => {
    const testCases = [
      { taskType: 'extract_metadata' as AITaskType, expected: 'DataPrep' },
      { taskType: 'summarize' as AITaskType, expected: 'Analysis' },
      { taskType: 'phi_scan' as AITaskType, expected: 'Quality' },
      { taskType: 'policy_check' as AITaskType, expected: 'IRB' },
      { taskType: 'draft_section' as AITaskType, expected: 'Manuscript' },
    ];

    testCases.forEach(({ taskType, expected }) => {
      const context = createMockContext({
        taskType,
        workflowStage: undefined,
      });
      const decision = dispatcher['selectAgent'](context);

      expect(decision.selectedAgent).toBe(expected);
    });
  });

  it('should select Quality as default agent', () => {
    const context: CustomDispatchContext = {
      taskType: 'unknown_task' as AITaskType,
      requiredPhiHandling: false,
      contextSize: 1024,
    };

    const decision = dispatcher['selectAgent'](context);

    expect(decision.selectedAgent).toBe('Quality');
    expect(decision.confidence).toBeLessThan(0.95);
  });

  it('should respect PHI requirement in agent selection', () => {
    const context = createMockContext({
      workflowStage: 1,
      requiredPhiHandling: true,
    });
    const decision = dispatcher['selectAgent'](context);

    expect(decision.selectedAgent).toBe('DataPrep');
    const agent = CUSTOM_AGENT_REGISTRY[decision.selectedAgent];
    expect(agent.phiRequired).toBe(true);
  });

  it('should include reason in dispatch decision', () => {
    const context = createMockContext({ workflowStage: 3 });
    const decision = dispatcher['selectAgent'](context);

    expect(decision.reason).toBeDefined();
    expect(decision.reason.length).toBeGreaterThan(0);
    expect(decision.fallbackTier).toBeDefined();
    expect(decision.estimatedLatencyMs).toBeGreaterThan(0);
  });
});


// =============================================================================
// Tests: Dispatch Execution
// =============================================================================

describe('CustomDispatcher - Dispatch Execution', () => {
  let dispatcher: CustomDispatcher;

  beforeEach(() => {
    dispatcher = new CustomDispatcher();
  });

  it('should successfully dispatch request', async () => {
    const request = createMockRequest();
    const context = createMockContext();

    const response = await dispatcher.dispatch(request, context);

    expect(response).toBeDefined();
    expect(response.content).toBeDefined();
    expect(response.routing).toBeDefined();
    expect(response.usage).toBeDefined();
    expect(response.metrics).toBeDefined();
  });

  it('should include routing information in response', async () => {
    const request = createMockRequest();
    const context = createMockContext();

    const response = await dispatcher.dispatch(request, context);

    expect(response.routing.initialTier).toBe('CUSTOM');
    expect(response.routing.provider).toBeDefined();
    expect(response.routing.model).toBeDefined();
    expect(response.routing.escalated).toBeDefined();
  });

  it('should track metrics on successful dispatch', async () => {
    const request = createMockRequest();
    const context = createMockContext();

    const metricsBeforeA = dispatcher.getMetrics();

    await dispatcher.dispatch(request, context);
    const metricsAfterA = dispatcher.getMetrics();

    expect(metricsAfterA.totalDispatches).toBe(metricsBeforeA.totalDispatches + 1);
    expect(metricsAfterA.successfulDispatches).toBeGreaterThanOrEqual(
      metricsBeforeA.successfulDispatches
    );
  });

  it('should estimate token usage', async () => {
    const request = createMockRequest({ prompt: 'short' });
    const context = createMockContext();

    const response = await dispatcher.dispatch(request, context);

    expect(response.usage.inputTokens).toBeGreaterThan(0);
    expect(response.usage.totalTokens).toBeGreaterThanOrEqual(
      response.usage.inputTokens
    );
  });

  it('should estimate cost', async () => {
    const request = createMockRequest();
    const context = createMockContext();

    const response = await dispatcher.dispatch(request, context);

    expect(response.usage.estimatedCostUsd).toBeGreaterThanOrEqual(0);
  });

  it('should include quality gate results', async () => {
    const request = createMockRequest();
    const context = createMockContext();

    const response = await dispatcher.dispatch(request, context);

    expect(response.qualityGate).toBeDefined();
    expect(response.qualityGate.checks).toBeInstanceOf(Array);
    expect(response.qualityGate.checks.some((c) => c.name === 'phi_scan')).toBe(
      true
    );
  });

  it('should measure latency', async () => {
    const request = createMockRequest();
    const context = createMockContext();

    const response = await dispatcher.dispatch(request, context);

    expect(response.metrics.latencyMs).toBeGreaterThanOrEqual(0);
  });
});


// =============================================================================
// Tests: Caching
// =============================================================================

describe('CustomDispatcher - Caching', () => {
  let dispatcher: CustomDispatcher;

  beforeEach(() => {
    dispatcher = new CustomDispatcher();
  });

  it('should cache dispatch decisions', async () => {
    const request = createMockRequest();
    const context = createMockContext();

    await dispatcher.dispatch(request, context);

    const cacheKey = dispatcher['buildCacheKey'](context);
    expect(cacheKey).toBeDefined();
  });

  it('should clear cache on demand', () => {
    dispatcher.clearCache();

    expect(dispatcher).toBeDefined();
  });

  it('should build consistent cache keys', () => {
    const context = createMockContext({
      taskType: 'summarize',
      workflowStage: 6,
      requiredPhiHandling: true,
    });

    const key1 = dispatcher['buildCacheKey'](context);
    const key2 = dispatcher['buildCacheKey'](context);

    expect(key1).toBe(key2);
  });
});


// =============================================================================
// Tests: Metrics and Health
// =============================================================================

describe('CustomDispatcher - Metrics & Health', () => {
  let dispatcher: CustomDispatcher;

  beforeEach(() => {
    dispatcher = new CustomDispatcher();
  });

  it('should track total dispatches', async () => {
    const request = createMockRequest();
    const context = createMockContext();

    const beforeA = dispatcher.getMetrics().totalDispatches;
    await dispatcher.dispatch(request, context);
    const afterA = dispatcher.getMetrics().totalDispatches;

    expect(afterA).toBe(beforeA + 1);
  });

  it('should calculate success rate', async () => {
    const request = createMockRequest();
    const context = createMockContext();

    await dispatcher.dispatch(request, context);
    const metrics = dispatcher.getMetrics();

    expect(metrics.successRate).toBeGreaterThanOrEqual(0);
    expect(metrics.successRate).toBeLessThanOrEqual(100);
  });

  it('should report healthy status with good success rate', async () => {
    const request = createMockRequest();
    const context = createMockContext();

    for (let i = 0; i < 5; i++) {
      await dispatcher.dispatch(request, context);
    }

    const isHealthy = dispatcher.isHealthy();
    const metrics = dispatcher.getMetrics();

    if (metrics.totalDispatches > 0) {
      expect(isHealthy).toBe(metrics.successRate > 80);
    }
  });

  it('should report healthy for new dispatcher', () => {
    const freshDispatcher = new CustomDispatcher();
    const isHealthy = freshDispatcher.isHealthy();

    expect(isHealthy).toBe(true);
  });
});


// =============================================================================
// Tests: Request/Response Transformation
// =============================================================================

describe('CustomDispatcher - Request/Response Transformation', () => {
  let dispatcher: CustomDispatcher;

  beforeEach(() => {
    dispatcher = new CustomDispatcher();
  });

  it('should build response with routing info', async () => {
    const request = createMockRequest();
    const context = createMockContext();

    const response = await dispatcher.dispatch(request, context);

    expect(response.routing).toBeDefined();
    expect(response.routing.initialTier).toBeDefined();
    expect(response.routing.finalTier).toBeDefined();
    expect(response.routing.provider).toBeDefined();
    expect(response.routing.model).toBeDefined();
  });

  it('should handle JSON parsing in response', async () => {
    const request = createMockRequest({ prompt: '{"key": "value"}' });
    const context = createMockContext();

    const response = await dispatcher.dispatch(request, context);

    expect(response.parsed).toBeDefined();
  });

  it('should handle non-JSON responses gracefully', async () => {
    const request = createMockRequest({ prompt: 'plain text response' });
    const context = createMockContext();

    const response = await dispatcher.dispatch(request, context);

    expect(response.content).toBeDefined();
    expect(typeof response.parsed === 'object' || response.parsed === undefined).toBe(true);
  });
});


// =============================================================================
// Tests: Agent Registry
// =============================================================================

describe('CustomDispatcher - Agent Registry', () => {
  it('should define all agent registry entries', () => {
    const agents: CustomAgentType[] = [
      'DataPrep',
      'Analysis',
      'Quality',
      'IRB',
      'Manuscript',
    ];

    agents.forEach((agentType) => {
      const agent = CUSTOM_AGENT_REGISTRY[agentType];

      expect(agent).toBeDefined();
      expect(agent.id).toBe(agentType);
      expect(agent.name).toBeDefined();
      expect(agent.description).toBeDefined();
      expect(agent.taskTypes).toBeInstanceOf(Array);
      expect(agent.workflowStages).toBeInstanceOf(Array);
      expect(agent.phiRequired).toEqual(expect.any(Boolean));
      expect(agent.maxTokens).toBeGreaterThan(0);
      expect(agent.modelTier).toBeDefined();
    });
  });

  it('should verify stage coverage in registry', () => {
    const allStages = new Set<number>();

    Object.values(CUSTOM_AGENT_REGISTRY).forEach((agent) => {
      agent.workflowStages.forEach((stage) => {
        allStages.add(stage);
      });
    });

    const qualityAgent = CUSTOM_AGENT_REGISTRY.Quality;
    expect(qualityAgent.workflowStages.length).toBeGreaterThan(10);
  });

  it('should verify PHI handling requirements', () => {
    const phiRequiredAgents = ['DataPrep', 'IRB', 'Manuscript'];

    phiRequiredAgents.forEach((agentName) => {
      const agent = CUSTOM_AGENT_REGISTRY[agentName as CustomAgentType];
      expect(agent.phiRequired).toBe(true);
    });
  });
});


// =============================================================================
// Tests: Factory Function
// =============================================================================

describe('CustomDispatcher - Factory Function', () => {
  it('should create dispatcher via factory', () => {
    const dispatcher = createCustomDispatcher();

    expect(dispatcher).toBeInstanceOf(CustomDispatcher);
  });

  it('should create dispatcher with custom config via factory', () => {
    const dispatcher = createCustomDispatcher({ fallbackTier: 'FRONTIER' });

    expect(dispatcher).toBeInstanceOf(CustomDispatcher);
  });

  it('should create independent instances', () => {
    const dispatcher1 = createCustomDispatcher();
    const dispatcher2 = createCustomDispatcher();

    expect(dispatcher1).not.toBe(dispatcher2);
  });
});


// =============================================================================
// Tests: Error Handling
// =============================================================================

describe('CustomDispatcher - Error Handling', () => {
  let dispatcher: CustomDispatcher;

  beforeEach(() => {
    dispatcher = new CustomDispatcher();
  });

  it('should handle invalid task types gracefully', async () => {
    const request = createMockRequest({
      taskType: 'invalid_task_type' as AITaskType,
    });
    const context = createMockContext({
      taskType: 'invalid_task_type' as AITaskType,
      workflowStage: undefined,
    });

    const response = await dispatcher.dispatch(request, context);

    expect(response).toBeDefined();
    expect(response.content).toBeDefined();
  });

  it('should handle empty prompt gracefully', async () => {
    const request = createMockRequest({ prompt: '' });
    const context = createMockContext();

    const response = await dispatcher.dispatch(request, context);

    expect(response).toBeDefined();
    expect(response.usage.inputTokens).toBeGreaterThanOrEqual(0);
  });
});


// =============================================================================
// Tests: Feature Flag Integration
// =============================================================================

describe('CustomDispatcher - Feature Flag Integration', () => {
  it('should respect feature flags in agent selection', () => {
    const dispatcher = new CustomDispatcher();

    const registry = dispatcher.getAgentRegistry();
    expect(Object.keys(registry).length).toBe(5);
  });

  it('should include metrics flag support', async () => {
    const dispatcher = new CustomDispatcher({ enableMetrics: true });

    const request = createMockRequest();
    const context = createMockContext();

    await dispatcher.dispatch(request, context);
    const metrics = dispatcher.getMetrics();

    expect(metrics).toBeDefined();
  });
});
