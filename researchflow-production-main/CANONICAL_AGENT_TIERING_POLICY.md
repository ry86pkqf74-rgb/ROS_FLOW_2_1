# Canonical Model Tier Policy for ResearchFlow Agents

**Document Version:** 1.0  
**Created:** 2025-01-30  
**Model:** Claude Opus 4.6  
**Purpose:** Define standardized model tier assignments for all ResearchFlow agents

---

## Executive Summary

This document establishes the canonical tiering policy for ResearchFlow agents based on the `PhaseAgentDefinition` schema (`modelTier`, `phiScanRequired`, `maxTokens`, `taskType`, `knowledgeBase`). The policy balances cost optimization with quality requirements across 10 core agents.

**Key Principles:**
- **NANO tier** for simple, deterministic tasks (chunking, metadata extraction)
- **MINI tier** for moderate complexity (classification, structured extraction, technical writing)
- **FRONTIER tier** for complex reasoning (synthesis, compliance checking, creative writing)

---

## Agent Tiering Policy Table

| Agent ID | Model Tier | Max Tokens | Temperature | PHI Scan Required | Task Type | Knowledge Base |
|----------|-----------|------------|-------------|-------------------|-----------|----------------|
| **rag-ingest** | NANO | 2048 | 0.1 | ✅ Yes | `extract_metadata` | `research_papers` |
| **rag-retrieve** | MINI | 4096 | 0.3 | ❌ No | `summarize` | `research_papers` |
| **verify** | FRONTIER | 8192 | 0.5 | ✅ Yes | `policy_check` | `clinical_guidelines` |
| **stage2-screen** | MINI | 4096 | 0.2 | ❌ No | `classify` | `research_papers` |
| **stage2-extract** | MINI | 6144 | 0.3 | ❌ No | `extract_metadata` | `research_papers` |
| **stage2-synthesize** | FRONTIER | 12288 | 0.4 | ❌ No | `complex_synthesis` | `research_papers` |
| **introduction-writer** | FRONTIER | 8192 | 0.5 | ❌ No | `draft_section` | `research_papers` |
| **methods-writer** | MINI | 8192 | 0.3 | ✅ Yes* | `draft_section` | `research_papers` |
| **results-writer** | MINI | 8192 | 0.3 | ✅ Yes* | `draft_section` | `research_papers` |
| **discussion-writer** | FRONTIER | 8192 | 0.5 | ❌ No | `complex_synthesis` | `research_papers` |

\* *PHI scan required only if section references patient-level data or identifiable details*

---

## Tier Selection Rationale

### NANO Tier (Fast, Cheap: $0.25/$1.25 per MTok)
**Use Case:** Simple, deterministic operations with structured outputs

- **rag-ingest**: Document chunking and metadata extraction. Pattern matching with no complex reasoning.
- **Temperature:** 0.1 (maximize determinism)

### MINI Tier (Balanced: $3.00/$15.00 per MTok)
**Use Case:** Moderate complexity tasks requiring structured reasoning

- **rag-retrieve**: Query expansion + semantic search orchestration
- **stage2-screen**: Binary classification with clear inclusion/exclusion criteria
- **stage2-extract**: Structured data extraction from scientific text
- **methods-writer**: Technical writing following established conventions (less creative than intro/discussion)
- **results-writer**: Data presentation with narrative coherence
- **Temperature:** 0.2-0.3 (mostly deterministic with slight natural language variability)

### FRONTIER Tier (Complex: $15.00/$75.00 per MTok)
**Use Case:** Complex reasoning, synthesis, and creative tasks

- **verify**: Multi-faceted compliance checking (PHI, IRB, quality). Requires nuanced judgment.
- **stage2-synthesize**: Cross-document synthesis, gap analysis, evidence integration
- **introduction-writer**: Compelling narrative with literature integration
- **discussion-writer**: Interpreting findings in broader context, balancing strengths/limitations
- **Temperature:** 0.4-0.5 (creative synthesis while maintaining accuracy)

---

## PHI Scan Policy

### Required (✅)
- **rag-ingest**: Documents may contain patient data before de-identification
- **verify**: Explicitly checks for PHI leakage (core function)
- **methods-writer**: May reference patient recruitment/characteristics
- **results-writer**: May reference patient outcomes/demographics

### Not Required (❌)
- **rag-retrieve**: Retrieves from sanitized knowledge base
- **stage2-screen/extract/synthesize**: Operates on published literature (no original PHI)
- **introduction-writer**: Background/context only
- **discussion-writer**: Interpretation of aggregated findings

---

## Expected Input/Output JSON Schemas

### rag-ingest

**Input:**
```json
{
  "request_id": "req-abc123",
  "task_type": "RAG_INGEST",
  "inputs": {
    "documents": [
      {
        "id": "paper-001",
        "content": "Full paper text...",
        "metadata": {"title": "Study Title", "authors": ["Smith J"], "year": 2024}
      }
    ],
    "chunkSize": 512,
    "chunkOverlap": 50
  }
}
```

