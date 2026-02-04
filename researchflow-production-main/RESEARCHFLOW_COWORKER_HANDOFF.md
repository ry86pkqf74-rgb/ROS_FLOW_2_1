# ResearchFlow Integration - Coworker Handoff Document
## For New Claude Cowork Sessions
### Last Updated: February 2, 2026

---

## 🎯 PROJECT OVERVIEW

**Project:** ResearchFlow Production - A 20-stage clinical research workflow platform
**Goal:** Complete integration of manuscript generation, PHI compliance, governance modes, and testing infrastructure
**Method:** Parallel execution using **Composio** (backend/Python) and **Cursor** (frontend/TypeScript) agents

---

## 📍 CRITICAL LOCATIONS

### Local Repository
```
/Users/lhglosser/researchflow-production
```

### GitHub Repository
```
Owner: ry86pkqf74-rgb
Repo: researchflow-production
Branch: main (all work committed directly to main)
URL: https://github.com/ry86pkqf74-rgb/researchflow-production
```

### Key Directories
```
services/
├── orchestrator/          # Node.js/Express - Workflow, Governance, Stage APIs
│   ├── routes.ts          # Main routes (workflow stages, execution)
│   ├── src/routes/        # Modular routes (workflows.ts, governance.ts, etc.)
│   └── src/services/      # Business logic
├── worker/                # Python/FastAPI - AI/ML, Manuscript, PHI
│   ├── src/api/routes/    # API endpoints (manuscript_generate.py, phi_scan.py)
│   ├── src/generators/    # Manuscript generators (abstract, methods, results, discussion, imrad_assembler)
│   └── src/phi/           # PHI scanning (patterns/, redaction/, scanner/)
└── web/                   # React/TypeScript - Frontend UI
    ├── src/components/    # UI components (manuscript/, compliance/, common/)
    ├── src/hooks/         # Custom hooks (useManuscriptGeneration, usePHIGate)
    └── src/pages/         # Page components (ComplianceDashboard)

tests/
├── e2e/                   # Playwright E2E tests
│   ├── fixtures/          # TestUser, TestProject
│   ├── helpers/           # Navigation, assertions
│   └── accessibility/     # WCAG compliance tests (pending)
├── integration/           # API integration tests (pending)
│   └── api/               # test_workflow_api.py, test_manuscript_api.py, etc.
├── unit/                  # Unit tests
│   └── phi/               # PHI scanner tests
└── perf/                  # Performance tests
    └── k6/                # Load testing scripts
```

---

## 🔧 TOOLS & HOW TO USE THEM

### 1. Control My Mac (osascript)
**Purpose:** Execute shell commands on user's local machine
**Use for:** Git operations, file verification, searching

```
Tool: mcp__Control_your_Mac__osascript
Parameter: script (AppleScript with do shell script)

Example - Check git status:
do shell script "cd /Users/lhglosser/researchflow-production && git status"

Example - Fetch and view commits:
do shell script "cd /Users/lhglosser/researchflow-production && git fetch origin && git log origin/main --oneline -5"

Example - Push commits:
do shell script "cd /Users/lhglosser/researchflow-production && git push origin main"

Example - Rebase and push (when branches diverge):
do shell script "cd /Users/lhglosser/researchflow-production && git pull --rebase origin main && git push origin main"
```

### 2. Claude in Chrome (Browser Automation)
**Purpose:** View Composio logs, interact with web interfaces
**Use for:** Monitoring Composio progress, checking GitHub

```
Key Tools:
- mcp__Claude_in_Chrome__tabs_context_mcp - Get available browser tabs
- mcp__Claude_in_Chrome__computer (action: screenshot) - Take screenshot
- mcp__Claude_in_Chrome__computer (action: left_click) - Click elements
- mcp__Claude_in_Chrome__computer (action: scroll) - Scroll page

Example - Get tabs:
mcp__Claude_in_Chrome__tabs_context_mcp with createIfEmpty: false

Example - Screenshot Composio:
mcp__Claude_in_Chrome__computer with action: "screenshot", tabId: <composio_tab_id>

Example - Scroll:
mcp__Claude_in_Chrome__computer with action: "scroll", coordinate: [x, y], scroll_direction: "down", scroll_amount: 3, tabId: <id>
```

### 3. Desktop Commander
**Purpose:** Alternative file/command execution
**Use for:** Searching files, reading content, process management

```
Key Tools:
- mcp__Desktop_Commander__start_search - Search for files
- mcp__Desktop_Commander__read_file - Read file contents
- mcp__Desktop_Commander__list_directory - List directory contents
```

---

## 🤖 AGENT WORKFLOW

