#!/usr/bin/env python3
"""
Execution Sweep v2 - With agent-specific input schemas
Validates dispatch + run for all 31 task types with appropriate minimal inputs
"""
import os
import sys
import json
import urllib.request
import urllib.error
from datetime import datetime
from typing import Dict, List, Tuple

ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://127.0.0.1:3001")
DISPATCH_URL = f"{ORCHESTRATOR_URL}/api/ai/router/dispatch"
MODE = os.getenv("MODE", "DEMO")
RISK_TIER = os.getenv("RISK_TIER", "NON_SENSITIVE")
TIMEOUT_SECS = int(os.getenv("TIMEOUT_SECS", "120"))
WORKER_SERVICE_TOKEN = os.getenv("WORKER_SERVICE_TOKEN")

if not WORKER_SERVICE_TOKEN:
    print("ERROR: WORKER_SERVICE_TOKEN not set", file=sys.stderr)
    sys.exit(1)

# Agent-specific input schemas (minimal valid inputs)
AGENT_INPUTS = {
    "LIT_RETRIEVAL": {"query": "machine learning"},
    "LIT_TRIAGE": {"papers": []},
    "EVIDENCE_SYNTHESIS": {"papers": [], "question": "test question"},
    "CLAIM_VERIFY": {"claim": "test claim", "evidence": []},
    "RESULTS_INTERPRETATION": {"data": {"results": "test"}},
    "STATISTICAL_ANALYSIS": {"data": {"results": "test"}},
    "SECTION_WRITE_INTRO": {"topic": "test topic"},
    "SECTION_WRITE_METHODS": {"methods": "test methods"},
    "SECTION_WRITE_RESULTS": {"results": "test results"},
    "SECTION_WRITE_DISCUSSION": {"findings": "test findings"},
    "CLINICAL_SECTION_DRAFT": {"section_type": "introduction", "context": {}},
    "CLINICAL_MANUSCRIPT_WRITE": {"title": "test", "sections": {}},
    "STAGE2_SCREEN": {"papers": []},
    "STAGE2_EXTRACT": {"paper_id": "test", "paper_text": "test"},
    "STAGE2_SYNTHESIZE": {"extractions": []},
    "STAGE_2_EXTRACT": {"paper_id": "test", "paper_text": "test"},
    "STAGE_2_LITERATURE_REVIEW": {"query": "test"},
    "RAG_INGEST": {"documents": []},
    "RAG_RETRIEVE": {"query": "test query"},
    "POLICY_REVIEW": {"policy_text": "test policy"},
    "COMPLIANCE_AUDIT": {"document": "test document"},
    "ARTIFACT_AUDIT": {"artifact": "test artifact"},
    "PEER_REVIEW_SIMULATION": {"manuscript": "test manuscript"},
    "CLINICAL_BIAS_DETECTION": {"text": "test text"},
    "DISSEMINATION_FORMATTING": {"content": "test content"},
    "HYPOTHESIS_REFINEMENT": {"hypothesis": "test hypothesis"},
    "JOURNAL_GUIDELINES_CACHE": {"journal": "test journal"},
    "MULTILINGUAL_LITERATURE_PROCESSING": {"text": "test text", "language": "en"},
    "PERFORMANCE_OPTIMIZATION": {"metrics": {}},
    "CLINICAL_MODEL_FINE_TUNING": {"dataset": "test", "parameters": {}},
}

# Special cases: agents that use "input" (singular) instead of "inputs" (plural)
SINGULAR_INPUT_AGENTS = ["RESILIENCE_ARCHITECTURE"]

TASKS = [
    "ARTIFACT_AUDIT",
    "CLAIM_VERIFY",
    "CLINICAL_BIAS_DETECTION",
    "CLINICAL_MANUSCRIPT_WRITE",
    "CLINICAL_MODEL_FINE_TUNING",
    "CLINICAL_SECTION_DRAFT",
    "COMPLIANCE_AUDIT",
    "DISSEMINATION_FORMATTING",
    "EVIDENCE_SYNTHESIS",
    "HYPOTHESIS_REFINEMENT",
    "JOURNAL_GUIDELINES_CACHE",
    "LIT_RETRIEVAL",
    "LIT_TRIAGE",
    "MULTILINGUAL_LITERATURE_PROCESSING",
    "PEER_REVIEW_SIMULATION",
    "PERFORMANCE_OPTIMIZATION",
    "POLICY_REVIEW",
    "RAG_INGEST",
    "RAG_RETRIEVE",
    "RESILIENCE_ARCHITECTURE",
    "RESULTS_INTERPRETATION",
    "SECTION_WRITE_DISCUSSION",
    "SECTION_WRITE_INTRO",
    "SECTION_WRITE_METHODS",
    "SECTION_WRITE_RESULTS",
    "STATISTICAL_ANALYSIS",
    "STAGE2_EXTRACT",
    "STAGE2_SCREEN",
    "STAGE2_SYNTHESIZE",
    "STAGE_2_EXTRACT",
    "STAGE_2_LITERATURE_REVIEW",
]


