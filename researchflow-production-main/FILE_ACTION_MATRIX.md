# Quick Reference: File Action Matrix

## At-a-Glance Summary

```
┌──────────────────────────────┬────────────┬──────────┬─────────────────────────────────┐
│ File Name                    │ Exists?    │ Action   │ New Location/Name               │
├──────────────────────────────┼────────────┼──────────┼─────────────────────────────────┤
│ .env.docker.new              │ No target  │ MERGE    │ .env.docker-example             │
│ nginx.prod.conf.new          │ No target  │ ADD      │ infrastructure/nginx/           │
│ docker-deploy-prod.sh.new    │ No target  │ ADD      │ scripts/docker-deploy-prod.sh   │
│ generate-dev-certs.sh.new    │ No target  │ ADD      │ scripts/generate-dev-certs.sh   │
└──────────────────────────────┴────────────┴──────────┴─────────────────────────────────┘
```

## Recommended Command Sequence

```bash
# 1. Environment configuration
cp .env.docker.new .env.docker-example

# 2. Production nginx config
mv infrastructure/nginx/nginx.prod.conf.new infrastructure/nginx/nginx.prod.conf

# 3. Deployment scripts
mv scripts/docker-deploy-prod.sh.new scripts/docker-deploy-prod.sh
chmod +x scripts/docker-deploy-prod.sh

mv scripts/generate-dev-certs.sh.new scripts/generate-dev-certs.sh
chmod +x scripts/generate-dev-certs.sh

# 4. Verification
ls -la .env.docker-example .env.example
ls -la infrastructure/nginx/nginx.prod.conf infrastructure/docker/nginx/nginx.conf
ls -lah scripts/docker-deploy-prod.sh scripts/generate-dev-certs.sh
```

## File Organization After Implementation

```
.
├── .env                              (current active config)
├── .env.example                      (production/ML-focused template)
├── .env.docker-example    ← NEW      (Docker dev template)
│
├── scripts/
│   ├── deploy.sh                     (Kubernetes deployment)
│   ├── docker-deploy-prod.sh    ← NEW (Docker Compose deployment)
│   ├── generate-dev-certs.sh    ← NEW (Certificate generation)
│   └── [other scripts...]
│
└── infrastructure/
    ├── nginx/
    │   └── nginx.prod.conf      ← NEW (Production hardened)
    ├── docker/
    │   └── nginx/nginx.conf          (Dev/Docker config)
    └── [other infrastructure...]
```

## Key Decision Points

### For .env.docker.new
**Question:** Replace .env.example or create new file?
**Answer:** CREATE NEW (.env.docker-example)
**Why:** 
- Different purposes (ML/AI vs Application stack)
- Both templates have value for different setups
- No conflicts, only complementary

### For nginx.prod.conf.new
**Question:** Merge into docker/nginx.conf?
**Answer:** KEEP SEPARATE
**Why:**
- Different environments (prod vs dev)
- Different security/performance requirements
- Clear separation of concerns

### For docker-deploy-prod.sh.new
**Question:** Merge into deploy.sh?
**Answer:** KEEP SEPARATE
**Why:**
- Different deployment methods (Docker Compose vs Kubernetes)
- Both needed in modern projects
- No conflicts

### For generate-dev-certs.sh.new
**Question:** Critical feature?
**Answer:** YES - Add immediately
**Why:**
- Fills setup gap (no existing cert script)
- Essential for development
- No conflicts with existing code

## Risk Level Assessment

| File | Risk | Reason |
|------|------|--------|
| .env.docker-example | ✅ NONE | New file, no conflicts |
| nginx.prod.conf | ✅ NONE | New location, no conflicts |
| docker-deploy-prod.sh | ✅ NONE | New file, complements existing |
| generate-dev-certs.sh | ✅ NONE | New file, fills gap |

**Overall Risk: MINIMAL** - All changes are additive, no existing files modified.

## Validation Checklist

Before considering implementation complete:

### Environment Files
- [ ] .env.docker-example exists and is readable
- [ ] .env.example still intact
- [ ] Both files have proper structure

### Nginx Configuration
- [ ] infrastructure/nginx/nginx.prod.conf exists
- [ ] infrastructure/docker/nginx/nginx.conf untouched
- [ ] No .new files remain

### Deployment Scripts
- [ ] scripts/docker-deploy-prod.sh exists and is executable
- [ ] scripts/deploy.sh untouched
- [ ] --dry-run flag works correctly
- [ ] Cert validation works

### Certificate Script
- [ ] scripts/generate-dev-certs.sh exists and is executable
- [ ] Script runs without errors
- [ ] Creates certs/ directory structure
- [ ] Generates proper certificate files

### Clean Up
- [ ] All .new files removed (or archived)
- [ ] No duplicate configurations
- [ ] Documentation links point to correct files

## Integration with CI/CD

**Recommended additions to CI pipeline:**

```yaml
# Check 1: Validate nginx syntax
- name: Validate nginx config
  run: nginx -t -c infrastructure/nginx/nginx.prod.conf

# Check 2: Verify shell scripts
- name: Check script syntax
  run: |
    bash -n scripts/docker-deploy-prod.sh
    bash -n scripts/generate-dev-certs.sh

# Check 3: Validate environment files
- name: Verify .env structure
  run: |
    grep -E "^[A-Z_]+=" .env.docker-example | wc -l
    grep -E "^[A-Z_]+=" .env.example | wc -l
```

## Documentation Updates

| Document | Update | Priority |
|----------|--------|----------|
| README.md | Add Docker Compose setup section | HIGH |
| SETUP.md | Add .env.docker-example reference | HIGH |
| DEPLOYMENT.md | Document both K8s and Docker paths | HIGH |
| CONTRIBUTING.md | Add cert generation to setup | MEDIUM |
| infrastructure/README | Explain nginx.prod.conf | MEDIUM |

## Migration Path for Existing Teams

1. **Day 1:** Add new files (no impact on current setup)
2. **Day 2:** Update documentation with new options
3. **Gradual:** Teams can migrate to new templates at their own pace
4. **Future:** Phase out old configs if unified approach preferred

