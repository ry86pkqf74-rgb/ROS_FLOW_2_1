/**
 * Tests for FeatureFlagsService
 *
 * Tests feature flag evaluation, rollout percentages, and mode constraints.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

// Mock @researchflow/core/schema
vi.mock('@researchflow/core/schema', () => ({
  featureFlags: 'feature_flags_table',
  GOVERNANCE_MODES: ['DEMO', 'LIVE', 'STANDBY'],
}));

// Mock database module
vi.mock('../../../db', () => ({
  db: {
    select: vi.fn(),
    from: vi.fn(),
    where: vi.fn(),
    limit: vi.fn(),
    insert: vi.fn().mockReturnThis(),
    values: vi.fn().mockReturnThis(),
    onConflictDoUpdate: vi.fn().mockResolvedValue({}),
    delete: vi.fn().mockReturnThis(),
  },
}));

// Mock audit service
vi.mock('../audit-service', () => ({
  logAction: vi.fn().mockResolvedValue(undefined),
}));

// Mock event bus
vi.mock('../event-bus', () => ({
  eventBus: {
    publishGovernanceEvent: vi.fn(),
  },
}));

// Mock governance config service — reads from process.env so tests can override
vi.mock('../governance-config.service', () => ({
  getMode: vi.fn().mockImplementation(() =>
    Promise.resolve((process.env.GOVERNANCE_MODE as any) || 'DEMO')
  ),
}));

// Mock drizzle-orm (eq function)
vi.mock('drizzle-orm', () => ({
  eq: vi.fn().mockImplementation((col, val) => ({ col, val })),
}));

// NOTE: vi.mock() calls above are hoisted by Vitest and take effect before
// any imports, so the static imports below receive the mocked modules.
// (vi.resetModules() before static imports has no effect in ESM.)

import { db } from '../../../db';
import {
  isFlagEnabled,
  getFlags,
  listFlags,
  setFlag,
  clearFlagCache,
} from '../feature-flags.service';

/**
 * Helper: create a mock flag with the shape the service expects from the DB.
 * The service reads flag.flagKey, flag.enabled, flag.description, and
 * (flag.metadata as any)?.requiredModes / rolloutPercent.
 */
function mockFlag(overrides: Record<string, unknown> = {}) {
  return {
    flagKey: 'TEST_FLAG',
    enabled: true,
    description: null,
    metadata: { requiredModes: [], rolloutPercent: 100, scope: 'product' },
    ...overrides,
  };
}

/**
 * Helper: set up db.select mock so that:
 *  - `await db.select().from(table)` resolves to `flags` (for cache refresh)
 *  - `await db.select().from(table).where(...).limit(n)` also resolves to `flags`
 */
function setupSelectMock(flags: unknown[]) {
  (db.select as any).mockReturnValue({
    from: vi.fn().mockImplementation(() => {
      // Return an awaitable that also has .where() chaining
      const result = Promise.resolve(flags);
      (result as any).where = vi.fn().mockImplementation(() => {
        const whereResult = Promise.resolve(flags);
        (whereResult as any).limit = vi.fn().mockResolvedValue(flags);
        return whereResult;
      });
      return result;
    }),
  });
}

