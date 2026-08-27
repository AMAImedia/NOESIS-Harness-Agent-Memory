"""noesis_harness/bloom.py

Stdlib-only deterministic Bloom filter backed by pure hash functions.

Borrowed patterns:
  - LoopX: a bounded, append-only membership structure that answers
    "might this item have been seen?" with no false negatives and a tunable,
    deterministic false-positive rate. LoopX uses such a structure to gate
    replay of already-processed events without storing the full event payload
    and without mutating prior state. The filter is pure: add() only flips bits
    from 0 to 1, so a replay projection is identical regardless of how many times
    the same item was added (idempotent write path). No randomness is used; the
    hash functions are derived purely from hashlib over the item bytes, making
    might_contain() a deterministic function of (size, hashes, inserted items).

This module is safe inside the deterministic core: it never touches disk, never
calls an LLM, and has no hidden state beyond the bit array it owns.

Design notes:
  - `size` is the number of bits in the filter (the bit array length).
  - `hashes` is the number of independent hash functions to apply per item.
  - Each hash is computed by keying HMAC/SHA-256 with a per-index salt, then
    reducing the digest modulo `size`. This gives independent, stable positions.
  - false_positive_rate_estimate() returns the theoretical rate
    (1 - exp(-k*n/m))**k for the *current* number of inserted items, matching the
    classic Bloom filter bound. It returns an estimate, not a measurement.
"""

import hashlib
import math


class Bloom(object):
    """Deterministic Bloom filter over a fixed-size bit array.

    The filter answers membership queries with no false negatives: if add(x) was
    called, might_contain(x) is always True. Items never added may still report
    True (false positive); the probability is bounded by the size/hashes choices
    and reported by false_positive_rate_estimate().
    """

    def __init__(self, size, hashes):
        """Create an empty filter with `size` bits and `hashes` hash functions.

        Args:
            size: Positive integer bit-array length. Larger sizes lower the
                false-positive rate.
            hashes: Positive integer number of hash functions. Must be >= 1.

        Raises:
            ValueError: if size or hashes are not positive integers.
        """
        if not isinstance(size, int) or isinstance(size, bool):
            raise ValueError("size must be a positive integer")
        if not isinstance(hashes, int) or isinstance(hashes, bool):
            raise ValueError("hashes must be a positive integer")
        if size <= 0:
            raise ValueError("size must be a positive integer")
        if hashes <= 0:
            raise ValueError("hashes must be a positive integer")
        self._size = size
        self._hashes = hashes
        self._bits = bytearray(size)
        self._count = 0

    def _positions(self, item):
        """Return the list of bit positions for `item` (deterministic)."""
        if isinstance(item, str):
            data = item.encode("utf-8")
        elif isinstance(item, (bytes, bytearray)):
            data = bytes(item)
        else:
            data = repr(item).encode("utf-8")
        positions = []
        size = self._size
        for i in range(self._hashes):
            salt = b"noesis-bloom-" + str(i).encode("ascii")
            digest = hashlib.sha256(salt + data).digest()
            value = int.from_bytes(digest[:8], "big")
            positions.append(value % size)
        return positions

    def add(self, item):
        """Insert `item`. Idempotent: re-adding an item is a no-op at the bit level.

        Returns True if this call flipped at least one bit (i.e. the item was not
        previously fully present), False if the item was already a member.
        """
        changed = False
        for pos in self._positions(item):
            if self._bits[pos] == 0:
                self._bits[pos] = 1
                changed = True
        if changed:
            self._count += 1
        return changed

    def might_contain(self, item):
        """Return True if `item` may have been added.

        Never returns False for an item that was added. May return True for items
        that were never added (false positive).
        """
        for pos in self._positions(item):
            if self._bits[pos] == 0:
                return False
        return True

    def false_positive_rate_estimate(self, n=None):
        """Estimate the false-positive probability for `n` inserted items.

        Uses the classic bound (1 - exp(-k*n/m))**k where m is the bit count, k is
        the hash count, and n is the inserted-item count (defaults to the current
        count). Returns a float in [0, 1].
        """
        if n is None:
            n = self._count
        m = self._size
        k = self._hashes
        if n <= 0:
            return 0.0
        exponent = -k * n / m
        return (1.0 - math.exp(exponent)) ** k

    def count(self):
        """Return the number of distinct add() calls that flipped at least one bit."""
        return self._count

    def size(self):
        """Return the bit-array length."""
        return self._size

    def hashes(self):
        """Return the configured hash-function count."""
        return self._hashes
