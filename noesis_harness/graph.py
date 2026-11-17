"""noesis_harness/graph.py

Tiny knowledge graph over memory ids. Stdlib SQLite.

Pattern: Cognee/semantica edges without a graph DB.
Triple: subject --predicate--> object (memory ids or literals).
"""

from __future__ import annotations

import sqlite3
import threading

try:
    from .nextgen import _ManagedConnection
except ImportError:
    from nextgen import _ManagedConnection
import time
import uuid


class MemoryGraph:
    def __init__(self, db_path):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._init()

    def _conn(self):
        c = sqlite3.connect(self.db_path, timeout=10, factory=_ManagedConnection)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA journal_mode=WAL")
        return c

    def _init(self):
        with self._conn() as c:
            c.execute(
                "CREATE TABLE IF NOT EXISTS edges ("
                " id TEXT PRIMARY KEY, subj TEXT NOT NULL,"
                " pred TEXT NOT NULL, obj TEXT NOT NULL,"
                " created_at REAL NOT NULL)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_e_subj ON edges(subj)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_e_obj ON edges(obj)")

    def link(self, subj, pred, obj):
        eid = uuid.uuid4().hex
        with self._lock, self._conn() as c:
            row = c.execute(
                "SELECT id FROM edges WHERE subj=? AND pred=? AND obj=?",
                (subj, pred, obj)).fetchone()
            if row:
                return row["id"]
            c.execute(
                "INSERT INTO edges (id, subj, pred, obj, created_at) VALUES (?,?,?,?,?)",
                (eid, subj, pred, obj, time.time()))
        return eid

    def neighbors(self, node, pred=""):
        sql = "SELECT * FROM edges WHERE subj=? OR obj=?"
        params = [node, node]
        if pred:
            sql += " AND pred=?"
            params.append(pred)
        with self._conn() as c:
            return [dict(r) for r in c.execute(sql, params).fetchall()]

    def walk(self, start, depth=2):
        seen = set([start])
        frontier = [start]
        edges = []
        for _ in range(max(1, depth)):
            nxt = []
            for node in frontier:
                for e in self.neighbors(node):
                    edges.append(e)
                    other = e["obj"] if e["subj"] == node else e["subj"]
                    if other not in seen:
                        seen.add(other)
                        nxt.append(other)
            frontier = nxt
        return {"nodes": sorted(seen), "edges": edges}
