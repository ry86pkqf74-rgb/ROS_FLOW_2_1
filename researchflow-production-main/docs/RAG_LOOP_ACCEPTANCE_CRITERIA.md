# RAG Loop Acceptance Criteria

**Version:** 1.0  
**Date:** 2026-02-06  
**Derived from:** `docs/RAG_PIPELINE.md`, `services/agents/CONTRACT.md`, agent schemas (`agent-rag-ingest`, `agent-rag-retrieve`, `agent-verify`)  
**Applies to:** Milestone 3 agent fleet — the three-agent RAG loop (Ingest → Retrieve → Verify)

---

## 1  Success Metrics

Every green CI run of the RAG loop must satisfy **all** criteria below.  
Metrics are split by agent stage so failures are immediately attributable.

### 1.1  Ingest (`RAG_INGEST`)

| Metric | Gate | Required output fields |
|--------|------|------------------------|
| **Document acceptance** | Every document in `inputs.documents[]` is chunked and stored | `outputs.ingestedCount == len(documents)` |
| **Chunk creation** | At least 1 chunk per document | `outputs.chunkCount >= outputs.ingestedCount` |
| **Chunk-ID stability** | Chunk IDs follow `{docId}-chunk-{N}` pattern | `outputs.chunkIds[]` match pattern |
| **Collection written** | ChromaDB collection name echoed back | `outputs.collection` is non-empty string |
| **Doc-ID echo** | All input `docId` values returned | `set(outputs.docIds) == set(input docIds)` |
| **No silent drops** | `outputs.errors` list is empty for a clean run | `outputs.errors == []` |
| **Envelope shape** | Response matches `AgentRunResponse` | `status == "ok"`, `request_id` echoed, `outputs` present |

### 1.2  Retrieve (`RAG_RETRIEVE`)

| Metric | Gate | Required output fields |
|--------|------|------------------------|
| **Non-empty retrieval** | ≥ 1 chunk returned for any query matching ingested content | `grounding.chunks` length ≥ 1 |
| **Chunk shape** | Every chunk has `chunk_id`, `doc_id`, `text`, `score` | All four fields non-null |
| **Score range** | Scores in `[0.0, 1.0]` (cosine-normalised) | `0.0 <= chunk.score <= 1.0` for every chunk |
| **Citations populated** | `grounding.citations[]` contains at least one entry per returned chunk | `len(grounding.citations) >= 1` |
| **Retrieval trace** | `grounding.retrieval_trace.stages` lists executed stages | At minimum `["semantic"]` |
| **Envelope GroundingPack** | Top-level `grounding` field set on the response envelope | `response.grounding is not None` |
| **Envelope shape** | `status == "ok"`, `request_id` echoed, `outputs` present | — |
| **topK respected** | Returned chunk count ≤ requested `topK` / `n_results` | `len(chunks) <= topK` |

### 1.3  Verify (`CLAIM_VERIFY`)

| Metric | Gate | Required output fields |
|--------|------|------------------------|
| **Verdict per claim** | Exactly one `ClaimVerdict` per input claim | `len(outputs.claim_verdicts) == len(inputs.claims)` |
| **Verdict enum** | Each `verdict` ∈ `{"pass", "fail", "unclear"}` | — |
| **Evidence required for pass** | `verdict == "pass"` → `evidence[]` non-empty with valid `chunk_id` | `evidence[].chunkId` references a real chunk |
| **Fail-closed (LIVE mode)** | No evidence → verdict forced to `"unclear"`, never `"pass"` | — |
| **Overall pass derivation** | `overallPass == True` iff every verdict is `"pass"` | — |
| **Envelope shape** | `status == "ok"`, `request_id` echoed, `outputs` present | — |

### 1.4  End-to-End Loop (Ingest → Retrieve → Verify)

