import { request, expect } from "@playwright/test";

export const E2E_USER_ID =
  "e2e-test-user-00000000-0000-0000-0000-000000000001";

export async function devLoginAndGetToken(baseURL: string) {
  const ctx = await request.newContext({
    baseURL,
    extraHTTPHeaders: {
      "X-Dev-User-Id": E2E_USER_ID,
    },
  });

  const resp = await ctx.post("/api/dev-auth/login");
  expect(resp.ok()).toBeTruthy();
  const json = await resp.json();

  const accessToken = json.accessToken as string;
  expect(typeof accessToken).toBe("string");
  expect(accessToken.length).toBeGreaterThan(20);

  return accessToken;
}

export function modeStore(aiEnabled: boolean) {
  return { state: { aiEnabled }, version: 0 };
}
