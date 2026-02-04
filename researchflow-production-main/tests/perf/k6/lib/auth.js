/**
 * Authentication helpers for k6 load tests.
 * Supports login, token refresh, and optional AUTH_TOKEN env.
 */

import http from 'k6/http';

/**
 * Login with email and password.
 * @param {string} baseUrl - API base URL (e.g. http://localhost:3001)
 * @param {string} email - User email
 * @param {string} password - User password
 * @returns {{ accessToken?: string, refreshToken?: string, headers: object }} Tokens and headers for Authorization
 */
export function login(baseUrl, email, password) {
  const url = `${baseUrl}/api/auth/login`;
  const payload = JSON.stringify({ email, password });
  const params = { headers: { 'Content-Type': 'application/json' } };
  const res = http.post(url, payload, params);
  if (res.status !== 200) {
    return { headers: {} };
  }
  const body = res.json();
  const accessToken = body.accessToken || null;
  const refreshToken = res.cookies?.refreshToken?.[0]?.value || body.refreshToken || null;
  return {
    accessToken,
    refreshToken,
    headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
  };
}

/**
 * Refresh access token using refresh token (from cookie or body).
 * @param {string} baseUrl - API base URL
 * @param {string} refreshToken - Refresh token
 * @returns {{ accessToken?: string, headers: object }}
 */
export function refresh(baseUrl, refreshToken) {
  if (!refreshToken) return { headers: {} };
  const url = `${baseUrl}/api/auth/refresh`;
  const payload = JSON.stringify({ refreshToken });
  const params = { headers: { 'Content-Type': 'application/json' } };
  const res = http.post(url, payload, params);
  if (res.status !== 200) {
    return { headers: {} };
  }
  const body = res.json();
  const accessToken = body.accessToken || null;
  return {
    accessToken,
    headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
  };
}

/**
 * Get headers for authenticated requests.
 * Uses AUTH_TOKEN env if set; otherwise tries login with LOAD_TEST_EMAIL / LOAD_TEST_PASSWORD.
 * @param {string} baseUrl - API base URL
 * @returns {object} Headers object (possibly empty for public endpoints)
 */
export function getAuthHeaders(baseUrl) {
  const token = __ENV.AUTH_TOKEN;
  if (token) {
    return { Authorization: `Bearer ${token}` };
  }
  const email = __ENV.LOAD_TEST_EMAIL || 'k6-load@test.local';
  const password = __ENV.LOAD_TEST_PASSWORD || 'k6-load-password';
  const result = login(baseUrl, email, password);
  return result.headers;
}
