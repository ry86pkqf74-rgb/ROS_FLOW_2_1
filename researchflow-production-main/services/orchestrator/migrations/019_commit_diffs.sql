-- Migration: 019_commit_diffs
-- Add optional stored-diff fields to manuscript_branch_commits for diff_strategy=stored.
-- PHI-min and HIPAA-safe: diff_summary_json holds section-level metadata only (no raw manuscript text).
-- Immutability trigger is unchanged; no new indexes (avoid over-indexing).

-- diff_unified: full unified diff when stored. TEXT chosen for simplicity; BYTEA could be used later
-- for compression if size becomes an issue (e.g. gzip in app layer and store as BYTEA).
ALTER TABLE manuscript_branch_commits
  ADD COLUMN IF NOT EXISTS diff_unified TEXT NULL;

ALTER TABLE manuscript_branch_commits
  ADD COLUMN IF NOT EXISTS diff_summary_json JSONB NULL;

-- diff_strategy: how the diff was produced (computed on read vs stored at commit time).
ALTER TABLE manuscript_branch_commits
  ADD COLUMN IF NOT EXISTS diff_strategy TEXT NULL;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'manuscript_branch_commits_diff_strategy_check'
  ) THEN
    ALTER TABLE manuscript_branch_commits
      ADD CONSTRAINT manuscript_branch_commits_diff_strategy_check
      CHECK (diff_strategy IS NULL OR diff_strategy IN ('computed', 'stored'));
  END IF;
END $$;

COMMENT ON COLUMN manuscript_branch_commits.diff_unified IS 'Optional stored unified diff; used when diff_strategy=stored.';
COMMENT ON COLUMN manuscript_branch_commits.diff_summary_json IS 'Section-level diff summary only; no raw manuscript text (PHI-safe).';
COMMENT ON COLUMN manuscript_branch_commits.diff_strategy IS 'How diff was produced: computed (on read) or stored (at commit).';
