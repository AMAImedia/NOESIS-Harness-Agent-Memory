"""noesis_harness/invariant.py

Read-only invariant checker over the append-only event log.

Patterns adapted from:
  - LoopX (event_sourced_state.py: AppendOnlyStateEventStore + build_state_projection)
  - agentmemory (read-only consistency assertions over the event stream)

Design goals:
  - Pure and read-only: the event log is never opened for writing and no state
    is mutated. check() only replays events through user-supplied predicates.
  - Zero dependencies (stdlib only). One file, one job.
  - Deterministic: the same log and the same rules always yield the same result.

A rule is a mapping {"name": str, "fn": Callable}. The checker constructs an
EventStore over `events_path` and hands it to each rule function. A rule returns
a falsy value (None / "" / False) to signal PASS, or a truthy string describing
the violation to signal FAIL. check() never raises for a well-formed log; a
missing file is treated as an empty log.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Iterable, List

from .event_store import EventStore


def check(events_path: str, rules: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """Run each rule over the event log at `events_path`.

    Args:
        events_path: path to the append-only JSONL event log (or missing file).
        rules: iterable of {"name": str, "fn": Callable} mappings. Each `fn` is
            invoked as fn(store) where `store` is a read-only EventStore; the
            rule should iterate store.iter_events() and return a falsy value to
            pass or a truthy detail string to fail.

    Returns:
        {"passed": bool, "failures": List[{"name": str, "detail": str}]}.
    """
    store = EventStore(events_path)
    failures: List[Dict[str, str]] = []
    for rule in rules:
        name = rule.get("name", "<unnamed>")
        fn = rule.get("fn")
        if fn is None:
            continue
        detail = fn(store)
        if detail:
            failures.append({"name": name, "detail": str(detail)})
    return {"passed": not failures, "failures": failures}


__all__ = ["check"]
