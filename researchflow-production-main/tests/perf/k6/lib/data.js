/**
 * Test data generators for k6 load tests.
 * Deterministic per VU/iteration for repeatable scenarios.
 */

/**
 * Generate a unique project name for this VU/iteration.
 */
export function projectName() {
  return `k6-load-${__VU}-${__ITER}`;
}

/**
 * Generate a unique dataset ID (string) for this VU/iteration.
 */
export function datasetId() {
  return `ds-${__VU}-${__ITER}-${Date.now()}`;
}

/**
 * Generate a unique user email for load test users.
 */
export function userEmail() {
  return `k6-load-${__VU}-${__ITER}@test.local`;
}

/**
 * Minimal payload for create-project (if API exists).
 */
export function createProjectPayload() {
  return {
    name: projectName(),
    description: 'k6 load test project',
  };
}

/**
 * Minimal payload for create-manuscript (if API exists).
 */
export function createManuscriptPayload(projectId) {
  return {
    title: `k6 manuscript ${__VU}-${__ITER}`,
    projectId: projectId || `proj-${__VU}-${__ITER}`,
  };
}

/**
 * Minimal payload for AI research-brief / evidence-gap-map.
 */
export function aiResearchBriefPayload() {
  return {
    projectId: `proj-${__VU}-${__ITER}`,
    query: 'k6 load test research brief',
  };
}

/**
 * Minimal payload for manuscript generate/results.
 */
export function manuscriptGeneratePayload() {
  return {
    manuscriptId: `ms-${__VU}-${__ITER}`,
    datasetId: datasetId(),
    analysisResults: { summary: 'k6 load test' },
  };
}