**Output:**
```json
{
  "status": "ok",
  "request_id": "req-abc123",
  "outputs": {
    "chunks": [
      {"id": "paper-001-chunk-0", "text": "...", "tokenCount": 128}
    ],
    "indexedCount": 15,
    "duration_ms": 1230
  }
}
```

### rag-retrieve

**Input:**
```json
{
  "request_id": "req-xyz789",
  "task_type": "RAG_RETRIEVE",
  "inputs": {
    "query": "What statistical methods are used for propensity score matching?",
    "topK": 10,
    "semanticWeight": 0.7,
    "filters": {"source": "paper", "minConfidence": 0.75}
  }
}
```

**Output:**
```json
{
  "status": "ok",
  "request_id": "req-xyz789",
  "outputs": {
    "results": [
      {
        "id": "paper-042-chunk-3",
        "score": 0.92,
        "content": "Propensity score matching reduces selection bias...",
        "metadata": {"paperId": "paper-042", "title": "Advanced PSM", "year": 2023}
      }
    ],
    "searchLatency_ms": 145,
    "totalHits": 27
  }
}
```

### verify

**Input:**
```json
{
  "request_id": "req-verify-001",
  "task_type": "VERIFY",
  "inputs": {
    "content": "Patient John Doe (MRN: 123456) showed improvement...",
    "checkTypes": ["phi", "irb", "quality"],
    "context": {"stage": 12, "researchId": "res-789"}
  }
}
```

**Output:**
```json
{
  "status": "ok",
  "request_id": "req-verify-001",
  "outputs": {
    "passed": false,
    "findings": [
      {
        "type": "PHI_DETECTED",
        "severity": "error",
        "location": "line 1, char 8-16",
        "finding": "Patient name detected",
        "suggestion": "Replace with 'Patient A'"
      }
    ],
    "confidence": 0.95,
    "riskLevel": "high"
  }
}
```

### stage2-screen

**Input:**
```json
{
  "request_id": "req-screen-001",
  "task_type": "STAGE2_SCREEN",
  "inputs": {
    "papers": [
      {
        "id": "pmid-12345678",
        "title": "RCT of Telemedicine in Diabetes",
        "abstract": "Background: Telemedicine has emerged...",
        "year": 2023
      }
    ],
    "inclusionCriteria": ["RCT design", "Adults with T2DM", "Telemedicine"],
    "exclusionCriteria": ["Type 1 diabetes", "Pediatric"]
  }
}
```

**Output:**
```json
{
  "status": "ok",
  "request_id": "req-screen-001",
  "outputs": {
    "decisions": [
      {
        "paperId": "pmid-12345678",
        "decision": "include",
        "confidence": 0.89,
        "reasoning": "Meets all inclusion criteria. No exclusions apply."
      }
    ],
    "totalScreened": 1,
    "included": 1,
    "excluded": 0
  }
}
```

### stage2-extract

**Input:**
```json
{
  "request_id": "req-extract-001",
  "task_type": "STAGE2_EXTRACT",
  "inputs": {
    "paperId": "pmid-12345678",
    "fullText": "METHODS\nStudy Design: RCT...",
    "extractionSchema": {
      "fields": ["methods", "population", "sample_size", "outcomes"]
    }
  }
}
```

**Output:**
```json
{
  "status": "ok",
  "request_id": "req-extract-001",
  "outputs": {
    "extracted": {
      "methods": "RCT with 1:1 allocation",
      "population": {"description": "Adults with T2DM", "age_range": "18-75"},
      "sample_size": 240,
      "outcomes": {"primary": "HbA1c at 12 months"}
    },
    "completeness": 0.92,
    "warnings": ["Effect sizes not reported"]
  }
}
```

### stage2-synthesize

**Input:**
```json
{
  "request_id": "req-synth-001",
  "task_type": "STAGE2_SYNTHESIZE",
  "inputs": {
    "papers": [
      {"id": "pmid-001", "extracted_data": {...}},
      {"id": "pmid-002", "extracted_data": {...}}
    ],
    "synthesisType": "narrative",
    "researchQuestion": "Does telemedicine improve glycemic control?"
  }
}
```

**Output:**
```json
{
  "status": "ok",
  "request_id": "req-synth-001",
  "outputs": {
    "synthesis": {
      "narrative": "Across 12 studies (n=2,840), telemedicine showed consistent HbA1c reduction...",
      "themes": ["Intervention heterogeneity", "Consistent HbA1c reduction"],
      "evidence_table": [{"study": "Smith 2023", "n": 240, "outcome": "HbA1c -0.6%"}],
      "gaps": ["Limited long-term data", "Few rural studies"],
      "recommendations": ["Examine dose-response", "Economic evaluations needed"]
    },
    "citations": ["Smith 2023", "Jones 2022"],
    "confidenceLevel": 0.87
  }
}
```

### Manuscript Section Writers (introduction-writer example)

