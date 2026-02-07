"""
BM25-lite: lightweight pure-Python BM25 scoring for post-retrieval reranking.

No external dependencies. Runs over the top-N semantic results returned by
ChromaDB and blends BM25 keyword scores with the original semantic scores.

PHI-safe: operates on chunk text only for scoring — no content is logged.
"""
from __future__ import annotations

import math
from typing import Dict, List


def _tokenize(text: str) -> List[str]:
    """Lowercase whitespace-split tokenization — deliberately simple."""
    return text.lower().split()


def bm25_rerank(
    query: str,
    chunks: List[Dict],
    *,
    text_key: str = "text",
    k1: float = 1.5,
    b: float = 0.75,
    semantic_weight: float = 0.5,
) -> List[Dict]:
    """
    Score *already-retrieved* chunks with BM25-lite and blend with their
    existing semantic ``score``.

    Each chunk dict is expected to have:
        - ``score``  (float)  — semantic similarity from ChromaDB
        - ``<text_key>`` (str) — chunk text

    Returns the same list **sorted by blended score descending**, with
    ``bm25Score`` and ``semanticScore`` injected into each chunk's
    ``metadata`` (backward-compatible).

    Parameters
    ----------
    query : str
        The user query to score against.
    chunks : list[dict]
        Retrieved chunks, each with at least ``score`` and ``text_key``.
    text_key : str
        Key in chunk dict that holds the text content.
    k1 : float
        BM25 term-frequency saturation parameter.
    b : float
        BM25 document-length normalization parameter.
    semantic_weight : float
        Weight for the semantic component in [0, 1].
        ``blended = semantic_weight * sem + (1 - semantic_weight) * norm_bm25``
    """
    if not chunks:
        return chunks

    query_terms = _tokenize(query)
    if not query_terms:
        # No query terms → can't compute BM25, return as-is
        for ch in chunks:
            meta = ch.get("metadata", {})
            meta["semanticScore"] = round(ch.get("score", 0.0), 6)
            meta["bm25Score"] = 0.0
            ch["metadata"] = meta
        return chunks

    # ── corpus-level stats (over the retrieved window only) ──
    n_docs = len(chunks)
    doc_tokens: List[List[str]] = []
    doc_tf: List[Dict[str, int]] = []

    for ch in chunks:
        tokens = _tokenize(ch.get(text_key, "") or "")
        doc_tokens.append(tokens)
        tf: Dict[str, int] = {}
        for t in tokens:
            tf[t] = tf.get(t, 0) + 1
        doc_tf.append(tf)

    avg_dl = sum(len(t) for t in doc_tokens) / max(n_docs, 1)

    # document frequency for query terms only
    df: Dict[str, int] = {}
    for term in set(query_terms):
        df[term] = sum(1 for tf in doc_tf if term in tf)

    # ── per-chunk BM25 score ──
    raw_scores: List[float] = []
    for i in range(n_docs):
        dl = len(doc_tokens[i])
        score = 0.0
        for term in query_terms:
            tf_val = doc_tf[i].get(term, 0)
            if tf_val == 0:
                continue
            d = df.get(term, 0)
            idf = math.log((n_docs - d + 0.5) / (d + 0.5) + 1.0)
            tf_norm = (tf_val * (k1 + 1)) / (
                tf_val + k1 * (1 - b + b * (dl / max(avg_dl, 1)))
            )
            score += idf * tf_norm
        raw_scores.append(score)

    # ── normalise BM25 to [0, 1] ──
    max_bm25 = max(raw_scores) if raw_scores else 1.0
    if max_bm25 == 0:
        max_bm25 = 1.0
    norm_scores = [s / max_bm25 for s in raw_scores]

    # ── blend & annotate ──
    for i, ch in enumerate(chunks):
        sem = ch.get("score", 0.0)
        bm25 = norm_scores[i]
        blended = semantic_weight * sem + (1 - semantic_weight) * bm25

        ch["score"] = blended

        meta = ch.get("metadata", {})
        meta["semanticScore"] = round(sem, 6)
        meta["bm25Score"] = round(bm25, 6)
        ch["metadata"] = meta

    # sort descending by blended score
    chunks.sort(key=lambda c: c.get("score", 0.0), reverse=True)
    return chunks
