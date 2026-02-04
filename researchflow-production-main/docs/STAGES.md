# ResearchFlow 20-Stage Pipeline

This document describes all 20 workflow stages: their purpose, inputs (from `StageContext` and config), and outputs (`StageResult` and stage-specific `output` shapes).

Stages run in order. Each stage receives a **StageContext** and returns a **StageResult**. The orchestrator passes `previous_results` (and in LIVE mode, `prior_stage_outputs` / `cumulative_data`) so later stages can use prior outputs.

---

## Common Types

### Input: StageContext

| Field | Type | Description |
|-------|------|-------------|
| `job_id` | str | Unique job identifier |
| `config` | Dict[str, Any] | Job configuration (stage-specific keys below) |
| `dataset_pointer` | Optional[str] | Path or URI to the dataset |
| `artifact_path` | str | Base path for artifact storage (default `/data/artifacts`) |
| `log_path` | str | Base path for log storage (default `/data/logs`) |
| `governance_mode` | str | `DEMO`, `STAGING`, or `PRODUCTION` (LIVE) |
| `previous_results` | Dict[int, StageResult] | Results from earlier stages in this run |
| `metadata` | Dict[str, Any] | Additional context metadata |
| `manifest_id` | Optional[str] | Project manifest UUID (LIVE) |
| `project_id` | Optional[str] | Project ID for cumulative tracking (LIVE) |
| `research_id` | Optional[str] | Research ID (LIVE) |
| `cumulative_data` | Dict[str, Any] | Accumulated data from prior stages across sessions (LIVE) |
| `phi_schemas` | Dict[str, Any] | PHI detection/protection schemas (LIVE) |
| `prior_stage_outputs` | Dict[int, Dict] | Raw outputs from prior stages from DB (LIVE) |

### Output: StageResult

| Field | Type | Description |
|-------|------|-------------|
| `stage_id` | int | Stage identifier (1–20) |
| `stage_name` | str | Human-readable name |
| `status` | str | `completed`, `failed`, or `skipped` |
| `started_at` | str | ISO timestamp when stage started |
| `completed_at` | str | ISO timestamp when stage completed |
| `duration_ms` | int | Execution duration in milliseconds |
| `output` | Dict[str, Any] | Stage-specific output (see per-stage below) |
| `artifacts` | List[str] | Generated artifact paths |
| `errors` | List[str] | Error messages (PHI-sanitized) |
| `warnings` | List[str] | Warning messages |
| `metadata` | Dict[str, Any] | Additional stage metadata |

---

## Stage 01: Upload Intake

**Purpose:** Validates and processes incoming file uploads: file type, size limits, checksum, initial metadata. Does not perform PHI scanning (that is Stage 05).

**Inputs:**

- **Context:** `dataset_pointer` (path to uploaded file), `artifact_path`, `config` (e.g. `MAX_UPLOAD_SIZE_BYTES` via env).
- **Config:** Optional overrides for size/type; otherwise uses env defaults.

**Outputs:**

- **StageResult:** `status`, `output` with file metadata (checksum, size, extension), `artifacts` (path to validated file if applicable), `errors`/`warnings` on validation failure.

---

## Stage 02: Literature Review

**Purpose:** Automated literature search and summary for the research topic.

**Inputs:**

- **Context:** `config` (topic, query, limits), `previous_results` (e.g. from Stage 01/04 for context).
- **Config:** Search query, source filters, max results.

**Outputs:**

- **StageResult:** `output` with search results, summaries, citations; `artifacts` (e.g. bibliography file); `warnings` if sources unavailable.

---

## Stage 03: IRB Compliance Check

**Purpose:** IRB compliance check and drafting support (institution-specific templates, consent, protocol).

**Inputs:**

- **Context:** `config` (institution, study type), `previous_results` (hypothesis, design from prior stages).
- **Config:** Institution ID, study type, protocol summary.

**Outputs:**

- **StageResult:** `output` with draft application, risk assessment, consent template, protocol summary; `artifacts` (e.g. IRB draft documents).

---

## Stage 04: Hypothesis Refinement

**Purpose:** Refines research questions based on literature and prior context.

**Inputs:**

- **Context:** `previous_results` (e.g. Stage 02 literature, Stage 01 metadata), `config` (refinement constraints).
- **Config:** Optional scope (PICO, etc.).

**Outputs:**

- **StageResult:** `output` with refined hypothesis, research questions, scope; `artifacts` optional.

