# Stage Worker Specifications (Stages 6–20)

> Scope: Worker requirements for stages **6–20** (ANALYSIS, WRITING, PUBLISH). This document defines **input schema**, **output schema**, **LLM requirements**, and **error handling** for each stage worker.
>
> Assumptions:
> - Workers are invoked server-side (queue/job runner) and persist results back to the workflow state.
> - Authentication/authorization is handled upstream; workers operate on a `workflowId` with server credentials.
> - JSON examples are illustrative; implementers should enforce validation via Zod/JSON Schema/etc.

## Global Concepts

### Canonical Worker Contract

All stage workers SHOULD accept and return these envelope fields:

- `workflowId: string`
- `stage: number` (6–20)
- `runId: string` (idempotency key)
- `requestedBy: { userId: string }`
- `inputs: object` (stage-specific)

All stage workers SHOULD return:

- `ok: boolean`
- `workflowId: string`
- `stage: number`
- `runId: string`
- `outputs: object` (stage-specific)
- `artifacts?: Artifact[]`
- `metrics?: Metrics`
- `warnings?: Warning[]`
- `errors?: WorkerError[]` (present when `ok=false`)

### Artifact

- `id: string`
- `type: "source" | "note" | "outline" | "draft" | "citation" | "docx" | "report" | "export"`
- `name: string`
- `mimeType?: string`
- `uri?: string` (S3/DB reference)
- `stage: number`
- `createdAt: string` (ISO)
- `hash?: string` (content hash for dedupe)

### Metrics

- `llmModel?: string`
- `llmTokensIn?: number`
- `llmTokensOut?: number`
- `llmLatencyMs?: number`
- `sourcesUsed?: number`
- `citationsGenerated?: number`

### Standard Errors (use across all stages)

| Code | Meaning | Retry? |
|------|---------|--------|
| `VALIDATION_ERROR` | Input shape invalid / missing required fields | No |
| `UPSTREAM_4XX` | External API returned 4xx (bad request, unauthorized) | No |
| `UPSTREAM_5XX` | External API returned 5xx | Yes (backoff) |
| `TIMEOUT` | LLM or upstream timeout | Yes (backoff) |
| `RATE_LIMITED` | Upstream/LLM rate limiting | Yes (respect retry-after) |
| `LLM_REFUSAL` | Model refused due to policy/safety | No (requires prompt/data change) |
| `LOW_CONFIDENCE` | Output confidence below threshold | Maybe (with adjusted strategy) |
| `INCONSISTENT_OUTPUT` | Output failed post-validation (e.g., non-JSON) | Yes (1–2 prompt repairs) |
| `NOT_FOUND` | Workflow/doc/source not found | No |
| `CONFLICT` | Stage output already exists with same runId or newer | No |

### Idempotency

- Workers MUST be idempotent on `(workflowId, stage, runId)`.
- If a duplicate request arrives, return the previously computed result.

### LLM Output Discipline

- Prefer structured outputs: **strict JSON** (no markdown) for machine-consumed fields.
- Validate model output; if invalid, run 1–2 repair attempts before failing with `INCONSISTENT_OUTPUT`.

---

## ANALYSIS Phase (Stages 6–11)

### Stage 06 — Data Collection

**Goal**: Gather relevant sources (URLs, papers, docs) and extract key claims.

#### Input Schema

- `topic: string`
- `researchQuestion?: string`
- `keywords?: string[]`
- `constraints?: { timeRange?: string, domainsAllowlist?: string[], domainsBlocklist?: string[] }`
- `maxSources: number` (recommended 10–30)

#### Output Schema

- `sources: Array<{ id: string, title: string, url: string, publisher?: string, publishedAt?: string, summary: string, keyClaims: string[] }>`
- `queryLog: Array<{ query: string, resultsCount: number }>`

#### LLM Requirements

- Model: general reasoning + summarization.
- Must produce:
  - search queries (if worker composes them)
  - concise summaries per source
  - extracted key claims as bullet strings

#### Error Handling

- If fewer than `min(5, maxSources)` sources found: return `ok=true` with warning `LOW_COVERAGE` and proceed.
- If source fetch fails for subset: continue; include warning with failed URLs.

---

### Stage 07 — Source Validation

**Goal**: Evaluate credibility/quality of collected sources.

#### Input Schema

- `sources: Array<{ id: string, title: string, url: string, publisher?: string, publishedAt?: string, rawText?: string }>`
- `rubric?: { requireAuthor?: boolean, preferPrimary?: boolean, minRecencyDays?: number }`

#### Output Schema

- `validatedSources: Array<{ id: string, score: number, verdict: "accept"|"caution"|"reject", rationale: string, flags: string[] }>`

#### LLM Requirements

- Must apply rubric consistently.
- Provide *actionable* rationale and flags (e.g., `"no-author"`, `"blog-opinion"`, `"primary-source"`).

#### Error Handling

