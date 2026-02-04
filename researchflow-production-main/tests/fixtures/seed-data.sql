-- Seed data for isolated test environment (synthetic, no PHI)
-- Assumes a Postgres DB reachable as configured in docker-compose.test.yml

BEGIN;

-- Create extension for UUIDs if used by the app
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Generic tables used by tests if application migrations have not created them yet.
-- These are minimal and only created when missing to avoid conflicts.

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'test_users'
  ) THEN
    CREATE TABLE public.test_users (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
      email text UNIQUE NOT NULL,
      role text NOT NULL,
      created_at timestamptz NOT NULL DEFAULT now()
    );
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'test_projects'
  ) THEN
    CREATE TABLE public.test_projects (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
      code text UNIQUE NOT NULL,
      name text NOT NULL,
      governance_mode text NOT NULL CHECK (governance_mode IN ('DEMO','LIVE','STANDBY')),
      created_at timestamptz NOT NULL DEFAULT now()
    );
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'test_workflow_states'
  ) THEN
    CREATE TABLE public.test_workflow_states (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
      project_code text NOT NULL,
      stage int NOT NULL,
      state text NOT NULL,
      updated_at timestamptz NOT NULL DEFAULT now()
    );
    CREATE INDEX IF NOT EXISTS idx_test_workflow_states_project_stage
      ON public.test_workflow_states(project_code, stage);
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'test_datasets'
  ) THEN
    CREATE TABLE public.test_datasets (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
      project_code text NOT NULL,
      dataset_key text NOT NULL,
      description text NOT NULL,
      rows_count int NOT NULL DEFAULT 0,
      has_phi boolean NOT NULL DEFAULT false,
      created_at timestamptz NOT NULL DEFAULT now(),
      UNIQUE(project_code, dataset_key)
    );
  END IF;
END $$;

-- Users
INSERT INTO public.test_users (email, role)
VALUES
  ('researcher@test.com', 'researcher'),
  ('steward@test.com', 'steward'),
  ('admin@test.com', 'admin')
ON CONFLICT (email) DO UPDATE SET role = EXCLUDED.role;

-- Projects
INSERT INTO public.test_projects (code, name, governance_mode)
VALUES
  ('DEMO-001', 'Demo Project', 'DEMO'),
  ('LIVE-001', 'Live Project', 'LIVE'),
  ('STANDBY-001', 'Standby Project', 'STANDBY')
ON CONFLICT (code) DO UPDATE SET
  name = EXCLUDED.name,
  governance_mode = EXCLUDED.governance_mode;

-- Workflow states for stages 1, 5, 10, 20
INSERT INTO public.test_workflow_states (project_code, stage, state)
VALUES
  ('DEMO-001', 1,  'queued'),
  ('DEMO-001', 5,  'running'),
  ('DEMO-001', 10, 'review'),
  ('DEMO-001', 20, 'complete'),

  ('LIVE-001', 1,  'queued'),
  ('LIVE-001', 5,  'running'),
  ('LIVE-001', 10, 'review'),
  ('LIVE-001', 20, 'complete'),

  ('STANDBY-001', 1,  'queued'),
  ('STANDBY-001', 5,  'paused'),
  ('STANDBY-001', 10, 'awaiting_approval'),
  ('STANDBY-001', 20, 'standby')
ON CONFLICT DO NOTHING;

-- Synthetic datasets (no PHI)
INSERT INTO public.test_datasets (project_code, dataset_key, description, rows_count, has_phi)
VALUES
  ('DEMO-001', 'synthetic-patients-v1', 'Synthetic patient-like records (randomized; no identifiers)', 500, false),
  ('DEMO-001', 'synthetic-labs-v1',     'Synthetic lab values correlated to synthetic patients', 2000, false),
  ('LIVE-001', 'synthetic-claims-v1',   'Synthetic claims-like events (no PHI)', 10000, false),
  ('STANDBY-001', 'synthetic-notes-v1', 'Synthetic free-text notes (generated; no PHI)', 250, false)
ON CONFLICT (project_code, dataset_key) DO UPDATE SET
  description = EXCLUDED.description,
  rows_count = EXCLUDED.rows_count,
  has_phi = EXCLUDED.has_phi;

COMMIT;