### Composio (Backend Agent)
**Platform:** https://platform.composio.dev
**Workspace:** logan.glosser_workspace / logan.glosser_workspace_first_project
**Capabilities:**
- GitHub file creation/modification
- Code execution in sandbox
- Multi-file commits

**How to monitor:**
1. Use Chrome tools to view Composio Platform tab
2. Check "Logs" panel for GITHUB_CREATE_OR_UPDATE_FILE_CONTENTS calls
3. Look for spinners indicating active work
4. Verify commits with git fetch + git log

**Common Composio states:**
- Green checkmarks (✓) = Completed actions
- Yellow/Orange icons = In progress
- Spinning loader = Active task

### Cursor (Frontend Agent)
**Platform:** Local IDE (Cursor editor)
**Capabilities:**
- TypeScript/React development
- Local file editing
- Git operations (may need manual push)

**Important:** Cursor commits locally but sometimes fails to push due to credential issues. Always verify with:
```
git log main --oneline -3        # Local commits
git log origin/main --oneline -3 # Remote commits
```

If local is ahead of origin, push manually:
```
git push origin main
```

If branches diverge (Composio pushed while Cursor was working):
```
git pull --rebase origin main
git push origin main
```

---

## 📋 PROMPT TEMPLATE

### Standard Composio Prompt Structure:
```
REPOSITORY: ry86pkqf74-rgb/researchflow-production
BRANCH: main (commit directly)

## TASK: [Clear task description]

### CONTEXT
[Background information and what exists already]

### REQUIREMENTS
1. Create `path/to/file.py`:
   - Feature 1
   - Feature 2

2. Create `path/to/another_file.py`:
   - Feature 1
   - Feature 2

### FILE STRUCTURE
[Show expected directory layout]

### TECHNICAL SPECS
- [Technical requirements]
- [Dependencies]
- [Integration points]

### GIT REQUIREMENTS
After completing:
1. Stage: git add [paths]
2. Commit: git commit -m "[type](scope): [description]

- [Bullet point 1]
- [Bullet point 2]

Co-Authored-By: Composio <composio@anthropic.com>"
3. Push: git push origin main
4. VERIFY: git log origin/main --oneline -1
```

### Standard Cursor Prompt Structure:
```
REPOSITORY: researchflow-production (local)
BRANCH: main (commit directly)

## TASK: [Clear task description]

### CONTEXT
[Background information]

### REQUIREMENTS
1. Create `path/to/Component.tsx`:
   - Feature 1
   - Feature 2

### TECHNICAL SPECS
- [React/TypeScript requirements]
- [UI/UX requirements]

### GIT REQUIREMENTS
After completing:
1. Stage: git add [paths]
2. Commit: git commit -m "[type](scope): [description]

Co-Authored-By: Cursor <cursor@anthropic.com>"
3. Push: git push origin main
4. VERIFY: git log origin/main --oneline -1
```

---

## ✅ COMPLETED WORK (as of Feb 2, 2026)

### Phase 1: Foundation
| Task | Agent | Commit | Status |
|------|-------|--------|--------|
| docker-compose.test.yml | Composio | 2d2a44c | ✅ |
| E2E Test Infrastructure | Cursor | c0eb6e5 | ✅ |

### Phase 2: Manuscript Engine
| Task | Agent | Commit | Status |
|------|-------|--------|--------|
| Abstract Generator | Composio | 09caf2d | ✅ |
| Manuscript Editor Integration | Cursor | 9bd8d4f | ✅ |
| Methods Generator | Composio | a0c2944 | ✅ |
| PHI Gates in Stages | Cursor | e01e908 | ✅ |
| Results Generator | Composio | d4ee214 | ✅ |
| Compliance Dashboard | Cursor | 1775b7b | ✅ |
| Discussion Generator | Composio | cbb4c22 | ✅ |
| Full Workflow E2E Tests | Cursor | 0208982 | ✅ |
| IMRaD Assembler | Composio | 5e2e729 | ✅ |
| Manuscript Export UI | Cursor | 2223c74 | ✅ |

### Phase 3: PHI & Performance
| Task | Agent | Commits | Status |
|------|-------|---------|--------|
| PHI Scanner Enhancement | Composio | 14 commits | ✅ |
| PHI Custom Patterns + Tests | Composio | a2b44d0 | ✅ |
| Load Testing (k6) | Cursor | 27688fa | ✅ |

### Phase 4: Final Testing (IN PROGRESS)
| Task | Agent | Status |
|------|-------|--------|
| API Integration Tests | Composio | 🔄 In Progress |
| Accessibility Tests | Cursor | ⏳ Pending |

---

## 🔄 PENDING TASKS

