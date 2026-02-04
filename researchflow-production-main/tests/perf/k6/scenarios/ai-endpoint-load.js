/**
 * AI/LLM endpoints under load (higher latency tolerance).
 * Run with: k6 run scenarios/ai-endpoint-load.js --config config/ai-focused.json
 */

import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { getAuthHeaders } from '../lib/auth.js';
import { recordAiResponse, recordManuscriptGeneration } from '../lib/metrics.js';
import { aiResearchBriefPayload, manuscriptGeneratePayload } from '../lib/data.js';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:3001';

export const options = {
  httpReqTimeout: '60s',
  thresholds: {
    http_req_duration: ['p(95)<5000'],
    http_req_failed: ['rate<0.01'],
    ai_response_time: ['p(95)<30000'],
    manuscript_generation_time: ['p(95)<60000'],
  },
};

export default function () {
  const headers = {
    'Content-Type': 'application/json',
    ...getAuthHeaders(BASE_URL),
  };

  group('AI providers', function () {
    const start = Date.now();
    const res = http.get(`${BASE_URL}/api/ai/providers`, { headers });
    recordAiResponse(Date.now() - start);
    check(res, { 'ai providers 2xx': (r) => r.status >= 200 && r.status < 300 });
  });
  sleep(0.5);

  group('AI research-brief', function () {
    const payload = JSON.stringify(aiResearchBriefPayload());
    const start = Date.now();
    const res = http.post(`${BASE_URL}/api/ai/research-brief`, payload, { headers });
    recordAiResponse(Date.now() - start);
    check(res, { 'research-brief not 5xx': (r) => r.status < 500 });
  });
  sleep(1);

  group('Manuscript generate', function () {
    const payload = JSON.stringify(manuscriptGeneratePayload());
    const start = Date.now();
    const res = http.post(`${BASE_URL}/api/manuscript/generate/results`, payload, { headers });
    const duration = Date.now() - start;
    recordAiResponse(duration);
    recordManuscriptGeneration(duration);
    check(res, { 'manuscript generate not 5xx': (r) => r.status < 500 });
  });

  sleep(2);
}
