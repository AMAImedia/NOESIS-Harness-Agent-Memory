"""Read-only lease TTL clock helper for the NOESIS harness.

Patterns borrowed from:
- agentmemory: time-bounded leases on memory entries where a lease grants
  exclusive or privileged access until an ``expires_at`` timestamp, after which
  the entry is reclaimable. This module provides a pure, dependency-free way to
  compute how much time remains on such a lease and whether it has lapsed.

The helper is strictly read-only: it never mutates the lease dict and never
persists anything. It depends only on the Python standard library (``time``)
so it remains importable from any dependency-free path in the harness. Both
functions are deterministic given the same inputs.
"""

import time


def remaining(lease, now=None):
    """Return seconds left until the lease expires, clamped at 0.

    ``lease`` is a mapping expected to carry an ``expires_at`` key (a Unix
    timestamp in seconds, int or float). ``now`` is an optional override for
    the current time (seconds since the epoch); when ``None`` the current wall
    clock is read via :func:`time.time`.

    Returns a non-negative ``float``. If the lease has no ``expires_at`` field
    (missing or ``None``) the lease is treated as already expired and ``0.0``
    is returned. The result is clamped at 0 so a lapsed lease never reports a
    negative remaining time.
    """
    expires_at = lease.get("expires_at") if isinstance(lease, dict) else None
    if expires_at is None:
        return 0.0
    if now is None:
        now = time.time()
    left = float(expires_at) - float(now)
    if left < 0.0:
        return 0.0
    return left


def is_expired(lease, now=None):
    """Return ``True`` when the lease has no remaining time.

    ``lease`` and ``now`` are as described for :func:`remaining`. The lease is
    considered expired when there is no positive remaining time: either the
    ``expires_at`` field is missing/``None``, or the current time has reached
    or passed it.
    """
    return remaining(lease, now) <= 0.0
