# Stage 2 Pipeline Contract

> **Version:** 1.0.0  
> **Date:** 2026-02-06  
> **Author:** Claude Opus 4.6 coordination  
> **Scope:** Defines the exact JSON handoff objects, verification gates, and regression eval set for the 4-step Stage 2 pipeline.

---

## 1. Pipeline Overview

```
┌──────────────┐     H1      ┌───────────────┐     H2      ┌────────────────┐     H3      ┌─────────────────────┐
│ stage2-lit   │ ──────────▶ │ stage2-screen │ ──────────▶ │ stage2-extract │ ──────────▶ │ stage2-synthesize  │
│ (retrieval)  │             │ (screen/dedup)│             │ (PICO extract) │             │ (grounded review)   │
└──────────────┘             └───────────────┘             └────────────────┘             └─────────────────────┘
task: stage2_lit             task: STAGE2_SCREEN           task: STAGE_2_EXTRACT          task: STAGE2_SYNTHESIZE
```

### Invariants

| Rule | Description |
|------|-------------|
| **Envelope** | Every step uses `AgentRunRequest` → `AgentRunResponse` (see [CONTRACT.md](CONTRACT.md)) |
| **request_id** | Propagated unchanged through all 4 steps (trace-wide unique) |
| **workflow_id** | Optional; if set by the orchestrator, echoed through all steps |
| **mode** | `DEMO` or `LIVE`; propagated; determines AI backend behaviour |
| **PHI** | No paper content in logs at any step |

---

## 2. Handoff Object H1 — `stage2-lit` → `stage2-screen`

The orchestrator reads `stage2-lit.outputs.papers` and injects it into the screen request's `inputs.papers`.

### H1 JSON shape (per paper)

```jsonc
// stage2-lit response → outputs.papers[]
{
  "pmid":       "39012345",                          // string, PubMed ID
  "title":      "A randomized controlled trial ...", // string
  "abstract":   "BACKGROUND: ...",                   // string (may be empty)
  "authors":    ["Alice Smith", "Bob Jones"],        // string[]
  "journal":    "The Lancet",                        // string
  "year":       2023,                                // int | null
  "doi":        "10.1016/j.example.2023.001",        // string | null
  "mesh_terms": ["Diabetes Mellitus", "Metformin"],  // string[]
  "url":        "https://pubmed.ncbi.nlm.nih.gov/39012345/", // string | null
  "source":     "pubmed"                             // string, always "pubmed"
}
```

### Orchestrator mapping (pseudo-code)

```python
screen_request = {
    "request_id":  lit_response["request_id"],
    "task_type":   "STAGE2_SCREEN",
    "mode":        lit_request["mode"],
    "workflow_id": lit_request.get("workflow_id"),
    "domain_id":   lit_request.get("domain_id", "clinical"),
    "inputs": {
        "papers":  lit_response["outputs"]["papers"],   # H1 — direct pass-through
        "criteria": workflow_criteria,                   # from workflow config
        "use_ai":  False                                 # default deterministic
    }
}
```

### Required fields for H1 (paper)

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `pmid` or `id` | string | **yes** (at least one) | Used as `paper_id` downstream |
| `title` | string | **yes** | Used for dedup signature + criteria match |
| `abstract` | string | recommended | Required when `criteria.require_abstract=true` |
| `authors` | string[] | recommended | Used for dedup fallback |
| `year` | int \| null | recommended | Used for year range filter |
| `doi` | string \| null | preferred | Primary dedup key |

---

## 3. Handoff Object H2 — `stage2-screen` → `stage2-extract`

The orchestrator reads `stage2-screen.outputs.included` and maps each paper into the extract request's `inputs.papers` (or `inputs.abstracts`).

### H2 JSON shape (per included paper)

```jsonc
// stage2-screen response → outputs.included[]
{
  "paper_id":          "39012345",                    // string
  "title":             "A randomized controlled ...", // string
  "verdict":           "included",                    // literal "included"
  "reason":            "Meets criteria: Inclusion: diabetes; Inclusion: metformin",
  "study_type":        "randomized_controlled_trial", // StudyType enum value
  "confidence":        1.0,                           // float 0.0–1.0
  "matched_criteria":  ["Inclusion: diabetes"],       // string[]
  "duplicate_of":      null,                          // null for included papers
  "metadata": {
    "year":    2023,
    "authors": ["Alice Smith", "Bob Jones"],
    "doi":     "10.1016/j.example.2023.001"
  }
}
```

