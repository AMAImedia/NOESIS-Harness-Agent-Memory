"""noesis_harness/merkle_chain.py

Stdlib-only append-only hash chain (Merkle-style linked digest chain).

Borrowed patterns:
  - deepseek-harness: an append-only event log where each entry carries the
    digest of the previous entry, so the log is tamper-evident: mutating any
    payload invalidates every subsequent self_digest and the chain breaks on
    verify(). Used in deepseek-harness to make the event/replay log trustworthy
    without external signing infrastructure.
  - LoopX: a deterministic, idempotent append path where the only mutating op is
    append() and the canonical digest is a pure function of (prev_digest,
    payload). LoopX relies on this for stable replay projections and leases.

This module is part of the deterministic core: it never touches disk, never
calls an LLM, and append() is the only mutating operation. Each entry's
self_digest is sha256(prev_digest || canonical(payload)), so the chain is
verifiable end to end and any tampering is detectable by verify().
"""

import hashlib
import json


ZERO_DIGEST = "0" * 64


def _canonical(payload):
    """Return a stable, deterministic UTF-8 encoding of an arbitrary payload.

    JSON serialization with sorted keys and no whitespace ensures that the same
    logical payload always produces the same bytes, independent of dict ordering
    or pretty-printing differences.
    """
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _digest(prev_digest, payload):
    """Compute the self_digest for an entry given its predecessor digest."""
    h = hashlib.sha256()
    h.update(prev_digest.encode("ascii"))
    h.update(b"|")
    h.update(_canonical(payload))
    return h.hexdigest()


class HashChain:
    """An append-only, tamper-evident hash chain.

    Each appended entry stores the digest of the previous entry (prev_digest)
    and the sha256 digest of ``prev_digest || canonical(payload)`` (self_digest).
    The chain can be verified in full by recomputing each self_digest from its
    predecessor and confirming it matches what was stored.

    The empty chain has a head digest equal to ``ZERO_DIGEST`` (64 zero hex
    chars). The first entry therefore chains off the zero digest.
    """

    def __init__(self):
        self._entries = []
        self._head = ZERO_DIGEST

    def append(self, payload):
        """Append ``payload`` and return its entry_id.

        The entry_id is the self_digest of the newly appended entry. The chain
        head advances to that self_digest.
        """
        prev = self._head
        self_digest = _digest(prev, payload)
        entry = {
            "entry_id": self_digest,
            "prev_digest": prev,
            "self_digest": self_digest,
            "payload": payload,
        }
        self._entries.append(entry)
        self._head = self_digest
        return self_digest

    def head_digest(self):
        """Return the digest of the most recent entry (ZERO_DIGEST if empty)."""
        return self._head

    def verify(self):
        """Return True if every entry's self_digest matches the recomputed value.

        A clean chain always verifies. If any stored payload or prev_digest was
        altered, the recomputed digest will diverge and verify() returns False.
        """
        expected_prev = ZERO_DIGEST
        for entry in self._entries:
            recomputed = _digest(expected_prev, entry["payload"])
            if recomputed != entry["self_digest"]:
                return False
            if entry["prev_digest"] != expected_prev:
                return False
            expected_prev = entry["self_digest"]
        return True

    def __len__(self):
        return len(self._entries)

    def entries(self):
        """Return a read-only snapshot of all entries (no side effects)."""
        return list(self._entries)
