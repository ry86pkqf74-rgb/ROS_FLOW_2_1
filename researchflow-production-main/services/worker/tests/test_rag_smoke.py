"""
RAG Smoke Test — Minimal regression harness

Ingests 10 research documents into ChromaDB (with domain_id & permissions metadata),
runs 5 retrieval queries, and asserts:
  1. Non-empty retrieved context
  2. Document IDs / citations present in results
  3. Answer payload matches expected JSON schema

Run:
  pytest tests/test_rag_smoke.py -v -k rag_smoke
  make rag-smoke
"""

import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List

import pytest

# ---------------------------------------------------------------------------
# Path setup — mirrors existing test_rag.py convention
# ---------------------------------------------------------------------------
worker_src = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(worker_src))


# ---------------------------------------------------------------------------
# Test documents — realistic medical-research corpus (10 docs, 3 domains)
# ---------------------------------------------------------------------------

DOMAIN_CARDIOLOGY = "domain-cardio-001"
DOMAIN_ONCOLOGY = "domain-onco-002"
DOMAIN_NEUROLOGY = "domain-neuro-003"

SMOKE_DOCUMENTS: List[Dict[str, Any]] = [
    {
        "id": "smoke-doc-001",
        "text": "Atrial fibrillation (AFib) is the most common sustained cardiac arrhythmia, "
                "associated with increased stroke risk and heart failure progression.",
        "metadata": {"domain_id": DOMAIN_CARDIOLOGY, "permissions": "public", "topic": "cardiology", "year": 2024},
    },
    {
        "id": "smoke-doc-002",
        "text": "Anticoagulation with DOACs (direct oral anticoagulants) such as apixaban "
                "reduces stroke risk in atrial fibrillation patients by approximately 70%.",
        "metadata": {"domain_id": DOMAIN_CARDIOLOGY, "permissions": "public", "topic": "cardiology", "year": 2024},
    },
    {
        "id": "smoke-doc-003",
        "text": "Left ventricular ejection fraction (LVEF) below 40% is classified as heart "
                "failure with reduced ejection fraction (HFrEF).",
        "metadata": {"domain_id": DOMAIN_CARDIOLOGY, "permissions": "restricted", "topic": "cardiology", "year": 2023},
    },
    {
        "id": "smoke-doc-004",
        "text": "CAR-T cell therapy has shown remarkable efficacy in relapsed/refractory "
                "B-cell acute lymphoblastic leukemia, with complete remission rates exceeding 80%.",
        "metadata": {"domain_id": DOMAIN_ONCOLOGY, "permissions": "public", "topic": "oncology", "year": 2024},
    },
    {
        "id": "smoke-doc-005",
        "text": "Immune checkpoint inhibitors targeting PD-1/PD-L1 have transformed the "
                "treatment landscape for non-small cell lung cancer (NSCLC).",
        "metadata": {"domain_id": DOMAIN_ONCOLOGY, "permissions": "public", "topic": "oncology", "year": 2024},
    },
    {
        "id": "smoke-doc-006",
        "text": "Tumor mutational burden (TMB) greater than 10 mutations/Mb is a predictive "
                "biomarker for immunotherapy response in solid tumors.",
        "metadata": {"domain_id": DOMAIN_ONCOLOGY, "permissions": "restricted", "topic": "oncology", "year": 2023},
    },
    {
        "id": "smoke-doc-007",
        "text": "Alzheimer's disease is characterized by extracellular amyloid-beta plaques "
                "and intraneuronal neurofibrillary tangles composed of hyperphosphorylated tau.",
        "metadata": {"domain_id": DOMAIN_NEUROLOGY, "permissions": "public", "topic": "neurology", "year": 2024},
    },
    {
        "id": "smoke-doc-008",
        "text": "Lecanemab (anti-amyloid antibody) showed a 27% reduction in cognitive "
                "decline over 18 months in early Alzheimer's patients in the CLARITY-AD trial.",
        "metadata": {"domain_id": DOMAIN_NEUROLOGY, "permissions": "public", "topic": "neurology", "year": 2024},
    },
    {
        "id": "smoke-doc-009",
        "text": "Deep brain stimulation (DBS) of the subthalamic nucleus remains a standard "
                "surgical therapy for advanced Parkinson's disease motor symptoms.",
        "metadata": {"domain_id": DOMAIN_NEUROLOGY, "permissions": "public", "topic": "neurology", "year": 2023},
    },
    {
        "id": "smoke-doc-010",
        "text": "The APOE ε4 allele is the strongest genetic risk factor for late-onset "
                "Alzheimer's disease, increasing risk 3-15 fold depending on zygosity.",
        "metadata": {"domain_id": DOMAIN_NEUROLOGY, "permissions": "restricted", "topic": "neurology", "year": 2024},
    },
]

