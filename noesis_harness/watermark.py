"""Deterministic watermark over a set of event ids.

Borrowed patterns:
- LoopX: verifiable watermark / commitment over an unordered set of event
  ids so two independent coordinators can prove they observed the same event
  set without revealing ordering or contents.

Pure, stdlib-only, deterministic. A watermark is the SHA-256 of the sorted,
de-duplicated set of ids joined by newlines, so the result is independent of
input order or duplicate ids. `combine` merges two watermarks deterministically
and commutatively from their opaque digests.
"""

import hashlib

_COMBINE_DOMAIN = b"noesis:watermark:combine:"
_EMPTY_WATERMARK = hashlib.sha256(b"").hexdigest()


def watermark(ids):
    """Return a stable SHA-256 hex digest for an unordered iterable of event ids.

    The watermark is computed over the sorted, de-duplicated set of ids joined
    by newlines, so the result is independent of input order, duplicates, or
    repeated ids. Empty input yields the watermark of the empty set.
    """
    normalized = sorted(set(ids))
    payload = "\n".join(normalized).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def combine(w1, w2):
    """Deterministically merge two watermarks into a single watermark.

    The merged watermark is the SHA-256 over the two input digests sorted
    canonically, so merging is commutative (combine(a, b) == combine(b, a)).
    The empty-set watermark (watermark([])) is the identity, so combining it
    with any watermark returns that watermark. Both inputs are treated as
    opaque commitments; no event ids are recovered.
    """
    if w1 == _EMPTY_WATERMARK:
        return w2
    if w2 == _EMPTY_WATERMARK:
        return w1
    pair = "\n".join(sorted([w1, w2]))
    return hashlib.sha256(_COMBINE_DOMAIN + pair.encode("utf-8")).hexdigest()
