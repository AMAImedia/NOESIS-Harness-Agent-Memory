"""Time and clock helpers for the NOESIS harness.

Patterns borrowed from:
- LoopX: monotonic, monotonic clock usage for measuring elapsed wall-clock
  intervals without drift from system clock adjustments, plus deterministic
  UTC timestamp formatting for event log entries.

This module is pure and side-effect free. It depends only on the Python
standard library (time, datetime) so it can be imported anywhere in the
harness, including paths that must stay dependency-free. All functions are
deterministic given their inputs.
"""

import time
from datetime import datetime, timezone


def now_ns():
    """Return the current time as integer nanoseconds since the epoch."""
    return time.time_ns()


def now_sec():
    """Return the current time as a float seconds since the epoch."""
    return time.time()


def iso_utc(ts=None):
    """Return an ISO-8601 UTC timestamp string for ``ts``.

    ``ts`` is a Unix timestamp in seconds (float or int). When ``ts`` is
    ``None`` the current time is used. The output is always timezone-aware
    UTC (``Z`` suffix) and stable across runs for the same input.
    """
    if ts is None:
        ts = time.time()
    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def monotonic_ns():
    """Return a monotonic clock reading in integer nanoseconds.

    Monotonic means the value only moves forward and is unaffected by
    system clock adjustments. Use for measuring elapsed time, never for
    absolute wall-clock time.
    """
    return time.monotonic_ns()


def format_elapsed(seconds):
    """Return a human-readable elapsed-time string for ``seconds``.

    ``seconds`` is a non-negative number of seconds. Buckets:
    - < 60s:  ``<n>s``
    - < 3600s (1h): ``<m>m<ss>s``
    - otherwise: ``<h>h<m>m``
    The result is deterministic for a given input.
    """
    if seconds is None:
        return "0s"
    total = int(seconds)
    if total < 0:
        total = 0
    if total < 60:
        return "%ds" % total
    if total < 3600:
        minutes = total // 60
        secs = total % 60
        return "%dm%02ds" % (minutes, secs)
    hours = total // 3600
    minutes = (total % 3600) // 60
    return "%dh%dm" % (hours, minutes)
