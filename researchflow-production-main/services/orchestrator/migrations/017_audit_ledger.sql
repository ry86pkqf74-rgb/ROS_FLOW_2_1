-- Orchestrator migration: tamper-evident audit ledger (append-only)
--
-- Design notes:
-- - Each "stream" is an independent, append-only event log (e.g., GLOBAL, RUN, MANUSCRIPT).
-- - Events are ordered by (stream_id, seq) and chained by hashes:
--     prev_event_hash -> event_hash of the previous event in the same stream.
-- - The application is responsible for computing hashes (no triggers in this migration).
--
-- Hash strategy (recommended):
-- - payload_hash: SHA-256 over a canonical serialization of payload_json.
-- - event_hash: SHA-256 over a canonical concatenation of stable fields, including payload_hash and prev_event_hash,
--   e.g. sha256(stream_id || '|' || seq || '|' || created_at || '|' || actor_type || '|' || service || '|' ||
--               action || '|' || resource_type || '|' || resource_id || '|' || before_hash || '|' || after_hash || '|' ||
--               payload_hash || '|' || prev_event_hash).
-- - Canonicalization rules must be consistent (UTF-8, explicit null handling) so hashes are reproducible.

BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS audit_event_streams (
  stream_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  stream_type TEXT NOT NULL,
  stream_key TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT audit_event_streams_unique_type_key UNIQUE (stream_type, stream_key)
);

COMMENT ON TABLE audit_event_streams IS
  'Defines append-only audit streams (e.g., GLOBAL/RUN/MANUSCRIPT) keyed by (stream_type, stream_key).';

COMMENT ON COLUMN audit_event_streams.stream_type IS
  'Stream category, e.g. GLOBAL, RUN, MANUSCRIPT.';

COMMENT ON COLUMN audit_event_streams.stream_key IS
  'Stream identifier within stream_type (e.g., run_id or manuscript_id).';

CREATE TABLE IF NOT EXISTS audit_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  stream_id UUID NOT NULL REFERENCES audit_event_streams(stream_id),
  seq BIGINT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  run_id TEXT NULL,
  trace_id TEXT NULL,
  node_id TEXT NULL,
  actor_type TEXT NOT NULL,
  actor_id TEXT NULL,
  service TEXT NOT NULL,
  action TEXT NOT NULL,
  resource_type TEXT NOT NULL,
  resource_id TEXT NOT NULL,
  before_hash TEXT NULL,
  after_hash TEXT NULL,
  payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  payload_hash TEXT NOT NULL,
  prev_event_hash TEXT NULL,
  event_hash TEXT NOT NULL,
  CONSTRAINT audit_events_unique_stream_seq UNIQUE (stream_id, seq)
);

COMMENT ON TABLE audit_events IS
  'Append-only audit events. Hash-chained by (prev_event_hash, event_hash) per stream to provide tamper evidence.';

COMMENT ON COLUMN audit_events.seq IS
  'Monotonic sequence per stream (enforced as unique; monotonicity ensured by writer).';

COMMENT ON COLUMN audit_events.payload_hash IS
  'SHA-256 of canonical payload_json serialization (computed by writer).';

COMMENT ON COLUMN audit_events.prev_event_hash IS
  'event_hash of the previous event in the same stream (NULL for first event).';

COMMENT ON COLUMN audit_events.event_hash IS
  'SHA-256 of canonical concatenation of stable event fields + payload_hash + prev_event_hash (computed by writer).';

CREATE INDEX IF NOT EXISTS idx_audit_events_resource_created_at
  ON audit_events(resource_type, resource_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_audit_events_run_created_at
  ON audit_events(run_id, created_at DESC)
  WHERE run_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_audit_events_trace_id
  ON audit_events(trace_id)
  WHERE trace_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_audit_events_node_created_at
  ON audit_events(node_id, created_at DESC)
  WHERE node_id IS NOT NULL;

COMMIT;

