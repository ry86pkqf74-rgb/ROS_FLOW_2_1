# Security Audit Quick Start Guide

## Overview

Track D implements two complementary security tools:

1. **SBOM Workflow** - Automated GitHub Actions for supply chain transparency
2. **Security Audit Script** - Local CLI tool for comprehensive security analysis

## Quick Start

### Running Local Security Audit

```bash
# Navigate to project root
cd /path/to/researchflow-production

# Make script executable (first time only)
chmod +x scripts/security-audit.sh

# Run the security audit
./scripts/security-audit.sh
```

### View Results

```bash
# Latest audit report
cat security-reports/security-audit-YYYYMMDD.json

# Detailed npm audit results
cat security-reports/npm-audit-YYYYMMDD.json

# Detailed pip audit results
cat security-reports/pip-audit-YYYYMMDD.json

# Secret scanning results
cat security-reports/secrets-found-YYYYMMDD.json
```

## What Gets Checked

### 1. npm Audit (Node.js Dependencies)
- Scans all npm packages
- Reports vulnerabilities by severity
- Suggests remediation

```bash
# Manual npm audit
npm audit --json > audit-report.json
```

### 2. pip-audit (Python Dependencies)
- Checks Python packages in requirements.txt
- Reports known vulnerabilities
- Links to vulnerability databases

```bash
# Manual pip audit
pip-audit --desc --format json --requirements services/worker/requirements.txt
```

### 3. Outdated Dependencies
- Finds packages with available updates
- Prioritizes security-relevant updates
- Reports version information

```bash
# Check npm outdated
npm outdated --json

# Check pip outdated
pip list --outdated --format json
```

### 4. Secret Scanning
- Detects hardcoded API keys, passwords
- Uses pattern matching for common secrets
- Falls back to trufflehog if available

**Patterns scanned:**
- API keys and secrets
- Private keys
- AWS credentials
- GitHub tokens
- Database passwords

### 5. License Compliance
- Identifies package licenses
- Flags GPL/AGPL usage
- Checks commercial compatibility

## Exit Codes

| Code | Status | Meaning |
|------|--------|---------|
| 0 | PASSED | No issues found |
| 1 | WARNING | Medium severity issues detected |
| 2 | ERROR | High severity issues detected |
| 3 | CRITICAL | Critical vulnerabilities found |

## Report Format

All reports use standardized JSON format with audit metadata, summary, and per-component results.

## GitHub Workflow Integration

### Automatic Triggers

The SBOM workflow automatically runs:

1. **On Push to Main** - When dependency files change
2. **On Pull Request** - Full SBOM and security gate
3. **Weekly** - Every Monday at 6 AM UTC
4. **Manual** - Via workflow_dispatch

### Checking Workflow Results

1. **In GitHub UI:**
   - Go to Actions tab
   - Find "SBOM Generation & Supply Chain" workflow
   - View job logs and artifacts

2. **In PR:** 
   - Scroll to Checks section
   - Find security-gate result
   - Click Details to see full scan

3. **Download Artifacts:**
   - Click workflow result
   - Scroll to Artifacts section
   - Download individual SBOMs

## Common Scenarios

### Found High Severity Vulnerability

```bash
# 1. View the vulnerability details
cat security-reports/npm-vulnerabilities.json | jq '.[] | select(.severity == "High")'

# 2. Update the affected package
npm update package-name

# 3. Re-run audit to verify fix
./scripts/security-audit.sh

# 4. Commit and push
git add package*.json
git commit -m "fix: update package to address CVE"
git push
```

### Reviewing License Compliance

```bash
# 1. Export license report
pip-licenses --format=markdown > LICENSE_REVIEW.md

# 2. Check for GPL packages
cat security-reports/npm-licenses-*.json

# 3. Document any exceptions
echo "License Exception approved" > EXCEPTIONS.md
```

### Finding Secrets in Code

```bash
# 1. View detected secrets
cat security-reports/secrets-found-*.json

# 2. Locate and remove the secret from source

# 3. Rotate compromised credentials

# 4. Re-run audit
./scripts/security-audit.sh
```

### Pre-deployment Verification

```bash
# 1. Run full audit
./scripts/security-audit.sh

# 2. Check exit code
echo $?

# 3. Review combined report
jq '.audit_summary' security-reports/security-audit-*.json

# 4. Export SBOM for compliance
cp security-reports/sbom-report.json deployment-sbom.json
```

## Troubleshooting

### npm audit shows no vulnerabilities
**Normal** - means Node dependencies are clean

### jq: command not found
```bash
# Ubuntu/Debian
sudo apt-get install jq

# macOS
brew install jq
```

### pip-audit not found
```bash
pip install pip-audit
```

### Script permission denied
```bash
chmod +x scripts/security-audit.sh
```

## Best Practices

1. **Run Regularly**
   - Before every commit (pre-commit hook)
   - Before every deployment
   - Weekly minimum

2. **Review Reports**
   - Check for new vulnerabilities
   - Track trends over time
   - Prioritize remediations

3. **Keep Dependencies Updated**
   - Critical/high patches: immediately
   - Medium patches: weekly review
   - Low patches: quarterly planning

4. **Handle Secrets Properly**
   - Never commit secrets
   - Use environment variables
   - Rotate compromised credentials

5. **Document Decisions**
   - Record license exceptions
   - Document accepted risks
   - Track remediation status

---

**Version:** 1.0.0  
Last Updated: January 30, 2026
