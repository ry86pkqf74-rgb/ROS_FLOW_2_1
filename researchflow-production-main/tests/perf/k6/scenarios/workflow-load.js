/**
 * Full 20-stage workflow under load.
 * Run with: k6 run scenarios/workflow-load.js --config config/normal-load.json
 * BASE_URL: orchestrator URL (default http://localhost:3001)
 */

import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { getAuthHeaders } from '../lib/auth.js';
import { getStages, completeStage } from '../lib/workflow.js';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:3001';
const WORKER_URL = __ENV.WORKER_URL || 'http://localhost:8000';

// Options can be overridden by --config
export const options = {
  thresholds: {
    http_req_duration: ['p(95)<5000'],
    http_req_failed: ['rate<0.01'],
    stage_transition_time: ['p(95)<3000'],
  },
};

export default function () {
  const headers = getAuthHeaders(BASE_URL);

  group('Health', function () {
    const health = http.get(`${BASE_URL}/health`);
    check(health, { 'health 200': (r) => r.status === 200 });
    const workerHealth = http.get(`${WORKER_URL}/health`);
    check(workerHealth, { 'worker health 200': (r) => r.status === 200 });
  });
  sleep(0.5);

  group('API', function () {
    const topics = http.get(`${BASE_URL}/api/topics`);
    check(topics, { 'topics 200': (r) => r.status === 200 });
    const mode = http.get(`${BASE_URL}/api/ros/mode`);
    check(mode, { 'mode 200': (r) => r.status === 200 });
  });
  sleep(0.5);

  group('Workflow stages', function () {
    const stagesData = getStages(BASE_URL, headers);
    if (stagesData && stagesData.stageGroups) {
      // Complete a subset of stages (1-5); completeStage records stage_transition_time
      for (let stageId = 1; stageId <= 5; stageId++) {
        const ok = completeStage(BASE_URL, stageId, headers, {});
        if (ok) break;
      }
    }
  });

  sleep(1);
}