SMOKE_QUERIES = [
    {"query": "What treatments are available for atrial fibrillation?", "expected_domain": DOMAIN_CARDIOLOGY},
    {"query": "CAR-T cell therapy efficacy in leukemia", "expected_domain": DOMAIN_ONCOLOGY},
    {"query": "Immunotherapy biomarkers for lung cancer", "expected_domain": DOMAIN_ONCOLOGY},
    {"query": "Alzheimer's disease amyloid treatments", "expected_domain": DOMAIN_NEUROLOGY},
    {"query": "Parkinson's disease surgical options", "expected_domain": DOMAIN_NEUROLOGY},
]

# JSON schema the RAG answer envelope must satisfy
RAG_ANSWER_SCHEMA_KEYS = {"query", "results", "total"}
RAG_RESULT_ITEM_KEYS = {"id", "document", "metadata", "score"}

COLLECTION_NAME = f"rag_smoke_test_{uuid.uuid4().hex[:8]}"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def chroma_store():
    """Create an ephemeral ChromaVectorStore for smoke testing.

    Uses embedded (in-memory) mode so no running server is required.
    Falls back to a temp dir if CHROMA_HOST is not set.
    """
    from vectordb.chroma_client import ChromaVectorStore

    # Force ephemeral / embedded mode for CI
    store = ChromaVectorStore(persist_dir=None, host=None, port=8000)
    # Override _get_client to use purely in-memory Chroma
    import chromadb
    store._client = chromadb.Client()

    yield store

    # Cleanup
    try:
        store.delete_collection(COLLECTION_NAME)
    except Exception:
        pass


