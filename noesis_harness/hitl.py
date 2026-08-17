"""noesis_harness/hitl.py

Human-in-the-loop as architecture: draft never becomes sent without approve.
"""

from __future__ import annotations

import sqlite3
import threading
import time
import uuid

STATUSES = ("draft", "approved", "rejected", "sent")


class HitlGate:
    def __init__(self, db_path):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._init()

    def _conn(self):
        c = sqlite3.connect(self.db_path, timeout=10)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA journal_mode=WAL")
        return c

    def _init(self):
        with self._conn() as c:
            c.execute(
                "CREATE TABLE IF NOT EXISTS drafts ("
                " id TEXT PRIMARY KEY, text TEXT NOT NULL,"
                " status TEXT NOT NULL, created_at REAL NOT NULL,"
                " updated_at REAL NOT NULL)")

    def draft(self, text):
        did = uuid.uuid4().hex
        now = time.time()
        with self._lock, self._conn() as c:
            c.execute(
                "INSERT INTO drafts (id, text, status, created_at, updated_at)"
                " VALUES (?,?,?,?,?)", (did, text, "draft", now, now))
        return did

    def approve(self, draft_id):
        return self._set(draft_id, "approved", allow=("draft",))

    def reject(self, draft_id):
        return self._set(draft_id, "rejected", allow=("draft", "approved"))

    def mark_sent(self, draft_id):
        return self._set(draft_id, "sent", allow=("approved",))

    def _set(self, draft_id, status, allow):
        with self._lock, self._conn() as c:
            row = c.execute("SELECT status FROM drafts WHERE id=?", (draft_id,)).fetchone()
            if not row:
                return {"ok": False, "reason": "missing"}
            if row["status"] not in allow:
                return {"ok": False, "reason": "illegal_transition",
                        "from": row["status"], "to": status}
            c.execute(
                "UPDATE drafts SET status=?, updated_at=? WHERE id=?",
                (status, time.time(), draft_id))
        return {"ok": True, "status": status}

    def get(self, draft_id):
        with self._conn() as c:
            row = c.execute("SELECT * FROM drafts WHERE id=?", (draft_id,)).fetchone()
        return dict(row) if row else None
