-- Migration: 020_edit_sessions
-- Phase 3: Human-in-the-loop edit sessions (draft → submit → approve/reject → merge)
-- Each state transition emits a canonical audit ledger event (see edit-session.service).
--
-- Idempotency: Every statement uses IF NOT EXISTS / CREATE OR REPLACE / DROP IF EXISTS
-- so this migration is safe to run repeatedly without error.

CREATE TABLE IF NOT EXISTS edit_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  branch_id UUID NOT NULL REFERENCES manuscript_branches(id) ON DELETE CASCADE,
  manuscript_id UUID NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'draft'
    CHECK (status IN ('draft', 'submitted', 'approved', 'rejected', 'merged')),
  submitted_at TIMESTAMPTZ,
  approved_at TIMESTAMPTZ,
  rejected_at TIMESTAMPTZ,
  merged_at TIMESTAMPTZ,
  created_by UUID,
  submitted_by UUID,
  approved_by UUID,
  rejected_by UUID,
  merged_by UUID,
  rejection_reason TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(branch_id)
);

-- Indices (IF NOT EXISTS for idempotent re-runs)
CREATE INDEX IF NOT EXISTS idx_edit_sessions_manuscript ON edit_sessions(manuscript_id);
CREATE INDEX IF NOT EXISTS idx_edit_sessions_status    ON edit_sessions(status);
CREATE INDEX IF NOT EXISTS idx_edit_sessions_branch    ON edit_sessions(branch_id);

-- Auto-update trigger for updated_at column
-- Function uses CREATE OR REPLACE; trigger uses DROP IF EXISTS + CREATE for safety.
CREATE OR REPLACE FUNCTION update_edit_session_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS edit_session_updated_at ON edit_sessions;
CREATE TRIGGER edit_session_updated_at
  BEFORE UPDATE ON edit_sessions
  FOR EACH ROW
  EXECUTE FUNCTION update_edit_session_updated_at();

COMMENT ON TABLE edit_sessions IS 'HITL edit sessions: draft → submit → approve/reject → merge with audit events';
