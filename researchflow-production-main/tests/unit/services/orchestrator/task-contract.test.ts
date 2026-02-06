/**
 * Unit tests for TaskContract buildAndValidateTaskContract.
 * Ensures request_id, task_type enum, and inputs-per-task-type guardrails.
 */

import { describe, it, expect } from 'vitest';
import {
  buildAndValidateTaskContract,
  TaskContractValidationError,
  ALLOWED_TASK_TYPES,
} from '../../../../services/orchestrator/src/services/task-contract';

describe('task-contract', () => {
  describe('ALLOWED_TASK_TYPES', () => {
    it('includes STAGE_2_LITERATURE_REVIEW, LIT_RETRIEVAL, POLICY_REVIEW', () => {
      expect(ALLOWED_TASK_TYPES).toContain('STAGE_2_LITERATURE_REVIEW');
      expect(ALLOWED_TASK_TYPES).toContain('LIT_RETRIEVAL');
      expect(ALLOWED_TASK_TYPES).toContain('POLICY_REVIEW');
    });
  });

  describe('buildAndValidateTaskContract', () => {
    describe('request_id', () => {
      it('throws MISSING_REQUEST_ID when request_id is missing', () => {
        expect(() =>
          buildAndValidateTaskContract({
            task_type: 'LIT_RETRIEVAL',
            inputs: { query: 'test' },
          })
        ).toThrow(TaskContractValidationError);
        try {
          buildAndValidateTaskContract({
            task_type: 'LIT_RETRIEVAL',
            inputs: { query: 'test' },
          });
        } catch (e) {
          expect((e as TaskContractValidationError).code).toBe('MISSING_REQUEST_ID');
        }
      });

      it('throws MISSING_REQUEST_ID when request_id is empty string', () => {
        expect(() =>
          buildAndValidateTaskContract({
            request_id: '',
            task_type: 'LIT_RETRIEVAL',
            inputs: { query: 'test' },
          })
        ).toThrow(TaskContractValidationError);
      });

      it('accepts non-empty request_id', () => {
        const out = buildAndValidateTaskContract({
          request_id: 'req-1',
          task_type: 'POLICY_REVIEW',
          inputs: {},
        });
        expect(out.request_id).toBe('req-1');
      });
    });

    describe('task_type', () => {
      it('throws INVALID_TASK_TYPE for unknown task type', () => {
        expect(() =>
          buildAndValidateTaskContract({
            request_id: 'r',
            task_type: 'UNKNOWN_TASK',
            inputs: {},
          })
        ).toThrow(TaskContractValidationError);
        try {
          buildAndValidateTaskContract({
            request_id: 'r',
            task_type: 'UNKNOWN_TASK',
            inputs: {},
          });
        } catch (e) {
          expect((e as TaskContractValidationError).code).toBe('INVALID_TASK_TYPE');
        }
      });

      it('accepts each allowed task type', () => {
        for (const taskType of ALLOWED_TASK_TYPES) {
          const inputs: Record<string, unknown> =
            taskType === 'LIT_RETRIEVAL'
              ? { query: 'q' }
              : taskType === 'STAGE_2_LITERATURE_REVIEW'
                ? { research_question: 'rq' }
                : {};
          const out = buildAndValidateTaskContract({
            request_id: 'r',
            task_type: taskType,
            inputs,
          });
          expect(out.task_type).toBe(taskType);
        }
      });
    });

    describe('inputs per task type', () => {
      it('LIT_RETRIEVAL requires inputs.query', () => {
        expect(() =>
          buildAndValidateTaskContract({
            request_id: 'r',
            task_type: 'LIT_RETRIEVAL',
            inputs: {},
          })
        ).toThrow(TaskContractValidationError);
        try {
          buildAndValidateTaskContract({
            request_id: 'r',
            task_type: 'LIT_RETRIEVAL',
            inputs: {},
          });
        } catch (e) {
          expect((e as TaskContractValidationError).code).toBe('INVALID_INPUTS');
        }
      });

      it('LIT_RETRIEVAL rejects empty query string', () => {
        expect(() =>
          buildAndValidateTaskContract({
            request_id: 'r',
            task_type: 'LIT_RETRIEVAL',
            inputs: { query: '   ' },
          })
        ).toThrow(TaskContractValidationError);
      });

      it('LIT_RETRIEVAL accepts non-empty query', () => {
        const out = buildAndValidateTaskContract({
          request_id: 'r',
          task_type: 'LIT_RETRIEVAL',
          inputs: { query: 'statins meta-analysis', max_results: 10 },
        });
        expect(out.inputs.query).toBe('statins meta-analysis');
        expect(out.inputs.max_results).toBe(10);
      });

      it('STAGE_2_LITERATURE_REVIEW requires inputs.research_question', () => {
        expect(() =>
          buildAndValidateTaskContract({
            request_id: 'r',
            task_type: 'STAGE_2_LITERATURE_REVIEW',
            inputs: {},
          })
        ).toThrow(TaskContractValidationError);
      });

      it('STAGE_2_LITERATURE_REVIEW accepts research_question', () => {
        const out = buildAndValidateTaskContract({
          request_id: 'r',
          task_type: 'STAGE_2_LITERATURE_REVIEW',
          inputs: { research_question: 'Does X improve Y?' },
        });
        expect(out.inputs.research_question).toBe('Does X improve Y?');
      });

      it('POLICY_REVIEW accepts empty inputs', () => {
        const out = buildAndValidateTaskContract({
          request_id: 'r',
          task_type: 'POLICY_REVIEW',
          inputs: {},
        });
        expect(out.inputs).toEqual({});
      });

      it('normalizes missing inputs to {}', () => {
        const out = buildAndValidateTaskContract({
          request_id: 'r',
          task_type: 'POLICY_REVIEW',
          inputs: undefined as unknown as Record<string, unknown>,
        });
        expect(out.inputs).toEqual({});
      });
    });

    describe('output shape', () => {
      it('sets mode to DEMO when not LIVE', () => {
        const out = buildAndValidateTaskContract({
          request_id: 'r',
          task_type: 'POLICY_REVIEW',
          inputs: {},
          mode: 'DEMO',
        });
        expect(out.mode).toBe('DEMO');
      });

      it('sets mode to LIVE when provided', () => {
        const out = buildAndValidateTaskContract({
          request_id: 'r',
          task_type: 'POLICY_REVIEW',
          inputs: {},
          mode: 'LIVE',
        });
        expect(out.mode).toBe('LIVE');
      });

      it('defaults risk_tier and domain_id', () => {
        const out = buildAndValidateTaskContract({
          request_id: 'r',
          task_type: 'POLICY_REVIEW',
          inputs: {},
        });
        expect(out.risk_tier).toBe('NON_SENSITIVE');
        expect(out.domain_id).toBe('clinical');
      });
    });
  });
});
