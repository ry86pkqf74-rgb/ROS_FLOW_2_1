import crypto from 'crypto';

import * as z from 'zod';

/**
 * Figma Service Integration
 * Provides design file access, component extraction, and AI-driven design review
 * via Figma's REST API
 */

// Configuration schema
export const FigmaConfigSchema = z.object({
  accessToken: z.string().min(1),
  webhookSecret: z.string().optional(),
  teamId: z.string().optional(),
});

export type FigmaConfig = z.infer<typeof FigmaConfigSchema>;

// Figma API endpoint
const FIGMA_API_URL = 'https://api.figma.com/v1';

// Webhook event types
export interface FigmaWebhookPayload {
  event_type:
    | 'FILE_UPDATE'
    | 'FILE_VERSION_UPDATE'
    | 'FILE_COMMENT'
    | 'LIBRARY_PUBLISH';
  passcode: string;
  timestamp: string;
  file_key: string;
  file_name: string;
  webhook_id: string;
  triggered_by?: {
    id: string;
    handle: string;
  };
  description?: string;
}

/**
 * Verify Figma webhook passcode
 * Figma uses a simple passcode verification
 */
export function verifyFigmaWebhookPasscode(
  payload: FigmaWebhookPayload,
  expectedPasscode: string
): boolean {
  return payload.passcode === expectedPasscode;
}

/**
 * Execute request against Figma API
 */
