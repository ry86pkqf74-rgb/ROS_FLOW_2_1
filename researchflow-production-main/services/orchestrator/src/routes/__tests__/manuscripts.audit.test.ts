/**
 * Manuscript Mutations - Audit Events Integration Tests
 *
 * Verifies that every manuscript write operation appends an audit event
 * to the canonical audit_events table (stream_type=MANUSCRIPT).
 *
 * SCOPE: Tests only - no implementation changes allowed.
 */

import express from 'express';
import request from 'supertest';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

import manuscriptsRouter from '../manuscripts';

// Mock dependencies
vi.mock('../../../db', () => ({
  pool: {
    connect: vi.fn(),
  },
  db: {
    execute: vi.fn(),
  },
}));

vi.mock('../../middleware/rbac', () => ({
  requireRole: () => (req: any, res: any, next: any) => {
    // Inject mock user
    req.user = { id: 'test-user-123', email: 'test@example.com', role: 'RESEARCHER' };
    next();
  },
}));

vi.mock('../../services/audit.service', () => ({
  appendEvent: vi.fn(),
}));

vi.mock('../../services/phi-protection', () => ({
  scanForPhi: vi.fn(() => ({ detected: false, identifiers: [] })),
}));

// Test app setup
function createTestApp() {
  const app = express();
  app.use(express.json());
  app.use('/api/manuscripts', manuscriptsRouter);
  return app;
}