### COMPOSIO - API Integration Tests
**Files to create:**
```
tests/integration/
├── api/
│   ├── test_workflow_api.py      # Workflow/stage endpoints
│   ├── test_manuscript_api.py    # Manuscript generation
│   ├── test_phi_api.py           # PHI scanning
│   ├── test_governance_api.py    # Governance modes
│   └── test_compliance_api.py    # Compliance checklists
├── conftest.py                   # Shared fixtures
└── utils/
    ├── api_client.py             # HTTP clients
    └── factories.py              # Test data factories
```

**Key API Architecture:**
- Orchestrator (Node.js): http://localhost:3001 - Workflow, Governance
- Worker (Python): http://localhost:8000 - Manuscript, PHI

### CURSOR - Accessibility Tests
**Files to create:**
```
tests/e2e/accessibility/
├── axe-core.spec.ts              # Automated a11y scans
├── keyboard-navigation.spec.ts   # Tab/focus testing
├── screen-reader.spec.ts         # ARIA/landmarks
├── color-contrast.spec.ts        # Contrast ratios
├── motion-and-timing.spec.ts     # Reduced motion
├── forms.spec.ts                 # Form accessibility
└── helpers/
    ├── a11y-matchers.ts
    └── focus-helpers.ts
```

---

## 🔍 VERIFICATION WORKFLOW

### After Each Phase Completion:

1. **Check Composio status** (if applicable):
```
# Take screenshot of Composio Platform tab
mcp__Claude_in_Chrome__computer action: "screenshot", tabId: <composio_tab>
```

2. **Fetch latest from GitHub:**
```
do shell script "cd /Users/lhglosser/researchflow-production && git fetch origin && git log origin/main --oneline -5"
```

3. **Check local vs remote:**
```
do shell script "cd /Users/lhglosser/researchflow-production && echo 'LOCAL:' && git log main --oneline -3 && echo 'REMOTE:' && git log origin/main --oneline -3"
```

4. **If branches diverged:**
```
do shell script "cd /Users/lhglosser/researchflow-production && git pull --rebase origin main && git push origin main"
```

5. **Verify files exist:**
```
do shell script "cd /Users/lhglosser/researchflow-production && find <path> -name '*.py' | sort"
```

---

## 🚨 COMMON ISSUES & SOLUTIONS

### Issue: Cursor commit not on remote
**Symptom:** Local has commits that origin doesn't
**Solution:**
```
do shell script "cd /Users/lhglosser/researchflow-production && git push origin main"
```

### Issue: Branches diverged
**Symptom:** "Your branch and 'origin/main' have diverged"
**Solution:**
```
do shell script "cd /Users/lhglosser/researchflow-production && git pull --rebase origin main && git push origin main"
```

### Issue: Composio appears stuck
**Action:**
1. Screenshot the Composio tab
2. Check if there's a spinner (still working) or error
3. Check logs panel for recent activity
4. Verify if commits are appearing on GitHub

### Issue: Files not found after Composio "completes"
**Cause:** Composio works in cloud sandbox, files may not be on local
**Solution:**
```
do shell script "cd /Users/lhglosser/researchflow-production && git fetch origin && git pull origin main"
```

---

## 📊 PROJECT METRICS

| Metric | Value |
|--------|-------|
| Total Phases | 4 |
| Phases Complete | 3 |
| Total Commits | 25+ |
| Composio Commits | 18+ |
| Cursor Commits | 7+ |
| Python Files Created | 30+ |
| TypeScript Files Created | 25+ |
| Test Files Created | 20+ |

---

## 📝 MASTER PLAN DOCUMENT

Full integration plan with all prompts:
```
/sessions/zen-vibrant-gauss/mnt/Documents/RESEARCHFLOW_INTEGRATION_PARALLEL_EXECUTION.md
```

---

## 🎯 QUICK START FOR NEW SESSION

1. **Read this document** for context

2. **Check current status:**
```
do shell script "cd /Users/lhglosser/researchflow-production && git fetch origin && git log origin/main --oneline -10"
```

3. **Get browser context:**
```
mcp__Claude_in_Chrome__tabs_context_mcp with createIfEmpty: false
```

4. **Review pending tasks** in the PENDING TASKS section above

5. **Create prompts** using the templates provided

6. **Execute in parallel:**
   - Give Composio prompt via Composio Platform
   - Give Cursor prompt via Cursor IDE

7. **Verify and push** using the verification workflow

---

## 📞 KEY CONTACTS

- **User:** Logan (logan.glosser@gmail.com)
- **GitHub Owner:** ry86pkqf74-rgb

---

*Document Version 1.0 - February 2, 2026*
*For use in Claude Cowork sessions*
