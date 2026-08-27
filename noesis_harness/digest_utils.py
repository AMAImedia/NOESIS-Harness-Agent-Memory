"""Deterministic digest and fingerprint helpers for the NOESIS harness.

Patterns borrowed from:
- LoopX: canonical, order-independent event fingerprinting for idempotent
  append-only state projection.
- deepseek-harness: stable JSON canonicalization for cache keys and
  content-addressed storage.

This module is pure and side-effect free. It depends only on the Python
standard library (hashlib, json) so it can be imported anywhere in the
harness, including paths that must stay dependency-free.
"""

import hashlib
import json


def canonical_json(obj):
    """Return a canonical JSON string for ``obj``.

    Keys are sorted, no insignificant whitespace is emitted, and non-ASCII
    characters are preserved as UTF-8 rather than escaped. The result is
    stable across runs and Python versions, which makes it safe to use for
    content-addressing and fingerprints.
    """
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def sha256_hex(text):
    """Return the hex SHA-256 digest of ``text``.

    ``text`` may be ``str`` or ``bytes``. Strings are encoded as UTF-8.
    """
    if isinstance(text, str):
        data = text.encode("utf-8")
    else:
        data = text
    return hashlib.sha256(data).hexdigest()


def fingerprint(*parts):
    """Combine ``parts`` into a single SHA-256 hex digest.

    Each part is first reduced to a stable per-part SHA-256 digest (string
    and bytes are hashed directly; other values are hashed over their
    canonical JSON form). The per-part digests are then combined in sorted
    order so the result is a true multiset digest: the same set of parts
    always yields the same fingerprint regardless of the order in which they
    are passed or how the values were originally represented (e.g. dict key
    order).
    """
    part_digests = []
    for part in parts:
        if isinstance(part, (str, bytes)):
            if isinstance(part, str):
                chunk = part.encode("utf-8")
            else:
                chunk = part
        else:
            chunk = canonical_json(part).encode("utf-8")
        part_digests.append(hashlib.sha256(chunk).hexdigest())
    hasher = hashlib.sha256()
    for digest in sorted(part_digests):
        hasher.update(digest.encode("ascii"))
    return hasher.hexdigest()


def stable_digest(obj):
    """Return a stable SHA-256 hex digest over the canonical form of ``obj``."""
    return sha256_hex(canonical_json(obj))
