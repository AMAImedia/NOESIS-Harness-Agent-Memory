"""noesis_harness/bounded_cache.py

In-memory bounded cache with deterministic FIFO eviction.

Borrowed patterns:
  - LoopX: bounded, order-preserving FIFO eviction with a single lock so the
    projection of "what is cached" is fully deterministic under replay.

The cache never touches disk, never calls an LLM, and is pure/read-only safe:
get() has no side effects on eviction ordering, only put() advances the queue.
This keeps cache reads replay-safe when used inside a deterministic core.
"""

import threading


class BoundedCache:
    """A thread-safe, in-memory bounded cache with FIFO eviction.

    When the cache is full, the oldest inserted entry is evicted on the next
    put(). Overwriting an existing key refreshes its recency (it becomes the
    most-recently inserted entry). Reads via get() do not change ordering, so
    the cache is safe to use in read-only / replay contexts.

    Args:
        maxsize: maximum number of entries retained. Must be >= 1.
    """

    def __init__(self, maxsize=128):
        if maxsize < 1:
            raise ValueError("maxsize must be >= 1")
        self._maxsize = maxsize
        self._store = {}
        self._order = []
        self._lock = threading.Lock()

    def get(self, key):
        """Return the value for key, or None if absent. Read-only, no side effects."""
        with self._lock:
            return self._store.get(key)

    def put(self, key, value):
        """Insert or overwrite key -> value, evicting the oldest entry if full."""
        with self._lock:
            if key in self._store:
                self._store[key] = value
                self._order.remove(key)
                self._order.append(key)
                return
            self._store[key] = value
            self._order.append(key)
            if len(self._order) > self._maxsize:
                oldest = self._order.pop(0)
                del self._store[oldest]

    def __len__(self):
        with self._lock:
            return len(self._order)

    def keys(self):
        """Return a snapshot list of keys in insertion order (oldest first)."""
        with self._lock:
            return list(self._order)

    @property
    def maxsize(self):
        return self._maxsize
