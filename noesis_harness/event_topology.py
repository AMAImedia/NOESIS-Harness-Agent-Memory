"""noesis_harness/event_topology.py

Read-only dependency graph over an append-only event log.

Patterns adapted from:
  - LoopX (event_sourced_state.py: pure projection helpers that never mutate
    the log; build_state_projection returns a derived view, not a write path)

This module is a *pure read-only* projection: it reads an event log (JSONL,
the same shape produced by event_store.py) and derives a dependency graph from
optional payload fields:

  - "parent"     : single event_id this event descends from
  - "depends_on" : list of event_ids this event depends on

It never appends, edits, or truncates the source file, and it never contacts
an LLM or network. Deterministic output: all collections are sorted so the
result dict is stable across runs (append-only state, replay projection).

Zero dependencies (stdlib only). One file, one job.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Tuple


def _read_events(events_path: str) -> List[Dict[str, Any]]:
    """Yield event records from a JSONL file without writing to it.

    A missing file is an error (caller decides how to handle it). Malformed
    lines are skipped so a corrupt tail does not crash a read-only scan, but
    valid records before it are still observed.
    """
    if not os.path.exists(events_path):
        raise FileNotFoundError("event log not found: %s" % events_path)
    records: List[Dict[str, Any]] = []
    with open(events_path, "r", encoding="utf-8") as fh:
        for raw in fh:
            if not raw.strip():
                continue
            try:
                rec = json.loads(raw)
            except (ValueError, TypeError):
                continue
            if isinstance(rec, dict):
                records.append(rec)
    return records


def _collect_dependencies(payload: Any) -> List[str]:
    """Extract the list of dependency event_ids from a payload.

    Accepts either a dict payload with "parent" (str) and/or "depends_on"
    (list of str), or any other shape (returns no dependencies). Missing or
    non-list/non-str fields are ignored rather than raising.
    """
    if not isinstance(payload, dict):
        return []
    deps: List[str] = []
    parent = payload.get("parent")
    if isinstance(parent, str) and parent:
        deps.append(parent)
    depends_on = payload.get("depends_on")
    if isinstance(depends_on, list):
        for item in depends_on:
            if isinstance(item, str) and item and item not in deps:
                deps.append(item)
    return deps


def _detect_back_edge(nodes: List[str], out_edges: Dict[str, List[str]]) -> bool:
    """Return True if a back-edge (cycle) exists using DFS coloring.

    WHITE = unvisited, GRAY = on current DFS stack, BLACK = fully explored.
    A GRAY successor indicates a back-edge (simple cycle), so the graph is
    not cycle-free.
    """
    WHITE, GRAY, BLACK = 0, 1, 2
    color: Dict[str, int] = {n: WHITE for n in nodes}

    def visit(node: str) -> bool:
        color[node] = GRAY
        for nxt in out_edges.get(node, []):
            if nxt not in color:
                continue
            if color[nxt] == GRAY:
                return True
            if color[nxt] == WHITE and visit(nxt):
                return True
        color[node] = BLACK
        return False

    for node in nodes:
        if color[node] == WHITE:
            if visit(node):
                return True
    return False


def build(events_path: str) -> Dict[str, Any]:
    """Build a read-only dependency graph from an event log.

    Args:
        events_path: path to a JSONL event log (event_store.py format).

    Returns a dict with:
        nodes      : sorted list of all event_ids present in the log
        edges      : sorted list of (from, to) tuples where `from` depends on
                     `to` (dependency direction: child -> parent/dep)
        roots      : sorted list of nodes with no outgoing edges (origins)
        leaves     : sorted list of nodes with no incoming edges (terminals)
        cycle_free : bool, True iff the graph has no back-edge / simple cycle

    The function is pure: it only reads the file and returns a fresh dict.
    """
    records = _read_events(events_path)

    nodes_set: set = set()
    out_edges: Dict[str, List[str]] = {}
    in_degree: Dict[str, int] = {}

    for rec in records:
        if not isinstance(rec, dict):
            continue
        event_id = rec.get("event_id")
        if not isinstance(event_id, str) or not event_id:
            continue
        nodes_set.add(event_id)
        deps = _collect_dependencies(rec.get("payload"))
        out_edges.setdefault(event_id, [])
        for dep in deps:
            nodes_set.add(dep)
            out_edges[event_id].append(dep)
            in_degree[dep] = in_degree.get(dep, 0) + 1
            # ensure the dependent node has an out-edge entry even if it never
            # appears as a primary record
            out_edges.setdefault(dep, [])

    nodes = sorted(nodes_set)
    edges: List[Tuple[str, str]] = []
    for src in sorted(out_edges):
        for dst in out_edges[src]:
            edges.append((src, dst))
    edges.sort()

    roots = sorted(n for n in nodes if not out_edges.get(n))
    leaves = sorted(n for n in nodes if in_degree.get(n, 0) == 0)
    cycle_free = not _detect_back_edge(nodes, out_edges)

    return {
        "nodes": nodes,
        "edges": edges,
        "roots": roots,
        "leaves": leaves,
        "cycle_free": cycle_free,
    }


__all__ = ["build"]
