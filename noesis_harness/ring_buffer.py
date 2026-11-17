"""noesis_harness/ring_buffer.py

Stdlib-only fixed-size ring buffer (circular buffer) with overwrite-on-full.

Borrowed patterns:
  - LoopX: a bounded, order-preserving in-memory buffer that retains the most
    recent N items and deterministically drops the oldest when full. Used in
    LoopX to keep a sliding window of recent observations/events without growing
    unbounded memory. The buffer is pure: push() is the only mutating op, and
    to_list() always returns items oldest-first so a replay projection is stable.

This module never touches disk, never calls an LLM, and is safe to use inside a
deterministic core: to_list() is a read-only snapshot with no side effects.
"""

from collections import deque


class RingBuffer:
    """A fixed-capacity ring buffer that overwrites the oldest item when full.

    Items are retained in insertion order. Once the buffer reaches capacity,
    each subsequent push() evicts the oldest retained item. ``to_list()`` returns
    a snapshot of the retained items from oldest to newest without mutating state.

    Args:
        capacity: maximum number of items retained. Must be >= 1.
    """

    def __init__(self, capacity):
        if capacity < 1:
            raise ValueError("capacity must be >= 1")
        self._capacity = capacity
        self._buf = deque()

    def push(self, item):
        """Append item, evicting the oldest retained item if the buffer is full."""
        if len(self._buf) >= self._capacity:
            self._buf.popleft()
        self._buf.append(item)

    def to_list(self):
        """Return a snapshot list of retained items, oldest first (no side effects)."""
        return list(self._buf)

    def __len__(self):
        return len(self._buf)

    def is_full(self):
        """Return True when the buffer holds exactly ``capacity`` items."""
        return len(self._buf) >= self._capacity