### Orchestrator mapping (pseudo-code)

The orchestrator must **enrich** each included result with the original abstract (from H1 papers or from the lit response cache) because the screen agent strips content.

```python
# Build a lookup from the original lit papers
papers_by_id = {p["pmid"]: p for p in lit_response["outputs"]["papers"]}

extract_request = {
    "request_id":  screen_response["request_id"],
    "task_type":   "STAGE_2_EXTRACT",
    "mode":        screen_request["mode"],
    "workflow_id": screen_request.get("workflow_id"),
    "inputs": {
        "papers": [                                     # H2 — enriched
            {
                "id":       r["paper_id"],
                "doc_id":   r["paper_id"],              # extract expects doc_id
                "title":    r["title"],
                "abstract": papers_by_id.get(r["paper_id"], {}).get("abstract", ""),
                "year":     r["metadata"].get("year"),
                "authors":  r["metadata"].get("authors", []),
                "doi":      r["metadata"].get("doi"),
                "study_type": r["study_type"],
            }
            for r in screen_response["outputs"]["included"]
        ],
        "governanceMode": screen_request["mode"]
    }
}
```

### Required fields for H2 (included paper → extract input)

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `id` / `doc_id` | string | **yes** | Stable document identifier for citations |
| `title` | string | **yes** | Used in extraction prompt |
| `abstract` | string | **yes** | Primary extraction source (must be re-attached from H1) |
| `study_type` | string | recommended | Helps extraction focus |
| `year` | int \| null | recommended | For citation construction |
| `authors` | string[] | recommended | For citation construction |
| `doi` | string \| null | recommended | For citation linking |

---

## 4. Handoff Object H3 — `stage2-extract` → `stage2-synthesize`

The orchestrator reads `stage2-extract.outputs.extraction_table` and `stage2-extract.outputs.citations`, then maps them into the synthesize request.

### H3 JSON shape — extraction_table row

```jsonc
// stage2-extract response → outputs.extraction_table[]
{
  "doc_id":      "39012345",           // string
  "chunk_id":    "39012345-abstract",  // string | null
  "pico": {                            // PICOElements | null
    "population":   "Adults with type 2 diabetes (n=200)",
    "intervention": "Metformin 500mg twice daily",
    "comparator":   "Placebo",
    "outcomes":     ["HbA1c reduction", "Fasting glucose"],
    "timeframe":    "12 months"
  },
  "endpoints":    ["HbA1c reduction", "Fasting glucose"],
  "sample_size":  200,                 // int | string | null
  "key_results":  "Metformin reduced HbA1c by 1.2% vs placebo (p<0.001)"
}
```

### H3 JSON shape — citation ref

```jsonc
// stage2-extract response → outputs.citations[]
{
  "doc_id":   "39012345",
  "chunk_id": "39012345-abstract"
}
```

### Orchestrator mapping (pseudo-code)

```python
# Re-attach original paper metadata for synthesis citations
papers_by_id = {p["pmid"]: p for p in lit_response["outputs"]["papers"]}

synthesize_request = {
    "request_id":  extract_response["request_id"],
    "task_type":   "STAGE2_SYNTHESIZE",
    "mode":        extract_request["mode"],
    "workflow_id": extract_request.get("workflow_id"),
    "inputs": {
        "research_question": workflow_config["research_question"],
        "synthesis_type":    "narrative",          # or "thematic", "framework"
        "papers": [
            {
                "id":             row["doc_id"],
                "extracted_data": {
                    "pico":        row.get("pico"),
                    "endpoints":   row.get("endpoints", []),
                    "sample_size": row.get("sample_size"),
                    "key_results": row.get("key_results"),
                },
                "title":   papers_by_id.get(row["doc_id"], {}).get("title"),
                "authors": papers_by_id.get(row["doc_id"], {}).get("authors"),
                "year":    str(papers_by_id.get(row["doc_id"], {}).get("year", "")),
                "doi":     papers_by_id.get(row["doc_id"], {}).get("doi"),
                "url":     papers_by_id.get(row["doc_id"], {}).get("url"),
            }
            for row in extract_response["outputs"]["extraction_table"]
        ],
        "citations": [                              # H3 — citation refs
            {
                "key":     str(i + 1),
                "title":   papers_by_id.get(c["doc_id"], {}).get("title"),
                "authors": papers_by_id.get(c["doc_id"], {}).get("authors"),
                "year":    str(papers_by_id.get(c["doc_id"], {}).get("year", "")),
                "doi":     papers_by_id.get(c["doc_id"], {}).get("doi"),
                "url":     papers_by_id.get(c["doc_id"], {}).get("url"),
            }
            for i, c in enumerate(extract_response["outputs"]["citations"])
        ]
    }
}
```

