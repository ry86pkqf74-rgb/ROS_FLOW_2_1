# Peer Review Simulator - Workflow Alignment

**Date:** 2026-02-08  
**Agent:** agent-peer-review-simulator  
**Status:** Imported and documented  

## Overview

This document describes how the Peer Review Simulator agent aligns with and enhances the ResearchFlow production workflow.

## Workflow Integration Map

```
┌─────────────────────────────────────────────────────────────────┐
│                   RESEARCHFLOW WORKFLOW                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Stage 1-9: Data Prep → Literature → IRB → Analysis            │
│                         ↓                                        │
│  Stage 10: Validation & Gap Analysis                           │
│                         ↓                                        │
│  Stage 11: Iteration ◄─────────────────┐                       │
│              │                          │                       │
│              │ Can invoke Peer Review   │ Feedback loop        │
│              │ Simulator for feedback   │                       │
│              ↓                          │                       │
│  Stage 12: Manuscript Drafting         │                       │
│              ↓                          │                       │
│  Stage 13: Internal Review ◄───────────┴─ PRIMARY INTEGRATION  │
│              │                             POINT                │
│              │                                                  │
│              ├─[Option A]─► peer-review.service.ts             │
│              │               (Quick validation)                │
│              │                                                  │
│              └─[Option B]─► agent-peer-review-simulator        │
│                              (Comprehensive review)            │
│                              │                                 │
│                              ├─ Critique Phase (parallel)      │
│                              │  ├─ Critique Workers × N        │
│                              │  ├─ Literature Checker          │
│                              │  ├─ Readability Reviewer        │
│                              │  └─ Checklist Auditor           │
│                              │                                 │
│                              ├─ Revision Phase                 │
│                              │  └─ Revision Worker             │
│                              │                                 │
│                              └─ Output Delivery                │
│                                 ├─ Google Doc Report           │
│                                 ├─ Tracking Spreadsheet        │
│                                 └─ Email Distribution          │
│                                                                 │
│  Stage 14-20: Ethical Review → Polish → Handoff → Impact       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Primary Integration: Stage 13 (Internal Review)

### Current Behavior (peer-review.service.ts)
```typescript
// packages/manuscript-engine/src/services/peer-review.service.ts
async simulateReview(
  manuscript: Record<string, string>,
  metadata: { studyType, sampleSize, hasEthicsApproval, hasCOI }
): Promise<PeerReviewResult> {
  // Single-pass automated review
  // Returns: overallScore, recommendation, comments, categoryScores
}
```

**Use Case:** Quick in-pipeline validation for workflow progression

### Enhanced Option (agent-peer-review-simulator)
```python
# services/worker/src/workflow_engine/stages/stage_13_internal_review.py
if context.config.get("use_langsmith_peer_review", False):
    # Multi-persona comprehensive review
    # Returns: critiques from multiple personas, literature audit,
    #          readability review, checklist compliance, revised draft
```

**Use Case:** Pre-submission manuscript strengthening with iterative refinement

### Configuration Decision Tree

```
Is manuscript near completion and requires rigorous pre-submission review?
├─ YES → use_langsmith_peer_review: true
│         ├─ Set personas: ["methodologist", "statistician", "ethics_reviewer", "domain_expert"]
│         ├─ Set max_review_cycles: 2-3
│         └─ Enable Google Docs output for detailed reports
│
└─ NO  → use_langsmith_peer_review: false (default)
          └─ Use peer-review.service.ts for quick validation
```

## Secondary Integration: Stage 11 (Iteration)

The Peer Review Simulator can be invoked during iterative refinement:

```python
# services/worker/src/workflow_engine/stages/stage_11_iteration.py
async def execute(self, context: StageContext) -> StageResult:
    # ... existing iteration logic ...
    
    if context.config.get("enable_comprehensive_feedback", False):
        # Invoke Peer Review Simulator for detailed critique
        feedback = await call_langsmith_agent(
            "peer-review-simulator",
            manuscript=current_draft,
            personas=["methodologist", "domain_expert"],
            max_cycles=1
        )
        
        # Use feedback to guide next iteration
        iteration_suggestions = extract_actionable_items(feedback)
```

## Tertiary Integration: Standalone Tool

The Peer Review Simulator can be invoked independently for manuscripts generated outside the workflow:

```bash
# CLI invocation (future feature)
researchflow peer-review \
  --manuscript-file /path/to/manuscript.md \
  --study-type RCT \
  --personas methodologist,statistician,ethics_reviewer \
  --output-format google-docs
