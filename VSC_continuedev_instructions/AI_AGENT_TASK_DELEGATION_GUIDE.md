# 🤖 AI Agent Task Delegation Guide for Continue.dev
**Project**: ResearchFlow Production  
**Version**: 2.0  
**Last Updated**: February 4, 2026  
**Status**: ✅ Continue.dev Configured & Ready

---

## 📋 Table of Contents
1. [Quick Start](#quick-start)
2. [Model Selection Guide](#model-selection-guide)
3. [Task Delegation Framework](#task-delegation-framework)
4. [Agent Assignments](#agent-assignments)
5. [Example Workflows](#example-workflows)
6. [Custom Commands](#custom-commands)
7. [Best Practices](#best-practices)

---

## 🚀 Quick Start

### Access Continue.dev in VSCode
```bash
# Open Continue Chat
Cmd+L

# Inline Edit Mode
Cmd+I

# Tab Autocomplete
Just start typing (Codestral auto-activates)
```

### Select Your Model
In the Continue.dev chat, click the model dropdown to choose from:
- **Claude Opus 4.5** - Architecture, security, complex analysis
- **Claude Sonnet 4.5** - General coding, debugging
- **GPT-4o** - API design, documentation
- **GPT-4o Mini** - Quick tasks, simple edits
- **Codestral** - Fast code generation
- **Gemini 2.5 Flash** - Vision tasks, diagrams
- **Mercury Coder** - Rapid prototyping
- **Grok** - Experimental approaches

---

## 🎯 Model Selection Guide

### By Task Type

| Task Type | Best Model | Context Length | Speed | Use Case |
|-----------|-----------|----------------|-------|----------|
| **Security Review** | Claude Opus 4.5 | 16K | Slow | HIPAA, auth, encryption |
| **Code Generation** | Claude Sonnet 4.5 | 16K | Medium | New features, refactoring |
| **Quick Fixes** | Codestral | 16K | Fast | Bug fixes, small changes |
| **API Design** | GPT-4o | 16K | Medium | REST endpoints, schemas |
| **Documentation** | GPT-4o | 16K | Medium | READMEs, comments, guides |
| **Simple Tasks** | GPT-4o Mini | 16K | Fast | Formatting, simple edits |
| **Rapid Prototyping** | Mercury Coder | 8K | Very Fast | POCs, experiments |
| **Alternative Ideas** | Grok | 16K | Medium | Edge cases, new approaches |
| **Image Analysis** | Gemini 2.5 Flash | 16K | Fast | Diagrams, screenshots |
| **Instant Edits** | Relace Instant Apply | 8K | Ultra Fast | One-line fixes |
| **Refactoring** | Morph v2 | 8K | Fast | Code restructuring |

### By Project Area

#### 🔐 Security & HIPAA Compliance
```
Primary: Claude Opus 4.5
Backup: Claude Sonnet 4.5
Commands: /phi-check, /rbac-audit
```

#### 🏗️ Architecture & Design
```
Primary: Claude Opus 4.5
Backup: GPT-4o
Context: @codebase for full understanding
```

#### 💻 Backend Development (Node.js/Python)
```
Primary: Claude Sonnet 4.5
Secondary: Codestral (for speed)
Commands: /test-route
```

#### 🎨 Frontend Development (React)
```
Primary: Claude Sonnet 4.5
Secondary: GPT-4o Mini (simple components)
Tab Complete: Codestral
```

#### 🐳 DevOps & Docker
```
Primary: Claude Sonnet 4.5
Backup: GPT-4o
Commands: /docker-check
```

#### 🧪 Testing & QA
```
Primary: Claude Sonnet 4.5
Rapid: Codestral
Commands: /test-route
```

---

## 🎭 Task Delegation Framework

### Task Priority Matrix

| Priority | Model | Response Time | Cost | Best For |
|----------|-------|---------------|------|----------|
| **CRITICAL** | Claude Opus 4.5 | Slowest | Highest | Security, architecture |
| **HIGH** | Claude Sonnet 4.5 | Medium | Medium | Feature development |
| **MEDIUM** | Codestral/GPT-4o | Fast | Low-Medium | Routine tasks |
| **LOW** | GPT-4o Mini/Mercury | Fastest | Lowest | Simple edits |

### Parallel Task Execution

When you have **independent tasks**, delegate to **different models simultaneously**:

```markdown
Example: Feature Implementation

1. Architecture Review → Claude Opus 4.5
2. Code Implementation → Claude Sonnet 4.5  
3. Test Generation → Codestral
4. Documentation → GPT-4o
```

---

## 📊 Agent Assignments

### 🔐 AGENT 1: Security & Compliance Specialist
**Model**: Claude Opus 4.5  
**Trigger**: Auth, encryption, PHI, user input validation

**Responsibilities**:
- Review authentication flows
- Audit PHI compliance (HIPAA)
- Check encryption implementation
- Validate RBAC/access control
- Security pattern review

**Example Prompts**:
```
"Review this authentication middleware for security vulnerabilities"
"/phi-check this patient data handling code"
"Audit this API endpoint for RBAC compliance"
```

**Deliverables**:
- Security audit reports
- Vulnerability assessments
- Remediation recommendations
- Code fixes with explanations

---

### 💻 AGENT 2: Full-Stack Developer
**Model**: Claude Sonnet 4.5  
**Trigger**: Feature development, debugging, refactoring

**Responsibilities**:
- Implement new features
- Debug complex issues
- Refactor existing code
- Integrate services
- Write middleware/utilities

**Example Prompts**:
```
"Implement a REST endpoint for protocol generation"
"Debug why the auth flow isn't setting LIVE mode"
"Refactor this component to use React hooks"
"/test-route for this Express endpoint"
```

**Deliverables**:
- Working feature implementations
- Bug fixes with explanations
- Refactored code
- Integration solutions

---

### ⚡ AGENT 3: Rapid Code Generator
**Model**: Codestral or Mercury Coder  
**Trigger**: Boilerplate, repetitive tasks, quick fixes

**Responsibilities**:
- Generate boilerplate code
- Create test files
- Quick bug fixes
- Template generation
- Repetitive patterns

**Example Prompts**:
```
"Generate Jest tests for all these API routes"
"Create RBAC middleware for these endpoints"
"Generate TypeScript interfaces from this schema"
"Quick fix: add null checks to these functions"
```

**Deliverables**:
- Boilerplate code
- Test suites
- Quick fixes
- Code templates

---

### 📚 AGENT 4: Documentation Specialist
**Model**: GPT-4o  
**Trigger**: Documentation, comments, READMEs

**Responsibilities**:
- Write technical documentation
- Generate API documentation
- Create README files
- Add code comments
- Write deployment guides

**Example Prompts**:
```
"Generate API documentation for these endpoints"
"Write a comprehensive README for this service"
"Add JSDoc comments to these functions"
"Create a deployment guide for this Docker setup"
```

**Deliverables**:
- API documentation
- README files
- Code comments
- User guides

---

### 🔬 AGENT 5: Test Engineer
**Model**: Codestral + Claude Sonnet 4.5  
**Trigger**: Testing, coverage, validation

**Responsibilities**:
- Write unit tests
- Create integration tests
- E2E test scenarios
- Coverage analysis
- Test fixture generation

**Example Prompts**:
```
"Generate unit tests with >80% coverage for this module"
"Create Playwright E2E tests for the auth flow"
"Write integration tests for the protocol API"
"/test-route for all CRUD operations"
```

**Deliverables**:
- Test suites
- Test coverage reports
- Fixtures and mocks
- Test documentation

---

### 🐳 AGENT 6: DevOps Engineer
**Model**: Claude Sonnet 4.5 + GPT-4o  
**Trigger**: Docker, CI/CD, deployment, monitoring

**Responsibilities**:
- Docker configuration
- CI/CD pipeline setup
- Deployment scripts
- Monitoring setup
- Infrastructure as code

**Example Prompts**:
```
"/docker-check this docker-compose.yml"
"Create a GitHub Actions workflow for deployment"
"Set up health check endpoints for all services"
"Generate Kubernetes manifests for this app"
```

**Deliverables**:
- Docker configurations
- CI/CD pipelines
- Deployment scripts
- Monitoring configs

---

### 🔍 AGENT 7: Code Reviewer
**Model**: Claude Opus 4.5  
**Trigger**: PR reviews, code quality, best practices

**Responsibilities**:
- Code review
- Best practices enforcement
- Performance analysis
- Architecture review
- Quality assurance

**Example Prompts**:
```
"Review this PR for code quality and best practices"
"Analyze performance bottlenecks in this function"
"Check this code for TypeScript best practices"
"Review architecture decisions in this module"
```

**Deliverables**:
- Code review comments
- Improvement suggestions
- Architecture recommendations
- Performance insights

---

## 🎬 Example Workflows

### Workflow 1: New Feature Implementation

```markdown
**Task**: Add PDF export feature to protocols

**Step 1** - Architecture (Claude Opus 4.5)
Prompt: "Design the architecture for PDF export feature including API endpoints, 
services, and error handling"

**Step 2** - Implementation (Claude Sonnet 4.5)  
Prompt: "Implement the PDF export service with the following requirements..."

**Step 3** - Tests (Codestral)
Prompt: "/test-route for the PDF export endpoints"

**Step 4** - Security Review (Claude Opus 4.5)
Prompt: "/phi-check the PDF export code for PHI leakage"

**Step 5** - Documentation (GPT-4o)
Prompt: "Document the PDF export API endpoints and usage"
```

---

### Workflow 2: Bug Fix

```markdown
**Task**: Auth flow not setting LIVE mode after login

**Step 1** - Investigation (Claude Sonnet 4.5)
Prompt: "@codebase Why doesn't login set mode to LIVE? Check mode-store.ts"

**Step 2** - Fix (Claude Sonnet 4.5 or Codestral)
Prompt: "Fix the mode switching in the auth flow"

**Step 3** - Test (Codestral)
Prompt: "Create Playwright test to verify mode changes on login"

**Step 4** - Verification (Claude Sonnet 4.5)
Prompt: "Review the fix and ensure no side effects"
```

---

### Workflow 3: Security Audit

```markdown
**Task**: HIPAA compliance audit for patient data handling

**Step 1** - PHI Detection (Claude Opus 4.5)
Prompt: "/phi-check all patient data handling code in services/worker/"

**Step 2** - Encryption Review (Claude Opus 4.5)
Prompt: "Audit encryption implementation for patient data at rest and in transit"

**Step 3** - Access Control (Claude Opus 4.5)
Prompt: "/rbac-audit all endpoints that handle patient data"

**Step 4** - Logging Review (Claude Opus 4.5)
Prompt: "Check all logging statements for potential PHI leakage"

**Step 5** - Report (GPT-4o)
Prompt: "Generate a HIPAA compliance audit report based on findings"
```

---

### Workflow 4: Docker Deployment

```markdown
**Task**: Prepare services for production deployment

**Step 1** - Config Review (Claude Sonnet 4.5)
Prompt: "/docker-check docker-compose.prod.yml for production readiness"

**Step 2** - Security Hardening (Claude Opus 4.5)
Prompt: "Review Docker configs for security best practices"

**Step 3** - Health Checks (Codestral)
Prompt: "Generate health check endpoints for all services"

**Step 4** - Monitoring (GPT-4o)
Prompt: "Set up Prometheus metrics and Grafana dashboards"

**Step 5** - Documentation (GPT-4o)
Prompt: "Create deployment guide with runbook"
```

---

### Workflow 5: Performance Optimization

```markdown
**Task**: Optimize slow API endpoint

**Step 1** - Analysis (Claude Sonnet 4.5)
Prompt: "@codebase Analyze performance bottlenecks in /api/protocols/generate"

**Step 2** - Alternative Approach (Grok)
Prompt: "Suggest alternative approaches to improve performance 10x"

**Step 3** - Implementation (Claude Sonnet 4.5)
Prompt: "Implement caching layer for protocol generation"

**Step 4** - Benchmarking (Codestral)
Prompt: "Generate performance benchmark tests"

**Step 5** - Validation (Claude Sonnet 4.5)
Prompt: "Verify performance improvements and check for regressions"
```

---

## 🛠️ Custom Commands

### Built-in Slash Commands

```bash
# Security & Compliance
/phi-check                 # Check code for PHI exposure
/rbac-audit               # Audit RBAC implementation

# Development
/test-route               # Generate route tests
/docker-check             # Verify Docker configuration

# Context
@codebase                 # Search entire codebase
@terminal                 # Include terminal output
@git                      # Include git history
```

### Custom Workflow Commands

Create your own prompts:

```markdown
**Backend API Template**
"Create a new Express endpoint with:
- TypeScript types
- Input validation (Zod)
- RBAC middleware
- Error handling
- PHI compliance
- Jest tests
- API documentation"

**React Component Template**  
"Create a React component with:
- TypeScript + strict mode
- Functional component + hooks
- Zustand for state
- TailwindCSS styling
- Unit tests (Vitest)
- Storybook story"

**Database Migration Template**
"Create a database migration with:
- Prisma schema
- Up/down migrations
- Seed data
- Test fixtures
- Rollback strategy"
```

---

## 📚 Best Practices

### 1. Model Selection Strategy

```markdown
✅ DO:
- Use Claude Opus for security-critical code
- Use Codestral for repetitive tasks
- Use GPT-4o Mini for simple formatting
- Delegate independent tasks in parallel

❌ DON'T:
- Use expensive models for simple tasks
- Use fast models for security reviews
- Try to do everything with one model
- Run slow models for every small change
```

### 2. Context Management

```markdown
✅ DO:
- Use @codebase for architectural questions
- Provide specific file paths when known
- Include relevant error messages
- Reference related code sections

❌ DON'T:
- Ask vague questions without context
- Expect models to guess file locations
- Provide entire codebases unnecessarily
- Forget to mention tech stack
```

### 3. Prompt Engineering

```markdown
✅ DO:
- Be specific and detailed
- Break complex tasks into steps
- Provide examples of desired output
- Specify constraints and requirements

❌ DON'T:
- Use vague descriptions
- Combine unrelated tasks
- Forget to mention edge cases
- Skip error handling requirements
```

### 4. Quality Assurance

```markdown
✅ DO:
- Review all generated code
- Run tests before committing
- Use multiple models for validation
- Document model decisions

❌ DON'T:
- Trust code blindly
- Skip security reviews
- Ignore warnings/suggestions
- Commit without testing
```

### 5. Efficiency Tips

```markdown
✅ DO:
- Use tab autocomplete for boilerplate
- Leverage model specializations
- Run independent tasks in parallel
- Cache common patterns

❌ DON'T:
- Re-generate identical code
- Use slow models for autocomplete
- Do tasks sequentially when parallel is possible
- Forget to save successful prompts
```

---

## 🎯 Task Priority Framework

### CRITICAL (Claude Opus 4.5)
- Security vulnerabilities
- Data breaches/PHI leaks
- Authentication bypasses
- Production outages
- Architecture decisions

### HIGH (Claude Sonnet 4.5)
- Feature implementation
- Bug fixes
- API development
- Database migrations
- Integration work

### MEDIUM (Codestral/GPT-4o)
- Test generation
- Code refactoring
- Documentation
- Performance optimization
- DevOps tasks

### LOW (GPT-4o Mini/Mercury)
- Formatting
- Simple edits
- Boilerplate generation
- Quick fixes
- Template creation

---

## 📊 Success Metrics

### Model Performance Tracking

Track which models work best for your use cases:

```markdown
**Security Reviews**
- Claude Opus 4.5: 95% accuracy, 10min avg
- Claude Sonnet 4.5: 85% accuracy, 5min avg

**Code Generation**
- Claude Sonnet 4.5: 90% usable, 3min avg
- Codestral: 80% usable, 30sec avg
- Mercury: 70% usable, 10sec avg

**Documentation**
- GPT-4o: 95% quality, 2min avg
- Claude Sonnet: 90% quality, 3min avg
```

### Quality Gates

Before committing generated code:

- [ ] Code compiles/runs without errors
- [ ] Tests pass (>80% coverage preferred)
- [ ] Security review completed (if applicable)
- [ ] No PHI leakage (for healthcare code)
- [ ] Follows project style guide
- [ ] Documentation updated
- [ ] Performance acceptable

---

## 🚀 Getting Started Checklist

### Initial Setup
- [x] Continue.dev installed in VSCode
- [x] Web approval completed
- [x] Configuration file in place (`~/.continue/config.yaml`)
- [x] Models tested and working

### First Tasks
- [ ] Test each model with simple prompt
- [ ] Try all slash commands
- [ ] Test tab autocomplete
- [ ] Create your first custom prompt
- [ ] Review generated code quality

### Ongoing Usage
- [ ] Track which models work best for your tasks
- [ ] Build library of successful prompts
- [ ] Share findings with team
- [ ] Optimize model selection over time

---

## 📞 Quick Reference

### Keyboard Shortcuts
```
Cmd+L          Open Continue chat
Cmd+I          Inline edit mode
Cmd+Shift+L    Clear chat history
```

### Essential Prompts
```
"@codebase explain this function"
"/phi-check this code"
"/test-route for this endpoint"
"/docker-check this compose file"
"Refactor this using best practices"
"Add comprehensive error handling"
"Generate TypeScript types for this"
```

### Model Quick Select
```
Security    → Claude Opus 4.5
Coding      → Claude Sonnet 4.5
Fast Code   → Codestral
Simple      → GPT-4o Mini
Docs        → GPT-4o
Vision      → Gemini 2.5 Flash
Experimental → Grok
```

---

## 🎉 Ready to Delegate!

Your Continue.dev setup is complete with **11 specialized AI models** ready to handle:
- 🔐 Security & HIPAA compliance
- 💻 Full-stack development  
- ⚡ Rapid prototyping
- 📚 Documentation
- 🧪 Testing & QA
- 🐳 DevOps & deployment
- 🔍 Code review

**Start delegating tasks and let AI agents accelerate your development!**

---

*Last Updated: February 4, 2026*  
*Continue.dev Version: Latest*  
*Configuration: ResearchFlow Production*
