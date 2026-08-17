"""noesis_harness/coordination.py

Multi-agent coordination primitives: leases, signals, actions.

Patterns adapted from:
  - agentmemory (leases.ts, signals.ts, actions.ts): the most complete open
    implementation of "agents must not overlap and must be able to talk".
  - LoopX (task_lease.py, claim_visibility.py): claims + TTL leases + handoff.

Design:
  - Leases  = exclusive, TTL-bounded ownership of a task (one task == one agent).
  - Signals = asynchronous mailbox between agents (broadcast, threads, receipts).
  - Actions = task graph with typed dependency edges + auto-unblock propagation.

Zero dependencies (stdlib only). SQLite-backed so it survives restarts.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Leases
# ---------------------------------------------------------------------------

class Leases:
    """Exclusive, TTL-bounded ownership of a task key.

    One task is owned by exactly one agent at a time. A lease expires if the
    holder does not renew, so a crashed agent cannot strand work forever.
    """

    DEFAULT_TTL = 10 * 60        # 10 min (agentmemory default)
    MAX_TTL = 60 * 60            # 1 hour cap

    def __init__(self, db_path: str, ttl: int = DEFAULT_TTL):
        self.db_path = db_path
        self.ttl = min(int(ttl), self.MAX_TTL)
        self._lock = threading.Lock()
        self._init()

    def _conn(self):
        c = sqlite3.connect(self.db_path, timeout=10)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA busy_timeout=10000")
        return c

    def _init(self):
        with self._conn() as c:
            c.execute(
                "CREATE TABLE IF NOT EXISTS leases ("
                " task_key TEXT PRIMARY KEY,"
                " holder TEXT NOT NULL,"
                " acquired_at REAL NOT NULL,"
                " expires_at REAL NOT NULL,"
                " status TEXT NOT NULL DEFAULT 'active')")

    def acquire(self, task_key: str, holder: str) -> Dict[str, Any]:
        """Try to claim a task. Returns {ok, holder, expires_at}."""
        now = time.time()
        with self._lock, self._conn() as c:
            row = c.execute("SELECT * FROM leases WHERE task_key=?", (task_key,)).fetchone()
            if row:
                if row["status"] == "active" and row["expires_at"] > now:
                    if row["holder"] == holder:
                        return {"ok": True, "holder": holder,
                                "expires_at": row["expires_at"], "renewed": False}
                    return {"ok": False, "holder": row["holder"],
                            "expires_at": row["expires_at"]}
                # expired / released -> reclaim
                c.execute("DELETE FROM leases WHERE task_key=?", (task_key,))
            expires = now + self.ttl
            c.execute(
                "INSERT OR REPLACE INTO leases "
                "(task_key, holder, acquired_at, expires_at, status) VALUES (?,?,?,?,?)",
                (task_key, holder, now, expires, "active"))
        return {"ok": True, "holder": holder, "expires_at": expires, "renewed": True}

    def renew(self, task_key: str, holder: str) -> bool:
        """Extend the lease. Returns False if the holder no longer owns it."""
        now = time.time()
        with self._lock, self._conn() as c:
            row = c.execute("SELECT * FROM leases WHERE task_key=?", (task_key,)).fetchone()
            if not row or row["holder"] != holder or row["status"] != "active":
                return False
            c.execute("UPDATE leases SET expires_at=? WHERE task_key=?",
                      (max(now, row["expires_at"]) + self.ttl, task_key))
        return True

    def release(self, task_key: str, holder: str) -> bool:
        with self._lock, self._conn() as c:
            row = c.execute("SELECT * FROM leases WHERE task_key=?", (task_key,)).fetchone()
            if not row or row["holder"] != holder:
                return False
            c.execute("UPDATE leases SET status='released' WHERE task_key=?", (task_key,))
        return True

    def cleanup(self) -> int:
        """Reclaim expired leases (returns count)."""
        now = time.time()
        with self._lock, self._conn() as c:
            cur = c.execute(
                "UPDATE leases SET status='expired' "
                "WHERE status='active' AND expires_at <= ?", (now,))
        return cur.rowcount or 0


# ---------------------------------------------------------------------------
# Signals (async mailbox)
# ---------------------------------------------------------------------------

class Signals:
    """Asynchronous mailbox between agents.

    Broadcast (no 'to'), threads (reply_to), read receipts (read_at). TTL sweep.
    """

    def __init__(self, db_path: str, ttl: int = 86400):
        self.db_path = db_path
        self.ttl = ttl
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
                "CREATE TABLE IF NOT EXISTS signals ("
                " id TEXT PRIMARY KEY,"
                " from_agent TEXT NOT NULL,"
                " to_agent TEXT NOT NULL DEFAULT '',"
                " type TEXT NOT NULL DEFAULT 'info',"
                " thread_id TEXT NOT NULL DEFAULT '',"
                " payload TEXT NOT NULL DEFAULT '',"
                " created_at REAL NOT NULL,"
                " read_at REAL,"
                " expires_at REAL NOT NULL)")

    def send(self, from_agent: str, payload: Any, to_agent: str = "",
             type_: str = "info", thread_id: str = "",
             reply_to: Optional[str] = "") -> str:
        """Send a signal. 'to' empty == broadcast. reply_to threads the message."""
        now = time.time()
        # If replying to a message, use that message's ID as the thread_id
        # and also update the original message to share the same thread_id
        if reply_to:
            tid = reply_to
        else:
            tid = thread_id or uuid.uuid4().hex[:12]
        sid = uuid.uuid4().hex
        with self._lock, self._conn() as c:
            c.execute(
                "INSERT INTO signals (id, from_agent, to_agent, type, thread_id,"
                " payload, created_at, expires_at) VALUES (?,?,?,?,?,?,?,?)",
                (sid, from_agent, to_agent, type_, tid,
                 json.dumps(payload, ensure_ascii=False, default=str),
                 now, now + self.ttl))
            # If replying, update the original message's thread_id to match
            if reply_to:
                c.execute(
                    "UPDATE signals SET thread_id=? WHERE id=?",
                    (tid, reply_to))
        return sid

    def read(self, agent: str, unread_only: bool = True, thread_id: str = "") -> List[Dict[str, Any]]:
        """Read messages for one agent (direct + broadcast). Marks read_at."""
        with self._lock, self._conn() as c:
            sql = ("SELECT * FROM signals WHERE expires_at > ? "
                   "AND (to_agent=? OR to_agent='')")
            args: list = [time.time(), agent]
            if unread_only:
                sql += " AND read_at IS NULL"
            if thread_id:
                sql += " AND thread_id=?"
                args.append(thread_id)
            sql += " ORDER BY created_at"
            rows = c.execute(sql, args).fetchall()
            ids = [r["id"] for r in rows]
            if ids and unread_only:
                c.execute(
                    "UPDATE signals SET read_at=? WHERE id IN (%s)"
                    % ",".join("?" * len(ids)), [time.time()] + ids)
            return [dict(r) for r in rows]

    def threads(self) -> List[Dict[str, Any]]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT thread_id, COUNT(*) n, MAX(created_at) last "
                "FROM signals WHERE thread_id != '' GROUP BY thread_id "
                "ORDER BY last DESC").fetchall()
            return [dict(r) for r in rows]

    def cleanup(self) -> int:
        with self._lock, self._conn() as c:
            cur = c.execute("DELETE FROM signals WHERE expires_at <= ?", (time.time(),))
        return cur.rowcount or 0


# ---------------------------------------------------------------------------
# Actions (task graph with dependencies)
# ---------------------------------------------------------------------------

class Actions:
    """Task graph with typed dependency edges + auto-unblock.

    Edge types (from agentmemory actions.ts): requires | unlocks | gated_by |
    conflicts_with | spawned_by. When an action completes, any action whose
    'requires' are all satisfied flips blocked -> pending automatically.
    """

    def __init__(self, db_path: str):
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
                "CREATE TABLE IF NOT EXISTS actions ("
                " id TEXT PRIMARY KEY, title TEXT NOT NULL DEFAULT '',"
                " status TEXT NOT NULL DEFAULT 'pending',"  # pending|active|done|blocked|cancelled
                " assigned_to TEXT NOT NULL DEFAULT '',"
                " priority INTEGER NOT NULL DEFAULT 5,"
                " created_at REAL NOT NULL)")
            c.execute(
                "CREATE TABLE IF NOT EXISTS action_edges ("
                " from_id TEXT NOT NULL, to_id TEXT NOT NULL,"
                " kind TEXT NOT NULL, PRIMARY KEY(from_id, to_id, kind))")

    def create(self, title: str, priority: int = 5,
               requires: Optional[List[str]] = None) -> str:
        aid = uuid.uuid4().hex[:12]
        with self._lock, self._conn() as c:
            blocked = bool(requires)
            status = "blocked" if blocked else "pending"
            c.execute("INSERT INTO actions (id, title, status, priority, created_at)"
                      " VALUES (?,?,?,?,?)", (aid, title, status, priority, time.time()))
            for dep in (requires or []):
                c.execute("INSERT OR IGNORE INTO action_edges (from_id, to_id, kind)"
                          " VALUES (?,?,?)", (dep, aid, "requires"))
        return aid

    def complete(self, aid: str) -> None:
        """Mark done and auto-unblock dependents whose requires are all met."""
        with self._lock, self._conn() as c:
            c.execute("UPDATE actions SET status='done' WHERE id=?", (aid,))
            cur = c.execute("SELECT to_id FROM action_edges WHERE from_id=? AND kind='requires'",
                            (aid,))
            for (to_id,) in cur.fetchall():
                unmet = c.execute(
                    "SELECT COUNT(*) FROM action_edges e "
                    "JOIN actions a ON a.id=e.from_id "
                    "WHERE e.to_id=? AND e.kind='requires' AND a.status!='done'",
                    (to_id,)).fetchone()[0]
                if unmet == 0:
                    c.execute("UPDATE actions SET status='pending' WHERE id=? AND status='blocked'",
                              (to_id,))

    def frontier(self, limit: int = 0) -> List[Dict[str, Any]]:
        """Unblocked (pending) actions, ranked by priority then age."""
        with self._conn() as c:
            sql = ("SELECT * FROM actions WHERE status='pending' "
                   "ORDER BY priority DESC, created_at")
            if limit:
                sql += f" LIMIT {int(limit)}"
            return [dict(r) for r in c.execute(sql).fetchall()]

    def next(self) -> Optional[Dict[str, Any]]:
        f = self.frontier(1)
        return f[0] if f else None

    def claim(self, aid: str, agent: str) -> bool:
        """Atomically claim a pending action for an agent (pending -> active)."""
        with self._lock, self._conn() as c:
            cur = c.execute(
                "UPDATE actions SET status='active', assigned_to=? "
                "WHERE id=? AND status='pending'", (agent, aid))
            return cur.rowcount > 0

    def counts(self) -> Dict[str, int]:
        with self._conn() as c:
            rows = c.execute("SELECT status, COUNT(*) FROM actions GROUP BY status").fetchall()
            return {r[0]: r[1] for r in rows}
