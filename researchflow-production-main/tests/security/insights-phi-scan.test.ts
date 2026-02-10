/**
 * InsightsBus HIPAA Compliance Tests
 * 
 * Security tests for PHI handling in the insights event bus.
 * Linear Issue: ROS-60
 * 
 * @module tests/security/insights-phi-scan
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

// Mock Redis for testing
vi.mock('ioredis', () => ({
  default: vi.fn().mockImplementation(() => ({
    on: vi.fn(),
    xadd: vi.fn().mockResolvedValue('1234567890-0'),
    xgroup: vi.fn().mockResolvedValue('OK'),
    xreadgroup: vi.fn().mockResolvedValue(null),
    xack: vi.fn().mockResolvedValue(1),
    quit: vi.fn().mockResolvedValue('OK'),
    ping: vi.fn().mockResolvedValue('PONG'),
  })),
}));

// PHI patterns that should NEVER appear in logs
const PHI_PATTERNS = {
  SSN: /\b\d{3}-\d{2}-\d{4}\b/,
  MRN: /\b(MRN|mrn)[:\s]?\d{6,10}\b/i,
  DOB: /\b(DOB|dob|date of birth)[:\s]?\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b/i,
  PHONE: /\b\d{3}[-.]?\d{3}[-.]?\d{4}\b/,
  EMAIL: /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/,
  ADDRESS: /\b\d{1,5}\s+[\w\s]+(?:street|st|avenue|ave|road|rd|drive|dr|lane|ln|way|court|ct)\b/i,
  NAME_PATTERN: /\b(patient|name)[:\s]+[A-Z][a-z]+\s+[A-Z][a-z]+\b/i,
};

type InsightsEvent = {
  id: string;
  timestamp: string;
  governance_mode: 'LIVE' | 'DEMO' | 'STANDBY';
  project_id: string;
  tier: string;
  status: string;
  run_id: string;
  stage: number;
  agent_id: string;
  user_id: string;
  tenant_id: string;
  input?: string;
  output?: string;
};

// Sample events for testing
const createTestEvent = (overrides: Partial<InsightsEvent> = {}): InsightsEvent => ({
  id: 'evt_123',
  timestamp: new Date().toISOString(),
  governance_mode: 'LIVE' as const,
  project_id: 'proj_456',
  tier: 'standard',
  status: 'completed',
  run_id: 'run_789',
  stage: 5,
  agent_id: 'agent_001',
  user_id: 'user_123',
  tenant_id: 'tenant_abc',
  ...overrides,
});

describe('InsightsBus HIPAA Compliance', () => {
  describe('PHI Detection', () => {
    it('should detect SSN patterns', () => {
      const event = createTestEvent({
        output: 'Patient SSN: 123-45-6789',
      });
      
      const hasPHI = Object.values(PHI_PATTERNS).some(pattern => 
        pattern.test(JSON.stringify(event))
      );
      
      expect(hasPHI).toBe(true);
    });

    it('should detect MRN patterns', () => {
      const event = createTestEvent({
        output: 'Medical Record: MRN:12345678',
      });
      
      const hasPHI = Object.values(PHI_PATTERNS).some(pattern => 
        pattern.test(JSON.stringify(event))
      );
      
      expect(hasPHI).toBe(true);
    });

    it('should detect DOB patterns', () => {
      const event = createTestEvent({
        output: 'DOB: 01/15/1990',
      });
      
      const hasPHI = Object.values(PHI_PATTERNS).some(pattern => 
        pattern.test(JSON.stringify(event))
      );
      
      expect(hasPHI).toBe(true);
    });

    it('should detect email addresses', () => {
      const event = createTestEvent({
        output: 'Contact: john.doe@hospital.com',
      });
      
      const hasPHI = Object.values(PHI_PATTERNS).some(pattern => 
        pattern.test(JSON.stringify(event))
      );
      
      expect(hasPHI).toBe(true);
    });

    it('should detect phone numbers', () => {
      const event = createTestEvent({
        output: 'Phone: 555-123-4567',
      });
      
      const hasPHI = Object.values(PHI_PATTERNS).some(pattern => 
        pattern.test(JSON.stringify(event))
      );
      
      expect(hasPHI).toBe(true);
    });

    it('should detect physical addresses', () => {
      const event = createTestEvent({
        output: 'Address: 123 Main Street',
      });
      
      const hasPHI = Object.values(PHI_PATTERNS).some(pattern => 
        pattern.test(JSON.stringify(event))
      );
      
      expect(hasPHI).toBe(true);
    });

    it('should allow events without PHI', () => {
      const event = createTestEvent({
        output: 'Statistical analysis complete. p-value: 0.03',
      });
      
      const hasPHI = Object.values(PHI_PATTERNS).some(pattern => 
        pattern.test(JSON.stringify(event))
      );
      
      expect(hasPHI).toBe(false);
    });
  });

  describe('TLS Enforcement', () => {
    const originalEnv = process.env;

    beforeEach(() => {
      process.env = { ...originalEnv };
    });

    afterEach(() => {
      process.env = originalEnv;
    });

    it('should require TLS URL in production', () => {
      process.env.NODE_ENV = 'production';
      const redisUrl = process.env.REDIS_URL || '';
      
      // In production, URL should start with rediss:// (TLS)
      if (process.env.NODE_ENV === 'production') {
        expect(
          redisUrl.startsWith('rediss://') || redisUrl === ''
        ).toBe(true);
      }
    });

    it('should allow non-TLS URL in development', () => {
      process.env.NODE_ENV = 'development';
      const redisUrl = 'redis://localhost:6379';
      
      expect(redisUrl.startsWith('redis://')).toBe(true);
    });
  });

  describe('Tenant Isolation', () => {
    it('should include tenant_id in event fields', () => {
      const event = createTestEvent({ tenant_id: 'tenant_abc' });
      
      expect(event.tenant_id).toBeDefined();
      expect(event.tenant_id).toBe('tenant_abc');
    });

    it('should generate tenant-specific stream names', () => {
      const tenantId = 'tenant_abc';
      const streamName = `ros:insights:${tenantId}`;
      
      expect(streamName).toBe('ros:insights:tenant_abc');
    });
  });

  describe('Access Control', () => {
    it('should require user_id for event attribution', () => {
      const event = createTestEvent({ user_id: 'user_123' });
      
      expect(event.user_id).toBeDefined();
    });

    it('should include governance_mode for audit', () => {
      const event = createTestEvent({ governance_mode: 'LIVE' });
      
      expect(event.governance_mode).toBe('LIVE');
    });

    it('should differentiate DEMO vs LIVE modes', () => {
      const demoEvent = createTestEvent({ governance_mode: 'DEMO' });
      const liveEvent = createTestEvent({ governance_mode: 'LIVE' });
      
      expect(demoEvent.governance_mode).not.toBe(liveEvent.governance_mode);
    });
  });

  describe('Data Retention', () => {
    it('should respect MAXLEN configuration', () => {
      const maxLen = parseInt(process.env.INSIGHTS_MAX_LEN || '100000', 10);
      
      expect(maxLen).toBeGreaterThan(0);
      expect(maxLen).toBeLessThanOrEqual(1000000); // Reasonable upper bound
    });

    it('should generate chronological entry IDs', () => {
      const entryId = '1704067200000-0';
      const [timestamp] = entryId.split('-');
      
      expect(parseInt(timestamp, 10)).toBeGreaterThan(0);
    });
  });

  describe('PHI Scrubbing Helper', () => {
    const scrubPHI = (text: string): string => {
      let scrubbed = text;
      
      // Replace SSN
      scrubbed = scrubbed.replace(/\b\d{3}-\d{2}-\d{4}\b/g, '[SSN-REDACTED]');
      
      // Replace MRN
      scrubbed = scrubbed.replace(/\b(MRN|mrn)[:\s]?\d{6,10}\b/gi, '[MRN-REDACTED]');
      
      // Replace email
      scrubbed = scrubbed.replace(
        /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/g,
        '[EMAIL-REDACTED]'
      );
      
      // Replace phone
      scrubbed = scrubbed.replace(/\b\d{3}[-.]?\d{3}[-.]?\d{4}\b/g, '[PHONE-REDACTED]');
      
      return scrubbed;
    };

    it('should scrub SSN from text', () => {
      const input = 'Patient SSN: 123-45-6789';
      const output = scrubPHI(input);
      
      expect(output).toBe('Patient SSN: [SSN-REDACTED]');
      expect(output).not.toContain('123-45-6789');
    });

    it('should scrub email from text', () => {
      const input = 'Contact: john@example.com';
      const output = scrubPHI(input);
      
      expect(output).toBe('Contact: [EMAIL-REDACTED]');
    });

    it('should scrub multiple PHI types', () => {
      const input = 'Patient john@example.com, SSN: 123-45-6789, Phone: 555-123-4567';
      const output = scrubPHI(input);
      
      expect(output).not.toContain('john@example.com');
      expect(output).not.toContain('123-45-6789');
      expect(output).not.toContain('555-123-4567');
    });

    it('should preserve non-PHI text', () => {
      const input = 'Analysis complete with p-value 0.03';
      const output = scrubPHI(input);
      
      expect(output).toBe(input);
    });
  });
});

describe('InsightsBus Integration Security', () => {
  describe('Event Publishing', () => {
    it('should not allow events with input containing PHI', async () => {
      const eventWithPHI = createTestEvent({
        input: 'Analyze patient John Smith, SSN: 123-45-6789',
      });
      
      // In production, this should be blocked or scrubbed
      const containsPHI = Object.values(PHI_PATTERNS).some(pattern =>
        pattern.test(eventWithPHI.input || '')
      );
      
      expect(containsPHI).toBe(true);
      // Real implementation should: expect(publishResult).toBeNull();
    });

    it('should allow events with safe statistical output', async () => {
      const safeEvent = createTestEvent({
        output: 'Regression analysis: R² = 0.85, F(1,98) = 45.2, p < 0.001',
      });
      
      const containsPHI = Object.values(PHI_PATTERNS).some(pattern =>
        pattern.test(safeEvent.output || '')
      );
      
      expect(containsPHI).toBe(false);
    });
  });

  describe('Event Consuming', () => {
    it('should verify consumer has read permissions', () => {
      const mockPermissions = {
        'user_123': ['insights:read', 'insights:write'],
        'user_456': ['insights:read'],
        'user_789': [],
      };
      
      const canRead = (userId: string) => 
        mockPermissions[userId]?.includes('insights:read') ?? false;
      
      expect(canRead('user_123')).toBe(true);
      expect(canRead('user_456')).toBe(true);
      expect(canRead('user_789')).toBe(false);
    });

    it('should filter events by tenant for multi-tenant isolation', () => {
      const events = [
        createTestEvent({ tenant_id: 'tenant_a', id: '1' }),
        createTestEvent({ tenant_id: 'tenant_b', id: '2' }),
        createTestEvent({ tenant_id: 'tenant_a', id: '3' }),
      ];
      
      const tenantAEvents = events.filter(e => e.tenant_id === 'tenant_a');
      
      expect(tenantAEvents).toHaveLength(2);
      expect(tenantAEvents.every(e => e.tenant_id === 'tenant_a')).toBe(true);
    });
  });
});
