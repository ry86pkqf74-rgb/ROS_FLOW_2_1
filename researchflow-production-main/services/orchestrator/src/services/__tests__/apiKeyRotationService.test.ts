/**
 * Tests for API Key Rotation Service
 * Task 138 - API key rotation reminders in profiles
 */

import { describe, it, expect, beforeEach } from 'vitest';

import {
  createApiKey,
  getApiKey,
  listUserApiKeys,
  rotateApiKey,
  revokeApiKey,
  getRotationReminders,
  getKeyRotationSummary,
  getKeyHistory,
} from '../apiKeyRotationService';

describe('ApiKeyRotationService', () => {
  const userId = 'test-user';
  const tenantId = 'test-tenant';

  describe('createApiKey', () => {
    it('should create a new API key', () => {
      const result = createApiKey({
        userId,
        tenantId,
        label: 'Test Key',
        scopes: ['READ', 'WRITE'],
      });

      expect(result.key).toBeDefined();
      expect(result.secretKey).toBeDefined();
      expect(result.key.label).toBe('Test Key');
      expect(result.key.scopes).toEqual(['READ', 'WRITE']);
      expect(result.key.status).toBe('ACTIVE');
      expect(result.secretKey).toMatch(/^rfk_/);
    });

    it('should generate unique key prefix', () => {
      const result = createApiKey({
        userId,
        tenantId,
        label: 'Prefix Test',
        scopes: ['READ'],
      });

      expect(result.key.keyPrefix).toBeDefined();
      expect(result.key.keyPrefix.length).toBeGreaterThan(0);
    });

    it('should set custom rotation interval', () => {
      const result = createApiKey({
        userId,
        tenantId,
        label: 'Rotation Test',
        rotationIntervalDays: 30,
        scopes: ['READ'],
      });

      expect(result.key.rotationIntervalDays).toBe(30);
    });

    it('should set expiration date', () => {
      const result = createApiKey({
        userId,
        tenantId,
        label: 'Expiry Test',
        expiresInDays: 365,
        scopes: ['READ'],
      });

      const expiresAt = new Date(result.key.expiresAt);
      const now = new Date();
      const diffDays = Math.ceil((expiresAt.getTime() - now.getTime()) / (24 * 60 * 60 * 1000));

      expect(diffDays).toBeCloseTo(365, 0);
    });
  });

  describe('getApiKey', () => {
    it('should return key by id', () => {
      const created = createApiKey({
        userId,
        tenantId,
        label: 'Get Test',
        scopes: ['READ'],
      });

      const key = getApiKey(created.key.id);
      expect(key).toBeDefined();
      expect(key?.id).toBe(created.key.id);
    });

    it('should return undefined for unknown key', () => {
      const key = getApiKey('non-existent-key');
      expect(key).toBeUndefined();
    });
  });

  describe('listUserApiKeys', () => {
    it('should list all keys for a user', () => {
      const testUserId = `list-user-${Date.now()}`;

      createApiKey({ userId: testUserId, tenantId, label: 'Key 1', scopes: ['READ'] });
      createApiKey({ userId: testUserId, tenantId, label: 'Key 2', scopes: ['READ'] });

      const keys = listUserApiKeys(testUserId);
      expect(keys.length).toBe(2);
      expect(keys.every(k => k.userId === testUserId)).toBe(true);
    });
  });

  describe('rotateApiKey', () => {
    it('should rotate key and invalidate old one', () => {
      const created = createApiKey({
        userId,
        tenantId,
        label: 'Rotate Test',
        scopes: ['READ'],
      });

      const oldKeyId = created.key.id;
      const result = rotateApiKey(oldKeyId, userId);

      expect(result).toBeDefined();
      expect(result!.secretKey).toBeDefined();
      expect(result!.secretKey).not.toBe(created.secretKey);

      // Old key should be rotated (inactive)
      const oldKey = getApiKey(oldKeyId);
      expect(oldKey?.status).toBe('ROTATED');
    });

    it('should throw error for revoked keys', () => {
      const created = createApiKey({
        userId,
        tenantId,
        label: 'Revoke Test',
        scopes: ['READ'],
      });

      revokeApiKey(created.key.id, userId);

      expect(() => rotateApiKey(created.key.id, userId))
        .toThrow('Cannot rotate');
    });
  });

  describe('revokeApiKey', () => {
    it('should revoke an active key', () => {
      const created = createApiKey({
        userId,
        tenantId,
        label: 'Revoke Test',
        scopes: ['READ'],
      });

      const success = revokeApiKey(created.key.id, userId, 'Security concern');
      expect(success).toBe(true);

      const key = getApiKey(created.key.id);
      expect(key?.status).toBe('REVOKED');
      expect(key?.revokedReason).toBe('Security concern');
    });
  });

  describe('getRotationReminders', () => {
    it('should return keys expiring within threshold', () => {
      const testUserId = `reminder-user-${Date.now()}`;

      // Create key expiring in 7 days
      createApiKey({
        userId: testUserId,
        tenantId,
        label: 'Expiring Soon',
        expiresInDays: 7,
        scopes: ['READ'],
      });

      const reminders = getRotationReminders({
        userId: testUserId,
        daysThreshold: 14,
      });

      expect(reminders.length).toBeGreaterThan(0);
      expect(reminders[0].reminderLevel).toBeDefined();
    });
  });

  describe('getKeyRotationSummary', () => {
    it('should return summary statistics', () => {
      const testUserId = `summary-user-${Date.now()}`;

      createApiKey({ userId: testUserId, tenantId, label: 'Summary Key', scopes: ['READ'] });

      const summary = getKeyRotationSummary(testUserId);

      expect(summary).toHaveProperty('totalKeys');
      expect(summary).toHaveProperty('activeKeys');
      expect(summary).toHaveProperty('expiringWithin30Days');
      expect(summary).toHaveProperty('revokedKeys');
    });
  });

  describe('getKeyHistory', () => {
    it('should track key events', () => {
      const created = createApiKey({
        userId,
        tenantId,
        label: 'History Test',
        scopes: ['READ'],
      });

      const history = getKeyHistory(created.key.id);

      expect(history.length).toBeGreaterThan(0);
      expect(history.some(h => h.action === 'CREATED')).toBe(true);
    });
  });
});
