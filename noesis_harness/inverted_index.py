"""Prefix-sharded inverted index with delta-varint postings and BM25 scoring.

Provenance / pattern source:
- Go repository ``deja-vu`` (internal/index/cjkindex.go ``bucket()``,
  store_io.go ``encodePostings``/``decodePostings``, internal/search/search.go
  ``scoreBM25``). The prefix-sharding scheme, delta-varint posting encoding and
  BM25 objective are ported here in a pure-stdlib, deterministic form.

This module is stdlib-only and deterministic. The index lives in memory as a
dict of token -> postings, sharded for introspection via :func:`bucket`.
Persistence is optional JSON (atomic temp file + ``os.replace``); loading
rebuilds the index from the stored documents so results are reproducible.

Python 3.9 compatible.
"""

from __future__ import annotations

import gzip
import json
import math
import os
import re
import tempfile
from typing import Dict, List, Tuple

__all__ = [
    "STOPWORDS",
    "tokenize",
    "bucket",
    "encode_postings",
    "decode_postings",
    "bm25_score",
    "InvertedIndex",
]

# Small English stopword list. Kept intentionally short and frozen for stable,
# deterministic behavior across runs and interpreters.
STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "but",
        "by",
        "for",
        "from",
        "had",
        "has",
        "have",
        "he",
        "her",
        "his",
        "i",
        "if",
        "in",
        "into",
        "is",
        "it",
        "its",
        "me",
        "my",
        "no",
        "not",
        "of",
        "on",
        "or",
        "our",
        "she",
        "so",
        "that",
        "the",
        "their",
        "them",
        "then",
        "there",
        "these",
        "they",
        "this",
        "to",
        "up",
        "us",
        "was",
        "we",
        "were",
        "what",
        "when",
        "which",
        "who",
        "will",
        "with",
        "you",
        "your",
    }
)

_ALNUM_RUN = re.compile(r"[^\W_]+", re.UNICODE)

# FNV-1a 32-bit constants.
_FNV_OFFSET_BASIS = 2166136261
_FNV_PRIME = 16777619
_FNV_MASK = 0xFFFFFFFF


def _token_stream(text: str) -> List[str]:
    """Return every kept token (with repeats) in first-seen order.

    Kept tokens are lowercased alphanumeric runs longer than one character and
    absent from :data:`STOPWORDS`. This is the shared primitive behind
    :func:`tokenize` (which dedupes) and index term-frequency counting (which
    must not).
    """
    if text is None:
        raise TypeError("tokenize requires a str, got None")
    result: List[str] = []
    for raw in _ALNUM_RUN.findall(text.lower()):
        if len(raw) < 2:
            continue
        if raw in STOPWORDS:
            continue
        result.append(raw)
    return result


def tokenize(text: str) -> List[str]:
    """Lowercase, split on non-alphanumeric, drop stopwords and singletons.

    Tokens are first-seen ordered and deduplicated: repeated terms appear once
    at the position of their first occurrence. Single-character tokens and
    members of :data:`STOPWORDS` are removed. ``text`` is lowercased before
    splitting, so "Hello Hello world" yields ``["hello", "world"]``.
    """
    seen: Dict[str, None] = {}
    result: List[str] = []
    for raw in _token_stream(text):
        if raw not in seen:
            seen[raw] = None
            result.append(raw)
    return result


def _fnv1a_32(data: bytes) -> int:
    """Return the FNV-1a 32-bit hash of ``data`` as an unsigned int."""
    h = _FNV_OFFSET_BASIS
    for byte in data:
        h ^= byte
        h = (h * _FNV_PRIME) & _FNV_MASK
    return h


def bucket(token: str) -> str:
    """Return the ASCII prefix shard key for ``token``.

    If the token begins with at least two ASCII alphanumeric characters, the
    first two characters lowercased are used (e.g. ``"Hello"`` -> ``"he"``).
    Otherwise the token is hashed with FNV-1a 32-bit over its first three
    characters; the hash mod 256 is formatted as two lowercase hex digits
    (``"00"``..``"ff"``). The result is deterministic for a given token.
    """
    if token is None:
        raise TypeError("bucket requires a str, got None")
    if (
        len(token) >= 2
        and token[0].isascii()
        and token[0].isalnum()
        and token[1].isascii()
        and token[1].isalnum()
    ):
        return token[:2].lower()
    digest = _fnv1a_32(token[:3].encode("utf-8")) & _FNV_MASK
    return "%02x" % (digest % 256)


def _encode_uvarint(value: int, out: bytearray) -> None:
    """Append an unsigned LEB128 varint for a non-negative ``value``."""
    if value < 0:
        raise ValueError("unsigned varint requires a non-negative value")
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            return


