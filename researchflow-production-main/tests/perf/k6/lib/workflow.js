/**
 * Workflow step helpers for k6 load tests.
 * GET stages, POST stage complete, POST lifecycle transition.
 * Records stage_transition_time for custom metric.
 */

import http from 'k6/http';
import { recordStageTransition } from './metrics.js';

/**
 * Get all workflow stages.
 * @param {string} baseUrl - API base URL
 * @param {object} headers - Auth headers (from auth.getAuthHeaders)
 * @returns {object|null} Response JSON or null on failure
 */
export function getStages(baseUrl, headers = {}) {
  const url = `${baseUrl}/api/workflow/stages`;
  const res = http.get(url, { headers });
  if (res.status !== 200) return null;
  try {
    return res.json();
  } catch {
    return null;
  }
}

/**
 * Complete a workflow stage and record transition time.
 * @param {string} baseUrl - API base URL
 * @param {number} stageId - Stage ID (1-20)
 * @param {object} headers - Auth headers
 * @param {object} [metadata] - Optional metadata for completion
 * @returns {boolean} True if request succeeded
 */
export function completeStage(baseUrl, stageId, headers = {}, metadata = {}) {
  const url = `${baseUrl}/api/workflow/stages/${stageId}/complete`;
  const payload = JSON.stringify({ metadata });
  const params = {
    headers: { 'Content-Type': 'application/json', ...headers },
  };
  const start = Date.now();
  const res = http.post(url, payload, params);
  const duration = Date.now() - start;
  recordStageTransition(duration);
  return res.status === 200;
}

/**
 * Transition lifecycle state.
 * @param {string} baseUrl - API base URL
 * @param {object} body - { newState: string, details?: object }
 * @param {object} headers - Auth headers
 * @returns {boolean} True if request succeeded
 */
export function transitionLifecycle(baseUrl, body, headers = {}) {
  const url = `${baseUrl}/api/workflow/lifecycle/transition`;
  const payload = JSON.stringify(body);
  const params = {
    headers: { 'Content-Type': 'application/json', ...headers },
  };
  const start = Date.now();
  const res = http.post(url, payload, params);
  const duration = Date.now() - start;
  recordStageTransition(duration);
  return res.status === 200;
}

/**
 * Get current lifecycle state.
 * @param {string} baseUrl - API base URL
 * @param {object} headers - Auth headers
 * @returns {object|null} Response JSON or null
 */
export function getLifecycle(baseUrl, headers = {}) {
  const url = `${baseUrl}/api/workflow/lifecycle`;
  const res = http.get(url, { headers });
  if (res.status !== 200) return null;
  try {
    return res.json();
  } catch {
    return null;
  }
}
