# Git Authentication Fix

## Problem

The `GITHUB_TOKEN` environment variable contains an invalid/expired token, causing authentication failures:
```
remote: Invalid username or token. Password authentication is not supported for Git operations.
fatal: Authentication failed for 'https://github.com/ry86pkqf74-rgb/ROS_FLOW_2_1.git/'
```

## Root Cause

- Environment variable `GITHUB_TOKEN` is set globally (possibly in a CI/CD context or startup script)
- This token takes precedence over the valid `gh` CLI token stored in keyring
- Git tries to use the invalid environment token instead of the working keyring token

## Solution Implemented

### Option 1: Use Git Alias (Recommended)

A git alias `pushgh` has been configured that temporarily unsets `GITHUB_TOKEN` and uses the gh CLI credentials:

```bash
# Push to origin main
git pushgh origin main

# Push with force
git pushgh --force origin feature-branch

# Push all branches
git pushgh --all origin
```

**How it works:**
```bash
git config alias.pushgh '!f() { unset GITHUB_TOKEN && git push "$@"; }; f'
```

### Option 2: Use Helper Script

A shell script `.git-push-helper.sh` is available:

```bash
# From repository root
./.git-push-helper.sh origin main
```

### Option 3: Manual Workaround

For one-time pushes:

```bash
unset GITHUB_TOKEN && git push origin main
```

## Verification

Check that gh CLI authentication is working:

```bash
# Verify gh CLI status
unset GITHUB_TOKEN && gh auth status

# Should show:
# ✓ Logged in to github.com account ry86pkqf74-rgb (keyring)
# - Active account: true
# - Token scopes: 'gist', 'read:org', 'repo', 'workflow'
```

## Permanent Fix (Optional)

To permanently resolve this, find where `GITHUB_TOKEN` is being set and either:

### A. Remove it from startup scripts

Check these files:
```bash
~/.zshrc
~/.zprofile
~/.bash_profile
~/.bashrc
~/.config/fish/config.fish
```

### B. Override it in your shell config

Add to `~/.zshrc` (or equivalent):
```bash
# Force use of gh CLI instead of GITHUB_TOKEN env var
unset GITHUB_TOKEN
```

### C. Update the token value

If the token is intentionally set for CI/CD, update it:
```bash
# Generate new token at: https://github.com/settings/tokens
export GITHUB_TOKEN="ghp_NEW_VALID_TOKEN_HERE"
```

## Quick Reference

| Command | Purpose |
|---------|---------|
| `git pushgh origin main` | Push using gh CLI credentials (bypasses GITHUB_TOKEN) |
| `git push origin main` | ❌ Will fail due to invalid GITHUB_TOKEN |
| `unset GITHUB_TOKEN && git push origin main` | Manual one-time workaround |
| `gh auth status` | Check gh CLI authentication status |
| `gh auth refresh` | Refresh gh CLI token if needed |

## Testing

```bash
# Test that pushgh works
cd researchflow-production-main
echo "test" >> .gitignore
git add .gitignore
git commit -m "test: verify pushgh alias"
git pushgh origin main

# Cleanup test
git reset --soft HEAD~1
git restore --staged .gitignore
git restore .gitignore
```

## Status

✅ **Fixed** - Use `git pushgh` instead of `git push` for all operations in this repository.

---

*Created: 2025-01-30*  
*Last Updated: 2025-01-30*