| Metric | Gate |
|--------|------|
| **Round-trip claim verification** | Ingest docs → retrieve for a known claim → verify → `overallPass == True` for factually supported claims |
| **False claim rejection** | Verify a claim contradicted by ingested evidence → verdict `"fail"` or `"unclear"` |
| **Latency budget** | Full loop (ingest 3 docs + retrieve + verify 3 claims) completes within `budgets.timeout_ms` (default 600 s) |
| **JSON serialisation round-trip** | Every `AgentRunResponse` survives `json.dumps` → `json.loads` without data loss |

---

## 2  Minimal Smoke-Test Dataset

Three documents, two queries, three claims — the smallest dataset that exercises every stage.

### 2.1  Documents (3)

```json
[
  {
    "docId": "smoke-001",
    "title": "DOAC Stroke Prevention",
    "source": "cardiology-review-2025",
    "text": "Direct oral anticoagulants (DOACs) such as apixaban reduce stroke risk in atrial fibrillation patients by approximately 70%. The ARISTOTLE trial demonstrated apixaban's superiority over warfarin with fewer major bleeding events.",
    "metadata": { "domain_id": "domain-cardio", "permissions": "public", "topic": "cardiology" }
  },
  {
    "docId": "smoke-002",
    "title": "CAR-T Efficacy in ALL",
    "source": "oncology-review-2025",
    "text": "CAR-T cell therapy targeting CD19 has achieved complete remission rates exceeding 80% in relapsed/refractory B-cell acute lymphoblastic leukemia (ALL). Long-term follow-up shows durable responses in approximately 50% of patients at 12 months.",
    "metadata": { "domain_id": "domain-onco", "permissions": "public", "topic": "oncology" }
  },
  {
    "docId": "smoke-003",
    "title": "Lecanemab in Early Alzheimer's",
    "source": "neurology-review-2025",
    "text": "Lecanemab, an anti-amyloid-beta antibody, demonstrated a 27% reduction in cognitive decline over 18 months in the CLARITY-AD trial. The drug targets soluble amyloid-beta protofibrils and received FDA accelerated approval in 2023.",
    "metadata": { "domain_id": "domain-neuro", "permissions": "public", "topic": "neurology" }
  }
]
```

### 2.2  Queries (2)

| ID | Query text | Expected domain hit | Min expected chunks |
|----|-----------|---------------------|---------------------|
| Q1 | `"stroke prevention anticoagulants atrial fibrillation"` | `domain-cardio` | 1 |
| Q2 | `"amyloid treatment Alzheimer's cognitive decline"` | `domain-neuro` | 1 |

### 2.3  Claims (3)

| ID | Claim text | Expected verdict | Rationale |
|----|-----------|-----------------|-----------|
| C1 | `"Apixaban reduces stroke risk by approximately 70% in AFib patients"` | `pass` | Directly supported by `smoke-001` |
| C2 | `"CAR-T therapy achieves 95% remission in ALL"` | `fail` or `unclear` | `smoke-002` says >80%, not 95% |
| C3 | `"Lecanemab targets tau protein tangles"` | `fail` or `unclear` | `smoke-003` says it targets amyloid-beta protofibrils, not tau |

### 2.4  Fixture file path

```
services/worker/tests/fixtures/rag_smoke_dataset.json
```

This file should be loadable by any test runner:

```python
import json, pathlib
DATASET = json.loads(
    (pathlib.Path(__file__).parent / "fixtures" / "rag_smoke_dataset.json").read_text()
)
docs   = DATASET["documents"]   # 3
queries = DATASET["queries"]    # 2
claims  = DATASET["claims"]     # 3
```

---

## 3  Hybrid Evolution Plan (Semantic-only → BM25 + Rerank)

The `GroundingPack.retrieval_trace` schema already reserves fields for multi-stage retrieval.  
This plan adds BM25 and optional rerank **without breaking the agent contract**.

### 3.1  Current state (v1 — semantic-only)

```
retrieval_trace: { stages: ["semantic"], semantic_k: 10, bm25_k: null, rerank_k: null }
```

- `HybridRetriever` exists in `RAG_PIPELINE.md` but `agent-rag-retrieve` currently calls ChromaDB semantic search only.
- `GroundingPack.chunks[]` shape is stable: `chunk_id`, `doc_id`, `text`, `score`, `metadata`.

