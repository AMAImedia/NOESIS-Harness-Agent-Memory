"""noesis_harness/bounded_set.py

In-memory bounded set with deterministic FIFO eviction.

Borrowed patterns:
  - LoopX: bounded, order-preserving FIFO eviction guarded by a single lock so
    the projection of "what is held" is fully deterministic under replay.

The set never touches disk, never calls an LLM, and is pure/read-only safe.
Membership queries (``__contains__``) and snapshots (``to_list``) have no side
effects on eviction ordering; only ``add`` advances the eviction queue. This
keeps the structure replay-safe when used inside a deterministic core.

Behavior notes:
  - Adding an item already present does NOT change its recency (FIFO order is
    based on first insertion). This keeps overflow eviction strictly oldest-first.
  - On overflow the oldest member is dropped; size never exceeds ``maxsize``.
"""

import threading


class BoundedSet:
    """A thread-safe, in-memory bounded set with FIFO eviction.

    When full, the oldest-added item is evicted on the next ``add`` of a new
    member. Re-adding an existing member is a no-op for ordering. All mutating
    and read paths are serialized by a single re-entrant-safe lock.

    Args:
        maxsize: maximum number of members retained. Must be >= 1.
    """

    def __init__(self, maxsize):
        if not isinstance(maxsize, int):
            raise ValueError("maxsize must be an int >= 1")
        if maxsize < 1:
            raise ValueError("maxsize must be >= 1")
        self._maxsize = maxsize
        self._members = set()
        self._order = []
        self._lock = threading.Lock()

    def add(self, item):
        """Add ``item``. No-op if already present; evicts oldest on overflow."""
        with self._lock:
            if item in self._members:
                return
            self._members.add(item)
            self._order.append(item)
            while len(self._members) > self._maxsize:
                oldest = self._order.pop(0)
                self._members.discard(oldest)

    def __contains__(self, item):
        """Return True if ``item`` is currently a member."""
        with self._lock:
            return item in self._members

    def __len__(self):
        """Return the current number of members."""
        with self._lock:
            return len(self._members)

    def to_list(self):
        """Return members in insertion order (oldest first) as a new list."""
        with self._lock:
            return list(self._order)
