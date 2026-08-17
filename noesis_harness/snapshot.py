"""noesis_harness/snapshot.py

Export/import memory snapshots (git-friendly JSON) with last-write-wins merge.

Pattern adapted from agentmemory snapshot.ts + mesh.ts LWW.
Stdlib only.
"""

from __future__ import annotations

import json
import os
import time


def export_snapshot(memory, path):
    """Dump memories + summaries to JSON. Returns row count."""
    with memory._conn() as c:
        mems = [dict(r) for r in c.execute(
            "SELECT id, kind, fact, confidence, strength, access_count,"
            " last_accessed_at, created_at FROM memories").fetchall()]
        sums = [dict(r) for r in c.execute(
            "SELECT id, session_id, text, created_at FROM summaries").fetchall()]
    payload = {"version": 1, "exported_at": time.time(),
               "memories": mems, "summaries": sums}
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    return len(mems) + len(sums)


def import_snapshot(memory, path):
    """LWW merge: keep the row with the later created_at. Returns merged count."""
    with open(path, "r", encoding="utf-8") as fh:
        payload = json.load(fh)
    n = 0
    with memory._lock, memory._conn() as c:
        for row in payload.get("memories") or []:
            existing = c.execute(
                "SELECT created_at FROM memories WHERE id=?", (row["id"],)).fetchone()
            if existing and existing["created_at"] >= row.get("created_at", 0):
                continue
            if existing:
                c.execute("DELETE FROM memories WHERE id=?", (row["id"],))
            c.execute(
                "INSERT INTO memories (id, kind, fact, confidence, strength,"
                " access_count, last_accessed_at, created_at)"
                " VALUES (?,?,?,?,?,?,?,?)",
                (row["id"], row.get("kind", "semantic"), row["fact"],
                 row.get("confidence", 0.5), row.get("strength", 1.0),
                 row.get("access_count", 0), row.get("last_accessed_at", 0),
                 row.get("created_at", time.time())))
            n += 1
        for row in payload.get("summaries") or []:
            existing = c.execute(
                "SELECT created_at FROM summaries WHERE id=?", (row["id"],)).fetchone()
            if existing:
                continue
            c.execute(
                "INSERT INTO summaries (id, session_id, text, created_at)"
                " VALUES (?,?,?,?)",
                (row["id"], row.get("session_id", ""), row.get("text", ""),
                 row.get("created_at", time.time())))
            n += 1
    return n
