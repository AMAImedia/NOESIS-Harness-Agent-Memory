"""Durable non-overlapping work coordinator for NOESIS agents."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

try:
    from .nextgen import AuditChain, _ManagedConnection, canonical_json
except ImportError:
    from noesis_nextgen import AuditChain, _ManagedConnection, canonical_json


@dataclass(frozen=True)
class WorkClaim:
    task_id: str
    agent_id: str
    lease_until: float
    attempt: int


class WorkCoordinator:
    """Only one live owner can claim a task; dependent tasks unblock on completion."""

    def __init__(self, db_path: str, audit: Optional[AuditChain] = None):
        self.db_path = db_path
        self.audit = audit
        with self._conn() as db:
            db.execute("PRAGMA busy_timeout=5000")
            db.executescript("""
            CREATE TABLE IF NOT EXISTS work_items(
                task_id TEXT PRIMARY KEY, deps TEXT NOT NULL, scope TEXT NOT NULL,
                status TEXT NOT NULL, owner TEXT NOT NULL, lease_until REAL NOT NULL,
                attempt INTEGER NOT NULL, result_digest TEXT NOT NULL, result TEXT NOT NULL)
            """)

    def _conn(self):
        db = sqlite3.connect(self.db_path, timeout=5, factory=_ManagedConnection)
        db.row_factory = sqlite3.Row
        return db

    def add(self, task_id: str, deps: Sequence[str] = (), scope: str = "shared") -> None:
        if not task_id or task_id in deps:
            raise ValueError("invalid task")
        with self._conn() as db:
            db.execute("INSERT INTO work_items VALUES(?,?,?,?,?,?,?,?,?)", (task_id, canonical_json(list(deps)), scope, "pending", "", 0.0, 0, "", ""))

    def _ready(self, db, now: float) -> List[sqlite3.Row]:
        rows = db.execute("SELECT * FROM work_items WHERE status='pending' OR (status='leased' AND lease_until<?) ORDER BY task_id", (now,)).fetchall()
        ready=[]
        for row in rows:
            deps=json.loads(row["deps"])
            if all(db.execute("SELECT status FROM work_items WHERE task_id=?", (dep,)).fetchone() and db.execute("SELECT status FROM work_items WHERE task_id=?", (dep,)).fetchone()["status"] == "done" for dep in deps):
                ready.append(row)
        return ready

    def claim(self, agent_id: str, scopes: Sequence[str] = (), ttl: float = 3600.0, now: Optional[float] = None) -> Optional[WorkClaim]:
        if not agent_id or ttl <= 0:
            raise ValueError("agent_id and positive ttl required")
        current = now if now is not None else time.time()
        allowed=set(scopes)
        with self._conn() as db:
            ready=self._ready(db, current)
            for row in ready:
                if row["scope"] not in allowed and row["scope"] != "shared":
                    continue
                lease_until=current + ttl
                cur=db.execute("UPDATE work_items SET status='leased',owner=?,lease_until=?,attempt=attempt+1 WHERE task_id=? AND (status='pending' OR (status='leased' AND lease_until<?))", (agent_id, lease_until, row["task_id"], current))
                if cur.rowcount == 1:
                    claim=WorkClaim(row["task_id"], agent_id, lease_until, row["attempt"] + 1)
                    if self.audit: self.audit.append(agent_id, "work_claimed", {"task_id": claim.task_id, "attempt": claim.attempt})
                    return claim
        return None

    def heartbeat(self, task_id: str, agent_id: str, ttl: float = 3600.0, now: Optional[float] = None) -> bool:
        current=now if now is not None else time.time()
        with self._conn() as db:
            cur=db.execute("UPDATE work_items SET lease_until=? WHERE task_id=? AND status='leased' AND owner=? AND lease_until>=?", (current+ttl, task_id, agent_id, current))
            return cur.rowcount == 1

    def complete(self, task_id: str, agent_id: str, result: Any) -> bool:
        digest=hashlib.sha256(canonical_json(result).encode("utf-8")).hexdigest()
        with self._conn() as db:
            cur=db.execute("UPDATE work_items SET status='done',owner=?,lease_until=0,result_digest=?,result=? WHERE task_id=? AND status='leased' AND owner=?", (agent_id, digest, canonical_json(result), task_id, agent_id))
            ok=cur.rowcount == 1
        if ok and self.audit: self.audit.append(agent_id, "work_completed", {"task_id": task_id, "result_digest": digest})
        return ok

    def status(self, task_id: str) -> Dict[str, Any]:
        with self._conn() as db:
            row=db.execute("SELECT * FROM work_items WHERE task_id=?", (task_id,)).fetchone()
        if row is None: raise KeyError(task_id)
        return {"task_id": row["task_id"], "deps": json.loads(row["deps"]), "scope": row["scope"], "status": row["status"], "owner": row["owner"], "attempt": row["attempt"], "result_digest": row["result_digest"], "result": json.loads(row["result"]) if row["result"] else None}

    def reclaim_expired(self, now: Optional[float] = None) -> int:
        current=now if now is not None else time.time()
        with self._conn() as db:
            cur=db.execute("UPDATE work_items SET status='pending',owner='',lease_until=0 WHERE status='leased' AND lease_until<?", (current,))
            return cur.rowcount


__all__=["WorkClaim", "WorkCoordinator"]
