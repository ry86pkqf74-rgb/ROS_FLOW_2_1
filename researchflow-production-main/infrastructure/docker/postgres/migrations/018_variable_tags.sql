-- Variable tagging with collaborative voting
CREATE TABLE IF NOT EXISTS variable_tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    variable_name VARCHAR(255) NOT NULL,
    tag_type VARCHAR(50) NOT NULL CHECK (tag_type IN ('outcome', 'predictor', 'covariate', 'confounder', 'instrument', 'exclude')),
    suggested_by UUID REFERENCES users(id),
    confidence FLOAT DEFAULT 0.5,
    rationale TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(project_id, variable_name)
);

CREATE TABLE IF NOT EXISTS variable_tag_votes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tag_id UUID NOT NULL REFERENCES variable_tags(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id),
    vote SMALLINT NOT NULL CHECK (vote IN (-1, 1)),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tag_id, user_id)
);

CREATE INDEX idx_variable_tags_project ON variable_tags(project_id);
CREATE INDEX idx_variable_tag_votes_tag ON variable_tag_votes(tag_id);