**Input:**
```json
{
  "request_id": "req-intro-001",
  "task_type": "MANUSCRIPT_INTRO",
  "inputs": {
    "researchQuestion": "Does telemedicine improve glycemic control in T2DM?",
    "literature": [
      {"id": "ref-1", "summary": "Telemedicine adoption increasing..."}
    ],
    "studyContext": {
      "studyDesign": "Propensity-matched cohort",
      "novelty": "First real-world long-term follow-up"
    },
    "targetJournal": "JAMA Internal Medicine",
    "wordLimit": 800
  }
}
```

**Output:**
```json
{
  "status": "ok",
  "request_id": "req-intro-001",
  "outputs": {
    "section": "Type 2 diabetes mellitus affects over 37 million Americans...",
    "wordCount": 785,
    "citations": ["Smith 2023", "CDC 2022"],
    "outline": [
      "Diabetes burden",
      "Telemedicine as solution",
      "Evidence gaps",
      "Study objectives"
    ],
    "qualityMetrics": {
      "readabilityScore": 12.5,
      "academicTone": 0.91,
      "logicalFlow": 0.88
    }
  }
}
```

---

## Cost & Performance Estimates

| Agent | Tier | Avg Input | Avg Output | Est. Cost/Call | Latency |
|-------|------|-----------|------------|----------------|---------|
| rag-ingest | NANO | 500 tok | 100 tok | $0.0002 | 1-2s |
| rag-retrieve | MINI | 200 tok | 800 tok | $0.012 | 2-3s |
| verify | FRONTIER | 1000 tok | 500 tok | $0.053 | 3-5s |
| stage2-screen | MINI | 600 tok | 300 tok | $0.007 | 2-3s |
| stage2-extract | MINI | 2000 tok | 1000 tok | $0.021 | 3-4s |
| stage2-synthesize | FRONTIER | 4000 tok | 2000 tok | $0.210 | 5-8s |
| introduction-writer | FRONTIER | 2000 tok | 1500 tok | $0.143 | 5-7s |
| methods-writer | MINI | 1500 tok | 1500 tok | $0.027 | 3-5s |
| results-writer | MINI | 2000 tok | 1500 tok | $0.029 | 3-5s |
| discussion-writer | FRONTIER | 2000 tok | 1500 tok | $0.143 | 5-7s |

**Pricing Basis:**
- NANO: $0.25/$1.25 per MTok (input/output)
- MINI: $3.00/$15.00 per MTok
- FRONTIER: $15.00/$75.00 per MTok

---

## Implementation Notes

### TypeScript Configuration (Phase Chat Registry)

```typescript
const AGENT_REGISTRY: Record<string, PhaseAgentDefinition> = {
  'rag-ingest': {
    id: 'rag-ingest',
    name: 'RAG Ingest Agent',
    description: 'Ingests documents into knowledge base',
    modelTier: 'NANO',
    phiScanRequired: true,
    maxTokens: 2048,
    taskType: 'extract_metadata',
    knowledgeBase: 'research_papers',
    stageHints: ['chunking', 'embedding', 'indexing'],
  },
  'verify': {
    id: 'verify',
    name: 'Verify Agent',
    description: 'Multi-faceted compliance and quality checking',
    modelTier: 'FRONTIER',
    phiScanRequired: true,
    maxTokens: 8192,
    taskType: 'policy_check',
    knowledgeBase: 'clinical_guidelines',
    stageHints: ['PHI scan', 'IRB compliance', 'quality gates'],
  },
  // ... additional agents
};
```

### Python Agent Implementation

```python
# agent/config.py
AGENT_CONFIG = {
    "model_tier": "MINI",  # NANO | MINI | FRONTIER
    "max_tokens": 4096,
    "temperature": 0.3,
    "phi_scan_required": False,
    "task_type": "STAGE2_SCREEN",
}
```

---

## Escalation Policy

Agents may escalate to higher tiers under these conditions:

1. **Quality gate failure** → Retry with next tier (NANO → MINI → FRONTIER)
2. **Token limit exceeded** → Use tier with higher `maxTokens`
3. **Complex edge case** → Manual escalation to FRONTIER with human review flag

**Example:**
```typescript
if (qualityCheck.score < 0.7 && currentTier === 'MINI') {
  return { shouldEscalate: true, targetTier: 'FRONTIER' };
}
```

---

## Monitoring & Optimization

### Key Metrics
- **Cost per agent invocation** (track against estimates)
- **Quality gate pass rate** (by tier)
- **Escalation frequency** (NANO→MINI→FRONTIER)
- **Latency P50/P95** (by agent and tier)

### Optimization Triggers
- If NANO agent shows <80% quality pass rate → upgrade to MINI
- If FRONTIER agent cost exceeds 2x estimate → investigate prompt optimization
- If latency P95 > 10s → consider async processing or caching

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-01-30 | Claude Opus 4.6 | Initial canonical policy |

---

*This document establishes the standardized tiering policy for Claude Opus 4.6 coordination across ResearchFlow agents.*
