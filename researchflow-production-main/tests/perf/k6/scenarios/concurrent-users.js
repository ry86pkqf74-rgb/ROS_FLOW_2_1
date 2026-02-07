/**
 * Multi-user collaboration: each VU logs in, hits projects + workflow/stages + stage complete, optional WS.
 * Run with: k6 run scenarios/concurrent-users.js --vus 20 --duration 5m
 */

import { check, sleep, group } from 'k6';
import http from 'k6/http';
import ws from 'k6/ws';

import { login, getAuthHeaders } from '../lib/auth.js';
import { userEmail } from '../lib/data.js';
import { getStages, completeStage } from '../lib/workflow.js';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:3001';
const WS_URL = __ENV.WS_URL || BASE_URL.replace(/^http/, 'ws');

export const options = {
  thresholds: {
    http_req_duration: ['p(95)<5000'],
    http_req_failed: ['rate<0.01'],
    stage_transition_time: ['p(95)<3000'],
  },
};

function jsonHeaders(h) {
  return { 'Content-Type': 'application/json', ...h };
}

export default function () {
  let headers = getAuthHeaders(BASE_URL);
  if (Object.keys(headers).length === 0) {
    const result = login(BASE_URL, userEmail(), __ENV.LOAD_TEST_PASSWORD || 'k6-load-password');
    headers = result.headers;
  }

  group('Projects / workflow', function () {
    const projects = http.get(`${BASE_URL}/api/projects`, { headers });
    check(projects, { 'projects not 5xx': (r) => r.status < 500 });

    const stagesData = getStages(BASE_URL, headers);
    check(stagesData !== null, { 'stages loaded': (v) => v });

    completeStage(BASE_URL, 1, headers, {});
  });
  sleep(0.5);

  group('WebSocket', function () {
    const wsPath = __ENV.WS_PATH || '/ws';
    ws.connect(
      `${WS_URL}${wsPath}`,
      { headers: headers.Authorization ? { Authorization: headers.Authorization } : {} },
      function (socket) {
        socket.on('open', function () {
          socket.send(JSON.stringify({ type: 'ping', ts: Date.now() }));
        });
        socket.on('message', function () {});
        socket.setTimeout(function () {
          socket.close();
        }, 1000);
      }
    );
  });

  sleep(1);
}