### 3.2  Phase A — Add BM25 (contract-safe)

| Change | Contract impact |
|--------|----------------|
| Add BM25 index alongside ChromaDB | None — internal implementation |
| Fuse scores: `final = semanticWeight * sem + (1 - semanticWeight) * bm25` | `chunk.score` remains `float [0,1]` — no contract change |
| Populate `retrieval_trace.bm25_k` | Field already reserved; consumers that don't read it are unaffected |
| Update `retrieval_trace.stages` → `["semantic", "bm25"]` | Additive — downstream only checks `"semantic" in stages` today |

**Implementation steps:**

1. Add `bm25_index.py` to `agent-rag-retrieve/agent/` — builds a BM25 term-frequency index at ingest time.
2. At query time, run BM25 in parallel with ChromaDB query; fuse using `semanticWeight` from config (default `0.7`).
3. Populate `retrieval_trace.stages = ["semantic", "bm25"]` and `retrieval_trace.bm25_k`.
4. **Tests:** Add `test_bm25_retrieval` — exact keyword match queries should score higher than semantic-only. Existing smoke tests must still pass.

### 3.3  Phase B — Add optional rerank (contract-safe)

| Change | Contract impact |
|--------|----------------|
| After fusion, optionally rerank top-N via LLM or cross-encoder | None — chunks shape unchanged |
| Populate `retrieval_trace.rerank_k` | Field already reserved |
| Update `retrieval_trace.stages` → `["semantic", "bm25", "rerank"]` | Additive |
| Config flag `rerank_enabled: bool` (default `false`) | New config key — no contract field |

**Implementation steps:**

1. Add `reranker.py` — accepts fused candidates, calls AI Bridge or a cross-encoder, returns re-scored list.
2. Post-fusion, if `rerank_enabled`, pass top-2× candidates through reranker, keep top-K.
3. Update `retrieval_trace` with `rerank_k` and stage name.
4. **Tests:** Add `test_rerank_ordering` — for ambiguous queries, reranked top result should be more relevant than un-reranked. All existing smoke tests must still pass (rerank is additive, not destructive).

### 3.4  Contract invariants that must hold across all phases

| Invariant | Enforcement |
|-----------|-------------|
| `GroundingPack.chunks[].chunk_id` is always a string | Pydantic schema + contract checker |
| `GroundingPack.chunks[].score` is always `float ∈ [0,1]` | Schema + smoke test assertion |
| `retrieval_trace.stages` is always `List[str]` | Schema — new stages are appended, never renamed |
| `AgentRunResponse` envelope shape unchanged | `scripts/check-agent-contract.py` CI gate |
| `grounding` field on envelope is `Optional[GroundingPack]` | Existing consumers handle `None` |
| Chunk ordering: highest score first | Smoke test assertion |

---

## 4  Failure Modes to Test

Every failure mode below must have a corresponding test case (unit or integration).  
Prefix: `test_failure_` in the test file for easy filtering.

### 4.1  Empty Retrieval

| Scenario | Expected behaviour | Test assertion |
|----------|-------------------|----------------|
| Query has zero semantic overlap with any ingested doc | `grounding.chunks == []`, `status == "ok"`, `outputs.total == 0` | Response is valid envelope, not an error |
| Collection exists but is empty | Same as above — empty results, not a crash | `status == "ok"` |
| Collection does not exist | `status == "error"`, `error.code == "TASK_FAILED"` | Agent does not crash; returns structured error |

### 4.2  Wrong Namespace / Collection

| Scenario | Expected behaviour | Test assertion |
|----------|-------------------|----------------|
| `inputs.knowledgeBase` points to non-existent collection | `error.code ∈ {"TASK_FAILED", "VALIDATION_ERROR"}`, 400 or 500 | Structured `AgentError` returned |
| `task_type` not supported by this agent | HTTP 400, `error.code == "UNSUPPORTED_TASK_TYPE"` | Body still matches `AgentRunResponse` shape |
| `domain_id` filter excludes all docs | `grounding.chunks == []`, `status == "ok"` (not an error — just no matches) | Valid envelope with empty results |

