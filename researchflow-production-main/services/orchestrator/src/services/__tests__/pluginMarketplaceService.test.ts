/**
 * Tests for Plugin Marketplace Service
 * Task 137 - Plugin marketplace for third-party extensions
 */

import crypto from 'crypto';
import { describe, it, expect, beforeEach } from 'vitest';

import {
  listPlugins,
  getPlugin,
  installPlugin,
  uninstallPlugin,
  enablePlugin,
  disablePlugin,
  getInstallation,
  getPluginAuditLog,
} from '../pluginMarketplaceService';

describe('PluginMarketplaceService', () => {
  const tenantId = 'test-tenant';
  const userId = 'test-user';

  describe('listPlugins', () => {
    it('should return all plugins by default', () => {
      const result = listPlugins();
      expect(result.items.length).toBeGreaterThan(0);
      expect(result.items[0]).toHaveProperty('id');
      expect(result.items[0]).toHaveProperty('name');
    });

    it('should filter by category', () => {
      const result = listPlugins({ category: 'ANALYTICS' });
      expect(result.items.every(p => p.category === 'ANALYTICS')).toBe(true);
    });

    it('should filter verified plugins only', () => {
      const result = listPlugins({ verified: true });
      expect(result.items.every(p => p.verified === true)).toBe(true);
    });

    it('should search by query term', () => {
      const result = listPlugins({ search: 'statistical' });
      expect(result.items.length).toBeGreaterThan(0);
      expect(result.items.some(p =>
        p.name.toLowerCase().includes('statistical') ||
        p.description.toLowerCase().includes('statistical')
      )).toBe(true);
    });
  });

  describe('getPlugin', () => {
    it('should return plugin by id', () => {
      const result = listPlugins();
      const plugin = getPlugin(result.items[0].id);
      expect(plugin).toBeDefined();
      expect(plugin?.id).toBe(result.items[0].id);
    });

    it('should return undefined for unknown plugin', () => {
      const plugin = getPlugin('non-existent-plugin');
      expect(plugin).toBeUndefined();
    });
  });

  describe('installPlugin', () => {
    it('should install a plugin successfully', () => {
      const result = listPlugins();
      const installation = installPlugin(result.items[0].id, tenantId, userId);

      expect(installation).toBeDefined();
      expect(installation.pluginId).toBe(result.items[0].id);
      expect(installation.tenantId).toBe(tenantId);
      expect(installation.installedBy).toBe(userId);
      // Plugins are disabled by default for security
      expect(installation.enabled).toBe(false);
    });

    it('should throw error for unknown plugin', () => {
      expect(() => installPlugin('non-existent', tenantId, userId))
        .toThrow('Plugin not found');
    });

    it('should allow configuration during installation', () => {
      const result = listPlugins();
      const config = { apiKey: 'test-key' };
      const uniqueTenant = `config-${crypto.randomUUID()}`;
      const installation = installPlugin(result.items[0].id, uniqueTenant, userId, config);

      expect(installation.config).toEqual(config);
    });
  });

  describe('enablePlugin / disablePlugin', () => {
    it('should enable a disabled plugin', () => {
      const result = listPlugins();
      const uniqueTenant = `enable-${crypto.randomUUID()}`;
      installPlugin(result.items[0].id, uniqueTenant, userId);
      disablePlugin(result.items[0].id, uniqueTenant, userId);

      const enabled = enablePlugin(result.items[0].id, uniqueTenant, userId);
      expect(enabled?.enabled).toBe(true);
    });

    it('should disable an enabled plugin', () => {
      const result = listPlugins();
      const uniqueTenant = `disable-${crypto.randomUUID()}`;
      installPlugin(result.items[0].id, uniqueTenant, userId);

      const disabled = disablePlugin(result.items[0].id, uniqueTenant, userId);
      expect(disabled?.enabled).toBe(false);
    });
  });

  describe('uninstallPlugin', () => {
    it('should uninstall a plugin', () => {
      const result = listPlugins();
      const uniqueTenant = `uninstall-${crypto.randomUUID()}`;
      installPlugin(result.items[0].id, uniqueTenant, userId);

      const success = uninstallPlugin(result.items[0].id, uniqueTenant, userId);
      expect(success).toBe(true);

      const installation = getInstallation(result.items[0].id, uniqueTenant);
      expect(installation).toBeUndefined();
    });

    it('should return false for non-installed plugin', () => {
      const success = uninstallPlugin('non-installed', tenantId, userId);
      expect(success).toBe(false);
    });
  });

  describe('getPluginAuditLog', () => {
    it('should record installation actions', () => {
      const result = listPlugins();
      installPlugin(result.items[0].id, `audit-${tenantId}`, userId);

      const logs = getPluginAuditLog({ tenantId: `audit-${tenantId}` });
      expect(logs.length).toBeGreaterThan(0);
      expect(logs.some(l => l.action === 'INSTALLED')).toBe(true);
    });

    it('should filter by pluginId', () => {
      const result = listPlugins();
      installPlugin(result.items[0].id, `filter-${tenantId}`, userId);

      const logs = getPluginAuditLog({ pluginId: result.items[0].id });
      expect(logs.every(l => l.pluginId === result.items[0].id)).toBe(true);
    });
  });
});
