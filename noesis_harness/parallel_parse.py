"""noesis_harness/parallel_parse.py

Parallel but deterministic, fail-soft fan-out parsing.

Borrowed patterns:
  - deja-vu (Go): internal/sources/util.go parseFiles -- sort the input paths,
    fan the parse over a bounded worker pool, collect results by input index,
    and reassemble strictly in input order. A batch therefore behaves exactly
    like a sequential loop while using all available cores. Every read is
    bounded by a wall-clock budget: an item that cannot start before the
    deadline is recorded as a failure instead of running.

Design notes:
  - Determinism: output order is always the input order, regardless of the
    order in which workers finish.
  - Fail-soft: a raising parse_fn is captured as a ParseFailure for that single
    item and never aborts the rest of the batch.
  - Stdlib only: concurrent.futures for the pool, typing for hints, os for the
    default worker count.
"""

from __future__ import annotations

import os
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

__all__ = [
    "ParseFailure",
    "ordered_fanout",
    "parse_files_parallel",
    "bounded_fanout",
    "DEFAULT_WORKER_CAP",
]

DEFAULT_WORKER_CAP = 32


@dataclass(frozen=True)
class ParseFailure:
    """A single item that could not be parsed.

    Attributes:
        item: the exact input that was handed to parse_fn.
        error: human-readable message (str(exception) or the fixed message
            "deadline exceeded").
        error_type: the exception class name, or "DeadlineExceeded" when the
            wall-clock budget expired before the item could start.
    """

    item: str
    error: str
    error_type: str


def _resolve_workers(workers: Optional[int]) -> int:
    """Cap the requested worker count at DEFAULT_WORKER_CAP and at least 1.

    A falsy ``workers`` (None or 0) falls back to ``os.cpu_count()``. The
    result is ``max(1, min(requested, DEFAULT_WORKER_CAP))``.
    """
    if workers:
        requested = workers
    else:
        requested = os.cpu_count() or 1
    return max(1, min(requested, DEFAULT_WORKER_CAP))


def _run_fanout(
    items: List[str],
    parse_fn: Callable[[str], Any],
    workers: Optional[int],
    deadline: Optional[float],
    now: Optional[Callable[[], float]],
) -> List[Tuple[str, Any]]:
    """Shared engine for ``ordered_fanout`` and ``bounded_fanout``."""
    total = len(items)
    if total == 0:
        return []

    worker_count = _resolve_workers(workers)
    clock = now if now is not None else time.monotonic

    def _work(indexed_item: Tuple[int, str]) -> Tuple[int, Any]:
        index, item = indexed_item
        if deadline is not None and clock() > deadline:
            return index, ParseFailure(item, "deadline exceeded", "DeadlineExceeded")
        try:
            return index, parse_fn(item)
        except Exception as exc:  # fail-soft by contract
            return index, ParseFailure(item, str(exc), type(exc).__name__)

    collected: List[Any] = [None] * total
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        futures = [
            executor.submit(_work, (index, item))
            for index, item in enumerate(items)
        ]
        for future in futures:
            index, value = future.result()
            collected[index] = value
    return [(item, collected[index]) for index, item in enumerate(items)]


def ordered_fanout(
    items: List[str],
    parse_fn: Callable[[str], Any],
    workers: Optional[int] = None,
) -> List[Tuple[str, Any]]:
    """Parse ``items`` concurrently and return results in the input order.

    Args:
        items: input strings (paths, keys, ids).
        parse_fn: callable applied to each item on a worker thread.
        workers: requested worker count; capped to
            ``max(1, min(workers or os.cpu_count(), DEFAULT_WORKER_CAP))``.

    Returns:
        A list of ``(item, result)`` tuples in the exact input order. If
        ``parse_fn`` raised for an item, its result is a ``ParseFailure``
        instance instead of aborting the batch.
    """
    return _run_fanout(list(items), parse_fn, workers, None, None)


def parse_files_parallel(
    paths: List[str],
    parse_fn: Callable[[str], Any],
    workers: Optional[int] = None,
) -> Dict[str, Any]:
    """Convenience split of ``ordered_fanout`` into successes and failures.

    Returns:
        ``{"ok": Dict[path, result], "failed": List[ParseFailure]}`` where
        ``ok`` preserves input insertion order and ``failed`` is sorted by
        ``ParseFailure.item``.
    """
    ordered = ordered_fanout(paths, parse_fn, workers=workers)
    ok: Dict[str, Any] = {}
    failed: List[ParseFailure] = []
    for path, value in ordered:
        if isinstance(value, ParseFailure):
            failed.append(value)
        else:
            ok[path] = value
    failed.sort(key=lambda failure: failure.item)
    return {"ok": ok, "failed": failed}


def bounded_fanout(
    items: List[str],
    parse_fn: Callable[[str], Any],
    workers: Optional[int] = None,
    deadline: Optional[float] = None,
    now: Optional[Callable[[], float]] = None,
) -> List[Tuple[str, Any]]:
    """Like ``ordered_fanout`` but bounded by an absolute wall-clock deadline.

    Args:
        items: input strings.
        parse_fn: callable applied to each item.
        workers: requested worker count (see ``ordered_fanout``).
        deadline: absolute time measured by ``now``. If the current time is
            past ``deadline`` when an item is about to start, ``parse_fn`` is
            not called and the item becomes a ``ParseFailure`` with
            ``error == "deadline exceeded"``.
        now: injectable clock returning seconds. Defaults to
            ``time.monotonic``.

    Returns:
        A list of ``(item, result)`` tuples in input order.
    """
    return _run_fanout(list(items), parse_fn, workers, deadline, now)
