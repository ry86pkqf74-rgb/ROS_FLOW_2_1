# CLAUDE.md - ResearchFlow Production

> Claude Code automatically reads this file. It provides project context, development workflows, and code review guidance.

## Project Overview

**ResearchFlow** is a HIPAA-compliant clinical research platform that transforms clinical data into publication-ready manuscripts using a 20-stage AI-assisted workflow.

| Attribute | Value |
|-----------|-------|
| Phase | Deployment & Integration - Production Ready |
| Completion | ~95% |
| Last Updated | 2026-02-03 |
| GitHub | `https://github.com/ry86pkqf74-rgb/researchflow-production.git` |

## Architecture

### Services (`/services/`)

| Service | Technology | Port | Purpose |
|---------|-----------|------|---------|
| **orchestrator** | Node.js/Express/TypeScript | 3001 | Main API server - auth, RBAC, job queue, AI routing, 124+ endpoints |
| **web** | React/TypeScript/Vite | 5173 (dev) / 80 (prod) | Frontend UI served via Nginx |
| **worker** | Python 3.11+/FastAPI | 8000 | Background processing, 19-stage workflow, Pandera validation, analysis |
| **collab** | Node.js/TypeScript/Yjs | 1234 | Real-time collaboration (WebSocket, CRDT) |

### Packages (`/packages/`)

| Package | Purpose |
|---------|---------|
| **core** | Central types, Drizzle schemas, security utilities, policy engine |
| **ai-router** | AI model routing (OpenAI, Anthropic, Ollama), cost optimization, quality gates |
| **phi-engine** | PHI detection patterns, fail-closed scanning, log scrubbing |
| **manuscript-engine** | Clinical data → IMRaD manuscripts, ICMJE/CONSORT/STROBE/PRISMA compliance |
| **ai-agents** | Agent implementation and coordination |
| **ui** | React component library (Radix UI, Tailwind) |
| **design-tokens** | Design system tokens (colors, spacing, typography) |
| **vector-store** | Vector database and RAG infrastructure (pgvector) |
| **guideline-engine** | Python clinical scoring and staging algorithms |
| **notion-integration** | Notion API integration |
| **cursor-integration** | Cursor IDE integration |
| **cli** | Command-line tools |
| **shared** | Shared utilities |

### Service Boundaries (CRITICAL)

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────┐
│   Frontend  │────▶│   Orchestrator   │────▶│   Worker    │
│  (web)      │     │  (Node.js API)   │     │  (Python)   │
└─────────────┘     └──────────────────┘     └─────────────┘
                           │
                    ┌──────┴──────┐
                    │   Collab    │
                    │  (WebSocket)│
                    └─────────────┘
```

**Forbidden imports:**
- Worker CANNOT import from Orchestrator
- Frontend CANNOT import from Worker
- Cross-service communication via HTTP/message queue only

## Quick Start

### Prerequisites

- Node.js 20+
- Python 3.11+
- Docker & Docker Compose
- PostgreSQL 16+ (or use Docker)

### Development Setup

```bash
# Clone and install
git clone https://github.com/ry86pkqf74-rgb/researchflow-production.git
cd researchflow-production
npm install

# Python dependencies
cd services/worker && pip install -r requirements.txt && cd ../..

# Environment
cp .env.example .env
# Edit .env with local configuration

# Start all services
docker-compose up -d

# Or run individually
npm run dev
```

### Common Commands

```bash
# Development
npm run dev              # Start Docker services
npm run dev:build        # Rebuild and start

# Building
npm run build            # Build packages + services
npm run build:packages   # Only packages
npm run build:services   # Only services

# Code Quality
npm run lint             # ESLint check
npm run lint:fix         # Fix linting issues
npm run format           # Prettier format
npm run typecheck        # TypeScript check

# Database
npm run db:push          # Push schema changes
npm run db:migrate       # Run migrations
npm run db:seed          # Seed database

# Docker
npm run docker:up        # Start containers
npm run docker:down      # Stop containers
npm run docker:rebuild   # Full rebuild
npm run docker:logs      # View logs
```

## Testing

### Test Commands

```bash
npm run test             # Unit + Integration
npm run test:unit        # Vitest unit tests
npm run test:integration # Integration tests
npm run test:e2e         # Playwright E2E
npm run test:a11y        # Accessibility tests
npm run test:visual      # Visual regression
npm run test:coverage    # With coverage report

# Governance Tests (CRITICAL)
npm run test:phi         # PHI scanner tests
npm run test:rbac        # RBAC tests
npm run test:fail-closed # Fail-closed behavior
npm run test:governance  # All governance tests

