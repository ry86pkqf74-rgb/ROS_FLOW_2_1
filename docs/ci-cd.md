# CI/CD — ROS_FLOW_2_1

Required repo settings, secrets, and rollback for **ry86pkqf74-rgb/ROS_FLOW_2_1**.

## Workflows

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| **CI** | `push` to `main`, `pull_request` to `main` | Lint, typecheck, unit tests (gate for deploy) |
| **Deploy to Hetzner (CI-gated)** | After **CI** succeeds on `main` | Build production images, push to GHCR, deploy to Hetzner |
| **Build, Push & Deploy to Hetzner (Full Stack)** | `workflow_dispatch` only | Manual deploy (no CI gate) |
| **AI Fix CI** | After **CI** fails (PRs or main) | Open/update PR with AI-generated fix, enable squash auto-merge (max 3 attempts) |
| **Post-Deploy Smoke** | After deploy workflows complete | Health + API smoke against deployed instance |
| **Smoke Scripts** | After deploy workflows complete | Stage2 + RAG smoke against deploy URL |

## Required GitHub settings

- **Branches:** Default branch `main` (so CI and gated deploy run on the correct ref).
- **Actions:** GitHub Actions enabled; workflows must be allowed to run from the default branch and from PRs.
- **Fork pull requests:** If you want the AI fixer to run only on non-fork PRs, keep the default (workflow runs in the base repo; the fixer already skips when the run is from a fork via `workflow_run.repository.full_name == github.repository`).
- **Environments:** Create an environment named **Hetzner production** if you use environment protection rules or secrets scoped to that environment.

## Required secrets

| Secret | Used by | Notes |
|--------|---------|------|
| `GITHUB_TOKEN` | All workflows | Provided by Actions; no setup. |
| `HETZNER_HOST` | Deploy (gated + manual) | Hetzner server hostname or IP. |
| `HETZNER_USER` | Deploy (gated + manual) | SSH user for deploy. |
| `HETZNER_SSH_KEY` | Deploy (gated + manual) | Private SSH key (full key, not path). |
| `HETZNER_DEPLOY_URL` | Smoke workflows | Base URL of deployed app (e.g. `http://178.156.180.37:3001`). |
| `ANTHROPIC_API_KEY` | AI Fix CI | For attempt 1 and 3. |
| `OPENAI_API_KEY` | AI Fix CI | For attempt 2. |

Optional (if using environment **Hetzner production**): store `HETZNER_*` and deploy-related secrets on that environment.

## Rollback by SHA tag

Production images are tagged with the commit SHA: `sha-<full_sha>` and `main`.

1. **Identify the good SHA** (e.g. last known good run or a previous tag).
2. **On the Hetzner server**, set the image tag and redeploy:
   ```bash
   export IMAGE_TAG=sha-<good_sha>
   bash /opt/researchflow/researchflow-production-main/tools/deploy/hetzner-fullstack-deploy.sh
   ```
3. **Optional:** Re-run the manual workflow **Build, Push & Deploy to Hetzner (Full Stack)** from the Actions tab after checking out that SHA locally, so that the same SHA is built and pushed before running the above on the server. For rollback you can also rely on existing images already in GHCR for that SHA.

## AI Fix CI behavior

- Runs only when **CI** fails; does **not** run on forks.
- Never pushes to `main`; always opens or updates a **PR** from a branch like `ci-fix/run-<run_id>`.
- Uses **Anthropic** (attempt 1), **OpenAI** (attempt 2), **Anthropic** (attempt 3).
- Enables **squash auto-merge** on the PR when CI passes.
- After **3 attempts**, stops and posts a “Needs human” summary on the PR; no further auto-fix PRs for that chain.

## Security

- CI does not disable or skip tests; the AI fixer must not suggest disabling tests or weakening checks.
- Deploy uses the same SSH and registry auth as before; no new production secrets beyond the listed ones.
