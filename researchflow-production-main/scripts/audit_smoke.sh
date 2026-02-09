#!/usr/bin/env bash
# =============================================================================
# Audit smoke runner: orchestrator ping + worker audit smoke test
# Phase 6 – run after deploy to verify audit path.
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Load env from repo root if present
if [[ -f "$REPO_ROOT/.env" ]]; then
  export $(grep -v '^#' "$REPO_ROOT/.env" | xargs)
fi

# Validate required env vars
missing=()
[[ -n "${ORCHESTRATOR_BASE_URL:-}" ]] || missing+=(ORCHESTRATOR_BASE_URL)
[[ -n "${INTERNAL_API_KEY:-}" ]] || missing+=(INTERNAL_API_KEY)
if [[ ${#missing[@]} -gt 0 ]]; then
  echo "ERROR: Missing required env vars: ${missing[*]}" >&2
  echo "Set them in the environment or in $REPO_ROOT/.env" >&2
  exit 1
fi

echo "Audit smoke: orchestrator ping..."
if ! curl -fsS "${ORCHESTRATOR_BASE_URL%/}/internal/audit/ping"; then
  echo "ERROR: Orchestrator audit ping failed (curl non-zero)." >&2
  exit 1
fi
echo ""

echo "Audit smoke: worker audit smoke test..."
WORKER_DIR="$REPO_ROOT/services/worker"
if ! (cd "$WORKER_DIR" && PYTHONPATH=src python3 -m src.clients.audit_smoke_test); then
  echo "ERROR: Worker audit smoke test failed." >&2
  exit 1
fi

echo "Audit smoke: all steps passed."