### Final output shape (stage2-synthesize response)

```jsonc
{
  "status": "ok",
  "request_id": "req-abc-123",
  "outputs": {
    "section_markdown": "## Literature Review\n\nMetformin reduced HbA1c by 1.2% [1]...",
    "citations": [
      {
        "key": "1",
        "title": "A randomized controlled trial...",
        "authors": ["Alice Smith", "Bob Jones"],
        "year": "2023",
        "doi": "10.1016/j.example.2023.001",
        "url": "https://pubmed.ncbi.nlm.nih.gov/39012345/"
      }
    ],
    "warnings": [],
    "research_question": "What is the efficacy of metformin in type 2 diabetes?",
    "paper_count": 5
  }
}
```

---

## 5. Verification Gates

Each gate **must pass** before the orchestrator dispatches to the next step. Failures trigger structured `AgentError` responses; the orchestrator must not silently skip failed steps.

| Gate | After | Condition | Action on failure |
|------|-------|-----------|-------------------|
| **V1: Papers retrieved** | `stage2-lit` | `status == "ok"` AND `outputs.papers` is non-empty list AND `outputs.count >= 1` | Return `DEGRADED` to user; do not proceed to screen. Log `request_id`, `pubmed_query` |
| **V2: Screening complete** | `stage2-screen` | `status == "ok"` AND `outputs.total_processed >= 1` AND `len(outputs.included) >= 1` | If 0 included: return structured result with `outputs.stats` (PRISMA data); pipeline terminates cleanly |
| **V3: Dedup sanity** | `stage2-screen` | `outputs.stats.duplicates_removed + outputs.stats.included_count + outputs.stats.excluded_count == outputs.stats.total_input` | Log warning if mismatch (non-blocking) |
| **V4: Extraction table** | `stage2-extract` | `status == "ok"` AND `len(outputs.extraction_table) >= 1` | If empty: pass empty papers to synthesize → synthesize returns no-evidence section |
| **V5: Citation alignment** | `stage2-extract` | `len(outputs.citations) == len(outputs.extraction_table)` | Log warning if mismatch; proceed (synthesize handles partial citations gracefully) |
| **V6: Synthesis grounding** | `stage2-synthesize` | `status == "ok"` AND `outputs.section_markdown` is non-empty | If empty section: return error to user |
| **V7: Citation integrity** | `stage2-synthesize` | `len(outputs.warnings) == 0` (no dangling citation keys) | If warnings present: include in user response as `provenance.warnings`; non-blocking |

### When to verify

```
lit ──[V1]──▶ screen ──[V2,V3]──▶ extract ──[V4,V5]──▶ synthesize ──[V6,V7]──▶ done
```

- **V1** is checked synchronously before dispatching screen.
- **V2+V3** are checked synchronously before dispatching extract.
- **V4+V5** are checked synchronously before dispatching synthesize.
- **V6+V7** are checked before returning the final result to the user/UI.

---

## 6. Minimal Eval Set for Regression Safety

### 6.1 Fixture: 5-paper smoke set

The canonical test fixture lives in `agent-stage2-screen/test_request.json`. It covers:

| Paper # | pmid/id | Expected screen verdict | Why |
|---------|---------|------------------------|-----|
| 1 | `12345` | **included** | RCT, metformin, diabetes, year 2020 ✓ |
| 2 | `67890` | **excluded** | Matches exclusion "pediatric", study type `case_report` |
| 3 | `11111` | **duplicate** | Same DOI as paper 1 |
| 4 | `22222` | **included** | Systematic review, diabetes + metformin, year 2021 ✓ |
| 5 | `33333` | **excluded** | Year 2018 < year_min 2019 |

### 6.2 Eval assertions per step

#### E1: `stage2-lit` (integration, requires network)
```python
def test_lit_returns_papers():
    resp = call_sync("stage2_lit", {
        "inputs": {
            "research_question": "metformin type 2 diabetes",
            "max_results": 5
        }
    })
    assert resp["status"] == "ok"
    assert len(resp["outputs"]["papers"]) >= 1
    for p in resp["outputs"]["papers"]:
        assert "pmid" in p
        assert "title" in p
        assert "abstract" in p
```

