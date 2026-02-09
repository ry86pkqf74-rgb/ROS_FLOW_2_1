-- Migration: 018_manuscript_branch_commits
-- Phase 2: Tracked changes — append-only commit log per branch
--
-- Design:
-- - One row per commit on a manuscript branch (hash, message, parent, optional revision link).
-- - Immutable: no UPDATE or DELETE allowed (trigger enforced).
-- - Unique (branch_id, commit_hash) to prevent duplicate commits per branch.

CREATE TABLE IF NOT EXISTS manuscript_branch_commits (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  branch_id UUID NOT NULL REFERENCES manuscript_branches(id) ON DELETE CASCADE,
  commit_hash VARCHAR(64) NOT NULL,
  parent_commit_id UUID REFERENCES manuscript_branch_commits(id) ON DELETE SET NULL,
  commit_message TEXT,
  revision_id UUID REFERENCES manuscript_revisions(id) ON DELETE SET NULL,
  content_hash VARCHAR(64),
  created_by UUID,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT manuscript_branch_commits_unique_branch_hash UNIQUE (branch_id, commit_hash)
);

-- Indexes for common access patterns
CREATE INDEX IF NOT EXISTS idx_branch_commits_branch_id ON manuscript_branch_commits(branch_id);
CREATE INDEX IF NOT EXISTS idx_branch_commits_created_at ON manuscript_branch_commits(branch_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_branch_commits_parent ON manuscript_branch_commits(parent_commit_id) WHERE parent_commit_id IS NOT NULL;

-- Immutability: forbid UPDATE and DELETE
CREATE OR REPLACE FUNCTION manuscript_branch_commits_immutable()
RETURNS TRIGGER AS $$
BEGIN
  IF TG_OP = 'UPDATE' THEN
    RAISE EXCEPTION 'manuscript_branch_commits is append-only: UPDATE not allowed';
  ELSIF TG_OP = 'DELETE' THEN
    RAISE EXCEPTION 'manuscript_branch_commits is append-only: DELETE not allowed';
  END IF;
  RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS manuscript_branch_commits_immutable_trigger ON manuscript_branch_commits;
CREATE TRIGGER manuscript_branch_commits_immutable_trigger
  BEFORE UPDATE OR DELETE ON manuscript_branch_commits
  FOR EACH ROW
  EXECUTE FUNCTION manuscript_branch_commits_immutable();

COMMENT ON TABLE manuscript_branch_commits IS 'Append-only commit log per manuscript branch; immutable.';
COMMENT ON COLUMN manuscript_branch_commits.commit_hash IS 'Content or logical hash identifying this commit (unique per branch).';
COMMENT ON COLUMN manuscript_branch_commits.parent_commit_id IS 'Previous commit in the same branch (chain).';
COMMENT ON COLUMN manuscript_branch_commits.revision_id IS 'Optional link to manuscript_revisions row.';
