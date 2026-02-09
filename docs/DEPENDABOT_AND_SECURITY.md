# Dependabot Alerts & Copilot Suggestions

## Viewing Dependabot Alerts

1. **GitHub Security tab**  
   `https://github.com/<owner>/<repo>/security/dependabot`

2. **What’s included**  
   Dependabot reports:
   - **npm** (Node): `researchflow-production-main` (pnpm lockfile), and any nested `package.json` / lockfiles
   - **pip** (Python): `researchflow-production-main/services/worker` and agents
   - **GitHub Actions**: workflows under `.github/workflows`
   - **Docker**: Dockerfiles and base images

3. **Local checks (no GitHub auth)**  
   - **Node**: From repo root, `cd researchflow-production-main && pnpm audit`
   - **Python**: `pip-audit -r researchflow-production-main/services/worker/requirements.txt` (requires `pip-audit`)

## Addressing Alerts

- **Critical / High**  
  Prefer upgrading the affected dependency to a patched version (Dependabot often opens a PR; review and merge, or replicate the version bump yourself).

- **Dependabot PRs**  
  - Open the PR from the Security tab or the Alerts list.
  - Run CI and any relevant tests.
  - Merge (squash or merge commit as per your policy).  
  If the repo uses a single lockfile (e.g. pnpm at monorepo root), one merged PR can clear multiple alerts.

- **Dismissing**  
  Only dismiss with a reason (e.g. “Won’t fix”, “False positive”) when you consciously accept the risk.

## Copilot Suggestions

- **Code review / suggestions**  
  GitHub Copilot can suggest dependency upgrades and refactors. Treat them like any other PR: run tests and security checks before merging.

- **AI Code Review workflow**  
  `researchflow-production-main/.github/workflows/ai-code-review.yml` runs on PRs (production repo only). Use its suggestions as input; still verify and run CI.

- **Applying suggestions**  
  - Apply only after reviewing the diff.
  - Ensure `pnpm audit` (and, if applicable, `pip-audit`) still pass after changes.

## Security Workflows in This Repo

- **Root (ROS_FLOW_2_1)**  
  - `ci.yml`: gitleaks secret scan, lint/typecheck/unit tests.
- **researchflow-production-main**  
  - `security-scan.yml`: Trivy (FS + image), Gitleaks, custom audit; SARIF to Security tab.
  - `docker-scout.yml`: Docker Scout for container CVEs.

## Pinning GitHub Actions (recommended)

To reduce supply-chain risk, pin actions by full commit SHA instead of a tag (e.g. `@v4`):

- `actions/checkout@v4` → `actions/checkout@<full-SHA>`
- `actions/setup-node@v4` → `actions/setup-node@<full-SHA>`

SHAs can be taken from the action’s release page or by resolving the tag (e.g. `git ls-remote https://github.com/actions/checkout refs/tags/v4.2.2`). Root workflows under `.github/workflows` use SHA pins for `actions/checkout` and `actions/setup-node`; other actions remain on tag refs.
