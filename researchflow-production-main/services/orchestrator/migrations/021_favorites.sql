-- Orchestrator migration: favorites table
-- Mirrors infrastructure/docker/postgres/migrations/005_favorites.sql

CREATE TABLE IF NOT EXISTS favorites (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL,
  resource_type VARCHAR(20) NOT NULL,
  resource_id VARCHAR(255) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT favorites_resource_type_check CHECK (resource_type IN ('project','workflow','artifact','paper')),
  CONSTRAINT favorites_unique_user_resource UNIQUE (user_id, resource_type, resource_id)
);

CREATE INDEX IF NOT EXISTS idx_favorites_user ON favorites(user_id);
