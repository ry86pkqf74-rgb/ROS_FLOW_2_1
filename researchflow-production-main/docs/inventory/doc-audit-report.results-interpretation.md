# Doc Audit Report — Results Interpretation Agent

**Date:** 2026-02-08  
**Auditor:** Agent (chore/inventory-capture)  
**Scope:** `agent-results-interpretation` docs, inventory refs, wiring code

---

## Files Changed

| File | Action | Summary |
|------|--------|---------|
| `docs/agents/results-interpretation/wiring.md` | **Created** | Canonical wiring doc (7 sections: what/invoke/deploy/auth/io/validate/failures) |
| `AGENT_INVENTORY.md` | Updated | Replaced verbose entry with concise deploy-truth format (execution model, router task types, env vars, canonical doc link) |
| `docs/inventory/capabilities.md` | Updated | Added Section 6: LangSmith-Hosted Agents, with Results Interpretation details |
| `docs/inventory/capabilities.json` | Updated | Added `langsmithHostedAgents` array with Results Interpretation + two siblings |
| `scripts/stagewise-smoke.sh` | Updated | Added step 12: `CHECK_RESULTS_INTERPRETATION=1` flag; checks LANGSMITH_API_KEY, router dispatch, artifact write |
| `scripts/hetzner-preflight.sh` | Updated | Added Results Interpretation preflight block (LANGSMITH_API_KEY, router registration, AGENT_ENDPOINTS_JSON check) |
| `AGENT_RESULTS_INTERPRETATION_BRIEFING.md` | Updated | Fixed status line; removed aspirational docker-compose snippet; added canonical doc pointer |
| `services/agents/agent-results-interpretation/README.md` | Updated | Added canonical doc pointer banner at top |
| `services/agents/agent-results-interpretation/WORKFLOW_INTEGRATION.md` | Updated | Added canonical doc pointer banner; noted designs are aspirational and not implemented |
| `docs/inventory/doc-audit-report.results-interpretation.md` | **Created** | This report |

---

## What Is Canonical Now

**`docs/agents/results-interpretation/wiring.md`** is the single source of
truth for deployment, routing, auth, I/O schema, validation commands, and
common failures.

All other docs defer to it:
- `AGENT_RESULTS_INTERPRETATION_BRIEFING.md` — capabilities & architecture reference
- `WORKFLOW_INTEGRATION.md` — aspirational integration designs (clearly labelled)
- `README.md` — agent capabilities overview

---

## Ground Truth Summary

| Question | Answer |
|----------|--------|
| Is there a Docker service? | **No** |
| Is there a Dockerfile? | **No** |
| Is the router task type registered? | **Yes** — `RESULTS_INTERPRETATION`, `STATISTICAL_ANALYSIS` in `ai-router.ts` lines 242-243 |
| Is it in `AGENT_ENDPOINTS_JSON`? | **No** — dispatch returns `AGENT_NOT_CONFIGURED` |
| Can it be called end-to-end today? | **No** — requires LangSmith proxy/adapter (not built) |
| Execution model | LangSmith cloud (Agent Builder) |
| Health endpoint | N/A (cloud-hosted) |
| Artifacts | Google Docs reports (no local `/data` writes) |

---

## Remaining TODOs

1. **Build LangSmith dispatcher** — The planned
   `services/orchestrator/src/dispatchers/langsmith-dispatcher.ts` described
   in `WORKFLOW_INTEGRATION.md` does not exist.  Until it is built, the
   router dispatch path is dead (task type resolves but URL lookup fails).

2. **Add to `AGENT_ENDPOINTS_JSON`** — Once a proxy/adapter URL is
   available, add `"agent-results-interpretation": "<url>"` to the
   orchestrator env.

3. **Wire to Stages 7-9** — The agent is designed for Results Analysis,
   Synthesis, and Refinement stages but is not connected to the workflow
   engine.

4. **Integration test** — No automated test exercises the full
   LangSmith → Google Docs pipeline.  The smoke check only validates
   router registration and env vars.

5. **Clarify `ResultsInterpretationAgent` (LangGraph) vs
   `agent-results-interpretation` (LangSmith)** — `AGENT_INVENTORY.md`
   Section 2 lists a LangGraph `ResultsInterpretationAgent` in the
   worker.  This is a different agent from the LangSmith-hosted one.
   Both share the name but have different execution models.  The
   inventory should clarify this to prevent confusion.

---

## Acceptance Checklist

- [x] `docs/agents/results-interpretation/wiring.md` exists and is canonical
- [x] Inventory entries match compose/router truth (no false claims)
- [x] Smoke validation flag `CHECK_RESULTS_INTERPRETATION=1` exists and is documented
- [x] Preflight check for LANGSMITH_API_KEY + router registration added
- [x] No contradictory docs remain (all old docs link to canonical wiring doc)
- [x] No secrets in docs
- [x] capabilities.md and capabilities.json updated with correct execution model
