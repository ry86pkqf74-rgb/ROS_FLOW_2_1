# Repository Maintenance Guide

Quick reference for keeping the repository clean and healthy.

## Running Quality Checks

```bash
# Type checking
pnpm run typecheck          # or: pnpm run type-check

# Unit tests
pnpm run test:unit

# Both together
pnpm run typecheck && pnpm run test:unit
```

## Branch Pruning

### Local branches
```bash
# List branches already merged into main
git branch --merged main | grep -v "^\*\|main\|master"

# Delete them (review list first!)
git branch --merged main | grep -v "^\*\|main\|master" | xargs git branch -d
```

### Remote branches
```bash
# Prune references to deleted remote branches
git fetch --prune

# ⚠️ Delete remote branch (DANGEROUS - verify first!)
git push origin --delete branch-name
```

**Safety rules:**
- Never force-delete (`-D`) without understanding why
- Verify branch is merged before deletion
- Check with team before deleting shared remote branches
- Keep release branches (`release-*`, `hotfix-*`)

## Minimal Extraction PRs

**Goal:** Avoid massive conflict-prone PRs. Extract clean, focused changes instead.

### Example: PR #31 approach

1. **Create a fresh branch from latest main**
   ```bash
   git checkout main && git pull
   git checkout -b feat/minimal-extraction
   ```

2. **Cherry-pick or manually extract ONLY the needed changes**
   - Don't merge entire branches with conflicts
   - Copy specific files or functions you need
   - Test the extraction works standalone

3. **Open a small, reviewable PR**
   - Clear title describing the ONE thing it does
   - Link to original work if relevant
   - Keep diff under ~500 lines when possible

4. **Merge and iterate**
   - Get it merged quickly (less time = fewer conflicts)
   - Extract next piece in a new PR
   - Repeat until all useful changes are migrated
