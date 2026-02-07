/**
 * TaskContract — single place to build and validate payloads for AI router/agent dispatch.
 * Prevents empty/missing inputs regressions (e.g. LIT_RETRIEVAL without query).
 */

/** Allowed task types for agent dispatch (single source of truth). */
export const ALLOWED_TASK_TYPES = [
  'STAGE_2_LITERATURE_REVIEW',
  'STAGE_2_EXTRACT',
  'STAGE2_SYNTHESIZE',
  'LIT_RETRIEVAL',
  'POLICY_REVIEW',
] as const;

export type AllowedTaskType = (typeof ALLOWED_TASK_TYPES)[number];

export interface TaskContract {
  request_id: string;
  task_type: string;
  workflow_id?: string;
  user_id?: string;
  mode: 'LIVE' | 'DEMO';
  risk_tier?: string;
  domain_id?: string;
  inputs: Record<string, unknown>;
  budgets?: Record<string, unknown>;
}

export class TaskContractValidationError extends Error {
  constructor(
    message: string,
    public readonly code: 'MISSING_REQUEST_ID' | 'INVALID_TASK_TYPE' | 'INVALID_INPUTS'
  ) {
    super(message);
    this.name = 'TaskContractValidationError';
  }
}

/** Input requirements per task type (minimal guardrails). */
const INPUT_REQUIREMENTS: Record<AllowedTaskType, { required: string[]; optional?: string[] }> = {
  STAGE_2_LITERATURE_REVIEW: { required: ['research_question'] },
  STAGE_2_EXTRACT: { required: [] }, // agent returns error if no groundingPack or abstracts
  STAGE2_SYNTHESIZE: { required: ['papers'], optional: ['research_question', 'synthesisType', 'citations'] },
  LIT_RETRIEVAL: { required: ['query'] },
  POLICY_REVIEW: { required: [] }, // stub accepts empty; we still normalize to object
};

function isAllowedTaskType(s: string): s is AllowedTaskType {
  return ALLOWED_TASK_TYPES.includes(s as AllowedTaskType);
}

/**
 * Validates and normalizes a raw dispatch payload into a TaskContract.
 * - request_id must be present and non-empty
 * - task_type must be one of ALLOWED_TASK_TYPES
 * - inputs must conform to task type (e.g. LIT_RETRIEVAL requires inputs.query)
 * - inputs is always an object (never undefined) to avoid {} regressions
 *
 * @throws TaskContractValidationError if validation fails
 */
export function buildAndValidateTaskContract(raw: {
  request_id?: string | null;
  task_type: string;
  workflow_id?: string | null;
  user_id?: string | null;
  mode?: string | null;
  risk_tier?: string | null;
  domain_id?: string | null;
  inputs?: Record<string, unknown> | null;
  budgets?: Record<string, unknown> | null;
}): TaskContract {
  const requestId = raw.request_id?.trim();
  if (!requestId) {
    throw new TaskContractValidationError('request_id is required and must be non-empty', 'MISSING_REQUEST_ID');
  }

  if (!isAllowedTaskType(raw.task_type)) {
    throw new TaskContractValidationError(
      `task_type must be one of: ${ALLOWED_TASK_TYPES.join(', ')}`,
      'INVALID_TASK_TYPE'
    );
  }

  const taskType = raw.task_type as AllowedTaskType;
  const inputs = raw.inputs && typeof raw.inputs === 'object' && !Array.isArray(raw.inputs)
    ? { ...raw.inputs }
    : {};

  const req = INPUT_REQUIREMENTS[taskType];
  for (const key of req.required) {
    const val = inputs[key];
    if (val === undefined || val === null || (typeof val === 'string' && !val.trim())) {
      throw new TaskContractValidationError(
        `Task type "${taskType}" requires inputs.${key} to be present and non-empty`,
        'INVALID_INPUTS'
      );
    }
  }

  return {
    request_id: requestId,
    task_type: raw.task_type,
    workflow_id: raw.workflow_id ?? undefined,
    user_id: raw.user_id ?? undefined,
    mode: raw.mode === 'LIVE' ? 'LIVE' : 'DEMO',
    risk_tier: raw.risk_tier ?? 'NON_SENSITIVE',
    domain_id: raw.domain_id ?? 'clinical',
    inputs,
    budgets: raw.budgets && typeof raw.budgets === 'object' ? raw.budgets : undefined,
  };
}
