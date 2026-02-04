/**
 * Custom k6 metrics for ResearchFlow load tests.
 * Names must match threshold keys in config/thresholds.json.
 */

import { Trend } from 'k6/metrics';

export const aiResponseTime = new Trend('ai_response_time');
export const stageTransitionTime = new Trend('stage_transition_time');
export const manuscriptGenerationTime = new Trend('manuscript_generation_time');

export function recordAiResponse(durationMs) {
  aiResponseTime.add(durationMs);
}

export function recordStageTransition(durationMs) {
  stageTransitionTime.add(durationMs);
}

export function recordManuscriptGeneration(durationMs) {
  manuscriptGenerationTime.add(durationMs);
}
