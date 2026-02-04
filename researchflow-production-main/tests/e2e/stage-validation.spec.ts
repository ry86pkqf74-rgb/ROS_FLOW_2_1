import { test, expect } from '@playwright/test';

test.describe('Stage Registration Validation', () => {
  const stages = Array.from({ length: 20 }, (_, i) => i + 1);

  for (const stageNum of stages) {
    test(`stage ${stageNum.toString().padStart(2, '0')} is registered`, async ({ request }) => {
      const response = await request.get(
        `http://localhost:8000/api/workflow/stages/${stageNum}/status`
      );
      expect(response.ok()).toBeTruthy();
      const body = await response.json();
      expect(body.registered).toBe(true);
    });
  }
});

test.describe('Stage Dependency Chain', () => {
  test('stage 07 requires real data in LIVE mode', async ({ request }) => {
    const response = await request.get('http://localhost:8000/health');
    const body = await response.json();

    if (body.governance_mode === 'LIVE') {
      const stage7Response = await request.post(
        'http://localhost:8000/api/workflow/execute',
        {
          data: {
            job_id: 'e2e-stage7-validation',
            stage_ids: [7],
            governance_mode: 'LIVE',
            config: { use_mock: true },
          },
        }
      );
      expect(stage7Response.status()).toBe(400);
    }
  });
});