**Note:** Two modules exist for stage 4: `stage_04_hypothesis` (Hypothesis Refinement) and `stage_04_validate` (Schema Validation). Only **Hypothesis Refinement** is currently registered; Schema Validation is commented out in `stages/__init__.py` due to `stage_id` conflict. To use schema validation, renumber one of the two or mount it at a different stage ID.

---

## Stage 05: PHI Scan

**Purpose:** Scans data for Protected Health Information (PHI) and applies HIPAA Safe Harbor–style handling (detection, redaction, audit).

**Inputs:**

- **Context:** `dataset_pointer`, `config`, `artifact_path`, `governance_mode`, `phi_schemas` (LIVE). May use `previous_results` (e.g. Stage 01 file path).
- **Config:** Scan options, redaction policy, Safe Harbor identifiers to check.

**Outputs:**

- **StageResult:** `output` with scan summary (e.g. columns/rows flagged, redaction counts), compliance status; `artifacts` (redacted dataset path, audit log); `warnings` for borderline findings.

---

## Stage 06: Study Design

**Purpose:** Study protocol, methodology, endpoints, sample size, and methods outline.

**Inputs:**

- **Context:** `previous_results` (hypothesis, literature, PHI status), `config` (design constraints).
- **Config:** Study type, primary/secondary endpoints, sample size targets.

**Outputs:**

- **StageResult:** `output` with protocol summary, methodology, endpoints, sample size, methods outline; `artifacts` (e.g. protocol document).

---

## Stage 07: Statistical Modeling

**Purpose:** Build and validate statistical models for the study design.

**Inputs:**

- **Context:** `dataset_pointer`, `previous_results` (Stage 06 design, Stage 05 PHI status), `config` (model type, tests).
- **Config:** Model type, significance level, correction method.

**Outputs:**

- **StageResult:** `output` with model fit, test results, diagnostics; `artifacts` (e.g. model objects, plots); `warnings` for assumptions or power.

---

## Stage 08: Data Validation

**Purpose:** Data quality checks (completeness, consistency, ranges).

**Inputs:**

- **Context:** `dataset_pointer`, `previous_results` (e.g. Stage 05/06/07), `config` (validation rules).
- **Config:** Validation rules, thresholds.

**Outputs:**

- **StageResult:** `output` with validation report (pass/fail per rule), summary; `artifacts` (report); `errors`/`warnings` for failures.

---

## Stage 09: Interpretation

**Purpose:** Collaborative result interpretation (findings, implications, limitations).

**Inputs:**

- **Context:** `previous_results` (Stage 07 stats, Stage 08 validation), `config` (interpretation guidelines).
- **Config:** Optional templates or constraints.

**Outputs:**

- **StageResult:** `output` with interpretation text, key findings, limitations; `artifacts` optional.

---

## Stage 10: Validation

**Purpose:** Research validation checklist (methodology, reporting, compliance).

**Inputs:**

- **Context:** `previous_results` (interpretation, stats, design), `config` (checklist type).
- **Config:** Checklist identifier (e.g. reporting standard).

**Outputs:**

- **StageResult:** `output` with checklist results (items passed/failed), overall status; `artifacts` (checklist report); `warnings` for incomplete items.

---

## Stage 11: Iteration

**Purpose:** Analysis iteration with AI routing (e.g. re-run or refine analysis based on validation).

**Inputs:**

- **Context:** `previous_results` (Stage 07–10), `config` (iteration policy, max iterations).
- **Config:** Iteration limits, routing rules.

**Outputs:**

- **StageResult:** `output` with iteration summary, final analysis refs; `artifacts`; `warnings` if max iterations reached.

---

## Stage 12: Manuscript Drafting

**Purpose:** Complete manuscript generation with IMRaD structure, ICMJE-style compliance, and citation formatting.

**Inputs:**

- **Context:** `previous_results` (interpretation, stats, literature, design), `config` (journal template, sections).
- **Config:** Template, sections to include, word limits.

**Outputs:**

- **StageResult:** `output` with manuscript metadata, section summaries; `artifacts` (draft document paths, e.g. DOCX); `warnings` for missing or placeholder sections.

---

## Stage 13: Internal Review

**Purpose:** AI-powered peer review simulation (feedback, suggestions).

**Inputs:**

- **Context:** `previous_results` (Stage 12 manuscript), `config` (review criteria).
- **Config:** Review criteria, rigor level.

**Outputs:**

- **StageResult:** `output` with review comments, suggested edits, overall score; `artifacts` (review report).

---

## Stage 14: Ethical Review

**Purpose:** Compliance and ethical verification (consent, data use, approvals).

**Inputs:**

- **Context:** `previous_results` (IRB, PHI, manuscript), `config` (ethics checklist).
- **Config:** Ethics checklist, institution rules.