- If LLM output has missing `id` mappings: fail with `VALIDATION_ERROR` (worker bug) or `INCONSISTENT_OUTPUT` (LLM).
- If more than 50% rejected: emit warning `LOW_TRUST_SET`.

---

### Stage 08 — Gap Analysis

**Goal**: Identify what is missing to answer the research question.

#### Input Schema

- `topic: string`
- `researchQuestion?: string`
- `validatedSources: Array<{ id: string, verdict: string, rationale: string, summary?: string, keyClaims?: string[] }>`

#### Output Schema

- `gaps: Array<{ gapId: string, description: string, impact: "low"|"medium"|"high", suggestedQueries: string[] }>`
- `nextActions: Array<{ action: "collect-more"|"clarify-scope"|"proceed", reason: string }>`

#### LLM Requirements

- Must be explicit about unknowns vs assumptions.
- Must generate suggested queries that are specific.

#### Error Handling

- If no gaps found, still return an empty array and `nextActions=[{action:"proceed",...}]`.

---

### Stage 09 — Synthesis

**Goal**: Build a coherent synthesis: themes, consensus, disagreement, and takeaways.

#### Input Schema

- `validatedSources: Array<{ id: string, verdict: "accept"|"caution"|"reject", summary: string, keyClaims: string[] }>`
- `focus?: string[]` (optional angles)

#### Output Schema

- `themes: Array<{ theme: string, description: string, supportingSourceIds: string[] }>`
- `consensus: string[]`
- `disagreements: Array<{ point: string, sides: Array<{ claim: string, sourceIds: string[] }> }>`
- `insights: string[]`

#### LLM Requirements

- Must cite source IDs for each theme/claim.
- Avoid hallucinating facts not in sources.

#### Error Handling

- If supportingSourceIds reference unknown IDs: treat as `INCONSISTENT_OUTPUT` and attempt repair.

---

### Stage 10 — Cross-Reference

**Goal**: Cross-check claims across sources and detect contradictions.

#### Input Schema

- `themes: Array<{ theme: string, supportingSourceIds: string[] }>`
- `sources: Array<{ id: string, summary: string, keyClaims: string[] }>`

#### Output Schema

- `crossRefs: Array<{ claim: string, corroborates: string[], contradicts: string[], notes: string }>`
- `riskRegister: Array<{ risk: string, severity: "low"|"medium"|"high", mitigation: string }>`

#### LLM Requirements

- Must explicitly mark corroboration vs contradiction.
- Must avoid overstating certainty.

#### Error Handling

- If contradictions are detected: `ok=true` with warnings and populate risk register.

---

### Stage 11 — Fact Check

**Goal**: Produce a fact-check report for key assertions.

#### Input Schema

- `draftClaims: string[]` (claims intended for final doc)
- `sources: Array<{ id: string, url: string, summary: string, keyClaims: string[] }>`

#### Output Schema

- `factChecks: Array<{ claim: string, status: "supported"|"uncertain"|"unsupported", evidenceSourceIds: string[], notes: string }>`
- `requiredEdits: string[]`

#### LLM Requirements

- Must label uncertainty.
- Must provide evidenceSourceIds.

#### Error Handling

- If >20% claims `unsupported`, emit warning `HIGH_FACT_RISK`.

---

## WRITING Phase (Stages 12–15)

### Stage 12 — Outline Generation

**Goal**: Create a structured outline aligned to the synthesis.

#### Input Schema

- `topic: string`
- `audience?: string`
- `tone?: "neutral"|"academic"|"executive"|"blog"`
- `themes: Array<{ theme: string, description: string }>`
- `constraints?: { maxSections?: number, requiredSections?: string[] }`

#### Output Schema

- `outline: { title: string, sections: Array<{ heading: string, bullets: string[], rationale?: string }> }`

#### LLM Requirements

- Must ensure logical ordering.
- Must include bullets that map to themes.

#### Error Handling

- If outline exceeds constraints: auto-trim and emit warning `TRIMMED_OUTLINE`.

---

### Stage 13 — Draft Writing

**Goal**: Generate a first full draft from the outline.

#### Input Schema

- `outline: { title: string, sections: Array<{ heading: string, bullets: string[] }> }`
- `sources?: Array<{ id: string, summary: string, keyClaims: string[] }>`
- `citationStyle?: "apa"|"mla"|"chicago"|"ieee"|"footnote"`

#### Output Schema

- `draft: { title: string, contentMarkdown: string }`
- `inlineCitations: Array<{ marker: string, sourceIds: string[] }>`

#### LLM Requirements

- Produce coherent prose.
- Keep citations consistent with markers.

#### Error Handling

- If contentMarkdown is empty or too short: fail with `LOW_CONFIDENCE`.

---

### Stage 14 — Revision

**Goal**: Revise for clarity, structure, and correctness; incorporate fact-check edits.

#### Input Schema

- `draft: { contentMarkdown: string }`
- `factChecks?: Array<{ claim: string, status: string, notes: string }>`
- `requiredEdits?: string[]`

