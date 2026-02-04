# ResearchFlow Production - Cleanup & Sync Analysis
Generated: 2026-01-29

## Summary

**GitHub Repo**: https://github.com/ry86pkqf74-rgb/researchflow-production (14 commits)
**Local Path**: /Users/ros/Documents/GitHub/researchflow-production

## Comparison Results

### ✅ Core Structure Match (In Both GitHub & Local)
| Directory/File | Status |
|---------------|--------|
| .github/workflows/ | ✅ Synced |
| docs/ | ✅ Synced |
| infrastructure/ | ✅ Synced |
| migrations/ | ✅ Synced |
| packages/ | ✅ Synced |
| scripts/ | ✅ Synced |
| services/ | ✅ Synced |
| shared/ | ✅ Synced |
| tests/ | ✅ Synced |
| docker-compose.yml | ✅ Synced |
| docker-compose.prod.yml | ✅ Synced |
| package.json | ✅ Synced |
| tsconfig.json | ✅ Synced |

### 🟡 Local-Only (Potential Additions to GitHub)
These exist locally but NOT in the GitHub repo:

| Item | Size | Recommendation |
|------|------|----------------|
| apps/ | 76K | ⚠️ Review - contains api-node, ros-backend |
| binder/ | 8K | 📌 Add to repo (Jupyter config) |
| config/ | 8K | 📌 Add to repo (AI orchestration) |
| evals/ | 20K | 📌 Add to repo (evaluation scripts) |
| integration-prompts/ | 116K | 📌 Add to repo (valuable prompts) |
| k8s/ | 4K | 📌 Add to repo (overlaps with infrastructure?) |
| notebooks/ | 8K | 📌 Add to repo (demo notebooks) |
| planning/ | 52K | 📌 Add to repo (planning docs) |
| prompts/ | 12K | 📌 Add to repo (prompt templates) |
| types/ | 12K | 📌 Add to repo (TypeScript types) |
| playwright.config.ts | - | 📌 Add to repo |
| vercel.json | - | 📌 Add to repo |
| mkdocs.yml | - | 📌 Add to repo |

### 🔴 Docker Compose Variants (Local Only - 9 extra)
GitHub has: `docker-compose.yml`, `docker-compose.prod.yml`
Local also has:
- docker-compose.backend.yml
- docker-compose.claude-integration.yml
- docker-compose.conference-test.yml
- docker-compose.hipaa.yml
- docker-compose.manuscript-test.yml
- docker-compose.medical.yml
- docker-compose.minimal.yml
- docker-compose.monitoring.yml
- docker-compose.test.yml

**Recommendation**: Add these to repo or consolidate

### 📝 Documentation Files (95 .md files at root)
Many checkpoint/phase/prompt files exist locally. Categories:
- CHECKPOINT_*.md (4 files) - Session snapshots
- PHASE*_*.md (20+ files) - Implementation phases
- CLAUDE_*.md (4 files) - AI prompts
- *_SUMMARY.md, *_REPORT.md (15+ files) - Reports
- FIX_*.md (5 files) - Bug fix docs

**Recommendation**: Archive older docs to `docs/archive/` or delete obsolete ones

### 🗑️ Cleanup Targets (Regeneratable/Temporary)
| Item | Size | Action |
|------|------|--------|
| node_modules/ | 729MB | Keep (regeneratable via npm install) |
| .pnpm-store/ | 6.4MB | Keep (pnpm cache) |
| playwright-report/ | 520KB | ✅ Gitignored |
| test-results/ | 4KB | ✅ Gitignored |
| .claude/ | - | ✅ IDE config, gitignored |
| .continue/ | - | ✅ IDE config, gitignored |
| dist/ directories | - | ✅ Build outputs, gitignored |

## Recommended Actions

### 1. Add Missing Valuable Content to GitHub
```bash
git add apps/ binder/ config/ evals/ integration-prompts/ k8s/ notebooks/ planning/ prompts/ types/
git add playwright.config.ts vercel.json mkdocs.yml
git add docker-compose.*.yml
git commit -m "chore: add missing local directories and configs"
git push
```

### 2. Archive Old Documentation
```bash
mkdir -p docs/archive/checkpoints docs/archive/phases
mv CHECKPOINT_*.md docs/archive/checkpoints/
mv PHASE*_*.md docs/archive/phases/
```

### 3. Consolidate Root Markdown Files
Move implementation docs into `docs/`:
- *_IMPLEMENTATION*.md → docs/implementation-guides/
- *_REPORT.md → docs/reports/
- SECURITY_*.md → docs/security/

### 4. Clean Build Artifacts (Optional - saves ~735MB)
```bash
rm -rf node_modules .pnpm-store playwright-report test-results
# Regenerate with: pnpm install
```

## File Counts
- Root .md files: 95
- Docker compose variants: 11
- Local-only directories: 10
- Gitignored correctly: Yes ✅
