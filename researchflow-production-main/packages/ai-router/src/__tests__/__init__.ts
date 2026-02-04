/**
 * Phase 8 Testing Module - AI Router Package
 *
 * Test suite for:
 * - CustomDispatcher routing logic and agent selection
 * - Feature flag integration
 * - Fallback behavior on dispatch failure
 * - WebSocket streaming support
 * - Dispatch metrics and health checks
 * - Quality gate evaluation
 *
 * Test Framework: Vitest with TypeScript
 * Coverage: Unit tests for dispatcher, integration tests for routing
 */

export const TEST_VERSION = '8.0.0';
export const TEST_DESCRIPTION = 'Phase 8: Testing & Validation for AI Router';

/**
 * Test configuration constants
 */
export const TEST_CONFIG = {
  timeoutMs: 10000,
  retries: 3,
  mockAgentLatencyMs: 100,
  defaultFallbackTier: 'MINI' as const,
};

/**
 * Mock data for tests
 */
export const MOCK_TEST_DATA = {
  projectId: 'test-proj-001',
  runId: 'test-run-001',
  threadId: 'test-thread-001',
};
