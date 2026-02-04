/**
 * Traffic spike: 10x normal load (e.g. 10 -> 100 VUs in 30s), sustain, then ramp down.
 * Run with: k6 run scenarios/spike-test.js
 */

import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { getAuthHeaders } from '../lib/auth.js';
import { getStages, completeStage } from '../lib/workflow.js';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:3001';

export const options = {
  stages: [
    { duration: '1m', target: 10 },
    { duration: '30s', target: 100 },
    { duration: '5m', target: 100 },
    { duration: '30s', target: 10 },
    { duration: '1m', target: 0 },
  ],
  thresholds: {
    http_req_duration: ['p(95)<5000'],
    http_req_failed: ['rate<0.01'],
    stage_transition_time: ['p(95)<3000'],
  },
};

export default function () {
  const headers = getAuthHeaders(BASE_URL);

  group('Health + API', function () {
    const health = http.get(`${BASE_URL}/health`);
    check(health, { 'health 200': (r) => r.status === 200 });
    const mode = http.get(`${BASE_URL}/api/ros/mode`);
    check(mode, { 'mode 200': (r) => r.status === 200 });
  });
  sleep(0.3);

  group('Workflow', function () {
    getStages(BASE_URL, headers);
    completeStage(BASE_URL, 1, headers, {});
  });

  sleep(0.5);
}