# Load Testing
npm run test:load        # Full load test
npm run test:load:auth   # Auth endpoints
npm run test:load:peak   # Peak load scenario
npm run test:load:stress # Stress test
```

### Test Coverage Targets

- 80%+ line coverage for critical paths
- 100% coverage for PHI handling code
- All public APIs tested

## Code Review Agent

When asked to "review", "check", or "audit" code, execute this checklist:

### Step 1: HIPAA Compliance (BLOCKING)

Search for PHI violations:

```bash
# PHI in logs
rg -n "(console|logger)\.(log|error|warn).*\b(patient|ssn|dob|mrn|name|diagnosis)\b" --type ts --type py

# PHI in template literals
rg -n "(console|logger)\.\w+\(.*\$\{" --type ts

# Unprotected PHI fields
rg -n "(patient_name|social_security|date_of_birth|medical_record)" --type ts --type py
```

**Flag as BLOCKING if found.** PHI must:
- Go through `packages/phi-engine` before external APIs
- Never appear in logs or error messages
- Have audit trail via `auditLog.record()`

### Step 2: Security (BLOCKING)

```bash
# SQL injection
rg -n "(query|execute)\s*\(.*\$\{" --type ts --type py

# Hardcoded secrets
rg -n "(api_key|password|secret|token)\s*[=:]\s*['\"][^'\"]{8,}" --type ts --type py

# eval usage
rg -n "\beval\s*\(" --type ts --type py
```

### Step 3: Architecture Violations (BLOCKING)

```bash
# Worker importing orchestrator (forbidden)
rg -n "from.*services/orchestrator" services/worker/

# Frontend importing worker (forbidden)
rg -n "from.*services/worker" services/web/
```

### Step 4: TypeScript Standards (WARNING)

```bash
# Any types
rg -n ":\s*any\b" --type ts

# Missing async error handling
rg -n "await.*\);$" --type ts
```

**Required patterns:**
```typescript
// Zod validation on endpoints
export const handler = async (
  req: ValidatedRequest<CreateJobSchema>,
  res: Response
): Promise<void> => {
  await requirePermission(req.user, 'jobs:create');
  await auditLog.record({ action: 'job.create', userId: req.user.id });
  // ...
};
```

### Step 5: Python Standards (WARNING)

```bash
# Print statements (use structlog)
rg -n "^\s*print\s*\(" --type py

# Missing type hints
rg -n "def \w+\([^)]*\)\s*:" --type py
```

**Required patterns:**
```python
def process_data(df: pd.DataFrame, config: ProcessConfig) -> ProcessResult:
    """Process research data.

    Args:
        df: Input DataFrame
        config: Processing configuration

    Returns:
        ProcessResult with validated data

    Raises:
        ValidationError: If validation fails
    """
    validated = DataSchema.validate(df)
    logger.info("processed_data", rows=len(df))
    return ProcessResult(data=validated)
```

### Step 6: React Standards (SUGGESTION)

- Components under 200 lines
- Custom hooks for data fetching
- Error boundaries for async operations
- ARIA labels for accessibility

### Review Output Format

```markdown
## Code Review: [file/directory]

### BLOCKING Issues
1. [HIPAA] Description - `file:line`
2. [Security] Description - `file:line`

### Warnings
1. [Standards] Description - `file:line`

### Suggestions
1. Improvement idea

### Good Patterns Observed
- What's working well

