# E2E Test Specification (Auth + Workflow)

> Scope: End-to-end verification of landing, authentication wiring (token mismatch + refresh), protected route gating, workflow creation, 21-stage navigation, document generation, and DOCX export.
>
> Base URL (local): `http://localhost:3000`
>
> Token storage: `localStorage["access_token"]`
>
> Auth header: `Authorization: Bearer <token>`

## Conventions

- **Test runner**: Cypress or Playwright (spec is framework-agnostic).
- **API verification**: Verify network calls via route interception (e.g., `page.route` / `cy.intercept`) and assert:
  - method + path
  - request headers (esp. `Authorization`)
  - status codes
  - response body shape (minimal required fields)
- **Selectors**: Prefer stable `data-testid` attributes. If missing, add them during implementation.
- **Test data**:
  - Use a dedicated test user in dev/staging.
  - Use seeded backend data where possible.
  - Ensure cleanup (delete created workflows) if environment persists.

### Environments

- **Local**: `BASE_URL=http://localhost:3000`
- **API base**: same origin unless otherwise configured.

### Common Preconditions

Unless overridden in a case:

- App is running and reachable at `http://localhost:3000`.
- Backend API is running and reachable.
- Test user credentials are available as environment secrets:
  - `E2E_EMAIL`
  - `E2E_PASSWORD`

### Common API Calls

- Login: `POST /api/auth/login`
- Refresh: `POST /api/auth/refresh`

---

## Test Cases

### E2E-001 — Landing page loads at `/`

- **Description**: Verify the public landing page renders and is interactive.
- **Preconditions**:
  - Browser storage cleared.
- **Steps**:
  1. Navigate to `/`.
  2. Assert HTTP 200 and no console errors.
  3. Verify primary UI elements exist (e.g., app header/logo, primary CTA, login link/button).
- **Expected Result**:
  - Landing page is visible and usable.
  - No redirect loops.
- **API calls to verify**:
  - None required (or assert *no* auth-gated calls happen on initial landing load).

---

### E2E-002 — Login form submission flow

- **Description**: Submitting valid credentials logs the user in.
- **Preconditions**:
  - Browser storage cleared.
  - Test credentials available.
- **Steps**:
  1. Navigate to the login page (via landing CTA or direct route if known).
  2. Fill email with `E2E_EMAIL`.
  3. Fill password with `E2E_PASSWORD`.
  4. Submit the form.
  5. Wait for login request to complete.
- **Expected Result**:
  - Login request succeeds.
  - UI transitions to authenticated state (redirect to dashboard or authenticated shell).
  - Access token is persisted (validated in E2E-003).
- **API calls to verify**:
  - `POST /api/auth/login`
    - Request payload includes submitted credentials (or equivalent).
    - Response is `200` (or `201`) and includes an access token (name may vary; storage key is `access_token`).

---

### E2E-003 — Token storage verification (`localStorage["access_token"]`)

- **Description**: After successful login, token is stored under the exact key `access_token`.
- **Preconditions**:
  - Complete E2E-002 successfully.
- **Steps**:
  1. Read `localStorage.getItem("access_token")`.
  2. Assert it is non-empty.
  3. Assert it matches expected token format (e.g., JWT: `xxx.yyy.zzz`) if applicable.
- **Expected Result**:
  - Token exists and is usable.
- **API calls to verify**:
  - None (storage-only check), or:
  - Perform a lightweight authenticated API call and assert `Authorization` header present (covered in E2E-005/E2E-006).

---

### E2E-004 — Dashboard redirect after login

- **Description**: Successful login redirects user to `/dashboard` (or equivalent) and loads authenticated content.
- **Preconditions**:
  - Browser storage cleared.
- **Steps**:
  1. Complete E2E-002.
  2. Assert the current URL path is `/dashboard`.
  3. Assert dashboard UI elements render (e.g., welcome header, workflows list, “New workflow” button).
- **Expected Result**:
  - User lands on dashboard without manual navigation.
- **API calls to verify**:
  - `POST /api/auth/login` (as in E2E-002)
  - Any dashboard bootstrap calls (if applicable):
    - Assert `Authorization: Bearer <token>` header is included.

---

### E2E-005 — Protected route access **without token**

