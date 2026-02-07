# Quick Push Instructions

## ⚠️ Important: Use `git pushgh` instead of `git push`

Due to an invalid `GITHUB_TOKEN` environment variable, use the custom alias:

```bash
# ✅ CORRECT - Use this
git pushgh origin main

# ❌ WRONG - This will fail
git push origin main
```

## Common Commands

```bash
# Stage all changes
git add -A

# Commit with message
git commit -m "feat: your commit message"

# Push to main branch
git pushgh origin main

# Push with force (use carefully!)
git pushgh --force origin main

# Push all branches
git pushgh --all origin

# Push and set upstream
git pushgh -u origin feature-branch
```

## Why?

The `git pushgh` alias temporarily unsets the invalid `GITHUB_TOKEN` environment variable and uses the valid `gh` CLI token from keyring.

## Full Documentation

See [GIT_AUTH_FIX.md](../GIT_AUTH_FIX.md) for complete details.

---

**TL;DR:** Replace `git push` with `git pushgh` everywhere.