**Verdict**: REQUEST_CHANGES / APPROVE_WITH_COMMENTS / APPROVE
```

## PHI Safety (CRITICAL)

### Non-Negotiable Rules

1. **Fail-Closed**: If PHI detection fails or is uncertain, BLOCK the operation
2. **No Raw PHI**: Never return raw PHI values; only return locations, hashes, or categories
3. **DEMO Mode**: Must work completely offline using fixtures only
4. **Audit Trail**: All operations must be logged (without PHI content)

### PHI Patterns to Detect

- Patient names, SSNs, dates of birth
- Medical record numbers (MRN)
- Diagnosis codes and descriptions
- Treatment details
- Contact information

### PHI Checklist for Changes

- [ ] No hardcoded PHI/PII in code or tests
- [ ] PHI scanner passes on all new code
- [ ] DEMO mode tested offline
- [ ] Error messages don't leak PHI
- [ ] Logs sanitized (no PHI in log output)
- [ ] API responses checked for PHI exposure

## Governance Modes

| Mode | Description |
|------|-------------|
| `LIVE` | Full AI execution with approval gates |
| `DEMO` | Fixtures only, works offline |
| `STANDBY` | User review before AI execution |

## Key Technologies

### Core Stack

| Technology | Version | Purpose |
|------------|---------|---------|
| Node.js | 20+ | Runtime |
| TypeScript | 5.6.3 | Type safety |
| React | 18.3.1 | Frontend UI |
| Express | 4.21.1 | API framework |
| FastAPI | Latest | Python API |
| PostgreSQL | 16+ | Database |
| Drizzle ORM | 0.39.3 | Database ORM |
| Zod | 3.25.76 | Schema validation |

### AI Integrations

| Package | Version | Purpose |
|---------|---------|---------|
| @anthropic-ai/sdk | 0.39.0 | Claude API |
| openai | 4.76.0 | OpenAI API |
| Ollama | - | Local LLM |

### Frontend

| Technology | Purpose |
|------------|---------|
| Vite | Build tool |
| Tailwind CSS | Styling |
| Radix UI | Headless components |
| Zustand | State management |
| React Query | Data fetching |
| Yjs | CRDT collaboration |
| Framer Motion | Animations |

### Testing

| Tool | Purpose |
|------|---------|
| Vitest | Unit/Integration tests |
| Playwright | E2E tests |
| Axe Core | Accessibility |
| K6 | Load testing |

## Docker Compose Variants

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Development (default) |
| `docker-compose.prod.yml` | Production |
| `docker-compose.test.yml` | Testing |
| `docker-compose.hipaa.yml` | HIPAA-compliant config |
| `docker-compose.ai.yml` | AI services |
| `docker-compose.ollama.yml` | Local LLM |
| `docker-compose.monitoring.yml` | Observability stack |
| `docker-compose.minimal.yml` | Minimal services |

## Directory Structure

```
researchflow-production/
├── services/
│   ├── orchestrator/     # Node.js API (Express)
│   ├── web/              # React frontend (Vite)
│   ├── worker/           # Python backend (FastAPI)
│   └── collab/           # Real-time collaboration (Yjs)
├── packages/
│   ├── core/             # Shared types, schemas, security
│   ├── ai-router/        # AI model routing
│   ├── phi-engine/       # PHI detection
│   ├── manuscript-engine/# Manuscript generation
│   ├── ui/               # React components
│   └── ...               # Other packages
├── tests/
│   ├── unit/             # Unit tests
│   ├── integration/      # Integration tests
│   ├── e2e/              # End-to-end tests
│   ├── governance/       # PHI, RBAC, fail-closed tests
│   └── load/             # K6 load tests
├── scripts/              # Build and deploy scripts
├── infrastructure/       # Docker, K8s configs
├── monitoring/           # Dashboards, alerts
├── migrations/           # Database migrations
├── docs/                 # Documentation
└── helm/                 # Kubernetes Helm charts
```

## Git Conventions

### Branch Naming

- `feature/short-description` - New features
- `fix/short-description` - Bug fixes
- `docs/short-description` - Documentation
- `refactor/short-description` - Refactoring
- `test/short-description` - Test updates

### Commit Messages

Follow conventional commits:
```
type(scope): short description

Longer description if needed.

Closes #123
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `perf`

### PR Requirements

- Under 2500 lines of code
- PHI safety checklist completed
- Tests pass (`npm test && npm run test:phi`)
- At least one maintainer approval

## Auto-Fix Suggestions

When finding issues, suggest fixes:

**PHI in logs → Fix:**
```typescript
// Before (bad)
console.log(`Processing patient ${patientName}`);

// After (good)
logger.info('processing_patient', { patientId: patient.id }); // ID only
```

**SQL injection → Fix:**
```typescript
// Before (bad)
await db.query(`SELECT * FROM users WHERE id = ${userId}`);

// After (good)
await db.query('SELECT * FROM users WHERE id = $1', [userId]);
```

**Missing validation → Fix:**
```typescript
// Before (bad)
const { data } = req.body;

// After (good)
const validated = CreateJobSchema.parse(req.body);
```

## Active Tasks

- [x] Route registration (34 routes active)
- [x] Docker health checks (6/6 services)
- [x] Security hardening (credentials, logging, ports)
- [x] HTTPS configuration (TLS 1.2/1.3)
- [x] API endpoint test script
- [x] 20-stage workflow implementation
- [ ] End-to-end UI testing
- [ ] Load testing validation
- [ ] API documentation (OpenAPI/Swagger)

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| Governance-first | No autonomous AI execution from CI |
| IMRaD structure | Standard academic manuscript format |
| Synthetic data | Until PHI approval obtained |
| Fail-closed PHI | Block on detection failure |
| HIPAA compliance | Required for clinical data |

## Quick Review Commands

```bash
# Full review
review services/orchestrator/src/routes/

# HIPAA focus
review --focus hipaa packages/phi-engine/

# Security focus
review --focus security services/

# Single file
review services/worker/src/analysis/validator.py
```

## Session Notes

- 2026-02-03: Updated CLAUDE.md with comprehensive codebase documentation
- 2026-02-02: All 20 stage workers complete, LangChain pinned, pnpm workspace configured
- 2026-01-22: Deployment review complete, HTTPS enabled, health checks operational
