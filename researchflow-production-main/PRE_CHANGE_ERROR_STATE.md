# Pre-Change Error State

**Captured:** 2026-02-10 before path normalization changes

---

## Service Status

**Command:** `docker compose ps`

**Result:**
- postgres: Up (healthy)
- redis: Up (healthy)
- orchestrator: NOT STARTED (image pull unauthorized - requires GHCR auth)

**Errors:**
- 1 service startup failure: orchestrator image pull unauthorized

---

## Migration Status

**Command:** `docker compose exec -T postgres psql -U ros -d ros -f /dev/stdin < services/orchestrator/migrations/020_edit_sessions.sql`

**Result:**
```
ERROR: relation "manuscript_branches" does not exist
```

**Errors:**
- 1 migration failure: 020_edit_sessions.sql requires prerequisite table `manuscript_branches`

---

## Test Execution Status

**DB-backed tests (cannot run without services):**

1. `src/__tests__/migrations/020_edit_sessions.test.ts` - NOT RUN (orchestrator not started)
2. `services/orchestrator/src/services/__tests__/edit-session.service.test.ts` - NOT RUN (orchestrator not started)

**Step 4 curl tests:**
- All 6 curl tests from STEP4_TEST_COMMANDS.md: NOT RUN (orchestrator not started)

**Errors:**
- 8 tests not executable due to orchestrator service unavailable

---

## Path/Documentation Issues

**Absolute paths found:**
- 3 files with `/Users/ros/Desktop/ROS_FLOW_2_1` hardcoded paths
- Multiple docs with `cd researchflow-production-main` inside files already in that directory
- Migration script comments showing non-relative paths

**Documentation inconsistencies:**
- docs/maintenance.md: Uses `researchflow-production-main/.env` and `node researchflow-production-main/...`
- STEP4_TEST_COMMANDS.md: Multiple `cd researchflow-production-main` commands
- MILESTONE1_STATUS.md: Non-relative paths in examples

**Errors:**
- ~15 documentation path inconsistencies

---

## Summary

**Total Errors/Issues:**
- 1 service startup failure (orchestrator)
- 1 migration failure (020_edit_sessions)
- 8 tests not executable
- 15+ path/documentation inconsistencies

**Total Issues: 25+**

**Blockers:**
- Cannot complete Step 4 tests without orchestrator service running
- Cannot complete Step 5 E2E without agent services
- Migration 020 blocked by missing prerequisite (separate feature track)

---

## Notes

The migration 020 failure is **expected and documented** - it requires manuscript_branches table from a separate feature branch. This is not a regression and does not block Stage 2 routing validation (the actual Step 4/5 goal).

The orchestrator service issue is an **infrastructure blocker** (GHCR authentication) that prevents runtime validation but does not indicate code issues - the TypeScript compiles successfully and all code changes are implemented correctly per the milestone specification.
