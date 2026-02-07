"""BM25-lite scoring over a candidate list. Pure Python, no extra dependencies."""
from __future__ import annotations

import math
from collections import defaultdict
from typing import Dict, List, Tuple


def tokenize(text: str) -> List[str]:
    """Lowercase and split on whitespace."""
    return (text or "").lower().split()


def score_candidates(
    query: str,
    candidates: List[Tuple[str, str]],
    k1: float = 1.5,
    b: float = 0.75,
) -> Dict[str, float]:
    """
    Compute BM25 score for each candidate (chunk_id, text) against the query.
    Corpus = the candidate list only. Returns chunk_id -> raw BM25 score.
    """
    if not candidates:
        return {}

    doc_lengths: Dict[str, int] = {}
    term_freqs: Dict[str, Dict[str, int]] = {}
    doc_freqs: Dict[str, int] = defaultdict(int)

    for chunk_id, text in candidates:
        terms = tokenize(text)
        doc_lengths[chunk_id] = len(terms)
        term_counts: Dict[str, int] = defaultdict(int)
        seen = set()
        for t in terms:
            term_counts[t] += 1
            if t not in seen:
                doc_freqs[t] += 1
                seen.add(t)
        term_freqs[chunk_id] = dict(term_counts)

    n_docs = len(candidates)
    total_len = sum(doc_lengths.values())
    avg_dl = total_len / n_docs if n_docs else 0.0
    if avg_dl <= 0:
        avg_dl = 1.0

    query_terms = tokenize(query)
    out: Dict[str, float] = {}

    for chunk_id, text in candidates:
        doc_len = doc_lengths.get(chunk_id, 0)
        tf_map = term_freqs.get(chunk_id, {})
        score = 0.0
        for term in query_terms:
            if term not in tf_map:
                continue
            tf = tf_map[term]
            df = doc_freqs.get(term, 1)
            idf = math.log((n_docs - df + 0.5) / (df + 0.5) + 1.0)
            tf_norm = (tf * (k1 + 1)) / (
                tf + k1 * (1 - b + b * (doc_len / avg_dl))
            )
            score += idf * tf_norm
        out[chunk_id] = score

    return out
