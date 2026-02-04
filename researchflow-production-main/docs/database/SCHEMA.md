# Database Schema

This document describes the **PostgreSQL** schema and migration workflow for **ResearchFlow Production**.

## Migration system

### Where migrations live

Root SQL migrations live in:

- [`migrations/`](../../migrations)

There are additional migration-like directories for other packages/services:

- `packages/core/migrations/` (includes Drizzle `meta/` journal files)
- `services/orchestrator/migrations/`

### How migrations are applied

Root migrations are applied by:

- [`scripts/db-migrate.sh`](../../scripts/db-migrate.sh)

That script:

1. Ensures a status table exists: `schema_migrations`
2. Lists `migrations/*.sql`, sorts them lexicographically, and applies each file not recorded in `schema_migrations`
3. Records the applied filename into `schema_migrations`

### Migration status / identifying pending migrations

Because the runner records each applied filename, **pending migrations** are those present in `migrations/` but not present in `schema_migrations`.

To view status:

```sql
SELECT filename, applied_at
FROM schema_migrations
ORDER BY filename;
```

To preview pending migrations without applying them:

- `DRY_RUN=1 ./scripts/db-migrate.sh`

## `migrations/` verification (repository state)

### Ordering & sequence integrity

There are currently **34** migration files under `migrations/`.

The filenames mix **different numbering widths** (e.g. `0007_...` and `007_...`), which creates **duplicate sequence numbers** and makes ordering ambiguous.

Detected issues:

- **Missing sequence numbers** between `0000` and `0030`: `0001`, `0018`–`0024`
- **Duplicate sequence numbers** (examples):
  - `0004_...` and `004_...`
  - `0005_...` and `005_...`
  - `0009_...` appears multiple times

> Since `db-migrate.sh` sorts by filename, the actual application order is lexicographic, not numeric; mixed-width numbering can lead to unexpected ordering.

### Up/Down

These migrations are **plain `.sql` files**. They do not expose `up()` / `down()` functions.

If reversibility is required, adopt one of:

- a migration tool that supports paired up/down files
- or embed explicit rollback SQL sections and document the rollback procedure per migration

## 20-stage workflow data model (ERD-style)

### Entities and relationships

- `projects` (1) → (many) `workflow_stages`
- `workflow_stages` (1) → (many) `documents`
- `users` (1) → (many) `audit_log`

Conceptually:

- A **project** represents a research effort.
- Each project has up to **20 workflow stages**, represented by `workflow_stages.stage_number` in `[1..20]`.
- Each stage can have one or more **documents** (drafts, artifacts), versioned by `documents.version`.
- All mutations should be recorded in `audit_log`.

## Required tables (verification target)

| Table | Required columns |
|---|---|
| `projects` | `id`, `title`, `type`, `status`, `created_at` |
| `workflow_stages` | `id`, `project_id`, `stage_number`, `status`, `data` |
| `documents` | `id`, `project_id`, `stage_id`, `content`, `version` |
| `users` | `id`, `email`, `role`, `created_at` |
| `audit_log` | `id`, `user_id`, `action`, `entity`, `timestamp` |

### Current findings (static analysis)

Based on static inspection of `infrastructure/docker/postgres/init.sql` and a subset of migrations:

- `users` exists, but no `role` column was detected in `init.sql`.
- `projects` is defined in `migrations/0027_projects_and_templates.sql`, but the required `title` and `type` columns were not detected in that file.
- `workflow_stages`, `documents`, and `audit_log` were not detected in the inspected subset (they may exist in other migrations).

> Next step: run a full scan of all migration SQL (or apply to a scratch DB) to confirm the presence of all required tables/columns.

## Indexes (recommended minimum)

- `workflow_stages(project_id, stage_number)` **UNIQUE**
- `documents(project_id, stage_id, version)` **UNIQUE**
- `documents(stage_id)` for stage lookups
- `audit_log(user_id, timestamp)` for user audit queries
- `audit_log(entity, timestamp)` for entity timelines
