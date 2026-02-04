# Security Remediation Plan
**Generated:** January 29, 2026
**Updated:** January 30, 2026
**Repository:** researchflow-production

## ✅ REMEDIATION STATUS (Updated 2026-01-30)

### Python Dependencies - FIXED ✅
All Python vulnerabilities have been addressed:
- `python-jose[cryptography]>=3.3.0` → Installed: 3.5.0 ✅
- `python-multipart>=0.0.7` → Installed: 0.0.22 ✅
- `protobuf>=4.25.0` → Installed: 6.33.5 ✅
- `pyasn1>=0.5.1` → Installed: 0.6.2 ✅
- `ecdsa` → REMOVED (CVE-2024-23342 has no fix; using cryptography library instead) ✅
- `scikit-learn>=1.4.0` → Installed: 1.7.2 ✅

### Credential Rotation - FIXED ✅
- Git history cleaned with git-filter-repo
- New PostgreSQL password generated: `TTQTYmXE8eyeFevpf1wLNLrC0zIgqjk5`
- Updated in `.env` file

### Node.js Dependencies - REQUIRES LOCAL ACTION ⚠️
Due to pnpm workspace constraints, run on your local machine:
```bash
cd /path/to/researchflow-production
pnpm update multer tar eslint lodash esbuild
```

---

## 🔴 Critical Vulnerabilities (1)

### 1. python-jose - Algorithm Confusion (#15)
**Severity:** CRITICAL
**Package:** python-jose
**Summary:** Algorithm confusion with OpenSSH ECDSA keys

**Remediation:**
```bash
# In worker directory
cd packages/worker
pip install python-jose[cryptography]>=3.3.0 --upgrade --break-system-packages
# OR replace with pyjwt:
pip install pyjwt[crypto] --break-system-packages
```

**Alternative:** Consider migrating to `pyjwt` which is actively maintained.

---

## 🟠 High Vulnerabilities (12)

### 2. python-multipart - Arbitrary File Write (#19)
**Package:** python-multipart
**Action:** Upgrade to python-multipart>=0.0.7
```bash
pip install python-multipart>=0.0.7 --upgrade --break-system-packages
```

### 3. protobuf - JSON Recursion Depth Bypass (#18)
**Package:** protobuf
**Action:** Upgrade to protobuf>=4.25.0
```bash
pip install protobuf>=4.25.0 --upgrade --break-system-packages
```

### 4. pyasn1 - DoS Vulnerability (#17)
**Package:** pyasn1
**Action:** Upgrade to pyasn1>=0.5.1
```bash
pip install pyasn1>=0.5.1 --upgrade --break-system-packages
```

### 5. ecdsa - Minerva Timing Attack (#16) ✅ RESOLVED
**Package:** ecdsa (P-256)
**Status:** REMOVED - The ecdsa project considers timing attacks out of scope (no fix available)
**Resolution:** Removed ecdsa from requirements.txt; ECDSA operations now use `cryptography` library via `python-jose[cryptography]`
**Commit:** 2026-02-03 - Removed ecdsa dependency, using cryptography backend instead

### 6-9. multer - Multiple DoS Vulnerabilities (#2, #3, #4, #5, #9, #10, #11, #12)
**Package:** multer
**Summary:** Multiple denial of service vulnerabilities
**Action:** Upgrade to multer>=1.4.5-lts.2
```bash
cd packages/orchestrator
pnpm update multer
```

### 10-11. tar - Path Sanitization Issues (#6, #7)
**Package:** tar
**Summary:** Race condition and symlink poisoning
**Action:** Upgrade to tar>=6.2.1
```bash
pnpm update tar
```

---

## 🟡 Medium Vulnerabilities (4)

### 12. eslint - Stack Overflow (#20)
**Package:** eslint
**Action:** Upgrade to eslint>=9.0.0
```bash
pnpm update eslint
```

### 13. python-jose - DoS via Compressed JWE (#14)
**Package:** python-jose
**Action:** Same fix as #15 above

### 14. scikit-learn - Data Leakage (#13)
**Package:** scikit-learn
**Action:** Upgrade to scikit-learn>=1.4.0
```bash
pip install scikit-learn>=1.4.0 --upgrade --break-system-packages
```

### 15. lodash - Prototype Pollution (#8)
**Package:** lodash
**Action:** Upgrade to lodash>=4.17.21
```bash
pnpm update lodash
```

### 16. esbuild - Dev Server Vulnerability (#1)
**Package:** esbuild
**Action:** Upgrade to esbuild>=0.25.0 (development only)
```bash
pnpm update esbuild -D
```

---

## 📋 Batch Remediation Commands

### Node.js Dependencies (Orchestrator/Web)
```bash
cd /Users/ros/researchflow-production

# Update all Node.js packages
pnpm update multer tar eslint lodash esbuild

# Or run security audit fix
pnpm audit fix
```

### Python Dependencies (Worker)
```bash
cd /Users/ros/researchflow-production/packages/worker

# Create requirements-security.txt with fixed versions
cat > requirements-security.txt << 'EOF'
python-jose[cryptography]>=3.3.0
python-multipart>=0.0.7
protobuf>=4.25.0
pyasn1>=0.5.1
# ecdsa REMOVED - CVE-2024-23342 has no fix; cryptography lib used instead
scikit-learn>=1.4.0
EOF

# Install security updates
pip install -r requirements-security.txt --upgrade --break-system-packages
```

---

## ⚠️ ROS-51: GitGuardian Credential Exposure

**Status:** REQUIRES MANUAL ACTION

### Steps to Remediate:
1. **Rotate the exposed credential immediately**
2. **Clean git history using BFG:**
   ```bash
   # Install BFG
   brew install bfg

   # Clone a fresh mirror
   git clone --mirror https://github.com/ry86pkqf74-rgb/researchflow-production.git

   # Remove sensitive data
   bfg --replace-text passwords.txt researchflow-production.git

   # Clean and push
   cd researchflow-production.git
   git reflog expire --expire=now --all
   git gc --prune=now --aggressive
   git push --force
   ```

3. **Update .gitignore to prevent future exposure:**
   ```
   .env
   .env.local
   .env.production
   *.pem
   *.key
   credentials.json
   ```

---

## 📊 Summary

| Severity | Count | Action Required |
|----------|-------|-----------------|
| Critical | 1 | Immediate - python-jose |
| High | 12 | This week |
| Medium | 4 | Next sprint |
| **Total** | **20** | |

## ✅ Verification After Remediation

```bash
# Run Dependabot check
gh api repos/ry86pkqf74-rgb/researchflow-production/dependabot/alerts | jq 'length'

# Run npm audit
pnpm audit

# Run pip check
pip check
```

---

**Document Author:** Claude Orchestrator
**Last Updated:** January 29, 2026