### 4.3  Auth / Credential Failure

| Scenario | Expected behaviour | Test assertion |
|----------|-------------------|----------------|
| OpenAI API key missing or invalid (embedding call fails) | Ingest agent: `status == "error"`, `error.code == "TASK_FAILED"` | No partial writes to ChromaDB |
| ChromaDB unreachable (network / connection refused) | `status == "error"`, `error.code == "TASK_FAILED"` | Agent returns within `timeout_ms` |
| AI Bridge unreachable (verify agent) | DEMO mode: returns stub verdicts. LIVE mode: all claims → `"unclear"`, `overallPass == false` | Contract shape preserved |

### 4.4  Evidence Mismatch (Verify Agent)

| Scenario | Expected behaviour | Test assertion |
|----------|-------------------|----------------|
| Claim supported by evidence | `verdict == "pass"`, `evidence[].chunkId` resolves to a real chunk | `evidence` list non-empty |
| Claim contradicted by evidence | `verdict == "fail"` or `"unclear"` | `overallPass == false` |
| Claim with no matching evidence in grounding pack | **LIVE mode:** `verdict == "unclear"` (fail-closed). **DEMO mode:** may pass with stub | `verdict != "pass"` in LIVE mode |
| `groundingPack` is `None` or has zero chunks | All claims → `"unclear"`, `overallPass == false` | Verify agent does not crash |
| `evidence[].chunkId` references a chunk not in `groundingPack.chunks` | Verify should still return a verdict; evidence is best-effort | Response is valid envelope |
| Numeric claim slightly off (e.g. "70%" vs "~70%") | Depends on LLM; test that a verdict is returned (not a crash) | Verdict ∈ `{"pass", "fail", "unclear"}` |

### 4.5  Malformed Input

| Scenario | Expected behaviour | Test assertion |
|----------|-------------------|----------------|
| `request_id` missing | HTTP 422 or `error.code == "VALIDATION_ERROR"` | — |
| `inputs.query` empty string (retrieve) | `error.code == "VALIDATION_ERROR"` | — |
| `inputs.documents` empty list (ingest) | `ingestedCount == 0`, `chunkCount == 0`, `status == "ok"` (no-op, not error) | — |
| `inputs.claims` empty list (verify) | `claim_verdicts == []`, `overallPass == true` (vacuously) | — |
| `topK` out of range (0, -1, 999) | Clamped to `[1, 100]` by schema | No crash |

### 4.6  Concurrency & Idempotency

| Scenario | Expected behaviour | Test assertion |
|----------|-------------------|----------------|
| Re-ingest same `docId` twice | ChromaDB upserts — `ingestedCount` reflects input count, no duplicate chunks | `collection.count()` does not double |
| Parallel retrieve calls with same query | Both return identical results (deterministic) | Results match |

---

## 5  Test Organisation

```
services/worker/tests/
├── fixtures/
│   └── rag_smoke_dataset.json          ← §2 dataset
├── test_rag_smoke.py                   ← existing (10-doc, 5-query harness)
└── test_rag_acceptance.py              ← NEW: acceptance tests per §1-§4

services/agents/agent-rag-retrieve/tests/
└── test_contract.py                    ← existing contract shape tests

services/agents/agent-verify/tests/
└── test_contract.py                    ← existing contract shape tests
```

### Pytest marks

| Mark | Scope |
|------|-------|
| `@pytest.mark.rag_smoke` | Fast (< 5 s), no network, in-memory ChromaDB |
| `@pytest.mark.rag_acceptance` | Full acceptance, may call embedded ChromaDB |
| `@pytest.mark.rag_failure` | Failure-mode tests (§4) |
| `@pytest.mark.rag_hybrid` | Phase A/B hybrid tests (§3) — skipped until implemented |

---

*Document generated from `docs/RAG_PIPELINE.md`, `services/agents/CONTRACT.md`, and the three agent schemas.*
