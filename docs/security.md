# Security Scanning

## Overview

This repository implements baseline security scanning for deploy readiness:

- **CodeQL**: Automated code analysis for vulnerabilities and coding errors
- **Secret Scanning**: Detection of accidentally committed secrets (requires manual enablement)
- **Push Protection**: Prevents pushes containing secrets (requires manual enablement)

---

## CodeQL Analysis

### What is CodeQL?

CodeQL is GitHub's semantic code analysis engine that finds security vulnerabilities and coding errors in your codebase. It runs automatically on:

- Every push to `main`
- Every pull request to `main`
- Weekly (Sundays at midnight UTC)

### Languages Analyzed

This repository is configured to scan:

- **JavaScript/TypeScript** (frontend and tooling code)
- **Python** (backend services and agents)

### Viewing Results

1. Navigate to the **Security** tab in the GitHub repository
2. Click **Code scanning alerts** in the left sidebar
3. Review any alerts and their severity
4. Click on an alert for:
   - Detailed explanation
   - Affected code location
   - Recommended fix

---

## Secret Scanning & Push Protection

### Current Status

⚠️ **Secret scanning and push protection are currently DISABLED** for this repository.

These features must be enabled manually through the GitHub UI to achieve full deploy readiness.

### What They Do

- **Secret Scanning**: GitHub automatically scans commits for known secret patterns (API keys, tokens, credentials, etc.)
- **Push Protection**: Blocks pushes that contain detected secrets, preventing accidental exposure

### How to Enable

Follow these steps to enable secret scanning and push protection:

#### Step 1: Navigate to Repository Settings

1. Go to the GitHub repository page
2. Click **Settings** (top navigation bar)
3. In the left sidebar, scroll to the **Security** section

#### Step 2: Enable Secret Scanning

1. Click **Code security and analysis**
2. Find the **Secret scanning** section
3. Click **Enable** next to "Secret scanning"
4. Confirm any prompts

#### Step 3: Enable Push Protection

1. In the same **Code security and analysis** page
2. Find the **Push protection** section (appears after enabling secret scanning)
3. Click **Enable** next to "Push protection"
4. Confirm any prompts

#### Step 4: Verify Configuration

After enabling:

1. Go to **Security** → **Code scanning alerts**
2. Verify both CodeQL and Secret Scanning are listed as active tools
3. Test by attempting to commit a dummy secret (optional):
   ```bash
   echo "github_pat_EXAMPLE123456" > test_secret.txt
   git add test_secret.txt
   git commit -m "test"
   git push
   ```
   Push protection should block this push.

---

## Deployment Readiness Requirements

Before deploying to production, ensure:

- ✅ CodeQL workflow is running successfully (check Actions tab)
- ⚠️ Secret scanning is enabled in repository settings
- ⚠️ Push protection is enabled in repository settings
- ✅ All critical/high-severity alerts are reviewed and addressed

---

## Limitations

**Important**: CodeQL and secret scanning features may be limited based on:

- GitHub plan (Free, Pro, Team, Enterprise)
- Repository visibility (public vs private)
- Organization settings (for org-owned repos)

If the CodeQL workflow fails with permissions errors or the secret scanning option is unavailable:

1. Check your GitHub plan limitations
2. Verify organization security policies (if applicable)
3. Consult GitHub documentation: https://docs.github.com/en/code-security

For private repositories, secret scanning typically requires GitHub Advanced Security (available on Enterprise plans or for public repos).
