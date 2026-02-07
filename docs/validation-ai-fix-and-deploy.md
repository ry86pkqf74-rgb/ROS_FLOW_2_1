# Validation: AI Fix CI loop & gated deploy (SHA images)

## Run 1 — Validate AI fixer loop (PR-based)

1. **Create a small PR that breaks CI** (e.g. add a TS lint error or a failing unit test).
   - This repo uses a **failing unit test** in `researchflow-production-main/tests/unit/ci-break-run1.test.ts` (`expect(1).toBe(2)`).
2. **Confirm:**
   - [ ] CI fails on the PR.
   - [ ] **AI Fix CI** workflow runs (triggered by CI failure).
   - [ ] It opens or updates a **ci-fix/run-&lt;run_id&gt;** PR.
   - [ ] It enables **squash auto-merge** on that PR.
   - [ ] The fix PR merges automatically once green.

**After validation:** Remove the intentional failure (e.g. delete `tests/unit/ci-break-run1.test.ts` or fix the assertion) and merge or close the test PR.

---

## Run 2 — Validate gated deploy uses correct SHA images

1. **Merge a green PR to `main`.**
2. **Confirm:**
   - [ ] CI passes on `main`.
   - [ ] **Deploy to Hetzner (CI-gated)** runs.
   - [ ] On Hetzner: `docker images | grep sha-<sha>` shows the expected SHA tag.
   - [ ] Running containers use that tag (e.g. `docker compose -f docker-compose.prod.yml ps` / inspect images).

**How SHA is set:** The gated workflow uses `github.event.workflow_run.head_sha`. It exports `IMAGE_TAG=sha-<sha>` and runs `hetzner-fullstack-deploy.sh`, which uses `docker-compose.prod.yml` with `image: .../service:${IMAGE_TAG}`.

---

## If something fails — fast diagnosis map

### If AI Fix CI fails immediately

- **Likely:** Missing secrets (`ANTHROPIC_API_KEY` / `OPENAI_API_KEY`) or `gh` permission issue enabling auto-merge.
- **Fix:** Add a PAT secret `AUTO_MERGE_TOKEN` and use it for GH CLI steps that create/update the PR and run `gh pr merge --auto --squash` (so auto-merge is allowed by repo policy).

### If deploy runs but wrong version is live

- **Likely:** Deploy script not exporting `IMAGE_TAG`, or compose not referencing `IMAGE_TAG`.
- **Fix:** Implement both:
  - **C1:** Ensure the gated workflow passes `IMAGE_TAG=sha-<sha>` into the deploy step (e.g. `export IMAGE_TAG=sha-${{ github.event.workflow_run.head_sha }}` in the SSH script).
  - **C2:** Ensure `docker-compose.prod.yml` uses `image: .../service:${IMAGE_TAG}` for all app services.

*(Current setup already does C1 and C2; use this if a change regresses it.)*