```

## Workflow Stage Comparison

| Stage | Current Capability | With Peer Review Simulator |
|-------|-------------------|----------------------------|
| **Stage 11: Iteration** | Basic feedback from AI suggestions | Deep multi-persona critiques for targeted improvements |
| **Stage 13: Internal Review** | Single-pass scoring (peer-review.service.ts) | Multi-cycle comprehensive review with revision generation |
| **Stage 14: Ethical Review** | Persona-based ethics checks | Dedicated Ethics Reviewer persona with comprehensive audit |
| **Stage 15: Final Polish** | Grammar/style improvements | Readability Reviewer + Checklist Auditor for publication readiness |

## Integration Benefits

### For Research Teams
1. **Confidence in Submission:** Manuscripts reviewed by multiple simulated personas before external submission
2. **Iterative Improvement:** Track improvements across review cycles with structured feedback
3. **Compliance Assurance:** Automated checklist audits (CONSORT, STROBE, etc.) ensure reporting standard compliance
4. **Literature Quality:** Citation verification and novelty claim validation reduce reviewer criticism risk

### For Workflow Efficiency
1. **Parallel Execution:** All reviewers/auditors run simultaneously (not sequential)
2. **Structured Output:** Google Docs reports and spreadsheets facilitate team review
3. **Flexible Invocation:** Can be used in-pipeline (Stage 13) or post-generation (standalone)
4. **Backward Compatible:** Existing peer-review.service.ts remains unchanged for quick checks

### For Quality Assurance
1. **Multi-Perspective Review:** Methodologist + Statistician + Ethics Reviewer + Domain Expert perspectives
2. **Evidence-Based Critiques:** Literature Checker validates all citations and claims
3. **Writing Quality:** Readability Reviewer ensures clarity and logical flow
4. **Reporting Standards:** Checklist Auditor ensures guideline compliance

## Configuration Examples

### Example 1: Quick Validation (Existing)
```json
{
  "stage_13_config": {
    "use_langsmith_peer_review": false
  }
}
```
**Behavior:** Standard peer-review.service.ts, single-pass, fast

### Example 2: Comprehensive Review (New)
```json
{
  "stage_13_config": {
    "use_langsmith_peer_review": true,
    "personas": ["methodologist", "statistician", "ethics_reviewer", "domain_expert"],
    "max_review_cycles": 2,
    "study_type": "RCT",
    "enable_google_docs_output": true
  }
}
```
**Behavior:** Multi-persona review, up to 2 revision cycles, Google Docs report

### Example 3: Ethics Focus
```json
{
  "stage_13_config": {
    "use_langsmith_peer_review": true,
    "personas": ["ethics_reviewer"],
    "max_review_cycles": 1,
    "enable_google_docs_output": false
  }
}
```
**Behavior:** Ethics-only review, single cycle, chat output only

### Example 4: Statistics + Methodology Focus
```json
{
  "stage_13_config": {
    "use_langsmith_peer_review": true,
    "personas": ["statistician", "methodologist"],
    "max_review_cycles": 1,
    "enable_google_docs_output": true
  }
}
```
**Behavior:** Stats and methods review, single cycle, detailed report

## Alignment with Existing Systems

### Complements (Does Not Replace)

| System | Purpose | Relationship |
|--------|---------|--------------|
| **peer-review.service.ts** | Quick automated scoring | Used for fast in-pipeline checks; Peer Review Simulator for deep pre-submission review |
| **Stage 13 InternalReviewAgent** | Internal review orchestration | Peer Review Simulator is an **option** within Stage 13, not a replacement |
| **Stage 14 EthicalReviewAgent** | Ethics simulation | Ethics Reviewer persona augments Stage 14 with more rigorous audit |
| **Manuscript Engine** | Section generation | Peer Review Simulator reviews **output** of Manuscript Engine |

### Dependencies

**Upstream (Provides Input):**
- Stage 12: Manuscript Drafting → Full manuscript sections
- Stage 11: Iteration → Iteratively refined drafts
- Stage 10: Validation → Validated study results

**Downstream (Consumes Output):**
- Stage 14: Ethical Review → Uses ethics findings
- Stage 15: Final Polish → Uses readability/writing critiques
- Stage 16: Collaboration Handoff → Shares Google Doc reports with collaborators

## Future Enhancements

### Phase 1: Basic Integration (Current)
- ✅ Files imported
- ⏳ LangSmith bridge configuration
- ⏳ Stage 13 enhancement
- ⏳ Configuration schema updates

### Phase 2: Advanced Features (Future)
- [ ] Custom persona definition (user-defined reviewer types)
- [ ] Domain-specific checklist support (computer science, social sciences, etc.)
- [ ] Automated revision acceptance (AI-driven approval logic)
- [ ] Multi-language support (non-English manuscripts)
- [ ] Integration with external submission systems (PubMed, bioRxiv auto-upload)

### Phase 3: Analytics & Learning (Future)
- [ ] Review quality metrics (correlation with actual peer review outcomes)
- [ ] Common critique pattern analysis
- [ ] Automated style guide adherence
- [ ] Journal-specific review simulation (Nature, NEJM, Lancet styles)

## Monitoring & Metrics

### Key Performance Indicators
- **Review Completion Time:** Time from invocation to final report delivery
- **Critique Count:** Number of critiques generated per review cycle
- **Revision Cycle Count:** Average number of cycles before approval
- **Checklist Compliance Improvement:** Before vs. after revision compliance percentage
- **User Acceptance Rate:** % of generated revisions accepted by users

### Health Checks
- LangSmith API availability
- Google Docs API connectivity
- Subagent worker availability
- Tool execution success rates

## Support & Documentation

- **Integration Guide:** [INTEGRATION_GUIDE.md](./INTEGRATION_GUIDE.md)
- **Agent Instructions:** [AGENTS.md](./AGENTS.md)
- **Configuration:** [config.json](./config.json)
- **Tools:** [tools.json](./tools.json)
- **Subagent Specs:** [subagents/*/AGENTS.md](./subagents/)

## Contact

- **Agent Fleet Coordination:** See AGENT_INVENTORY.md
- **Issues:** GitHub Issues with `peer-review-simulator` label
- **Questions:** Team discussion board

---

**Last Updated:** 2026-02-08  
**Status:** Documentation complete, integration pending