#### E2: `stage2-screen` (deterministic, offline)
```python
def test_screen_verdicts():
    resp = call_sync("STAGE2_SCREEN", FIXTURE_5_PAPERS)
    o = resp["outputs"]
    assert resp["status"] == "ok"
    assert o["total_processed"] == 5

    # Paper counts
    assert o["stats"]["duplicates_removed"] == 1
    assert o["stats"]["included_count"] == 2
    assert o["stats"]["excluded_count"] == 2

    # Specific verdicts
    ids_included = {r["paper_id"] for r in o["included"]}
    ids_excluded = {r["paper_id"] for r in o["excluded"]}
    ids_duped    = {r["paper_id"] for r in o["duplicates"]}
    assert "12345" in ids_included
    assert "22222" in ids_included
    assert "67890" in ids_excluded  # pediatric + case_report
    assert "33333" in ids_excluded  # year < 2019
    assert "11111" in ids_duped     # same DOI as 12345

    # V3 sanity check
    assert (o["stats"]["duplicates_removed"]
            + o["stats"]["included_count"]
            + o["stats"]["excluded_count"]) == o["stats"]["total_input"]
```

#### E3: `stage2-extract` (deterministic stub in DEMO mode)
```python
def test_extract_returns_table():
    included_papers = [
        {"id": "12345", "doc_id": "12345", "title": "...", "abstract": "...", "year": 2020},
        {"id": "22222", "doc_id": "22222", "title": "...", "abstract": "...", "year": 2021},
    ]
    resp = call_sync("STAGE_2_EXTRACT", {
        "inputs": {"papers": included_papers},
        "mode": "DEMO"
    })
    assert resp["status"] == "ok"
    assert len(resp["outputs"]["extraction_table"]) == 2
    assert len(resp["outputs"]["citations"]) == 2

    # V5 alignment
    assert len(resp["outputs"]["citations"]) == len(resp["outputs"]["extraction_table"])

    for row in resp["outputs"]["extraction_table"]:
        assert "doc_id" in row
        assert "pico" in row
        assert "endpoints" in row
```

#### E4: `stage2-synthesize` (deterministic demo fallback)
```python
def test_synthesize_returns_grounded_section():
    papers = [
        {"id": "12345", "extracted_data": {"pico": {"population": "Adults"}, "key_results": "HbA1c -1.2%"}, "title": "...", "year": "2020"},
        {"id": "22222", "extracted_data": {"pico": {"population": "Mixed"}, "key_results": "..."}, "title": "...", "year": "2021"},
    ]
    resp = call_sync("STAGE2_SYNTHESIZE", {
        "inputs": {
            "papers": papers,
            "research_question": "Efficacy of metformin",
            "citations": [{"key": "1"}, {"key": "2"}]
        }
    })
    assert resp["status"] == "ok"
    assert len(resp["outputs"]["section_markdown"]) > 50
    assert len(resp["outputs"]["citations"]) >= 1

    # V7 citation integrity
    assert isinstance(resp["outputs"]["warnings"], list)
```

#### E5: Full pipeline (end-to-end, offline with mocks)
```python
def test_e2e_pipeline_mock():
    """Run all 4 steps in sequence with the 5-paper fixture.
    Mock PubMed in stage2-lit to return the fixture papers.
    Verify data flows through without contract violations."""
    lit_resp    = call_sync("stage2_lit", MOCK_LIT_INPUT)
    screen_resp = call_sync("STAGE2_SCREEN", build_screen_input(lit_resp))
    extract_resp = call_sync("STAGE_2_EXTRACT", build_extract_input(screen_resp, lit_resp))
    synth_resp  = call_sync("STAGE2_SYNTHESIZE", build_synth_input(extract_resp, lit_resp))

    # Pipeline integrity
    assert lit_resp["request_id"] == synth_resp["request_id"]
    assert synth_resp["status"] == "ok"
    assert len(synth_resp["outputs"]["section_markdown"]) > 0
```

### 6.3 Regression matrix

