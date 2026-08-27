"""Frequency counter with deterministic ordering.

Borrowed patterns:
- LoopX: append-only, idempotent event accumulation and deterministic replay
  projection of aggregate counts.
- agentmemory: stable tie-break ordering so recall order never flickers between
  runs for equal-weight keys.
"""

from collections import defaultdict


class FreqCounter:
    """Deterministic multi-set frequency counter (stdlib only)."""

    def __init__(self):
        self._counts = defaultdict(int)

    def inc(self, key, n=1):
        """Increment count for key by n (n may be negative)."""
        self._counts[key] += n

    def total(self):
        """Return sum of all counts."""
        return sum(self._counts.values())

    def most_common(self):
        """Return list of (key, count) sorted by count desc, key asc on ties."""
        items = sorted(self._counts.items(), key=lambda kv: (-kv[1], kv[0]))
        return items

    def top(self, k):
        """Return top k (key, count) pairs with deterministic tie-break."""
        return self.most_common()[:k]

    def merge(self, other):
        """Merge another FreqCounter into this one (in-place)."""
        for key, count in other._counts.items():
            self._counts[key] += count
        return self
