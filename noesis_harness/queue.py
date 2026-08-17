"""noesis_harness/queue.py

Durable SQLite task queue: WAL, fingerprint dedup, retry, recover-on-restart.

Pattern adapted from agent-teams teams_server/queue.py.
Stdlib only.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
import time
import uuid


class DurableQueue:
    def __init__(self, db_path, max_attempts=3):
        self.db_path = db_path
        self.max_attempts = max_attempts
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
                "CREATE TABLE IF NOT EXISTS tasks ("
                " id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL,"
                " payload TEXT NOT NULL, status TEXT NOT NULL,"
                " attempts INTEGER NOT NULL DEFAULT 0,"
                " created_at REAL NOT NULL, updated_at REAL NOT NULL)")
            c.execute(
                "CREATE INDEX IF NOT EXISTS idx_q_status ON tasks(status)")

    def enqueue(self, payload, task_id=None):
        body = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
        fp = hashlib.sha256(body.encode("utf-8")).hexdigest()
        tid = task_id or uuid.uuid4().hex
        now = time.time()
        with self._lock, self._conn() as c:
            row = c.execute(
                "SELECT id FROM tasks WHERE fingerprint=? AND status IN ('pending','leased')",
                (fp,)).fetchone()
            if row:
                return row["id"]
            c.execute(
                "INSERT INTO tasks (id, fingerprint, payload, status, attempts,"
                " created_at, updated_at) VALUES (?,?,?,?,0,?,?)",
                (tid, fp, body, "pending", now, now))
        return tid

    def lease(self, worker, limit=1):
        out = []
        now = time.time()
        with self._lock, self._conn() as c:
            rows = c.execute(
                "SELECT * FROM tasks WHERE status='pending' "
                "ORDER BY created_at ASC LIMIT ?", (limit,)).fetchall()
            for r in rows:
                c.execute(
                    "UPDATE tasks SET status='leased', attempts=attempts+1,"
                    " updated_at=? WHERE id=?", (now, r["id"]))
                item = dict(r)
                item["payload"] = json.loads(item["payload"])
                item["worker"] = worker
                out.append(item)
        return out

    def ack(self, task_id):
        with self._lock, self._conn() as c:
            c.execute(
                "UPDATE tasks SET status='done', updated_at=? WHERE id=?",
                (time.time(), task_id))

    def fail(self, task_id):
        with self._lock, self._conn() as c:
            row = c.execute("SELECT attempts FROM tasks WHERE id=?", (task_id,)).fetchone()
            if not row:
                return "missing"
            nxt = "pending" if row["attempts"] < self.max_attempts else "dead"
            c.execute(
                "UPDATE tasks SET status=?, updated_at=? WHERE id=?",
                (nxt, time.time(), task_id))
            return nxt

    def recover(self):
        """Requeue leased tasks after a crash."""
        n = 0
        with self._lock, self._conn() as c:
            n = c.execute(
                "UPDATE tasks SET status='pending', updated_at=? WHERE status='leased'",
                (time.time(),)).rowcount
        return n

    def stats(self):
        with self._conn() as c:
            rows = c.execute(
                "SELECT status, COUNT(*) n FROM tasks GROUP BY status").fetchall()
        return {r["status"]: r["n"] for r in rows}