| Test ID | Scope | Offline? | Deterministic? | CI gate? |
|---------|-------|----------|----------------|----------|
| E1 | stage2-lit | ❌ (PubMed) | ❌ | ❌ nightly |
| E2 | stage2-screen | ✅ | ✅ | ✅ **blocking** |
| E3 | stage2-extract | ✅ (DEMO) | ✅ | ✅ **blocking** |
| E4 | stage2-synthesize | ✅ (DEMO) | ✅ | ✅ **blocking** |
| E5 | full pipeline | ✅ (mocked) | ✅ | ✅ **blocking** |

> **CI policy:** E2, E3, E4, E5 run on every PR that touches `services/agents/agent-stage2-*/**`. E1 runs nightly (network-dependent).

---

## 7. task_type Canonical Reference

| Step | `task_type` constant | Service | Port |
|------|---------------------|---------|------|
| 1 | `stage2_lit` | agent-stage2-lit | 8000 |
| 2 | `STAGE2_SCREEN` | agent-stage2-screen | 8000 |
| 3 | `STAGE_2_EXTRACT` | agent-stage2-extract | 8000 |
| 4 | `STAGE2_SYNTHESIZE` | agent-stage2-synthesize | 8000 |

> ⚠️ **Naming inconsistency:** `stage2_lit` uses lowercase/underscore while the others use UPPER_SNAKE. This is accepted for backward compatibility. The orchestrator must use the exact strings above.

---

## 8. Error Codes (pipeline-specific)

| Code | Raised by | Meaning |
|------|-----------|---------|
| `VALIDATION_ERROR` | any | Missing required inputs |
| `TASK_FAILED` | any | Unhandled exception |
| `SCREENING_FAILED` | stage2-screen | Screening logic error |
| `NO_PAPERS_FOUND` | orchestrator (V1) | stage2-lit returned empty results |
| `NO_INCLUDED_PAPERS` | orchestrator (V2) | All papers excluded after screening |
| `EXTRACTION_EMPTY` | orchestrator (V4) | Extract returned no rows |
| `SYNTHESIS_FAILED` | stage2-synthesize | LLM invocation failed |
| `CITATION_MISMATCH` | orchestrator (V5/V7) | Citation count doesn't match table rows |

---

## Appendix A: Full Pipeline Sequence Diagram

```
User/UI
  │
  ▼
Orchestrator
  │  POST /agents/run/sync  { task_type: "stage2_lit", inputs: { research_question, ... } }
  ├──────────▶ agent-stage2-lit
  │              │  PubMed ESearch + EFetch
  │              │  Returns: { papers: [...] }
  │  ◀──────────┘
  │  [V1: papers non-empty?]
  │
  │  POST /agents/run/sync  { task_type: "STAGE2_SCREEN", inputs: { papers: H1, criteria: ... } }
  ├──────────▶ agent-stage2-screen
  │              │  Dedup → Criteria → StudyType
  │              │  Returns: { included, excluded, duplicates, stats }
  │  ◀──────────┘
  │  [V2: included non-empty?]  [V3: dedup sanity]
  │
  │  POST /agents/run/sync  { task_type: "STAGE_2_EXTRACT", inputs: { papers: H2 } }
  ├──────────▶ agent-stage2-extract
  │              │  PICO extraction (AI Bridge or stub)
  │              │  Returns: { extraction_table, citations }
  │  ◀──────────┘
  │  [V4: table non-empty?]  [V5: citation alignment]
  │
  │  POST /agents/run/sync  { task_type: "STAGE2_SYNTHESIZE", inputs: { papers: H3, research_question, citations } }
  ├──────────▶ agent-stage2-synthesize
  │              │  Grounded LLM synthesis
  │              │  Returns: { section_markdown, citations, warnings }
  │  ◀──────────┘
  │  [V6: section non-empty?]  [V7: citation integrity]
  │
  ▼
User/UI  ← { section_markdown, citations, prisma_stats }
```

---

## Appendix B: PRISMA Stats Pass-Through

The orchestrator should collect PRISMA-relevant stats from the screen step and attach them to the final response:

```jsonc
{
  "prisma": {
    "identification": {
      "database_results": /* outputs.count from stage2-lit */,
      "databases": ["PubMed"]
    },
    "screening": {
      "records_screened":  /* stats.total_input */,
      "duplicates_removed": /* stats.duplicates_removed */,
      "records_excluded":  /* stats.excluded_count */,
      "records_included":  /* stats.included_count */
    },
    "included": {
      "studies_in_synthesis": /* len(extraction_table) */
    }
  }
}
```
