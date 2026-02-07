import crypto from 'crypto';

import * as z from 'zod';

/**
 * Docker Registry Service Integration
 * Provides Docker Hub API access for image management, vulnerability scanning,
 * and deployment automation
 */

// Configuration schema
export const DockerRegistryConfigSchema = z.object({
  username: z.string().min(1),
  accessToken: z.string().min(1),
  registry: z.string().default('https://hub.docker.com'),
  namespace: z.string().optional(),
});

export type DockerRegistryConfig = z.infer<typeof DockerRegistryConfigSchema>;

// Docker Hub API endpoints
const DOCKER_HUB_API = 'https://hub.docker.com/v2';
const DOCKER_REGISTRY_API = 'https://registry-1.docker.io/v2';

/**
 * Authenticate with Docker Hub and get JWT token
 */
async function getDockerHubToken(
  config: DockerRegistryConfig
): Promise<{ token?: string; error?: string }> {
  try {
    const response = await fetch(`${DOCKER_HUB_API}/users/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        username: config.username,
        password: config.accessToken,
      }),
    });

    if (!response.ok) {
      const error = await response.text();
      return { error: `Docker Hub auth failed: ${response.status} ${error}` };
    }

    const data = await response.json();
    return { token: data.token };
  } catch (error) {
    return {
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

/**
 * Execute Docker Hub API request with authentication
 */
async function dockerHubApiRequest<T>(
  config: DockerRegistryConfig,
  endpoint: string,
  options?: RequestInit & { requiresAuth?: boolean }
): Promise<{ data?: T; error?: string }> {
  try {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...options?.headers,
    };

    // Get token if authentication is required
    if (options?.requiresAuth !== false) {
      const authResult = await getDockerHubToken(config);
      if (authResult.error) {
        return { error: authResult.error };
      }
      if (authResult.token) {
        headers['Authorization'] = `Bearer ${authResult.token}`;
      }
    }

    const response = await fetch(`${DOCKER_HUB_API}${endpoint}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const errorText = await response.text();
      return {
        error: `Docker Hub API error: ${response.status} ${errorText}`,
      };
    }

    const data = await response.json();
    return { data };
  } catch (error) {
    console.error('Docker Hub API request failed:', error);
    return {
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

/**
 * List repositories in namespace
 */
export async function listDockerRepositories(
  config: DockerRegistryConfig,
  params?: {
    page?: number;
    pageSize?: number;
  }
): Promise<{
  success: boolean;
  repositories?: Array<{
    name: string;
    namespace: string;
    description?: string;
    isPrivate: boolean;
    pullCount: number;
    starCount: number;
    lastUpdated: string;
  }>;
  error?: string;
}> {
  const namespace = config.namespace || config.username;
  const page = params?.page || 1;
  const pageSize = params?.pageSize || 25;

  const result = await dockerHubApiRequest<{
    count: number;
    results: Array<{
      name: string;
      namespace: string;
      description?: string;
      is_private: boolean;
      pull_count: number;
      star_count: number;
      last_updated: string;
    }>;
  }>(
    config,
    `/repositories/${namespace}/?page=${page}&page_size=${pageSize}`,
    { requiresAuth: true }
  );

  return {
    success: !result.error,
    repositories: result.data?.results.map((repo) => ({
      name: repo.name,
      namespace: repo.namespace,
      description: repo.description,
      isPrivate: repo.is_private,
      pullCount: repo.pull_count,
      starCount: repo.star_count,
      lastUpdated: repo.last_updated,
    })),
    error: result.error,
  };
}

/**
 * Get repository details
 */
export async function getDockerRepository(
  config: DockerRegistryConfig,
  repositoryName: string
): Promise<{
  success: boolean;
  repository?: {
    name: string;
    namespace: string;
    description?: string;
    isPrivate: boolean;
    pullCount: number;
    starCount: number;
    lastUpdated: string;
    affiliation?: string;
  };
  error?: string;
}> {
  const namespace = config.namespace || config.username;

  const result = await dockerHubApiRequest<{
    name: string;
    namespace: string;
    description?: string;
    is_private: boolean;
    pull_count: number;
    star_count: number;
    last_updated: string;
    affiliation?: string;
  }>(config, `/repositories/${namespace}/${repositoryName}`, {
    requiresAuth: true,
  });

  return {
    success: !result.error,
    repository: result.data
      ? {
          name: result.data.name,
          namespace: result.data.namespace,
          description: result.data.description,
          isPrivate: result.data.is_private,
          pullCount: result.data.pull_count,
          starCount: result.data.star_count,
          lastUpdated: result.data.last_updated,
          affiliation: result.data.affiliation,
        }
      : undefined,
    error: result.error,
  };
}

/**
 * List image tags for a repository
 */
export async function listDockerImageTags(
  config: DockerRegistryConfig,
  repositoryName: string,
  params?: {
    page?: number;
    pageSize?: number;
  }
): Promise<{
  success: boolean;
  tags?: Array<{
    name: string;
    fullSize: number;
    lastUpdated: string;
    digest: string;
    images: Array<{
      architecture: string;
      os: string;
      size: number;
    }>;
  }>;
  error?: string;
}> {
  const namespace = config.namespace || config.username;
  const page = params?.page || 1;
  const pageSize = params?.pageSize || 25;

  const result = await dockerHubApiRequest<{
    count: number;
    results: Array<{
      name: string;
      full_size: number;
      last_updated: string;
      digest: string;
      images: Array<{
        architecture: string;
        os: string;
        size: number;
      }>;
    }>;
  }>(
    config,
    `/repositories/${namespace}/${repositoryName}/tags?page=${page}&page_size=${pageSize}`,
    { requiresAuth: true }
  );

  return {
    success: !result.error,
    tags: result.data?.results.map((tag) => ({
      name: tag.name,
      fullSize: tag.full_size,
      lastUpdated: tag.last_updated,
      digest: tag.digest,
      images: tag.images,
    })),
    error: result.error,
  };
}

/**
 * Get manifest for a specific image tag
 */
export async function getDockerImageManifest(
  config: DockerRegistryConfig,
  repositoryName: string,
  tag: string
): Promise<{
  success: boolean;
  manifest?: {
    schemaVersion: number;
    mediaType: string;
    config: {
      digest: string;
      size: number;
    };
    layers: Array<{
      digest: string;
      size: number;
    }>;
  };
  error?: string;
}> {
  const namespace = config.namespace || config.username;

  // Get registry token for manifest access
  const tokenResponse = await fetch(
    `https://auth.docker.io/token?service=registry.docker.io&scope=repository:${namespace}/${repositoryName}:pull`
  );

  if (!tokenResponse.ok) {
    return { success: false, error: 'Failed to get registry token' };
  }

  const tokenData = await tokenResponse.json();
  const registryToken = tokenData.token;

  try {
    const response = await fetch(
      `${DOCKER_REGISTRY_API}/${namespace}/${repositoryName}/manifests/${tag}`,
      {
        headers: {
          Authorization: `Bearer ${registryToken}`,
          Accept:
            'application/vnd.docker.distribution.manifest.v2+json, application/vnd.oci.image.manifest.v1+json',
        },
      }
    );

    if (!response.ok) {
      return {
        success: false,
        error: `Failed to get manifest: ${response.status}`,
      };
    }

    const manifest = await response.json();
    return {
      success: true,
      manifest: {
        schemaVersion: manifest.schemaVersion,
        mediaType: manifest.mediaType,
        config: manifest.config,
        layers: manifest.layers,
      },
    };
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

/**
 * Create or update repository webhook
 */
export async function createDockerRepositoryWebhook(
  config: DockerRegistryConfig,
  repositoryName: string,
  webhookUrl: string
): Promise<{
  success: boolean;
  webhookId?: string;
  error?: string;
}> {
  const namespace = config.namespace || config.username;

  const result = await dockerHubApiRequest<{
    id: string;
    name: string;
    webhook_url: string;
  }>(config, `/repositories/${namespace}/${repositoryName}/webhooks/`, {
    method: 'POST',
    requiresAuth: true,
    body: JSON.stringify({
      name: 'ROS Deployment Webhook',
      webhook_url: webhookUrl,
    }),
  });

  return {
    success: !result.error,
    webhookId: result.data?.id,
    error: result.error,
  };
}

/**
 * Docker webhook payload interface
 */
export interface DockerWebhookPayload {
  callback_url: string;
  push_data: {
    images: string[];
    pushed_at: number;
    pusher: string;
    tag: string;
  };
  repository: {
    comment_count: number;
    date_created: number;
    description: string;
    dockerfile?: string;
    full_description?: string;
    is_official: boolean;
    is_private: boolean;
    is_trusted: boolean;
    name: string;
    namespace: string;
    owner: string;
    repo_name: string;
    repo_url: string;
    star_count: number;
    status: string;
  };
}

/**
 * Verify Docker webhook callback URL
 */
export async function verifyDockerWebhook(
  callbackUrl: string
): Promise<{ success: boolean; error?: string }> {
  try {
    const response = await fetch(callbackUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        state: 'success',
        description: 'Webhook verified',
        context: 'researchflow/deployment',
      }),
    });

    return {
      success: response.ok,
      error: response.ok ? undefined : `Verification failed: ${response.status}`,
    };
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

/**
 * Interface with Docker Engine API (for local daemon control)
 */
export class DockerEngineClient {
  private socketPath: string;

  constructor(socketPath: string = '/var/run/docker.sock') {
    this.socketPath = socketPath;
  }

  /**
   * List running containers
   */
  async listContainers(
    all: boolean = false
  ): Promise<{
    success: boolean;
    containers?: Array<{
      Id: string;
      Names: string[];
      Image: string;
      State: string;
      Status: string;
      Created: number;
    }>;
    error?: string;
  }> {
    try {
      const response = await fetch(
        `http://unix:${this.socketPath}:/containers/json?all=${all}`,
        {
          method: 'GET',
        }
      );

      if (!response.ok) {
        return {
          success: false,
          error: `Docker Engine API error: ${response.status}`,
        };
      }

      const containers = await response.json();
      return { success: true, containers };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  }

  /**
   * Get container stats (CPU, memory, network)
   */
  async getContainerStats(
    containerId: string
  ): Promise<{
    success: boolean;
    stats?: {
      cpu_percent: number;
      memory_usage: number;
      memory_limit: number;
      memory_percent: number;
      network_rx: number;
      network_tx: number;
    };
    error?: string;
  }> {
    try {
      const response = await fetch(
        `http://unix:${this.socketPath}:/containers/${containerId}/stats?stream=false`,
        {
          method: 'GET',
        }
      );

      if (!response.ok) {
        return {
          success: false,
          error: `Docker Engine API error: ${response.status}`,
        };
      }

      const rawStats = await response.json();

      // Calculate CPU percentage
      const cpuDelta =
        rawStats.cpu_stats.cpu_usage.total_usage -
        rawStats.precpu_stats.cpu_usage.total_usage;
      const systemDelta =
        rawStats.cpu_stats.system_cpu_usage -
        rawStats.precpu_stats.system_cpu_usage;
      const cpuPercent =
        (cpuDelta / systemDelta) *
        rawStats.cpu_stats.online_cpus *
        100;

      // Memory stats
      const memoryUsage = rawStats.memory_stats.usage;
      const memoryLimit = rawStats.memory_stats.limit;
      const memoryPercent = (memoryUsage / memoryLimit) * 100;

      // Network stats
      let networkRx = 0;
      let networkTx = 0;
      if (rawStats.networks) {
        Object.values(rawStats.networks).forEach((net: any) => {
          networkRx += net.rx_bytes;
          networkTx += net.tx_bytes;
        });
      }

      return {
        success: true,
        stats: {
          cpu_percent: cpuPercent,
          memory_usage: memoryUsage,
          memory_limit: memoryLimit,
          memory_percent: memoryPercent,
          network_rx: networkRx,
          network_tx: networkTx,
        },
      };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  }

  /**
   * Restart container
   */
  async restartContainer(
    containerId: string,
    timeout: number = 10
  ): Promise<{ success: boolean; error?: string }> {
    try {
      const response = await fetch(
        `http://unix:${this.socketPath}:/containers/${containerId}/restart?t=${timeout}`,
        {
          method: 'POST',
        }
      );

      return {
        success: response.ok,
        error: response.ok ? undefined : `Restart failed: ${response.status}`,
      };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  }
}