describe('FeatureFlagsService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    clearFlagCache();
    // Clear environment overrides
    delete process.env.FEATURE_ALLOW_UPLOADS;
    delete process.env.FEATURE_ALLOW_EXPORTS;
    process.env.GOVERNANCE_MODE = 'DEMO';
  });

  afterEach(() => {
    // Use clearAllMocks instead of resetAllMocks to preserve
    // mock implementations set by vi.mock() factories
    vi.clearAllMocks();
  });

  describe('isFlagEnabled', () => {
    it('should return true for enabled flag with matching mode', async () => {
      const flag = mockFlag({
        flagKey: 'ALLOW_UPLOADS',
        enabled: true,
        metadata: { requiredModes: ['DEMO', 'LIVE'], rolloutPercent: 100 },
      });

      setupSelectMock([flag]);

      const result = await isFlagEnabled('ALLOW_UPLOADS');
      expect(result).toBe(true);
    });

    it('should return false for disabled flag', async () => {
      const flag = mockFlag({
        flagKey: 'ALLOW_EXPORTS',
        enabled: false,
        metadata: { requiredModes: ['LIVE'], rolloutPercent: 100 },
      });

      setupSelectMock([flag]);

      const result = await isFlagEnabled('ALLOW_EXPORTS');
      expect(result).toBe(false);
    });

    it('should return false when current mode not in requiredModes', async () => {
      process.env.GOVERNANCE_MODE = 'STANDBY';

      const flag = mockFlag({
        flagKey: 'ALLOW_UPLOADS',
        enabled: true,
        metadata: { requiredModes: ['DEMO', 'LIVE'], rolloutPercent: 100 },
      });

      setupSelectMock([flag]);

      const result = await isFlagEnabled('ALLOW_UPLOADS');
      expect(result).toBe(false);
    });

    it('should respect environment variable overrides', async () => {
      process.env.FEATURE_ALLOW_UPLOADS = 'false';

      const flag = mockFlag({
        flagKey: 'ALLOW_UPLOADS',
        enabled: true,
        metadata: { requiredModes: ['DEMO', 'LIVE'], rolloutPercent: 100 },
      });

      setupSelectMock([flag]);

      const result = await isFlagEnabled('ALLOW_UPLOADS');
      expect(result).toBe(false);
    });

    it('should use default value for unknown flags', async () => {
      setupSelectMock([]);

      const result = await isFlagEnabled('UNKNOWN_FLAG');
      expect(result).toBe(false);
    });

    it('should handle rollout percentage correctly', async () => {
      const flag = mockFlag({
        flagKey: 'EXPERIMENTAL_FEATURE',
        enabled: true,
        metadata: { requiredModes: ['DEMO', 'LIVE'], rolloutPercent: 50 },
      });

      setupSelectMock([flag]);

      // With 50% rollout, deterministic hash should give consistent results
      // for same user
      const result1 = await isFlagEnabled('EXPERIMENTAL_FEATURE', { userId: 'user-123' });
      clearFlagCache(); // Force re-fetch for second call
      setupSelectMock([flag]);
      const result2 = await isFlagEnabled('EXPERIMENTAL_FEATURE', { userId: 'user-123' });
      expect(result1).toBe(result2);
    });
  });

  describe('getFlags', () => {
    it('should return all flags as a boolean map', async () => {
      const flags = [
        mockFlag({ flagKey: 'ALLOW_UPLOADS', enabled: true, metadata: { requiredModes: ['DEMO', 'LIVE'], rolloutPercent: 100 } }),
        mockFlag({ flagKey: 'ALLOW_EXPORTS', enabled: false, metadata: { requiredModes: ['LIVE'], rolloutPercent: 100 } }),
      ];

      setupSelectMock(flags);

      const result = await getFlags({});
      expect(result.ALLOW_UPLOADS).toBe(true);
      expect(result.ALLOW_EXPORTS).toBe(false);
    });
  });

  describe('listFlags', () => {
    it('should return flags with full metadata', async () => {
      const flags = [
        mockFlag({
          flagKey: 'ALLOW_UPLOADS',
          enabled: true,
          description: 'Allow uploads',
          metadata: { requiredModes: ['DEMO', 'LIVE'], rolloutPercent: 100, scope: 'product' },
        }),
      ];

      setupSelectMock(flags);

      const result = await listFlags();
      expect(result).toHaveLength(1);
      expect(result[0]).toMatchObject({
        key: 'ALLOW_UPLOADS',
        enabled: true,
        description: 'Allow uploads',
      });
    });
  });

  describe('setFlag', () => {
    it('should update flag and publish event', async () => {
      const flag = mockFlag({
        flagKey: 'ALLOW_EXPORTS',
        enabled: false,
        description: 'Allow exports',
        metadata: { requiredModes: ['LIVE'], rolloutPercent: 100 },
      });

      setupSelectMock([flag]);

      await setFlag('ALLOW_EXPORTS', { enabled: true }, 'user-1');

      expect(db.insert).toHaveBeenCalled();
    });
  });
});
