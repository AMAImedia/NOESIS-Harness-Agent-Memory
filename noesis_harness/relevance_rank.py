"""noesis_harness/relevance_rank.py

Local, deterministic, read-only BM25-ish document ranker.

Patterns adapted from:
  - agentmemory  (deterministic term-frequency / inverse-document-frequency
                 scoring over a fixed corpus, no embeddings, no LLM)
  - LoopX        (replay projection: derive a read-only scoring view by folding
                 the corpus without mutating it)

This module ranks a list of documents against a query using a BM25-style
tf-idf-lite score. It is fully offline: no LLM call, no external search backend,
and no mutation of the input corpus. Given a query string and a list of
documents (each a dict with at least an ``id`` and a ``text`` field) it returns
the identifiers of the ``top_k`` documents in descending relevance order.

Design guarantees (see AGENTS.md):
  - Read-only: never mutates the input documents or the corpus order.
  - Deterministic: pure/stateless; identical inputs -> identical ranking.
  - Idempotent: ranking has no side effects.
  - Immutable result: the returned id list is a fresh copy.
  - Python 3.9+ syntax: no `X | None`, no `match`.

Zero dependencies (stdlib only): math, re.
"""

from __future__ import annotations

import math
import re
from typing import Any, Dict, List

_TOKEN_RE = re.compile(r"[a-z0-9_]+")

_K1 = 1.5
_B = 0.75


def _tokenize(text: str) -> List[str]:
    """Lowercase token list (preserving frequency) for deterministic scoring."""
    return _TOKEN_RE.findall((text or "").lower())


def rank(query: str, docs: List[Dict[str, Any]], top_k: int = 10) -> List[Any]:
    """Rank documents against a query and return the top_k document ids.

    Computes a BM25-style tf-idf-lite relevance score for each document using
    only term frequencies and inverse document frequencies over the supplied
    corpus. Documents are scored in a single read-only pass; the input ``docs``
    list is never mutated.

    Args:
        query: the query string; tokens are extracted deterministically.
        docs: list of documents, each a dict with at least ``id`` and ``text``.
        top_k: maximum number of ids to return (non-negative). When top_k is
            greater than or equal to the number of documents, all ranked ids are
            returned. When 0, an empty list is returned.

    Returns:
        A fresh list of document ids ordered by descending score. Ties are broken
        by ascending original document index so the result is fully deterministic.

    Notes:
        - An empty ``docs`` list returns an empty list.
        - A query with no overlapping terms yields an empty result.
        - Duplicate document ids are preserved; both entries are scored and
          ranked independently.
    """
    if top_k <= 0 or not docs:
        return []

    query_tokens = _tokenize(query)
    if not query_tokens:
        return []

    n_docs = len(docs)

    # Document frequency per term across the corpus (for idf).
    doc_freq: Dict[str, int] = {}
    # Per-document term frequencies and lengths, computed once.
    doc_tf: List[Dict[str, int]] = []
    doc_len: List[int] = []

    for doc in docs:
        text = doc.get("text", "")
        tokens = _tokenize(text)
        tf: Dict[str, int] = {}
        for tok in tokens:
            tf[tok] = tf.get(tok, 0) + 1
        doc_tf.append(tf)
        doc_len.append(len(tokens))
        for term in tf:
            doc_freq[term] = doc_freq.get(term, 0) + 1

    avg_len = (sum(doc_len) / n_docs) if n_docs else 0.0

    # Score each document against the query tokens.
    scored = []
    for idx, tf in enumerate(doc_tf):
        score = 0.0
        dl = doc_len[idx]
        for qtok in query_tokens:
            df = doc_freq.get(qtok, 0)
            if df == 0:
                continue
            f = tf.get(qtok, 0)
            if f == 0:
                continue
            # BM25 inverse document frequency (smoothed).
            idf = math.log(1.0 + (n_docs - df + 0.5) / (df + 0.5))
            denom = f + _K1 * (1.0 - _B + _B * (dl / avg_len if avg_len else 0.0))
            score += idf * (f * (_K1 + 1.0)) / denom
        # A zero score means no query term is present in this document; it is
        # not relevant and is excluded from the ranking entirely.
        if score > 0.0:
            scored.append((score, idx, docs[idx].get("id")))

    # Sort by score desc, then by original index asc for deterministic ties.
    scored.sort(key=lambda entry: (-entry[0], entry[1]))

    return [entry[2] for entry in scored[:top_k]]


__all__ = ["rank"]
