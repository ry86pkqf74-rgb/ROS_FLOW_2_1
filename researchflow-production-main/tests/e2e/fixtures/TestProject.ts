/**
 * E2E Test Project Fixture
 *
 * Reusable fixture for creating test projects via API.
 * Pass APIRequestContext and auth headers (e.g. from TestUser.getAuthHeaders()) for API-backed creation.
 */

import type { APIRequestContext } from '@playwright/test';

export type GovernanceMode = 'DEMO' | 'LIVE' | 'STANDBY';
export type StudyType = 'rct' | 'cohort' | 'case-control' | 'cross-sectional';

export interface ProjectConfig {
  name: string;
  type: StudyType;
  governanceMode: GovernanceMode;
}

const API_URL = process.env.API_URL || 'http://localhost:3001';

export class TestProject {
  readonly id: string;
  readonly name: string;
  readonly type: StudyType;
  readonly governanceMode: GovernanceMode;

  private _createdViaApi = false;
  private _request: APIRequestContext | null = null;
  private _authHeaders: Record<string, string> = {};

  private constructor(data: {
    id: string;
    name: string;
    type: StudyType;
    governanceMode: GovernanceMode;
    createdViaApi?: boolean;
    request?: APIRequestContext | null;
    authHeaders?: Record<string, string>;
  }) {
    this.id = data.id;
    this.name = data.name;
    this.type = data.type;
    this.governanceMode = data.governanceMode;
    this._createdViaApi = data.createdViaApi ?? false;
    this._request = data.request ?? null;
    this._authHeaders = data.authHeaders ?? {};
  }

  /**
   * Create a test project via API when request (and optionally authHeaders) are provided; otherwise return a stub instance.
   * For API creation, pass request and authHeaders from TestUser.getAuthHeaders() so the project is created as that user.
   */
  static async create(
    userId: string,
    config: ProjectConfig,
    request?: APIRequestContext,
    authHeaders?: Record<string, string>
  ): Promise<TestProject> {
    if (request && authHeaders && Object.keys(authHeaders).length > 0) {
      try {
        const res = await request.post(`${API_URL}/api/projects`, {
          data: {
            name: config.name,
            description: config.type,
          },
          headers: {
            ...authHeaders,
            'Content-Type': 'application/json',
          },
        });

        if (res.ok()) {
          const body = await res.json();
          return new TestProject({
            id: body.id,
            name: body.name ?? config.name,
            type: config.type,
            governanceMode: (body.governanceMode as GovernanceMode) ?? config.governanceMode,
            createdViaApi: true,
            request,
            authHeaders,
          });
        }
      } catch {
        // Fall through to stub
      }
    }

    return new TestProject({
      id: `project-${Date.now()}`,
      name: config.name,
      type: config.type,
      governanceMode: config.governanceMode,
      createdViaApi: false,
    });
  }

  /**
   * Retrieve artifact by type. No single project+type artifact endpoint in scope; implement when API is available.
   */
  async getArtifact(_type: string): Promise<unknown> {
    return Promise.resolve(undefined);
  }

  /**
   * Delete project via API when it was created via API. Backend may use different table (projects vs research_projects); 404 is possible.
   */
  async cleanup(): Promise<void> {
    if (!this._createdViaApi || !this._request || Object.keys(this._authHeaders).length === 0) {
      return;
    }
    try {
      await this._request.delete(
        `${API_URL}/api/projects/${this.id}?permanent=true`,
        { headers: this._authHeaders }
      );
    } catch {
      // Ignore; backend table alignment may be needed
    }
  }
}