#### Output Schema

- `revisedDraft: { contentMarkdown: string }`
- `changeLog: Array<{ type: "remove"|"rewrite"|"add"|"reorder", summary: string }>`

#### LLM Requirements

- Must preserve intent while fixing issues.
- Must not introduce new uncited factual claims.

#### Error Handling

- If revisions introduce new claims: flag `NEW_CLAIMS_DETECTED` warning (via heuristic diff + optional LLM check).

---

### Stage 15 — Final Polish

**Goal**: Final pass for grammar, tone, and consistency.

#### Input Schema

- `revisedDraft: { contentMarkdown: string }`
- `tone?: string`
- `styleGuide?: { useOxfordComma?: boolean, spelling?: "US"|"UK" }`

#### Output Schema

- `finalDraft: { contentMarkdown: string }`
- `qualitySignals: { readability?: string, issuesFound: number }`

#### LLM Requirements

- Editing-focused model or same model with strict editing prompt.

#### Error Handling

- If the model rewrites meaning significantly: return `ok=true` with warning `POTENTIAL_MEANING_SHIFT` and include diff summary.

---

## PUBLISH Phase (Stages 16–20)

### Stage 16 — Formatting

**Goal**: Normalize headings, lists, tables; ensure consistent document structure.

#### Input Schema

- `finalDraft: { contentMarkdown: string }`
- `formatProfile?: "docx"|"web"|"pdf"`

#### Output Schema

- `formatted: { contentMarkdown: string }`
- `formattingNotes: string[]`

#### LLM Requirements

- Prefer deterministic formatting rules; use LLM only for structure cleanup when needed.

#### Error Handling

- If formatting introduces invalid markdown: repair and warn `FORMAT_REPAIR`.

---

### Stage 17 — Citation Generation

**Goal**: Generate bibliography entries from sources and inline citations.

#### Input Schema

- `sources: Array<{ id: string, url: string, title?: string, publisher?: string, publishedAt?: string, authors?: string[] }>`
- `inlineCitations: Array<{ marker: string, sourceIds: string[] }>`
- `citationStyle: "apa"|"mla"|"chicago"|"ieee"|"footnote"`

#### Output Schema

- `bibliography: Array<{ sourceId: string, citationText: string }>`
- `citationMap: Array<{ marker: string, citationKeys: string[] }>`

#### LLM Requirements

- Must follow chosen style.
- Must be consistent (same source => same citation).

#### Error Handling

- Missing metadata: generate best-effort and emit warning `INCOMPLETE_METADATA`.

---

### Stage 18 — Quality Review

**Goal**: Run a quality gate before export/publish.

#### Input Schema

- `formatted: { contentMarkdown: string }`
- `factChecks?: Array<{ claim: string, status: string }>`
- `bibliography?: Array<{ sourceId: string, citationText: string }>`

#### Output Schema

- `qualityReport: { score: number, pass: boolean, issues: Array<{ severity: "low"|"medium"|"high", issue: string, fix: string }> }`

#### LLM Requirements

- Reviewer prompt; must be strict and enumerative.

#### Error Handling

- If `pass=false`, return `ok=true` but block downstream publish in UI unless overridden.

---

### Stage 19 — Export Prep

**Goal**: Convert markdown + citations into an export-ready intermediate representation.

#### Input Schema

- `formatted: { contentMarkdown: string }`
- `bibliography: Array<{ sourceId: string, citationText: string }>`
- `exportOptions?: { includeToc?: boolean, pageNumbers?: boolean }`

#### Output Schema

- `exportBundle: { contentMarkdown: string, bibliographyMarkdown: string, assets: Artifact[] }`

#### LLM Requirements

- Usually not required; deterministic transformations preferred.

#### Error Handling

- If assets missing: warn `MISSING_ASSETS`.

---

### Stage 20 — Publish

**Goal**: Finalize publish state and generate deliverables (DOCX export trigger may occur here or via API).

#### Input Schema

- `workflowId: string`
- `exportBundle: { contentMarkdown: string, bibliographyMarkdown: string }`
- `publishTarget?: "download"|"cms"|"email"`

#### Output Schema

- `published: { status: "published"|"ready"|"failed", publishedAt?: string }`
- `deliverables: Artifact[]` (should include DOCX when generated)

#### LLM Requirements

- Not required unless generating final publish metadata/abstract.

#### Error Handling

- If DOCX export API fails:
  - return `ok=false` with `UPSTREAM_5XX` or `UPSTREAM_4XX` as appropriate.
  - include `retryAfterMs` hint if rate-limited.

---

## Notes on Integration

- Export endpoint (current): `POST /api/workflows/:id/export`
  - Must receive `Authorization: Bearer <token>` when called from client.
  - Server worker may call internal export routine directly.

- Stage routes (UI): `/workflow/[id]?stage=6` … `?stage=20`

- Phases:
  - ANALYSIS: 6–11
  - WRITING: 12–15
  - PUBLISH: 16–20
