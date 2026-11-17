"""noesis_harness/id_gen.py

Deterministic and non-deterministic identifier generation.

Patterns adapted from:
  - LoopX (event_sourced_state.py: stable content fingerprints for idempotent keys)
  - agentmemory (content-addressable memory id + uuid handles)

Design goals:
  - content_id is a PURE, DETERMINISTIC sha256 fingerprint of its parts, so the
    same logical content always maps to the same id (idempotency, dedup, replay).
  - short_id is a truncated, human-friendly prefix of content_id.
  - uuid_safe is the NON-DETERMINISTIC path: a collision-resistant unique handle.

Zero dependencies (stdlib only). One file, one job.
"""

from __future__ import annotations

import hashlib
import json
import uuid


def content_id(*parts: object) -> str:
    """Return a stable sha256-based id for the given parts.

    The result is deterministic AND order-independent: the same multiset of
    parts yields the same id regardless of argument order. Each part is
    canonicalized to sorted-key JSON so dicts are order-independent and the hash
    is stable across runs and processes. Parts are sorted by canonical form
    before hashing to guarantee order-independence.

    Args:
        *parts: Arbitrary JSON-serializable values (str, int, dict, list, ...).

    Returns:
        A 64-character lowercase hex sha256 digest.
    """
    canon = "\x00".join(sorted(json_canonical(p) for p in parts))
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def short_id(parts: object, length: int = 12) -> str:
    """Return a deterministic `length`-char prefix of content_id(parts).

    `parts` is a single value or an iterable of values passed through to
    content_id. When multiple parts are needed, pass a tuple/list; the prefix
    is still fully order-independent.

    Args:
        parts: One value, or a tuple/list of values, used as content_id input.
        length: Truncation length (clamped to [1, 64]).

    Returns:
        A lowercase hex prefix of the full content id.
    """
    if isinstance(parts, (tuple, list)):
        full = content_id(*parts)
    else:
        full = content_id(parts)
    length = max(1, min(64, int(length)))
    return full[:length]


def uuid_safe() -> str:
    """Return a non-deterministic unique id as a 32-char uuid4 hex string."""
    return uuid.uuid4().hex


def json_canonical(value: object) -> str:
    """Canonicalize a value to sorted-key JSON so dict order never affects the hash."""
    return json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)
