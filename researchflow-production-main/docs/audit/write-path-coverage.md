# Audit Write-Path Coverage

> Last verified: 2026-02-11
> PR: fix/ts2345-zotero-config-type-mismatches (Audit Completion PR 1)

## Overview

Every mutation endpoint in the orchestrator is documented below with its audit status.
The audit strategy uses two layers:

1. **Canonical audit ledger** — `appendEvent()` / `appendAuditEvent()` inside a DB transaction (preferred)
2. **Legacy audit service** — `createAuditEntry()` / `logManuscriptEventTx()` (also acceptable)

Read-only endpoints (GET) are not listed unless they have special audit considerations.

---

## manuscripts.ts (`/api/manuscripts`)

| Method | Path | Audit | Mechanism | Notes |
|--------|------|-------|-----------|-------|
| POST | `/` | ✅ | `logManuscriptEventTx` + `appendEvent` in txn | Create manuscript |
| GET | `/` | — | Read-only | List manuscripts |
| GET | `/:id` | — | Read-only | Get manuscript |
| PATCH | `/:id` | ✅ | `logManuscriptEventTx` + `appendEvent` in txn | Update manuscript |
| DELETE | `/:id` | ⚠️ | Not implemented | Header mentions it but no route handler exists |
| GET | `/:id/sections` | — | Read-only | |
| GET | `/:id/doc` | — | Read-only | |
| POST | `/:id/doc/save` | ✅ | `logManuscriptEventTx` + `appendEvent` in txn | Save document snapshot |
| POST | `/:id/sections/:sectionId/refine` | ✅ | `logManuscriptEventTx` + `appendEvent` in txn | AI refine with PHI gate |
| POST | `/:id/abstract/generate` | ✅ | `logManuscriptEventTx` + `appendEvent` in txn | Generate abstract |
| GET | `/:id/events` | — | Read-only | Provenance log |
| GET | `/:id/comments` | — | Read-only | |
| POST | `/:id/comments` | ✅ | `logManuscriptEventTx` + `appendEvent` in txn | Add comment |
| POST | `/:id/comments/:commentId/resolve` | ✅ | `logManuscriptEventTx` + `appendEvent` in txn | Resolve comment |
| DELETE | `/:id/comments/:commentId` | ✅ | `logManuscriptEventTx` + `appendEvent` in txn | Soft-delete comment |

---

## manuscript-branches.ts (`/api/ros/manuscripts`)

### Router-level routes (artifact-based branching)

| Method | Path | Audit | Mechanism | Notes |
|--------|------|-------|-----------|-------|
| POST | `/manuscripts/:artifactId/branch` | ✅ | `createAuditEntry` | Create branch from artifact version |
| GET | `/manuscripts/:artifactId/branches` | — | Read-only | List branches |
| POST | `/manuscripts/:artifactId/merge` | ✅ | `createAuditEntry` | 3-way merge with conflict detection |
| DELETE | `/manuscripts/:artifactId/branches/:branchName` | ✅ | `createAuditEntry` | Delete branch (soft) |

### manuscriptBranchingRoutes (manuscript-level branching)

| Method | Path | Audit | Mechanism | Notes |
|--------|------|-------|-----------|-------|
| POST | `/:id/branches` | ✅ | `createAuditEntry` | **ADDED in this PR** — was missing |
| POST | `/:id/branches/:branchId/merge` | ✅ | `createAuditEntry` | **ADDED in this PR** — was missing |
| GET | `/:id/branches/:branchId/diff` | — | Read-only | |
| POST | `/:id/ai-refine` | ✅ | `createAuditEntry` | **ADDED in this PR** — was missing |
| GET | `/:id/versions` | — | Read-only | |

---

## commits.routes.ts (`/api/ros/branches`)

| Method | Path | Audit | Mechanism | Notes |
|--------|------|-------|-----------|-------|
| GET | `/branches/:branchId/commits` | — | Read-only | List commits |
| GET | `/branches/:branchId/commits/diff` | — | Read-only | Compute diff |
| POST | `/branches/:branchId/rollback` | ✅ | `appendEvent` in txn | Rollback as new commit, MANUSCRIPT stream |

---

## edit-sessions.routes.ts (`/api/edit-sessions`)

All mutations delegate to `EditSessionService` which emits `appendAuditEvent` internally for each state transition.

| Method | Path | Audit | Mechanism | Notes |
|--------|------|-------|-----------|-------|
| POST | `/` | ✅ | Service: `appendAuditEvent` | Create edit session (draft) |
| GET | `/branch/:branchId` | — | Read-only | |
| GET | `/manuscript/:manuscriptId` | — | Read-only | |
| GET | `/:sessionId` | — | Read-only | |
| POST | `/:sessionId/submit` | ✅ | Service: `appendAuditEvent` | draft → submitted |
| POST | `/:sessionId/approve` | ✅ | Service: `appendAuditEvent` | submitted → approved |
| POST | `/:sessionId/reject` | ✅ | Service: `appendAuditEvent` | submitted → rejected |
| POST | `/:sessionId/merge` | ✅ | Service: `appendAuditEvent` | approved → merged |

---

## branch-persistence.service.ts (internal service)

| Method | Operation | Audit | Mechanism | Notes |
|--------|-----------|-------|-----------|-------|
| `createRevision()` | Create revision + commit | ✅ | `appendEvent` in txn | Emits REVISION CREATE on MANUSCRIPT stream |

---

## Summary

| Category | Total Mutations | Audited | Missing | Exempt |
|----------|----------------|---------|---------|--------|
| manuscripts.ts | 8 | 8 | 0 | 0 |
| manuscript-branches.ts (router) | 3 | 3 | 0 | 0 |
| manuscript-branches.ts (ms routes) | 3 | 3 | 0 | 0 |
| commits.routes.ts | 1 | 1 | 0 | 0 |
| edit-sessions.routes.ts | 5 | 5 | 0 | 0 |
| **Total** | **20** | **20** | **0** | **0** |

### Known Gaps (Non-blocking)

1. **DELETE /api/manuscripts/:id** — Endpoint listed in route header comment but not implemented.
   When implemented, it must include audit coverage following the pattern in
   `POST /:id/comments/:commentId/resolve`.

2. **manuscriptVersionService / aiEditingService** — These service modules do not emit
   audit events internally. Audit coverage is provided at the route handler level.
   If these services are ever called from additional entry points, the service-level
   audit gap should be addressed.