- **Description**: Accessing protected routes without a token is blocked.
- **Preconditions**:
  - Clear storage/cookies.
  - Ensure `localStorage["access_token"]` is absent.
- **Steps**:
  1. Navigate to `/dashboard`.
  2. Navigate to `/documents`.
  3. Navigate to `/workflow/[id]` using a placeholder or known workflow id route (see notes).
- **Expected Result**:
  - User is redirected to login (or sees an auth-required screen) for all protected routes.
  - No protected data is shown.
- **API calls to verify**:
  - Assert **no** successful protected API responses occur while unauthenticated.
  - If the app calls refresh unauthenticated, verify:
    - `POST /api/auth/refresh` returns `401/403` and triggers logout flow.

**Notes**:
- For `/workflow/[id]`, use a known existing workflow ID if required; otherwise validate route guard logic by direct navigation to a non-existent but correctly-shaped URL and assert redirect to login occurs before fetching.

---

### E2E-006 — Protected route access **with token**

- **Description**: With a valid token, protected routes load successfully.
- **Preconditions**:
  - Complete E2E-002 and E2E-003 (token present).
- **Steps**:
  1. Navigate to `/dashboard`.
  2. Navigate to `/documents`.
  3. Open an existing workflow via dashboard, or create one (E2E-007) and navigate to `/workflow/[id]`.
- **Expected Result**:
  - Pages render protected content.
  - No redirect to login.
- **API calls to verify**:
  - For any protected API request triggered by these pages:
    - Request includes `Authorization: Bearer <token>`.
    - Response status is `200`.

---

### E2E-007 — Workflow creation flow

- **Description**: User can create a new workflow from the dashboard.
- **Preconditions**:
  - Authenticated session (token present).
- **Steps**:
  1. Navigate to `/dashboard`.
  2. Click “New workflow” (or equivalent CTA).
  3. Fill required fields (title/topic/etc.).
  4. Submit creation.
  5. Capture created workflow ID from the URL or API response.
- **Expected Result**:
  - Workflow is created.
  - User is redirected to `/workflow/[id]`.
- **API calls to verify**:
  - Workflow create endpoint (discover and assert):
    - Method + URL matches expected app behavior.
    - Includes `Authorization` header.
    - Response contains workflow `id`.

---

### E2E-008 — Stage navigation across all 21 stages (Stage00 … Stage20)

- **Description**: Each stage route renders the correct stage component and navigation works for all stages.
- **Preconditions**:
  - Authenticated.
  - A workflow exists (use the ID from E2E-007).
- **Steps**:
  1. For each `stage` in `0..20`:
     1. Navigate to `/workflow/[id]?stage=<stage>`.
     2. Assert the page renders a stage header/indicator showing current stage number.
     3. Assert the correct component is mounted (Stage00 for 0 … Stage20 for 20).
     4. If UI has next/prev controls, click next and verify it increments stage; click prev and verify it decrements stage.
  2. Verify stage boundaries:
     - From stage 0, prev is disabled or stays at 0.
     - From stage 20, next is disabled or stays at 20.
- **Expected Result**:
  - All 21 stage routes load without error.
  - Stage component mapping is correct.
  - Navigation works and does not break the workflow context.
- **API calls to verify**:
  - Any per-stage data fetches:
    - Must include `Authorization: Bearer <token>`.
    - Responses are `200`.
  - If token refresh happens during the loop:
    - `POST /api/auth/refresh` returns `200` and the app continues successfully.

#### Stage / Phase Matrix

| Stage | Component | Phase |
|------:|-----------|-------|
| 0 | Stage00 | SETUP |
| 1 | Stage01 | SETUP |
| 2 | Stage02 | SETUP |
| 3 | Stage03 | SETUP |
| 4 | Stage04 | SETUP |
| 5 | Stage05 | SETUP |
| 6 | Stage06 | ANALYSIS |
| 7 | Stage07 | ANALYSIS |
| 8 | Stage08 | ANALYSIS |
| 9 | Stage09 | ANALYSIS |
| 10 | Stage10 | ANALYSIS |
| 11 | Stage11 | ANALYSIS |
| 12 | Stage12 | WRITING |
| 13 | Stage13 | WRITING |
| 14 | Stage14 | WRITING |
| 15 | Stage15 | WRITING |
| 16 | Stage16 | PUBLISH |
| 17 | Stage17 | PUBLISH |
| 18 | Stage18 | PUBLISH |
| 19 | Stage19 | PUBLISH |
| 20 | Stage20 | PUBLISH |

