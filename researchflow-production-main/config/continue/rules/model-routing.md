# Model Routing & Parallel Task Assignment

## Model Selection by Task Type

When processing requests, select the optimal model based on task characteristics:

### PRIMARY TASK ROUTING

| Task Type | Recommended Model | Reason |
|-----------|-------------------|--------|
| Complex reasoning, architecture | Claude Opus 4.5 | Strongest reasoning |
| General coding, refactoring | Claude Sonnet 4.5 or Claude 4 Sonnet | Balanced power/speed |
| Quick code completions | GPT-4o Mini | Fast, low-cost |
| Code generation, autocomplete | Codestral | Specialized for code |
| Instant code edits/apply | Relace Instant Apply | Optimized for diffs |
| Code transformation | Morph v2 | Specialized transformer |
| Fast coding tasks | Mercury Coder | Speed-optimized |
| Multimodal (images, diagrams) | Gemini 2.5 Flash | Strong vision |
| Backup/fallback | Grok (Own Key) | Your own API key |

### PARALLEL TASK ASSIGNMENT

When multiple independent tasks can run concurrently:

**Research & Analysis (use Claude Opus 4.5)**
- Architecture design decisions
- Security audits
- HIPAA compliance reviews
- Complex debugging

**Code Generation (use Codestral or Mercury Coder)**
- New function implementations
- Test file generation
- Boilerplate code
- API endpoint scaffolding

**Quick Edits (use Relace Instant Apply or Morph v2)**
- Single-file modifications
- Rename/refactor operations
- Import statement updates
- Comment additions

**Simple Tasks (use GPT-4o Mini)**
- Documentation updates
- Simple Q&A
- Syntax checks
- Config file changes

### TASK DECOMPOSITION STRATEGY

1. **Identify independent subtasks** - Break requests into parallel-safe chunks
2. **Assign by complexity**:
   - High complexity → Claude Opus/Sonnet
   - Medium complexity → GPT-4o, Codestral
   - Low complexity → GPT-4o Mini, Mercury Coder
3. **Assign by specialization**:
   - Code-heavy → Codestral, Mercury Coder
   - Transform/diff → Relace, Morph v2
   - Vision/multimodal → Gemini 2.5 Flash

### COST OPTIMIZATION

- Use GPT-4o Mini for drafts, Claude Opus 4.5 for final review
- Batch simple file operations to Mercury Coder
- Reserve Claude Opus 4.5 for decisions that truly need deep reasoning
- Use Codestral for bulk code generation

### EXAMPLE PARALLEL WORKFLOWS

**Feature Implementation:**
```
Task 1 (Codestral): Generate API endpoint code
Task 2 (Mercury Coder): Generate TypeScript types
Task 3 (GPT-4o Mini): Update documentation
Task 4 (Claude Sonnet): Review for security issues
```

**Bug Investigation:**
```
Task 1 (Claude Opus 4.5): Analyze root cause
Task 2 (Codestral): Generate potential fixes
Task 3 (GPT-4o Mini): Update changelog
```

**Code Review:**
```
Task 1 (Claude Sonnet): Security/logic review
Task 2 (Codestral): Style/best practices check
Task 3 (GPT-4o Mini): Documentation completeness
```