async function figmaApiRequest<T>(
  config: FigmaConfig,
  endpoint: string,
  options?: RequestInit
): Promise<{ data?: T; error?: string; status?: number }> {
  try {
    const response = await fetch(`${FIGMA_API_URL}${endpoint}`, {
      ...options,
      headers: {
        'X-Figma-Token': config.accessToken,
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      return {
        error: `Figma API error: ${response.status} ${errorText}`,
        status: response.status,
      };
    }

    const data = await response.json();
    return { data, status: response.status };
  } catch (error) {
    console.error('Figma API request failed:', error);
    return {
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

/**
 * Get file metadata and structure
 */
export async function getFigmaFile(
  config: FigmaConfig,
  fileKey: string,
  options?: {
    version?: string;
    ids?: string[];
    depth?: number;
    geometry?: 'paths' | 'relative';
  }
): Promise<{
  success: boolean;
  file?: {
    name: string;
    lastModified: string;
    thumbnailUrl?: string;
    version: string;
    document: any;
    components?: Record<string, any>;
    styles?: Record<string, any>;
  };
  error?: string;
}> {
  const params = new URLSearchParams();
  if (options?.version) params.append('version', options.version);
  if (options?.ids) params.append('ids', options.ids.join(','));
  if (options?.depth) params.append('depth', options.depth.toString());
  if (options?.geometry) params.append('geometry', options.geometry);

  const queryString = params.toString();
  const endpoint = `/files/${fileKey}${queryString ? `?${queryString}` : ''}`;

  const result = await figmaApiRequest<{
    name: string;
    lastModified: string;
    thumbnailUrl?: string;
    version: string;
    document: any;
    components?: Record<string, any>;
    styles?: Record<string, any>;
  }>(config, endpoint);

  return {
    success: !result.error,
    file: result.data,
    error: result.error,
  };
}

/**
 * Get file images (renders)
 */
export async function getFigmaFileImages(
  config: FigmaConfig,
  fileKey: string,
  params: {
    ids: string[];
    scale?: number;
    format?: 'jpg' | 'png' | 'svg' | 'pdf';
    svgIncludeId?: boolean;
    svgSimplifyStroke?: boolean;
    useAbsoluteBounds?: boolean;
  }
): Promise<{
  success: boolean;
  images?: Record<string, string>;
  error?: string;
}> {
  const queryParams = new URLSearchParams();
  queryParams.append('ids', params.ids.join(','));
  if (params.scale) queryParams.append('scale', params.scale.toString());
  if (params.format) queryParams.append('format', params.format);
  if (params.svgIncludeId !== undefined)
    queryParams.append('svg_include_id', params.svgIncludeId.toString());
  if (params.svgSimplifyStroke !== undefined)
    queryParams.append('svg_simplify_stroke', params.svgSimplifyStroke.toString());
  if (params.useAbsoluteBounds !== undefined)
    queryParams.append('use_absolute_bounds', params.useAbsoluteBounds.toString());

  const result = await figmaApiRequest<{
    err?: string;
    images: Record<string, string>;
  }>(config, `/images/${fileKey}?${queryParams.toString()}`);

  return {
    success: !result.error && !result.data?.err,
    images: result.data?.images,
    error: result.error || result.data?.err,
  };
}

/**
 * Get comments from a file
 */
export async function getFigmaComments(
  config: FigmaConfig,
  fileKey: string
): Promise<{
  success: boolean;
  comments?: Array<{
    id: string;
    file_key: string;
    parent_id?: string;
    user: {
      id: string;
      handle: string;
      img_url?: string;
    };
    created_at: string;
    resolved_at?: string;
    message: string;
    client_meta?: {
      x?: number;
      y?: number;
      node_id?: string;
    };
    order_id?: string;
  }>;
  error?: string;
}> {
  const result = await figmaApiRequest<{
    comments: Array<{
      id: string;
      file_key: string;
      parent_id?: string;
      user: {
        id: string;
        handle: string;
        img_url?: string;
      };
      created_at: string;
      resolved_at?: string;
      message: string;
      client_meta?: {
        x?: number;
        y?: number;
        node_id?: string;
      };
      order_id?: string;
    }>;
  }>(config, `/files/${fileKey}/comments`);

  return {
    success: !result.error,
    comments: result.data?.comments,
    error: result.error,
  };
}

/**
 * Post a comment to a file
 */
export async function postFigmaComment(
  config: FigmaConfig,
  fileKey: string,
  params: {
    message: string;
    client_meta?: {
      x?: number;
      y?: number;
      node_id?: string;
      node_offset?: { x: number; y: number };
    };
    comment_id?: string;
  }
): Promise<{
  success: boolean;
  comment?: {
    id: string;
    file_key: string;
    parent_id?: string;
    user: {
      id: string;
      handle: string;
    };
    created_at: string;
    message: string;
  };
  error?: string;
}> {
  const result = await figmaApiRequest<{
    id: string;
    file_key: string;
    parent_id?: string;
    user: {
      id: string;
      handle: string;
    };
    created_at: string;
    message: string;
  }>(config, `/files/${fileKey}/comments`, {
    method: 'POST',
    body: JSON.stringify(params),
  });

  return {
    success: !result.error,
    comment: result.data,
    error: result.error,
  };
}

/**
 * Get team projects
 */
export async function getFigmaTeamProjects(
  config: FigmaConfig,
  teamId: string
): Promise<{
  success: boolean;
  projects?: Array<{
    id: string;
    name: string;
  }>;
  error?: string;
}> {
  const result = await figmaApiRequest<{
    projects: Array<{
      id: string;
      name: string;
    }>;
  }>(config, `/teams/${teamId}/projects`);

  return {
    success: !result.error,
    projects: result.data?.projects,
    error: result.error,
  };
}

/**
 * Get project files
 */
export async function getFigmaProjectFiles(
  config: FigmaConfig,
  projectId: string
): Promise<{
  success: boolean;
  files?: Array<{
    key: string;
    name: string;
    thumbnail_url?: string;
    last_modified: string;
  }>;
  error?: string;
}> {
  const result = await figmaApiRequest<{
    files: Array<{
      key: string;
      name: string;
      thumbnail_url?: string;
      last_modified: string;
    }>;
  }>(config, `/projects/${projectId}/files`);

  return {
    success: !result.error,
    files: result.data?.files,
    error: result.error,
  };
}

/**
 * Get component metadata
 */
export async function getFigmaComponent(
  config: FigmaConfig,
  componentKey: string
): Promise<{
  success: boolean;
  component?: {
    key: string;
    name: string;
    description: string;
    containing_frame?: {
      name: string;
      nodeId: string;
      pageId: string;
      pageName: string;
    };
    created_at: string;
    updated_at: string;
    user: {
      id: string;
      handle: string;
      img_url?: string;
    };
  };
  error?: string;
}> {
  const result = await figmaApiRequest<{
    meta: {
      key: string;
      name: string;
      description: string;
      containing_frame?: {
        name: string;
        nodeId: string;
        pageId: string;
        pageName: string;
      };
      created_at: string;
      updated_at: string;
      user: {
        id: string;
        handle: string;
        img_url?: string;
      };
    };
  }>(config, `/components/${componentKey}`);

  return {
    success: !result.error,
    component: result.data?.meta,
    error: result.error,
  };
}

/**
 * Get file component sets (for design system components)
 */
export async function getFigmaFileComponentSets(
  config: FigmaConfig,
  fileKey: string
): Promise<{
  success: boolean;
  componentSets?: Record<
    string,
    {
      key: string;
      name: string;
      description: string;
    }
  >;
  error?: string;
}> {
  const result = await getFigmaFile(config, fileKey);

  if (!result.success || !result.file) {
    return {
      success: false,
      error: result.error,
    };
  }

  // Extract component sets from the document
  const componentSets: Record<
    string,
    { key: string; name: string; description: string }
  > = {};

  function traverseNode(node: any) {
    if (node.type === 'COMPONENT_SET') {
      componentSets[node.id] = {
        key: node.id,
        name: node.name,
        description: node.description || '',
      };
    }
    if (node.children) {
      node.children.forEach(traverseNode);
    }
  }

  traverseNode(result.file.document);

  return {
    success: true,
    componentSets,
  };
}

/**
 * Extract design tokens from a Figma file (colors, typography, spacing)
 */
export async function extractDesignTokens(
  config: FigmaConfig,
  fileKey: string
): Promise<{
  success: boolean;
  tokens?: {
    colors: Record<string, string>;
    typography: Record<
      string,
      {
        fontFamily: string;
        fontSize: number;
        fontWeight: number;
        lineHeight: number;
        letterSpacing: number;
      }
    >;
    spacing: Record<string, number>;
  };
  error?: string;
}> {
  const result = await getFigmaFile(config, fileKey);

  if (!result.success || !result.file) {
    return {
      success: false,
      error: result.error,
    };
  }

  const tokens = {
    colors: {} as Record<string, string>,
    typography: {} as Record<
      string,
      {
        fontFamily: string;
        fontSize: number;
        fontWeight: number;
        lineHeight: number;
        letterSpacing: number;
      }
    >,
    spacing: {} as Record<string, number>,
  };

  // Extract styles if available
  if (result.file.styles) {
    Object.entries(result.file.styles).forEach(([key, style]: [string, any]) => {
      if (style.styleType === 'FILL') {
        tokens.colors[style.name] = rgbaToHex(style.fills?.[0]?.color);
      } else if (style.styleType === 'TEXT') {
        tokens.typography[style.name] = {
          fontFamily: style.fontFamily,
          fontSize: style.fontSize,
          fontWeight: style.fontWeight,
          lineHeight: style.lineHeight?.value || style.fontSize * 1.2,
          letterSpacing: style.letterSpacing?.value || 0,
        };
      }
    });
  }

  return {
    success: true,
    tokens,
  };
}

/**
 * Helper: Convert RGBA color to hex
 */
function rgbaToHex(color?: { r: number; g: number; b: number; a: number }): string {
  if (!color) return '#000000';

  const r = Math.round(color.r * 255);
  const g = Math.round(color.g * 255);
  const b = Math.round(color.b * 255);

  return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b
    .toString(16)
    .padStart(2, '0')}`;
}

/**
 * AI-driven design review: Post automated feedback as comments
 */
export async function postAIDesignReview(
  config: FigmaConfig,
  fileKey: string,
  params: {
    nodeId: string;
    feedback: string;
    position?: { x: number; y: number };
    agentName?: string;
  }
): Promise<{ success: boolean; commentId?: string; error?: string }> {
  const message = params.agentName
    ? `🤖 **AI Agent: ${params.agentName}**\n\n${params.feedback}`
    : `🤖 **AI Design Review**\n\n${params.feedback}`;

  const result = await postFigmaComment(config, fileKey, {
    message,
    client_meta: {
      node_id: params.nodeId,
      x: params.position?.x,
      y: params.position?.y,
    },
  });

  return {
    success: result.success,
    commentId: result.comment?.id,
    error: result.error,
  };
}
