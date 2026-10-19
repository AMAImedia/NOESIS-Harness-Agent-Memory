"""Layered retrieval ladder for the NOESIS harness agent memory.

Patterns borrowed from the Go project ``deja-vu``:
- ``internal/index/retrieval.go`` (``searchDetailedOnce``) -- the explicit
  tier ladder EXACT -> PREFIX -> SUBSTRING -> FUZZY -> RELEVANCE that returns
  the first tier with any hits.
- ``internal/search/search.go`` (``scoreBM25`` / ``freshnessDecay``) -- BM25
  relevance scoring over the corpus and a bounded recency multiplier.
- ``cmd/deja/mcp.go`` (byte budgets + ``cutMarker``) -- UTF-8-safe trimming of
  a payload to a byte budget with an explicit marker appended.

This module is pure and deterministic: no I/O, no global mutable state, no
LLM calls. Tokenization deduplicates tokens in first-seen order, all ranking
is a total order (score descending, then ``doc_id`` ascending), and byte
budgets are evaluated in encoded UTF-8 bytes so multibyte text is never split
mid-codepoint.

Tier semantics are deliberately disjoint so that every tier is reachable.
An exact token match is handled only by EXACT (all query tokens present) or by
RELEVANCE (some, but not all, query tokens present); PREFIX requires a doc
token that is strictly longer than, and starts with, a query token; SUBSTRING
requires a query token strictly inside a doc token; FUZZY requires a Damerau-
Levenshtein distance of at least one and at most ``max_edit_distance``.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple

_WORD_RE = re.compile(r"[^\W_]+", re.UNICODE)


class SearchTier(str, Enum):
    """Ordered retrieval tiers; earlier members are higher precedence."""

    EXACT = "exact"
    PREFIX = "prefix"
    SUBSTRING = "substring"
    FUZZY = "fuzzy"
    RELEVANCE = "relevance"


@dataclass(frozen=True)
class Hit:
    """A single ranked retrieval result.

    ``doc_id`` identifies the document, ``score`` is the tier-local relevance
    score (higher is better), and ``tier`` records which ladder step produced
    the hit.
    """

    doc_id: str
    score: float
    tier: SearchTier


def tokenize(text: str) -> List[str]:
    """Lowercase alphanumeric tokens, deduplicated in first-seen order.

    A token is a maximal run of Unicode word characters excluding the
    underscore, so ``foo_bar`` yields two tokens. Matching is case-insensitive
    because the text is lowercased before scanning. Empty or all-punctuation
    input yields an empty list.
    """
    if text is None:
        raise TypeError("tokenize requires a str, got None")
    seen = set()
    tokens = []
    for match in _WORD_RE.finditer(text.lower()):
        token = match.group(0)
        if token not in seen:
            seen.add(token)
            tokens.append(token)
    return tokens


def _idf(df: int, n_docs: int) -> float:
    if n_docs <= 0:
        return 0.0
    df = min(max(df, 0), n_docs)
    value = math.log(1.0 + (n_docs - df + 0.5) / (df + 0.5))
    return value if value > 0.0 else 0.0


def bm25_score(
    tf: int,
    df: int,
    doc_len: int,
    avg_doc_len: float,
    n_docs: int,
    k1: float = 1.2,
    b: float = 0.75,
) -> float:
    """Okapi BM25 score for one term in one document.

    ``tf`` is the term frequency in the document, ``df`` the document
    frequency across the corpus, ``doc_len`` the document token count,
    ``avg_doc_len`` the mean token count, and ``n_docs`` the corpus size.
    Degenerate inputs (empty corpus, zero term frequency, zero average length)
    degrade to ``0.0`` instead of raising.
    """
    if n_docs <= 0 or tf <= 0:
        return 0.0
    df = min(max(df, 0), n_docs)
    if avg_doc_len <= 0.0:
        avg_doc_len = 1.0
    idf = _idf(df, n_docs)
    if idf <= 0.0:
        return 0.0
    length_ratio = doc_len / avg_doc_len
    denominator = tf + k1 * (1.0 - b + b * length_ratio)
    if denominator <= 0.0:
        return 0.0
    return idf * (tf * (k1 + 1.0)) / denominator


def freshness_decay(age_days: float) -> float:
    """Recency multiplier bounded in ``(0.5, 1.0]``.

    ``age_days <= 0`` (fresh or future) yields ``1.0``. The value decreases
    monotonically and asymptotically approaches ``0.5`` for very old items.
    """
    if age_days is None:
        age_days = 0.0
    if age_days < 0.0:
        age_days = 0.0
    return 0.5 + 0.5 / (1.0 + age_days)


def trim_to_budget(
    text: str, budget_bytes: int, marker: str = "...[trimmed]"
) -> str:
    """Trim ``text`` so its UTF-8 encoding fits ``budget_bytes``.

    When the whole string fits it is returned unchanged. Otherwise the head is
    cut on a codepoint boundary and ``marker`` is appended, keeping the total
    encoded length at or below the budget whenever the marker itself can fit.
    If the budget is smaller than the marker, as much of the marker as fits is
    returned. Multibyte input (Cyrillic, CJK, emoji) never raises and never
    yields a split codepoint.
    """
    if text is None:
        raise TypeError("trim_to_budget requires a str, got None")
    if budget_bytes is None:
        return text
    if budget_bytes <= 0:
        return ""
    raw = text.encode("utf-8")
    if len(raw) <= budget_bytes:
        return text
    marker_bytes = marker.encode("utf-8")
    content_budget = budget_bytes - len(marker_bytes)
    if content_budget <= 0:
        return marker_bytes[:budget_bytes].decode("utf-8", errors="ignore")
    head = raw[:content_budget].decode("utf-8", errors="ignore")
    return head + marker


def damerau_levenshtein(
    a: str, b: str, max_distance: Optional[int] = None
) -> int:
    """Damerau-Levenshtein distance (optimal string alignment variant).

    Supports insertion, deletion, substitution, and transposition of two
    adjacent characters; a transposition costs ``1``. When ``max_distance`` is
    given the computation short-circuits and returns ``max_distance + 1`` as a
    bounded sentinel once the true distance is known to exceed it, which keeps
    fuzzy candidate checks cheap.
    """
    if a is None or b is None:
        raise TypeError("damerau_levenshtein requires two str values")
    len_a = len(a)
    len_b = len(b)
    if max_distance is not None and abs(len_a - len_b) > max_distance:
        return max_distance + 1
    if len_a == 0:
        return len_b
    if len_b == 0:
        return len_a

    previous_previous = None  # type: Optional[List[int]]
    previous = list(range(len_b + 1))
    for i in range(1, len_a + 1):
        current = [i] + [0] * len_b
        for j in range(1, len_b + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            value = min(
                previous[j] + 1,
                current[j - 1] + 1,
                previous[j - 1] + cost,
            )
            if (
                i > 1
                and j > 1
                and a[i - 1] == b[j - 2]
                and a[i - 2] == b[j - 1]
            ):
                transposed = previous_previous[j - 2] + 1
                if transposed < value:
                    value = transposed
            current[j] = value
        if max_distance is not None and min(current) > max_distance:
            return max_distance + 1
        previous_previous = previous
        previous = current
    return previous[len_b]


def _build_index(
    docs: Dict[str, str],
) -> Tuple[Dict[str, List[str]], Dict[str, int], Dict[str, int], float, int]:
    """Return ``(doc_tokens, df, doc_len, avg_doc_len, n_docs)``.

    ``doc_tokens`` maps each document to its deduplicated token list and
    ``df`` maps each token to the number of documents containing it.
    """
    doc_tokens = {}  # type: Dict[str, List[str]]
    df = {}  # type: Dict[str, int]
    doc_len = {}  # type: Dict[str, int]
    for doc_id, text in docs.items():
        tokens = tokenize(text)
        doc_tokens[doc_id] = tokens
        doc_len[doc_id] = len(tokens)
        for token in set(tokens):
            df[token] = df.get(token, 0) + 1
    n_docs = len(docs)
    total = sum(doc_len.values())
    avg_doc_len = (total / n_docs) if n_docs else 0.0
    return doc_tokens, df, doc_len, avg_doc_len, n_docs


def _tier_scores(
    doc_tokens: Dict[str, List[str]],
    doc_len: Dict[str, int],
    avg_doc_len: float,
    n_docs: int,
    query_tokens: List[str],
    match_tf,
) -> Dict[str, float]:
    """BM25-summed scores for every document matching ``match_tf``.

    ``match_tf(tokens, query_token)`` returns a positive term frequency when
    the document matches that query token under the tier's rule, else ``0``.
    """
    df_query = {}  # type: Dict[str, int]
    for query_token in query_tokens:
        count = 0
        for tokens in doc_tokens.values():
            if match_tf(tokens, query_token) > 0:
                count += 1
        df_query[query_token] = count

    scores = {}  # type: Dict[str, float]
    for doc_id, tokens in doc_tokens.items():
        total = 0.0
        for query_token in query_tokens:
            tf = match_tf(tokens, query_token)
            if tf > 0:
                total += bm25_score(
                    tf, df_query[query_token], doc_len[doc_id], avg_doc_len, n_docs
                )
        if total > 0.0:
            scores[doc_id] = total
    return scores


def _exact_matcher(tokens: List[str], query_token: str) -> int:
    for token in tokens:
        if token == query_token:
            return 1
    return 0


def _prefix_matcher(tokens: List[str], query_token: str) -> int:
    count = 0
    for token in tokens:
        if token != query_token and token.startswith(query_token):
            count += 1
    return count


def _substring_matcher(tokens: List[str], query_token: str) -> int:
    count = 0
    for token in tokens:
        if (
            token != query_token
            and not token.startswith(query_token)
            and query_token in token
        ):
            count += 1
    return count


def _fuzzy_matcher(max_distance: int):
    def matcher(tokens: List[str], query_token: str) -> int:
        count = 0
        for token in tokens:
            if token == query_token:
                continue
            distance = damerau_levenshtein(token, query_token, max_distance)
            if 1 <= distance <= max_distance:
                count += 1
        return count

    return matcher


def _relevance_scores(
    doc_tokens: Dict[str, List[str]],
    df: Dict[str, int],
    n_docs: int,
    query_tokens: List[str],
) -> Dict[str, float]:
    """IDF-weighted score for documents sharing at least one query token."""
    scores = {}  # type: Dict[str, float]
    for doc_id, tokens in doc_tokens.items():
        token_set = set(tokens)
        total = 0.0
        for query_token in query_tokens:
            if query_token in token_set:
                total += _idf(df.get(query_token, 0), n_docs)
        if total > 0.0:
            scores[doc_id] = total
    return scores


def _order_hits(scores: Dict[str, float], tier: SearchTier) -> List[Hit]:
    hits = [Hit(doc_id, score, tier) for doc_id, score in scores.items()]
    hits.sort(key=lambda hit: (-hit.score, hit.doc_id))
    return hits


def search_tiered(
    docs: Dict[str, str],
    query: str,
    limit: int = 10,
    max_edit_distance: int = 2,
) -> List[Hit]:
    """Run the retrieval ladder and return hits from the first non-empty tier.

    Tiers are tried in order EXACT, PREFIX, SUBSTRING, FUZZY, RELEVANCE. The
    first tier producing any hit wins, so an exact match always outranks a
    prefix match, a prefix match outranks a fuzzy match, and so on. Results are
    sorted by score descending then ``doc_id`` ascending, and truncated to
    ``limit`` (a non-positive ``limit`` is treated as no limit). An empty query
    or empty corpus yields ``[]``.
    """
    if not docs:
        return []
    query_tokens = tokenize(query)
    if not query_tokens:
        return []

    doc_tokens, df, doc_len, avg_doc_len, n_docs = _build_index(docs)

    exact_scores = _tier_scores(
        doc_tokens, doc_len, avg_doc_len, n_docs, query_tokens, _exact_matcher
    )
    exact_scores = {
        doc_id: score
        for doc_id, score in exact_scores.items()
        if all(_exact_matcher(doc_tokens[doc_id], token) > 0 for token in query_tokens)
    }
    if exact_scores:
        return _truncate(_order_hits(exact_scores, SearchTier.EXACT), limit)

    prefix_scores = _tier_scores(
        doc_tokens, doc_len, avg_doc_len, n_docs, query_tokens, _prefix_matcher
    )
    if prefix_scores:
        return _truncate(_order_hits(prefix_scores, SearchTier.PREFIX), limit)

    substring_scores = _tier_scores(
        doc_tokens, doc_len, avg_doc_len, n_docs, query_tokens, _substring_matcher
    )
    if substring_scores:
        return _truncate(_order_hits(substring_scores, SearchTier.SUBSTRING), limit)

    if max_edit_distance > 0:
        fuzzy_scores = _tier_scores(
            doc_tokens,
            doc_len,
            avg_doc_len,
            n_docs,
            query_tokens,
            _fuzzy_matcher(max_edit_distance),
        )
        if fuzzy_scores:
            return _truncate(_order_hits(fuzzy_scores, SearchTier.FUZZY), limit)

    relevance_scores = _relevance_scores(doc_tokens, df, n_docs, query_tokens)
    return _truncate(_order_hits(relevance_scores, SearchTier.RELEVANCE), limit)


def _truncate(hits: List[Hit], limit: int) -> List[Hit]:
    if limit is None or limit <= 0:
        return hits
    return hits[:limit]


def rank_with_relevance_tail(
    hits: List[Hit],
    docs: Dict[str, str],
    query: str,
    lead: float = 0.1,
) -> List[Hit]:
    """Attach a bounded relevance tail below the exact matches.

    Any non-exact hit is clamped so its score is at most
    ``min(exact_scores) - lead``; documents that match some but not all query
    tokens are then added as RELEVANCE hits under the same ceiling. This keeps
    every lower-tier match strictly below every exact match by at least
    ``lead`` in score. When there are no exact hits the input hits and the
    relevance candidates are merged untouched. Duplicate ``doc_id`` values keep
    their highest-precedence (first supplied) tier. The result is sorted by
    score descending then ``doc_id`` ascending and is deterministic.
    """
    if hits is None:
        hits = []
    exact_scores = [hit.score for hit in hits if hit.tier is SearchTier.EXACT]
    ceiling = (min(exact_scores) - lead) if exact_scores else None

    merged = []  # type: List[Hit]
    seen = set()
    for hit in hits:
        if hit.doc_id in seen:
            continue
        seen.add(hit.doc_id)
        if ceiling is not None and hit.tier is not SearchTier.EXACT:
            if hit.score > ceiling:
                hit = Hit(hit.doc_id, ceiling, hit.tier)
        merged.append(hit)

    query_tokens = tokenize(query)
    if query_tokens:
        doc_tokens, df, _doc_len, _avg, n_docs = _build_index(docs)
        relevance = _relevance_scores(doc_tokens, df, n_docs, query_tokens)
        for doc_id in sorted(relevance):
            if doc_id in seen:
                continue
            seen.add(doc_id)
            score = relevance[doc_id]
            if ceiling is not None and score > ceiling:
                score = ceiling
            merged.append(Hit(doc_id, score, SearchTier.RELEVANCE))

    merged.sort(key=lambda hit: (-hit.score, hit.doc_id))
    return merged


__all__ = [
    "Hit",
    "SearchTier",
    "bm25_score",
    "damerau_levenshtein",
    "freshness_decay",
    "rank_with_relevance_tail",
    "search_tiered",
    "tokenize",
    "trim_to_budget",
]
