/**
 * E2E Test User Fixture
 *
 * Reusable fixture for creating test users via API or falling back to seeded users.
 * Use with Playwright's request fixture for API-backed creation.
 */

import type { APIRequestContext } from '@playwright/test';
import { E2E_USERS } from './users.fixture';

export type UserRole = 'researcher' | 'steward' | 'admin';

const API_URL = process.env.API_URL || 'http://localhost:3001';

function mapApiRoleToUserRole(apiRole: string): UserRole {
  const upper = (apiRole || '').toUpperCase();
  if (upper === 'ADMIN') return 'admin';
  if (upper === 'STEWARD') return 'steward';
  if (upper === 'RESEARCHER' || upper === 'ANALYST' || upper === 'VIEWER') return 'researcher';
  return 'researcher';
}

function mapUserRoleToE2EKey(role: UserRole): keyof typeof E2E_USERS {
  if (role === 'admin') return 'ADMIN';
  if (role === 'steward') return 'STEWARD';
  return 'ANALYST'; // researcher -> ANALYST
}

export class TestUser {
  readonly id: string;
  readonly email: string;
  readonly role: UserRole;
  readonly token: string;

  private constructor(data: { id: string; email: string; role: UserRole; token: string }) {
    this.id = data.id;
    this.email = data.email;
    this.role = data.role;
    this.token = data.token;
  }

  /**
   * Create a test user via API or use seeded user when request is missing or API fails.
   */
  static async create(role: UserRole, request?: APIRequestContext): Promise<TestUser> {
    const email = `${role}-${Date.now()}@test.com`;

    if (request) {
      try {
        const res = await request.post(`${API_URL}/api/auth/register`, {
          data: {
            email,
            password: 'TestPass1!',
            firstName: role,
            lastName: 'E2E',
          },
        });

        if (res.ok()) {
          const body = await res.json();
          const user = body.user;
          const accessToken = body.accessToken;
          if (user?.id && accessToken) {
            const mappedRole = mapApiRoleToUserRole(user.role);
            return new TestUser({
              id: user.id,
              email: user.email ?? email,
              role: mappedRole,
              token: accessToken,
            });
          }
        }
      } catch {
        // Fall through to seeded user
      }
    }

    // Fallback: use seeded E2E user
    const e2eKey = mapUserRoleToE2EKey(role);
    const seeded = E2E_USERS[e2eKey];
    return new TestUser({
      id: seeded.id,
      email: seeded.email,
      role,
      token: `e2e-test-token-${seeded.id}`,
    });
  }

  /**
   * User cleanup is not implemented (no user-delete API in auth).
   */
  async cleanup(): Promise<void> {
    return Promise.resolve();
  }

  getAuthHeaders(): Record<string, string> {
    return { Authorization: `Bearer ${this.token}` };
  }
}