@pytest.fixture(scope="module")
def ingested_store(chroma_store):
    """Ingest SMOKE_DOCUMENTS into the test collection."""
    ids = [d["id"] for d in SMOKE_DOCUMENTS]
    texts = [d["text"] for d in SMOKE_DOCUMENTS]
    metadatas = [d["metadata"] for d in SMOKE_DOCUMENTS]

    # Use Chroma's default embedder (all-MiniLM-L6-v2 sentence-transformers)
    collection = chroma_store._get_client().get_or_create_collection(
        name=COLLECTION_NAME,
    )
    collection.add(
        ids=ids,
        documents=texts,
        metadatas=metadatas,
    )

    return chroma_store, collection


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_answer_envelope(query: str, results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build a standardised RAG answer envelope."""
    return {
        "query": query,
        "results": results,
        "total": len(results),
    }


def _validate_schema(envelope: Dict[str, Any]) -> List[str]:
    """Validate the answer envelope against the expected schema. Return errors."""
    errors: List[str] = []
    missing_top = RAG_ANSWER_SCHEMA_KEYS - set(envelope.keys())
    if missing_top:
        errors.append(f"Missing top-level keys: {missing_top}")

    if not isinstance(envelope.get("results"), list):
        errors.append("'results' is not a list")
        return errors

    for i, item in enumerate(envelope["results"]):
        missing_item = RAG_RESULT_ITEM_KEYS - set(item.keys())
        if missing_item:
            errors.append(f"Result[{i}] missing keys: {missing_item}")
        if "score" in item and not isinstance(item["score"], (int, float)):
            errors.append(f"Result[{i}].score is not a number")
        if "metadata" in item and not isinstance(item["metadata"], dict):
            errors.append(f"Result[{i}].metadata is not a dict")

    return errors


# ---------------------------------------------------------------------------
# Smoke Tests
# ---------------------------------------------------------------------------

class TestRagSmoke:
    """Minimal RAG regression smoke tests."""

    # ── Ingestion sanity ──────────────────────────────────────────────────

    @pytest.mark.rag_smoke
    def test_ingestion_count(self, ingested_store):
        """All 10 documents are stored in ChromaDB."""
        _, collection = ingested_store
        assert collection.count() == len(SMOKE_DOCUMENTS), (
            f"Expected {len(SMOKE_DOCUMENTS)} docs, got {collection.count()}"
        )

    @pytest.mark.rag_smoke
    def test_ingestion_ids_present(self, ingested_store):
        """Every expected doc ID is retrievable."""
        _, collection = ingested_store
        expected_ids = [d["id"] for d in SMOKE_DOCUMENTS]
        result = collection.get(ids=expected_ids)
        assert set(result["ids"]) == set(expected_ids)

    # ── Retrieval — non-empty context ─────────────────────────────────────

    @pytest.mark.rag_smoke
    @pytest.mark.parametrize("qobj", SMOKE_QUERIES, ids=[q["query"][:40] for q in SMOKE_QUERIES])
    def test_retrieval_non_empty(self, ingested_store, qobj):
        """Each query returns at least 1 result (non-empty context)."""
        _, collection = ingested_store
        results = collection.query(
            query_texts=[qobj["query"]],
            n_results=5,
            include=["documents", "metadatas", "distances"],
        )
        assert results["ids"][0], f"No results for query: {qobj['query']}"
        assert results["documents"][0], "Retrieved documents are empty"

    # ── Retrieval — citations / IDs present ───────────────────────────────

    @pytest.mark.rag_smoke
    @pytest.mark.parametrize("qobj", SMOKE_QUERIES, ids=[q["query"][:40] for q in SMOKE_QUERIES])
    def test_citations_present(self, ingested_store, qobj):
        """Each result has a valid document ID (citation)."""
        _, collection = ingested_store
        results = collection.query(
            query_texts=[qobj["query"]],
            n_results=5,
            include=["documents", "metadatas", "distances"],
        )
        for doc_id in results["ids"][0]:
            assert doc_id.startswith("smoke-doc-"), (
                f"Unexpected doc ID format: {doc_id}"
            )

    # ── Retrieval — domain filtering ──────────────────────────────────────

    @pytest.mark.rag_smoke
    @pytest.mark.parametrize("qobj", SMOKE_QUERIES, ids=[q["query"][:40] for q in SMOKE_QUERIES])
    def test_domain_filtering(self, ingested_store, qobj):
        """Filtering by domain_id returns only docs from that domain."""
        _, collection = ingested_store
        results = collection.query(
            query_texts=[qobj["query"]],
            n_results=5,
            where={"domain_id": qobj["expected_domain"]},
            include=["documents", "metadatas", "distances"],
        )
        for meta in results["metadatas"][0]:
            assert meta["domain_id"] == qobj["expected_domain"], (
                f"Got domain {meta['domain_id']}, expected {qobj['expected_domain']}"
            )

    # ── Retrieval — permissions filtering ─────────────────────────────────

    @pytest.mark.rag_smoke
    def test_permissions_filtering(self, ingested_store):
        """Filtering by permissions='restricted' only returns restricted docs."""
        _, collection = ingested_store
        results = collection.query(
            query_texts=["disease risk factors and treatment"],
            n_results=10,
            where={"permissions": "restricted"},
            include=["metadatas"],
        )
        for meta in results["metadatas"][0]:
            assert meta["permissions"] == "restricted"

    # ── Answer JSON schema validation ─────────────────────────────────────

    @pytest.mark.rag_smoke
    @pytest.mark.parametrize("qobj", SMOKE_QUERIES, ids=[q["query"][:40] for q in SMOKE_QUERIES])
    def test_answer_json_schema(self, ingested_store, qobj):
        """The answer envelope matches the expected JSON schema."""
        _, collection = ingested_store
        raw = collection.query(
            query_texts=[qobj["query"]],
            n_results=5,
            include=["documents", "metadatas", "distances"],
        )
        # Build the answer envelope the same way the service would
        result_items = []
        if raw["ids"][0]:
            for i, doc_id in enumerate(raw["ids"][0]):
                dist = raw["distances"][0][i] if raw.get("distances") else 0.0
                score = 1.0 / (1.0 + dist) if dist >= 0 else 0.0
                result_items.append({
                    "id": doc_id,
                    "document": raw["documents"][0][i] if raw.get("documents") else "",
                    "metadata": raw["metadatas"][0][i] if raw.get("metadatas") else {},
                    "score": score,
                })
        envelope = _build_answer_envelope(qobj["query"], result_items)
        errors = _validate_schema(envelope)
        assert not errors, f"Schema validation failed: {errors}"

    # ── Serialisation round-trip ──────────────────────────────────────────

    @pytest.mark.rag_smoke
    def test_answer_json_roundtrip(self, ingested_store):
        """Answer envelope survives JSON serialisation round-trip."""
        _, collection = ingested_store
        raw = collection.query(
            query_texts=["cardiac arrhythmia treatment options"],
            n_results=3,
            include=["documents", "metadatas", "distances"],
        )
        items = []
        for i, doc_id in enumerate(raw["ids"][0]):
            dist = raw["distances"][0][i] if raw.get("distances") else 0.0
            items.append({
                "id": doc_id,
                "document": raw["documents"][0][i],
                "metadata": raw["metadatas"][0][i],
                "score": 1.0 / (1.0 + dist),
            })
        envelope = _build_answer_envelope("cardiac arrhythmia treatment options", items)
        serialized = json.dumps(envelope)
        deserialized = json.loads(serialized)
        assert deserialized == envelope
        assert _validate_schema(deserialized) == []
