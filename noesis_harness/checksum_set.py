"""noesis_harness/checksum_set.py

Stdlib-only deterministic set of sha256 checksums with a stable, order-independent
aggregate digest.

Borrowed patterns:
  - LoopX: a bounded, append-only membership structure that records every distinct
    item it has seen as an opaque fingerprint, so a replay projection can prove
    "these exact items were processed" without retaining the payloads. LoopX
    commits such fingerprints to an immutable event log; this module is the pure
    building block that produces and combines those fingerprints. add() is
    idempotent (re-adding the same item is a no-op), so the set is identical
    regardless of how many times the same item was observed (idempotent write
    path, no double counting).

This module is safe inside the deterministic core: it never touches disk, never
calls an LLM, and has no hidden state beyond the set of checksums it owns.

Design notes:
  - Each item is reduced to its sha256 hex digest; the set stores only digests.
  - `contains(item)` is a pure membership test over the digest set.
  - `digest()` folds every stored digest into a single sha256 "merkle-ish" root:
    the digests are sorted (lexicographically) to make the result independent of
    insertion order, concatenated, and hashed. Sorting is what gives the
    order-independence guarantee. The fold is flat (not a tree) but is
    deterministic and stable, which is what callers need to compare two sets.
  - `to_list()` returns the stored digests sorted, so the externalized form is
    reproducible across runs and machines.
"""

import hashlib


class ChecksumSet(object):
    """Deterministic set of sha256 checksums over added text/bytes items.

    Stores only the sha256 hex digest of each item. Items never stored fail
    contains(); there are no false positives. add() is idempotent.
    """

    def __init__(self):
        """Create an empty checksum set."""
        self._digests = set()

    @staticmethod
    def _digest_of(item):
        """Return the sha256 hex digest for `item` (str or bytes)."""
        if isinstance(item, str):
            data = item.encode("utf-8")
        elif isinstance(item, (bytes, bytearray)):
            data = bytes(item)
        else:
            raise TypeError("item must be str or bytes, got %r" % type(item).__name__)
        return hashlib.sha256(data).hexdigest()

    def add(self, text_or_bytes):
        """Insert `text_or_bytes` as its sha256 digest. Idempotent.

        Returns True if the digest was newly added, False if it was already a
        member (no double counting).
        """
        digest = self._digest_of(text_or_bytes)
        if digest in self._digests:
            return False
        self._digests.add(digest)
        return True

    def contains(self, item):
        """Return True if the sha256 digest of `item` is a member."""
        return self._digest_of(item) in self._digests

    def digest(self):
        """Return a stable, order-independent sha256 root over all stored digests.

        The digests are sorted lexicographically and concatenated before hashing,
        so two sets holding the same items produce the same digest regardless of
        insertion order. Returns the 64-character hex string. The empty set has a
        stable, fixed digest (sha256 of the empty string).
        """
        joined = "".join(sorted(self._digests))
        return hashlib.sha256(joined.encode("ascii")).hexdigest()

    def to_list(self):
        """Return the stored digests as a sorted list of hex strings."""
        return sorted(self._digests)

    def __len__(self):
        """Return the number of distinct stored digests."""
        return len(self._digests)