---

### E2E-009 — Document generation trigger

- **Description**: User can trigger document generation from the workflow UI.
- **Preconditions**:
  - Authenticated.
  - Workflow exists.
- **Steps**:
  1. Navigate to `/workflow/[id]` (optionally a stage where generation is available).
  2. Click “Generate Document” (or equivalent).
  3. Wait for generation request(s) to complete.
  4. Assert UI indicates success (toast, status badge, generated preview link, etc.).
- **Expected Result**:
  - Generation is triggered and completes successfully.
  - Result becomes available for export.
- **API calls to verify**:
  - Generation endpoint(s) (discover and assert):
    - Includes `Authorization: Bearer <token>`.
    - Response status `200/202`.
    - If asynchronous, verify polling/status endpoint is called until “ready”.
  - If any auth refresh occurs mid-flight:
    - `POST /api/auth/refresh` succeeds and the original action continues.

---

### E2E-010 — DOCX export download

- **Description**: User can export a workflow document as DOCX and a file download is initiated.
- **Preconditions**:
  - Authenticated.
  - Workflow exists.
  - Document generation completed (E2E-009).
- **Steps**:
  1. Navigate to `/workflow/[id]` or `/documents` where export is available.
  2. Click “Export DOCX” (or equivalent).
  3. Intercept the export request.
  4. Validate response headers/content.
  5. Validate file is downloaded (framework-specific):
     - Playwright: use `page.waitForEvent('download')` and assert filename.
     - Cypress: use download task / intercept + blob validation.
- **Expected Result**:
  - Export request succeeds.
  - Download is triggered and produces a `.docx` file.
- **API calls to verify**:
  - `POST /api/workflows/:id/export`
    - Includes `Authorization: Bearer <token>`.
    - Status `200`.
    - Response `Content-Type` resembles DOCX:
      - `application/vnd.openxmlformats-officedocument.wordprocessingml.document`
    - Response includes appropriate `Content-Disposition` with `.docx` filename (if implemented).

---

## Auth Token Mismatch / Refresh Scenarios (Focused Regression Add-ons)

> These are key for verifying the current Cursor changes (token mismatch + login wiring).

### E2E-011 — Expired access token triggers refresh and retries

- **Description**: If an access token is expired, the app calls refresh and then retries the original request successfully.
- **Preconditions**:
  - Authenticated.
  - Ability to simulate expiry (one of):
    - seed a short-lived token in test env
    - manually set an invalid/expired token string in `localStorage`
- **Steps**:
  1. Set `localStorage["access_token"]` to an expired token value.
  2. Navigate to a protected route that makes an API request.
  3. Observe the first request fails `401`.
  4. Observe refresh call.
  5. Observe the original request is retried.
- **Expected Result**:
  - Refresh flow occurs once.
  - User remains logged in.
  - Retried request succeeds and content renders.
- **API calls to verify**:
  - Protected request returns `401` initially.
  - `POST /api/auth/refresh` returns `200`.
  - Retried protected request returns `200` and has updated `Authorization` header.

---

### E2E-012 — Refresh failure logs out and redirects to login

- **Description**: If refresh fails, user is logged out and redirected.
- **Preconditions**:
  - Authenticated OR token present but refresh is forced to fail.
- **Steps**:
  1. Force `POST /api/auth/refresh` to return `401/403` (test env stub or invalid refresh token scenario).
  2. Navigate to a protected route.
  3. Observe redirect to login.
  4. Assert token is cleared from `localStorage`.
- **Expected Result**:
  - User is logged out and cannot access protected routes.
- **API calls to verify**:
  - `POST /api/auth/refresh` returns `401/403`.
  - No further protected calls succeed afterward.

---

## Implementation Notes / Checklist

- Add `data-testid` for:
  - login email input, password input, submit button
  - dashboard shell
  - new workflow CTA
  - stage indicator, next/prev controls
  - generate document button
  - export DOCX button
- Ensure export endpoint returns correct `Content-Type` and sets `Content-Disposition` filename.
- Ensure all protected API calls include `Authorization: Bearer <token>`.
