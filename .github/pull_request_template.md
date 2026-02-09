# Summary
- What changed?
- Why?

## AI Review Link / Status (optional)
- [ ] AI review comment posted (link it here): <!-- paste URL to the AI review comment/thread -->
- Notes/overrides (if any):

## Security / PHI checklist
- [ ] No PHI in logs, screenshots, test fixtures, or example payloads
- [ ] Secrets not added (env files, configs, tests); rotated if exposed
- [ ] AuthN/AuthZ reviewed for new/changed access paths
- [ ] Input validation + safe error handling for new endpoints/queues/jobs

## Auditability checklist (when writing data)
- [ ] Any write path emits an audit event via `AuditService.appendEvent`
- [ ] Actor + tenant/org context captured (who did what, where/when)
- [ ] Audit event includes stable identifiers (not raw PHI)

## DB migration checklist (if applicable)
- [ ] Migration included + reversible (up/down) where supported
- [ ] Backfill/rollout plan documented (online vs offline, batching)
- [ ] Indexes/constraints validated; expected perf impact considered
