# 🚀 Continue.dev Quick Reference Card

## ⌨️ Keyboard Shortcuts
```
Cmd+L          Open Continue chat
Cmd+I          Inline edit mode  
Cmd+Shift+L    Clear chat history
Tab            Autocomplete (Codestral)
```

## 🎯 Model Selection Cheat Sheet

| Task | Use This Model | Speed |
|------|---------------|-------|
| 🔐 Security/HIPAA | Claude Opus 4.5 | ⭐⭐ Slow |
| 💻 Feature Dev | Claude Sonnet 4.5 | ⭐⭐⭐ Medium |
| ⚡ Quick Fixes | Codestral | ⭐⭐⭐⭐⭐ Ultra Fast |
| 📝 Documentation | GPT-4o | ⭐⭐⭐ Medium |
| 🔧 Simple Edits | GPT-4o Mini | ⭐⭐⭐⭐ Fast |
| 🎨 Vision/Images | Gemini 2.5 Flash | ⭐⭐⭐⭐ Fast |
| 🧪 Experiments | Grok | ⭐⭐⭐ Medium |
| 🚀 Prototyping | Mercury Coder | ⭐⭐⭐⭐⭐ Ultra Fast |

## 🛠️ Custom Commands

```bash
/phi-check          # Check for PHI exposure (HIPAA)
/test-route         # Generate route tests
/docker-check       # Verify Docker configuration
/rbac-audit         # Audit access control

@codebase           # Search entire codebase
@terminal           # Include terminal output
@git                # Include git history
```

## 💡 Common Prompts

### Security
```
"/phi-check this patient data handler"
"Review this auth middleware for vulnerabilities"
"/rbac-audit all API endpoints"
```

### Development
```
"@codebase explain this function"
"/test-route for this Express endpoint"
"Refactor this using React hooks"
"Add TypeScript types to this file"
```

### DevOps
```
"/docker-check docker-compose.yml"
"Generate health check endpoints"
"Create Kubernetes manifests"
```

### Testing
```
"/test-route with >80% coverage"
"Generate Playwright E2E tests"
"Create test fixtures for this API"
```

## 🎭 Task Priority Guide

| Priority | Model | Use For |
|----------|-------|---------|
| CRITICAL | Claude Opus 4.5 | Security, Architecture |
| HIGH | Claude Sonnet 4.5 | Features, Bugs |
| MEDIUM | Codestral | Tests, Refactoring |
| LOW | GPT-4o Mini | Formatting, Simple edits |

## 🔄 Parallel Task Pattern

When you have **independent tasks**, delegate to **multiple models**:

```markdown
Architecture → Claude Opus 4.5
Implementation → Claude Sonnet 4.5
Tests → Codestral
Docs → GPT-4o
```

## ✅ Quality Checklist

Before committing AI-generated code:
- [ ] Code compiles/runs
- [ ] Tests pass
- [ ] Security reviewed (if needed)
- [ ] No PHI leakage
- [ ] Style guide followed
- [ ] Documentation updated

## 🎯 Best Practices

✅ **DO:**
- Use Claude Opus for security
- Use Codestral for speed
- Provide specific context
- Review all generated code

❌ **DON'T:**
- Use expensive models for simple tasks
- Trust code blindly
- Skip security reviews
- Commit without testing

## 📊 Your Available Models

Free Trial Models (Continue.dev):
- Claude Opus 4.5, Sonnet 4.5, Claude 4 Sonnet
- GPT-4o, GPT-4o Mini
- Gemini 2.5 Flash
- Codestral
- Relace Instant Apply
- Morph v2
- Mercury Coder

Your API Keys:
- Grok (xAI) - grok-4-latest

## 🚨 Emergency Commands

```bash
# Reload VSCode if Continue stops working
Cmd+Shift+P → "Reload Window"

# Check Continue status
View → Output → Continue

# Reset Continue config
rm -rf ~/.continue/sessions
```

## 📚 Full Documentation

For complete guide, see: [AI_AGENT_TASK_DELEGATION_GUIDE.md](AI_AGENT_TASK_DELEGATION_GUIDE.md)

---

**Print this card or keep it open for quick reference!**