def _decode_uvarint(data: bytes, pos: int) -> Tuple[int, int]:
    """Decode one unsigned varint; return (value, next_position)."""
    result = 0
    shift = 0
    while True:
        if pos >= len(data):
            raise ValueError("truncated varint stream")
        byte = data[pos]
        pos += 1
        result |= (byte & 0x7F) << shift
        if not (byte & 0x80):
            return result, pos
        shift += 7


def _zigzag_encode(value: int) -> int:
    """Map a signed int to an unsigned one (small magnitude -> small uint)."""
    if value >= 0:
        return value << 1
    return ((-value) << 1) - 1


def _zigzag_decode(value: int) -> int:
    """Inverse of :func:`_zigzag_encode`."""
    return (value >> 1) ^ -(value & 1)


def encode_postings(postings: List[Tuple[int, int]]) -> bytes:
    """Encode ``(doc_ordinal, offset)`` postings as delta-varints.

    Postings are sorted by ``(doc_ordinal, offset)`` and deduplicated before
    encoding. Each entry stores the non-negative delta of the doc ordinal
    (unsigned varint) followed by the zigzag-encoded delta of the offset
    (unsigned varint), so negative offset deltas round-trip. Empty input
    yields ``b""``.
    """
    ordered = sorted(set((int(d), int(o)) for d, o in postings))
    out = bytearray()
    prev_doc = 0
    prev_off = 0
    for doc, off in ordered:
        doc_delta = doc - prev_doc
        if doc_delta < 0:
            raise ValueError("postings must not decrease in doc ordinal")
        off_delta = off - prev_off
        _encode_uvarint(doc_delta, out)
        _encode_uvarint(_zigzag_encode(off_delta), out)
        prev_doc = doc
        prev_off = off
    return bytes(out)


def decode_postings(data: bytes) -> List[Tuple[int, int]]:
    """Decode bytes produced by :func:`encode_postings`.

    Returns a list of ``(doc_ordinal, offset)`` tuples in ascending doc order.
    ``b""`` decodes to ``[]``. A truncated stream raises ``ValueError``.
    """
    if data is None:
        raise TypeError("decode_postings requires bytes, got None")
    result: List[Tuple[int, int]] = []
    pos = 0
    prev_doc = 0
    prev_off = 0
    total = len(data)
    while pos < total:
        doc_delta, pos = _decode_uvarint(data, pos)
        zz, pos = _decode_uvarint(data, pos)
        prev_doc += doc_delta
        prev_off += _zigzag_decode(zz)
        result.append((prev_doc, prev_off))
    return result


def bm25_score(
    tf: int,
    df: int,
    doc_len: int,
    avg_doc_len: float,
    n_docs: int,
    k1: float = 1.2,
    b: float = 0.75,
) -> float:
    """Return the BM25 contribution of one term in one document.

    ``IDF = ln(1 + (N - df + 0.5) / (df + 0.5))`` and the saturated term
    frequency weight is ``tf * (k1 + 1) / (tf + k1 * (1 - b + b * dl / avgdl))``.
    Returns ``0.0`` whenever a denominator would be zero (empty corpus,
    zero average length, zero tf, or degenerate parameters).
    """
    if n_docs <= 0 or df <= 0 or tf <= 0:
        return 0.0
    if avg_doc_len <= 0.0 or doc_len < 0:
        return 0.0
    denom_idf = df + 0.5
    if denom_idf == 0.0:
        return 0.0
    idf = math.log(1.0 + (n_docs - df + 0.5) / denom_idf)
    norm = k1 * (1.0 - b + b * (float(doc_len) / float(avg_doc_len)))
    denom_tf = tf + norm
    if denom_tf == 0.0:
        return 0.0
    return idf * (tf * (k1 + 1.0)) / denom_tf