**Outputs:**

- **StageResult:** `output` with ethics checklist result, attestations; `artifacts` (ethics memo); `warnings` for gaps.

---

## Stage 15: Artifact Bundling

**Purpose:** Package artifacts for sharing or archiving (e.g. ZIP with manuscript, data summary, logs).

**Inputs:**

- **Context:** `previous_results` (all relevant stages), `artifact_path`, `config` (bundle contents).
- **Config:** Include list, naming, formats.

**Outputs:**

- **StageResult:** `output` with bundle manifest (files included); `artifacts` (bundle path, e.g. ZIP).

---

## Stage 16: Collaboration Handoff

**Purpose:** Share with collaborators (invites, permissions, handoff package).

**Inputs:**

- **Context:** `previous_results` (bundle, manuscript), `config` (collaborators, permissions).
- **Config:** Collaborator list, access level, message.

**Outputs:**

- **StageResult:** `output` with handoff status, links/tokens if applicable; `artifacts` optional; `warnings` for pending invites.

---

## Stage 17: Archiving

**Purpose:** Long-term project archiving (cold storage, retention policy).

**Inputs:**

- **Context:** `previous_results` (bundle, handoff), `config` (retention, archive target).
- **Config:** Retention years, archive backend.

**Outputs:**

- **StageResult:** `output` with archive ID, location, retention; `artifacts` (manifest); `warnings` for retention limits.

---

## Stage 18: Impact Assessment

**Purpose:** Research impact metrics tracking (citations, outreach, reuse).

**Inputs:**

- **Context:** `previous_results` (dissemination, manuscript), `config` (metrics to collect).
- **Config:** Metric types, time window.

**Outputs:**

- **StageResult:** `output` with impact metrics (e.g. citation count, views); `artifacts` (impact report); `warnings` if data sparse.

---

## Stage 19: Dissemination

**Purpose:** Publication and sharing preparation (journal submission, preprint, data release).

**Inputs:**

- **Context:** `previous_results` (manuscript, review, ethics), `config` (target journal, preprint option).
- **Config:** Target venue, embargo, data availability.

**Outputs:**

- **StageResult:** `output` with submission status, DOIs/links; `artifacts` (submission package); `warnings` for incomplete items.

---

## Stage 20: Conference Report

**Purpose:** Final output generation for conferences (abstract, poster, slides, speaker notes).

**Inputs:**

- **Context:** `previous_results` (manuscript, dissemination), `config` (conference, format).
- **Config:** Conference ID, formats (poster, talk, abstract).

**Outputs:**

- **StageResult:** `output` with conference materials manifest; `artifacts` (poster PDF, slides, abstract, speaker notes); `warnings` for missing formats.

---

## Summary Table

| ID | Name | Key Inputs | Key Outputs |
|----|------|------------|-------------|
| 01 | Upload Intake | dataset_pointer, file path | checksum, size, validated path |
| 02 | Literature Review | topic, query | search results, summaries, citations |
| 03 | IRB Compliance | institution, study type | draft application, consent, protocol |
| 04 | Hypothesis Refinement | literature, prior context | refined hypothesis, research questions |
| 05 | PHI Scan | dataset, phi_schemas | scan summary, redacted path, audit |
| 06 | Study Design | hypothesis, literature | protocol, methodology, endpoints |
| 07 | Statistical Modeling | dataset, design | model fit, test results, diagnostics |
| 08 | Data Validation | dataset, rules | validation report |
| 09 | Interpretation | stats, validation | interpretation text, findings |
| 10 | Validation | interpretation, checklist | checklist results |
| 11 | Iteration | stats, validation | iteration summary, final refs |
| 12 | Manuscript Drafting | interpretation, literature | manuscript draft (IMRaD) |
| 13 | Internal Review | manuscript | review comments, score |
| 14 | Ethical Review | IRB, PHI, manuscript | ethics checklist, memo |
| 15 | Artifact Bundling | prior artifacts | bundle (ZIP) |
| 16 | Collaboration Handoff | bundle, collaborators | handoff status |
| 17 | Archiving | bundle | archive ID, location |
| 18 | Impact Assessment | dissemination | impact metrics |
| 19 | Dissemination | manuscript, venue | submission status, DOIs |
| 20 | Conference Report | manuscript, conference | poster, slides, abstract |

For implementation details, see [services/worker/src/workflow_engine/stages/](https://github.com/ry86pkqf74-rgb/researchflow-production/tree/main/services/worker/src/workflow_engine/stages) and [DEVELOPER.md](DEVELOPER.md).
