/**
 * Soak test: extended duration (1 hour) with moderate load.
 * Run with: k6 run scenarios/soak-test.js --config config/soak-load.json
 * Or: k6 run --vus 10 --duration 60m scenarios/soak-test.js
 */

import { check, sleep, group } from 'k6';
import http from 'k6/http';

import { getAuthHeaders } from '../lib/auth.js';
import { getStages, completeStage } from '../lib/workflow.js';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:3001';

export const options = {
  vus: 10,
  duration: '60m',
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
  });
  sleep(5);

  group('Workflow', function () {
    getStages(BASE_URL, headers);
    completeStage(BASE_URL, 1, headers, {});
  });

  sleep(5);
}