class InvertedIndex:
    """In-memory term index with BM25 ranking and optional JSON persistence.

    Documents are added with :meth:`add`, which assigns a stable ordinal in
    insertion order. A duplicate ``doc_id`` is idempotent: the first text wins
    and the existing ordinal is returned. Postings are stored per token as
    ``{ordinal: term_frequency}``.
    """

    SCHEMA = "noesis.inverted_index.v1"

    def __init__(self) -> None:
        self._docs: Dict[str, str] = {}
        self._ordinals: Dict[str, int] = {}
        self._order: List[str] = []
        self._postings: Dict[str, Dict[int, int]] = {}
        self._doc_len: Dict[int, int] = {}
        self._df: Dict[str, int] = {}

    # -- building ---------------------------------------------------------
    def add(self, doc_id: str, text: str) -> int:
        """Add a document and return its assigned ordinal.

        Adding an existing ``doc_id`` returns the previously assigned ordinal
        without modifying stored text (idempotent).
        """
        if doc_id is None:
            raise TypeError("doc_id must be a str")
        if text is None:
            raise TypeError("text must be a str")
        if doc_id in self._ordinals:
            return self._ordinals[doc_id]
        ordinal = len(self._order)
        self._ordinals[doc_id] = ordinal
        self._order.append(doc_id)
        self._docs[doc_id] = text
        tokens = _token_stream(text)
        self._doc_len[ordinal] = len(tokens)
        for token in tokens:
            posting = self._postings.get(token)
            if posting is None:
                posting = {}
                self._postings[token] = posting
                self._df[token] = 0
            if ordinal in posting:
                posting[ordinal] += 1
            else:
                posting[ordinal] = 1
                self._df[token] += 1
        return ordinal

    # -- inspection -------------------------------------------------------
    def postings(self, token: str) -> List[Tuple[int, int]]:
        """Return ``(doc_ordinal, term_frequency)`` pairs for ``token``."""
        posting = self._postings.get(token)
        if not posting:
            return []
        return sorted(posting.items())

    def doc_frequency(self, token: str) -> int:
        """Return the number of distinct documents containing ``token``."""
        return self._df.get(token, 0)

    def num_docs(self) -> int:
        """Return the number of indexed documents."""
        return len(self._order)

    def doc_text(self, doc_id: str) -> str:
        """Return the stored text for ``doc_id`` (raises ``KeyError``)."""
        return self._docs[doc_id]

    def buckets(self) -> Dict[str, int]:
        """Return ``bucket -> number of distinct tokens`` for introspection."""
        counts: Dict[str, int] = {}
        for token in self._postings:
            key = bucket(token)
            counts[key] = counts.get(key, 0) + 1
        return counts

    # -- search -----------------------------------------------------------
    def search(self, query: str, limit: int = 10) -> List[Tuple[str, float]]:
        """Rank documents for ``query`` using BM25.

        Returns ``(doc_id, score)`` tuples sorted by score descending and then
        by ``doc_id`` ascending (deterministic tie-break). An empty query, an
        empty index, or a non-positive ``limit`` yields ``[]``.
        """
        if limit <= 0 or not self._order:
            return []
        terms = tokenize(query)
        if not terms:
            return []
        n_docs = len(self._order)
        total_len = sum(self._doc_len.values())
        avg_doc_len = float(total_len) / float(n_docs) if n_docs else 0.0
        scores: Dict[int, float] = {}
        for term in terms:
            posting = self._postings.get(term)
            if not posting:
                continue
            df = self._df[term]
            for ordinal, tf in posting.items():
                contribution = bm25_score(
                    tf=tf,
                    df=df,
                    doc_len=self._doc_len.get(ordinal, 0),
                    avg_doc_len=avg_doc_len,
                    n_docs=n_docs,
                )
                scores[ordinal] = scores.get(ordinal, 0.0) + contribution
        ranked = [
            (self._order[ordinal], score)
            for ordinal, score in scores.items()
        ]
        ranked.sort(key=lambda pair: (-pair[1], pair[0]))
        return ranked[:limit]

    # -- persistence ------------------------------------------------------
    def save(self, path: str) -> None:
        """Persist the index to ``path`` as JSON atomically.

        Writes to a sibling temporary file then ``os.replace``s it into place,
        so readers never observe a partially written index.
        """
        target = os.fspath(path)
        directory = os.path.dirname(os.path.abspath(target))
        payload = {
            "schema": self.SCHEMA,
            "docs": [[doc_id, self._docs[doc_id]] for doc_id in self._order],
        }
        data = json.dumps(payload, ensure_ascii=True, separators=(",", ":"))
        fd, tmp_path = tempfile.mkstemp(
            prefix=".noesis_idx_", suffix=".tmp", dir=directory
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_path, target)
        except Exception:
            # Never delete files: leave the temp file for forensic inspection.
            raise

    @classmethod
    def load(cls, path: str) -> "InvertedIndex":
        """Load an index previously written by :meth:`save`.

        The index is rebuilt from the stored document list, so postings and
        BM25 scores are reproduced deterministically.
        """
        target = os.fspath(path)
        opener = gzip.open if target.endswith(".gz") else open
        with opener(target, "rt", encoding="utf-8") as handle:
            payload = json.load(handle)
        if not isinstance(payload, dict) or "docs" not in payload:
            raise ValueError("invalid inverted index payload")
        index = cls()
        for entry in payload["docs"]:
            if not isinstance(entry, (list, tuple)) or len(entry) != 2:
                raise ValueError("invalid document entry")
            index.add(str(entry[0]), str(entry[1]))
        return index