def http_post(url: str, payload: dict, auth_header: str = None) -> Tuple[int, dict, float]:
    """Make HTTP POST request and return (status_code, response_json, elapsed_time)"""
    import time
    
    headers = {"Content-Type": "application/json"}
    if auth_header:
        headers["Authorization"] = auth_header
    
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers)
    
    start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECS) as response:
            elapsed = time.time() - start
            body = response.read().decode("utf-8")
            return response.status, json.loads(body), elapsed
    except urllib.error.HTTPError as e:
        elapsed = time.time() - start
        try:
            body = e.read().decode("utf-8")
            return e.code, json.loads(body), elapsed
        except:
            return e.code, {"error": str(e)}, elapsed
    except urllib.error.URLError as e:
        elapsed = time.time() - start
        return 0, {"error": str(e)}, elapsed
    except Exception as e:
        elapsed = time.time() - start
        return 0, {"error": str(e)}, elapsed


def main():
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    output_file = f"/tmp/execution_sweep_v2_{ts}.tsv"
    
    # Write header
    with open(output_file, "w") as f:
        f.write("task_type\tdispatch_http\tagent_name\tagent_url\trun_http\tlatency_ms\tpass_fail\terror_preview\n")
    
    results = []
    
    for task in TASKS:
        req_id = f"exec-sweep-{task}-{ts}"
        
        # Get agent-specific inputs or use empty dict
        task_inputs = AGENT_INPUTS.get(task, {})
        
        dispatch_payload = {
            "task_type": task,
            "request_id": req_id,
            "mode": MODE,
            "risk_tier": RISK_TIER,
            "inputs": task_inputs,
            "budgets": {}
        }
        
        # Dispatch
        dispatch_code, dispatch_json, dispatch_time = http_post(
            DISPATCH_URL,
            dispatch_payload,
            f"Bearer {WORKER_SERVICE_TOKEN}"
        )
        
        agent_name = dispatch_json.get("agent_name", "")
        agent_url = dispatch_json.get("agent_url", "")
        
        if dispatch_code != 200 or not agent_url:
            error_preview = json.dumps(dispatch_json)[:220]
            result = {
                "task_type": task,
                "dispatch_http": dispatch_code,
                "agent_name": agent_name,
                "agent_url": agent_url,
                "run_http": "",
                "latency_ms": "",
                "pass_fail": "FAIL",
                "error_preview": f"DISPATCH_FAIL {error_preview}"
            }
            results.append(result)
            print(f"{task}\t{dispatch_code}\t{agent_name}\t{agent_url}\t\t\tFAIL\tDISPATCH_FAIL")
            continue
        
        # Run
        run_url = f"{agent_url.rstrip('/')}/agents/run/sync"
        run_payload = {
            "request_id": req_id,
            "task_type": task,
            "mode": MODE,
            "risk_tier": RISK_TIER,
            "budgets": {}
        }
        
        # Handle special cases: singular "input" vs plural "inputs"
        if task in SINGULAR_INPUT_AGENTS:
            run_payload["input"] = task_inputs
        else:
            run_payload["inputs"] = task_inputs
        
        run_code, run_json, run_time = http_post(run_url, run_payload)
        latency_ms = int(run_time * 1000)
        
        # Pass if HTTP 200 and non-trivial response
        response_size = len(json.dumps(run_json))
        if run_code == 200 and response_size > 50:
            result = {
                "task_type": task,
                "dispatch_http": dispatch_code,
                "agent_name": agent_name,
                "agent_url": agent_url,
                "run_http": run_code,
                "latency_ms": latency_ms,
                "pass_fail": "PASS",
                "error_preview": ""
            }
            results.append(result)
            print(f"{task}\t{dispatch_code}\t{agent_name}\t{agent_url}\t{run_code}\t{latency_ms}\tPASS\t")
        else:
            error_preview = json.dumps(run_json)[:220]
            result = {
                "task_type": task,
                "dispatch_http": dispatch_code,
                "agent_name": agent_name,
                "agent_url": agent_url,
                "run_http": run_code,
                "latency_ms": latency_ms,
                "pass_fail": "FAIL",
                "error_preview": f"RUN_FAIL {error_preview}"
            }
            results.append(result)
            print(f"{task}\t{dispatch_code}\t{agent_name}\t{agent_url}\t{run_code}\t{latency_ms}\tFAIL\tRUN_FAIL")
    
    # Write all results to TSV
    with open(output_file, "a") as f:
        for r in results:
            f.write(f"{r['task_type']}\t{r['dispatch_http']}\t{r['agent_name']}\t{r['agent_url']}\t{r['run_http']}\t{r['latency_ms']}\t{r['pass_fail']}\t{r['error_preview']}\n")
    
    print(f"\nSaved results: {output_file}")
    
    # Summary
    passes = [r for r in results if r["pass_fail"] == "PASS"]
    failures = [r for r in results if r["pass_fail"] == "FAIL"]
    
    print(f"\n{'='*60}")
    print(f"SUMMARY: {len(passes)}/{len(results)} PASS ({len(passes)*100//len(results)}%)")
    print(f"{'='*60}")
    
    if failures:
        print("\nFailures:")
        for f in failures:
            print(f"- {f['task_type']} => {f['error_preview'][:100]}")
    else:
        print("\n🎉 ALL TESTS PASSED! 🎉")


if __name__ == "__main__":
    main()
