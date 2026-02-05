-- Seed service user for worker JWT authentication (audit_logs FK)
-- Satisfies audit_logs.user_id REFERENCES users(id) for automated service calls.
-- JWT sub from tools/dev/generate-worker-service-token.ts: 00000000-0000-4000-8000-000000000001
-- Schema: users (id PK, email UNIQUE); user_roles (id PK only, no UNIQUE(user_id, role)).

-- Stable timestamps so reruns do not mutate the row; DO NOTHING keeps existing row unchanged.
INSERT INTO users (id, email, first_name, last_name, created_at, updated_at)
VALUES (
  '00000000-0000-4000-8000-000000000001',
  'svc-worker@local.dev',
  'Service',
  'Worker',
  '2026-01-01 00:00:00+00',
  '2026-01-01 00:00:00+00'
) ON CONFLICT (id) DO NOTHING;

-- Avoid duplicate ADMIN role: user_roles has no UNIQUE(user_id, role), so use WHERE NOT EXISTS.
INSERT INTO user_roles (id, user_id, role, created_at)
SELECT
  '00000000-0000-4000-8000-000000000002',
  '00000000-0000-4000-8000-000000000001',
  'ADMIN',
  '2026-01-01 00:00:00+00'
WHERE NOT EXISTS (
  SELECT 1 FROM user_roles
  WHERE user_id = '00000000-0000-4000-8000-000000000001' AND role = 'ADMIN'
);