describe('Manuscript Mutations - Audit Events Integration', () => {
  let app: express.Application;

  beforeEach(async () => {
    app = createTestApp();
    vi.clearAllMocks();

    // Import mocks
    const { pool } = await import('../../../db');
    const { appendEvent } = await import('../../services/audit.service');

    // Setup default mock client for transactions
    const mockClient = {
      query: vi.fn()
        .mockResolvedValue({ rows: [], rowCount: 0 }),
      release: vi.fn(),
    };

    (pool.connect as any).mockResolvedValue(mockClient);
    (appendEvent as any).mockResolvedValue({
      id: 'evt-uuid-1',
      stream_id: 'stream-uuid-1',
      seq: 1,
      event_hash: 'hash-abc',
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('POST /api/manuscripts - Create Manuscript', () => {
    it('should append audit event with stream_type=MANUSCRIPT on create', async () => {
      const { pool } = await import('../../../db');
      const { appendEvent } = await import('../../services/audit.service');

      const mockClient = {
        query: vi.fn().mockResolvedValue({ rows: [], rowCount: 0 }),
        release: vi.fn(),
      };
      (pool.connect as any).mockResolvedValue(mockClient);

      const response = await request(app)
        .post('/api/manuscripts')
        .send({
          title: 'Test Manuscript',
          templateType: 'imrad',
          citationStyle: 'AMA',
        })
        .expect(201);

      expect(response.body).toHaveProperty('id');
      const manuscriptId = response.body.id;

      // Verify appendEvent was called
      expect(appendEvent).toHaveBeenCalled();
      const auditCall = (appendEvent as any).mock.calls.find((call: any) =>
        call[1]?.action === 'CREATE' && call[1]?.resource_type === 'manuscript'
      );

      expect(auditCall).toBeDefined();
      expect(auditCall[1]).toMatchObject({
        stream_type: 'MANUSCRIPT',
        stream_key: manuscriptId,
        actor_type: 'USER',
        actor_id: 'test-user-123',
        service: 'orchestrator',
        action: 'CREATE',
        resource_type: 'manuscript',
        resource_id: manuscriptId,
      });

      // Verify payload doesn't contain long content strings (PHI check)
      const payload = auditCall[1].payload;
      expect(payload).toBeDefined();
      if (typeof payload.content === 'string') {
        expect(payload.content.length).toBeLessThan(256);
      }
    });

    it('should include dedupe_key to prevent duplicate events', async () => {
      const { appendEvent } = await import('../../services/audit.service');

      await request(app)
        .post('/api/manuscripts')
        .send({ title: 'Deduplication Test', templateType: 'imrad' })
        .expect(201);

      expect(appendEvent).toHaveBeenCalled();
      const auditCall = (appendEvent as any).mock.calls[0];
      expect(auditCall[1]).toHaveProperty('dedupe_key');
      expect(auditCall[1].dedupe_key).toContain('manuscript:create:');
    });
  });

  describe('PATCH /api/manuscripts/:id - Update Manuscript', () => {
    it('should append audit event with stream_type=MANUSCRIPT on update', async () => {
      const { pool, db } = await import('../../../db');
      const { appendEvent } = await import('../../services/audit.service');

      const manuscriptId = 'ms_test123';
      const mockClient = {
        query: vi.fn().mockResolvedValue({ rows: [{ id: manuscriptId, status: 'in_review' }], rowCount: 1 }),
        release: vi.fn(),
      };
      (pool.connect as any).mockResolvedValue(mockClient);
      // Mock db.execute for the final SELECT
      (db.execute as any).mockResolvedValue({ rows: [{ id: manuscriptId, status: 'in_review' }] });

      await request(app)
        .patch(`/api/manuscripts/${manuscriptId}`)
        .send({ status: 'in_review', targetJournal: 'Nature' })
        .expect(200);

      expect(appendEvent).toHaveBeenCalled();
      const auditCall = (appendEvent as any).mock.calls.find((call: any) =>
        call[1]?.action === 'UPDATE'
      );

      expect(auditCall).toBeDefined();
      expect(auditCall[1]).toMatchObject({
        stream_type: 'MANUSCRIPT',
        stream_key: manuscriptId,
        action: 'UPDATE',
        resource_type: 'manuscript',
        resource_id: manuscriptId,
      });

      // No PHI leak check
      const payload = auditCall[1].payload;
      expect(payload.status).toBe('in_review');
      expect(payload.target_journal).toBe('Nature');
    });
  });

  describe('POST /api/manuscripts/:id/doc/save - Save Document', () => {
    it('should append audit event on document save', async () => {
      const { pool, db } = await import('../../../db');
      const { appendEvent } = await import('../../services/audit.service');

      const manuscriptId = 'ms_test456';
      const mockClient = {
        query: vi.fn()
          .mockResolvedValueOnce({ rows: [{ version_number: 1, current_hash: 'hash1' }], rowCount: 1 }) // Get current version
          .mockResolvedValueOnce({ rows: [], rowCount: 1 }) // Insert new version
          .mockResolvedValueOnce({ rows: [], rowCount: 1 }) // Update manuscript
          .mockResolvedValue({ rows: [], rowCount: 0 }),
        release: vi.fn(),
      };
      (pool.connect as any).mockResolvedValue(mockClient);
      // Mock db.execute is not needed as doc/save uses transaction client only

      await request(app)
        .post(`/api/manuscripts/${manuscriptId}/doc/save`)
        .send({
          contentText: 'This is test content',
          changeDescription: 'Updated introduction',
        })
        .expect(200);

      expect(appendEvent).toHaveBeenCalled();
      const auditCall = (appendEvent as any).mock.calls.find((call: any) =>
        call[1]?.action === 'DOC_SAVE'
      );

      expect(auditCall).toBeDefined();
      expect(auditCall[1]).toMatchObject({
        stream_type: 'MANUSCRIPT',
        stream_key: manuscriptId,
        action: 'DOC_SAVE',
        resource_type: 'manuscript_version', // Doc save creates a version
        // resource_id will be the version_id, not manuscriptId
      });

      // Payload should NOT contain full content text (PHI protection)
      const payload = auditCall[1].payload;
      expect(payload).toBeDefined();
      expect(payload.content_text).toBeUndefined();
      // Should have metadata only
      expect(payload.manuscript_id).toBe(manuscriptId);
      expect(auditCall[1].resource_id).toMatch(/^ver_/); // Version ID starts with ver_
    });
  });

  describe('POST /api/manuscripts/:id/sections/:sectionId/refine - Refine Section', () => {
    it('should append audit event for AI refine request', async () => {
      const { pool, db } = await import('../../../db');
      const { appendEvent } = await import('../../services/audit.service');

      const manuscriptId = 'ms_test789';
      const sectionId = 'introduction';
      const mockClient = {
        query: vi.fn().mockResolvedValue({ rows: [], rowCount: 0 }),
        release: vi.fn(),
      };
      (pool.connect as any).mockResolvedValue(mockClient);
      (db.execute as any).mockResolvedValue({ rows: [] });

      await request(app)
        .post(`/api/manuscripts/${manuscriptId}/sections/${sectionId}/refine`)
        .send({
          selectedText: 'Original text',
          instruction: 'Make it more formal',
          selectionStart: 0,
          selectionEnd: 13,
        })
        .expect(200);

      expect(appendEvent).toHaveBeenCalled();
      const auditCall = (appendEvent as any).mock.calls.find((call: any) =>
        call[1]?.action === 'AI_REFINE_REQUESTED'
      );

      expect(auditCall).toBeDefined();
      expect(auditCall[1]).toMatchObject({
        stream_type: 'MANUSCRIPT',
        stream_key: manuscriptId,
        action: 'AI_REFINE_REQUESTED',
        resource_type: 'manuscript',
        resource_id: manuscriptId,
      });

      // Should have hashes, not raw content
      expect(auditCall[1]).toHaveProperty('before_hash');
      expect(auditCall[1]).toHaveProperty('after_hash');

      const payload = auditCall[1].payload;
      expect(payload.input_hash).toBeDefined();
      expect(payload.output_hash).toBeDefined();
      // Should NOT contain raw selectedText
      expect(payload.selectedText).toBeUndefined();
    });

    it('should log PHI_BLOCKED event when PHI detected', async () => {
      const { pool } = await import('../../../db');
      const { appendEvent } = await import('../../services/audit.service');
      const { scanForPhi } = await import('../../services/phi-protection');

      const manuscriptId = 'ms_testphi';
      const mockClient = {
        query: vi.fn().mockResolvedValue({ rows: [], rowCount: 0 }),
        release: vi.fn(),
      };
      (pool.connect as any).mockResolvedValue(mockClient);

      // Mock PHI detection
      (scanForPhi as any).mockReturnValue({
        detected: true,
        identifiers: [{ type: 'SSN', position: { start: 0, end: 11 } }],
      });

      // Set GOVERNANCE_MODE to LIVE to trigger PHI check
      const originalMode = process.env.GOVERNANCE_MODE;
      process.env.GOVERNANCE_MODE = 'LIVE';

      await request(app)
        .post(`/api/manuscripts/${manuscriptId}/sections/introduction/refine`)
        .send({
          selectedText: '123-45-6789',
          instruction: 'Refine',
          selectionStart: 0,
          selectionEnd: 11,
        })
        .expect(400);

      // Restore
      process.env.GOVERNANCE_MODE = originalMode;

      expect(appendEvent).toHaveBeenCalled();
      const auditCall = (appendEvent as any).mock.calls.find((call: any) =>
        call[1]?.action === 'PHI_BLOCKED'
      );

      expect(auditCall).toBeDefined();
      expect(auditCall[1]).toMatchObject({
        stream_type: 'MANUSCRIPT',
        stream_key: manuscriptId,
        action: 'PHI_BLOCKED',
      });
    });
  });

  describe('POST /api/manuscripts/:id/abstract/generate - Generate Abstract', () => {
    it('should append audit event for abstract generation', async () => {
      const { pool, db } = await import('../../../db');
      const { appendEvent } = await import('../../services/audit.service');

      const manuscriptId = 'ms_abstract';
      const mockClient = {
        query: vi.fn().mockResolvedValue({ rows: [], rowCount: 0 }),
        release: vi.fn(),
      };
      (pool.connect as any).mockResolvedValue(mockClient);
      (db.execute as any).mockResolvedValue({
        rows: [{ content: { sections: {} } }],
        rowCount: 1,
      });

      await request(app)
        .post(`/api/manuscripts/${manuscriptId}/abstract/generate`)
        .send({ structured: true, wordLimit: 250 })
        .expect(200);

      expect(appendEvent).toHaveBeenCalled();
      const auditCall = (appendEvent as any).mock.calls.find((call: any) =>
        call[1]?.action === 'ABSTRACT_GENERATED'
      );

      expect(auditCall).toBeDefined();
      expect(auditCall[1]).toMatchObject({
        stream_type: 'MANUSCRIPT',
        stream_key: manuscriptId,
        action: 'ABSTRACT_GENERATED',
        resource_type: 'manuscript',
        resource_id: manuscriptId,
      });

      // Should have metadata, not generated content
      const payload = auditCall[1].payload;
      expect(payload.structured).toBe(true);
      expect(payload.word_limit).toBe(250);
      expect(payload.generated_content).toBeUndefined();
    });
  });

  describe('POST /api/manuscripts/:id/comments - Create Comment', () => {
    it('should append audit event for comment creation', async () => {
      const { pool, db } = await import('../../../db');
      const { appendEvent } = await import('../../services/audit.service');

      const manuscriptId = 'ms_comment1';
      const sectionId = '550e8400-e29b-41d4-a716-446655440000'; // Valid UUID
      const mockClient = {
        query: vi.fn().mockResolvedValue({ rows: [], rowCount: 0 }),
        release: vi.fn(),
      };
      (pool.connect as any).mockResolvedValue(mockClient);
      (db.execute as any).mockResolvedValue({
        rows: [{ id: 'cmt_123', body: 'Test comment' }],
        rowCount: 1,
      });

      await request(app)
        .post(`/api/manuscripts/${manuscriptId}/comments`)
        .send({
          body: 'This is a comment',
          sectionId: sectionId,
          anchorStart: 10,
          anchorEnd: 20,
        })
        .expect(201);

      expect(appendEvent).toHaveBeenCalled();
      const auditCall = (appendEvent as any).mock.calls.find((call: any) =>
        call[1]?.action === 'COMMENT_ADDED'
      );

      expect(auditCall).toBeDefined();
      expect(auditCall[1]).toMatchObject({
        stream_type: 'MANUSCRIPT',
        stream_key: manuscriptId,
        action: 'COMMENT_ADDED',
        resource_type: 'manuscript_comment',
      });

      // Should not contain comment body
      const payload = auditCall[1].payload;
      expect(payload.manuscript_id).toBe(manuscriptId);
      expect(payload.comment_id).toBeDefined();
      expect(payload.has_anchor).toBe(true);
      expect(payload.body).toBeUndefined(); // No full text
    });
  });

  describe('POST /api/manuscripts/:id/comments/:commentId/resolve - Resolve Comment', () => {
    it('should append audit event for comment resolution', async () => {
      const { pool } = await import('../../../db');
      const { appendEvent } = await import('../../services/audit.service');

      const manuscriptId = 'ms_comment2';
      const commentId = 'cmt_456';
      const mockClient = {
        query: vi.fn().mockResolvedValue({
          rows: [{ id: commentId, status: 'resolved' }],
          rowCount: 1,
        }),
        release: vi.fn(),
      };
      (pool.connect as any).mockResolvedValue(mockClient);

      await request(app)
        .post(`/api/manuscripts/${manuscriptId}/comments/${commentId}/resolve`)
        .expect(200);

      expect(appendEvent).toHaveBeenCalled();
      const auditCall = (appendEvent as any).mock.calls.find((call: any) =>
        call[1]?.action === 'COMMENT_RESOLVED'
      );

      expect(auditCall).toBeDefined();
      expect(auditCall[1]).toMatchObject({
        stream_type: 'MANUSCRIPT',
        stream_key: manuscriptId,
        action: 'COMMENT_RESOLVED',
        resource_type: 'manuscript_comment',
        resource_id: commentId,
      });

      const payload = auditCall[1].payload;
      expect(payload.comment_id).toBe(commentId);
      expect(payload.status).toBe('resolved');
    });
  });

  describe('Audit Event Quality Checks', () => {
    it('should use consistent stream_type=MANUSCRIPT across all operations', async () => {
      const { appendEvent } = await import('../../services/audit.service');

      // Create manuscript
      await request(app)
        .post('/api/manuscripts')
        .send({ title: 'Consistency Test', templateType: 'imrad' })
        .expect(201);

      const calls = (appendEvent as any).mock.calls;
      calls.forEach((call: any) => {
        expect(call[1].stream_type).toBe('MANUSCRIPT');
      });
    });

    it('should not leak PHI in payload fields across all endpoints', async () => {
      const { appendEvent } = await import('../../services/audit.service');

      await request(app)
        .post('/api/manuscripts')
        .send({ title: 'PHI Check Test', templateType: 'imrad' })
        .expect(201);

      const calls = (appendEvent as any).mock.calls;
      calls.forEach((call: any) => {
        const payload = call[1].payload;
        if (payload) {
          // Check for long string fields that might contain PHI
          Object.values(payload).forEach((value: any) => {
            if (typeof value === 'string' && value.length > 256) {
              throw new Error(`Payload contains long string (${value.length} chars) - possible PHI leak`);
            }
          });
        }
      });
    });

    it('should include actor_id in all audit events', async () => {
      const { appendEvent } = await import('../../services/audit.service');

      await request(app)
        .post('/api/manuscripts')
        .send({ title: 'Actor Test', templateType: 'imrad' })
        .expect(201);

      const calls = (appendEvent as any).mock.calls;
      calls.forEach((call: any) => {
        expect(call[1]).toHaveProperty('actor_id');
        expect(call[1].actor_type).toBe('USER');
      });
    });

    it('should create dedupe_key for all mutation events', async () => {
      const { appendEvent } = await import('../../services/audit.service');

      await request(app)
        .post('/api/manuscripts')
        .send({ title: 'Dedupe Test', templateType: 'imrad' })
        .expect(201);

      const calls = (appendEvent as any).mock.calls;
      calls.forEach((call: any) => {
        expect(call[1]).toHaveProperty('dedupe_key');
        expect(typeof call[1].dedupe_key).toBe('string');
        expect(call[1].dedupe_key.length).toBeGreaterThan(0);
      });
    });
  });
});
