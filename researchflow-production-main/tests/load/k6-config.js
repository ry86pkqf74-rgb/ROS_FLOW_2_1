import { check, sleep } from 'k6';
import http from 'k6/http';
import ws from 'k6/ws';

// Base URL for the API (override in CI with BASE_URL secret/var)
const BASE_URL = __ENV.BASE_URL || 'http://localhost:3000';
// Optional WebSocket URL override; defaults to BASE_URL with ws(s) scheme.
const WS_URL = __ENV.WS_URL || BASE_URL.replace(/^http/, 'ws');

export const options = {
  scenarios: {
    load_100_users: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '2m', target: 100 }, // ramp-up
        { duration: '5m', target: 100 }, // sustained
        { duration: '1m', target: 0 },   // ramp-down
      ],
      gracefulRampDown: '30s',
    },
  },
  thresholds: {
    http_req_duration: ['p(95)<500'],
    http_req_failed: ['rate<0.01'],
  },
};

function jsonHeaders() {
  const headers = { 'Content-Type': 'application/json' };
  if (__ENV.AUTH_TOKEN) headers.Authorization = `Bearer ${__ENV.AUTH_TOKEN}`;
  return headers;
}

export default function () {
  // Healthcheck (works even if auth is required for the rest)
  const health = http.get(`${BASE_URL}/health`);
  check(health, { 'health status is 200': (r) => r.status === 200 });

  // Workflow creation (if endpoint exists)
  // Override path via WORKFLOW_CREATE_PATH if your API differs.
  const createPath = __ENV.WORKFLOW_CREATE_PATH || '/api/workflows';
  const createRes = http.post(
    `${BASE_URL}${createPath}`,
    JSON.stringify({
      name: `k6-load-${__VU}-${__ITER}`,
      description: 'k6 load test workflow',
      // keep payload minimal; adjust to your API contract via env var or editing this file
    }),
    { headers: jsonHeaders(), tags: { name: 'workflow_create' } },
  );

  // Stage execution (if endpoint exists)
  // Override via STAGE_EXEC_PATH; may include templating by your API.
  const stageExecPath = __ENV.STAGE_EXEC_PATH || '/api/stages/execute';
  const execRes = http.post(
    `${BASE_URL}${stageExecPath}`,
    JSON.stringify({
      workflowId: __ENV.WORKFLOW_ID || null,
      stageId: __ENV.STAGE_ID || null,
      // If your API requires IDs, pass WORKFLOW_ID/STAGE_ID env vars in CI.
    }),
    { headers: jsonHeaders(), tags: { name: 'stage_execute' } },
  );

  check(createRes, {
    'workflow create not 5xx': (r) => r.status < 500,
  });
  check(execRes, {
    'stage execute not 5xx': (r) => r.status < 500,
  });

  // Basic WebSocket connect (optional)
  // Override path via WS_PATH.
  const wsPath = __ENV.WS_PATH || '/ws';
  ws.connect(`${WS_URL}${wsPath}`, { headers: __ENV.AUTH_TOKEN ? { Authorization: `Bearer ${__ENV.AUTH_TOKEN}` } : {} }, function (socket) {
    socket.on('open', function () {
      socket.send(JSON.stringify({ type: 'ping', ts: Date.now() }));
    });

    socket.on('message', function () {
      // no-op: receiving any message is fine
    });

    socket.on('close', function () {
      // closed
    });

    // keep connection briefly to simulate clients
    socket.setTimeout(function () {
      socket.close();
    }, 1000);
  });

  sleep(1);
}
