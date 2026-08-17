"""Durable local fibers for resumable multi-step agent work."""
from __future__ import annotations

import json
import sqlite3
import time
import uuid
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

try:
    from .nextgen import AuditChain, _ManagedConnection, canonical_json
except ImportError:
    from noesis_nextgen import AuditChain, _ManagedConnection, canonical_json


@dataclass(frozen=True)
class FiberRecord:
    fiber_id: str
    name: str
    status: str
    step: int
    state: Dict[str, Any]
    payload: Dict[str, Any]
    attempt: int
    error: str = ""


class FiberInterrupted(RuntimeError):
    pass


class FiberStore:
    """SQLite-backed checkpoint store; a failed step never erases its last checkpoint."""

    def __init__(self, db_path: str, audit: Optional[AuditChain] = None):
        self.db_path = db_path
        self.audit = audit
        with self._conn() as db:
            db.execute("PRAGMA busy_timeout=5000")
            db.execute("""CREATE TABLE IF NOT EXISTS fibers(
                fiber_id TEXT PRIMARY KEY, name TEXT NOT NULL, status TEXT NOT NULL,
                step INTEGER NOT NULL, state TEXT NOT NULL, payload TEXT NOT NULL,
                attempt INTEGER NOT NULL, error TEXT NOT NULL, updated_at REAL NOT NULL)""")

    def _conn(self):
        db = sqlite3.connect(self.db_path, timeout=5, factory=_ManagedConnection)
        db.row_factory = sqlite3.Row
        return db

    def register(self, name: str, payload: Optional[Dict[str, Any]] = None, fiber_id: str = "") -> str:
        fid = fiber_id or uuid.uuid4().hex
        with self._conn() as db:
            db.execute("INSERT OR IGNORE INTO fibers VALUES(?,?,?,?,?,?,?,?,?)",
                       (fid, name, "checkpointed", 0, "{}", canonical_json(payload or {}), 0, "", time.time()))
        return fid

    def _row(self, fiber_id: str) -> FiberRecord:
        with self._conn() as db:
            row = db.execute("SELECT * FROM fibers WHERE fiber_id=?", (fiber_id,)).fetchone()
        if row is None:
            raise KeyError(fiber_id)
        return FiberRecord(row["fiber_id"], row["name"], row["status"], row["step"], json.loads(row["state"]), json.loads(row["payload"]), row["attempt"], row["error"])

    def get(self, fiber_id: str) -> FiberRecord:
        return self._row(fiber_id)

    def checkpoint(self, fiber_id: str, step: int, state: Dict[str, Any], done: bool = False) -> FiberRecord:
        current = self._row(fiber_id)
        if step < current.step:
            raise ValueError("checkpoint step cannot move backwards")
        status = "completed" if done else "checkpointed"
        with self._conn() as db:
            db.execute("UPDATE fibers SET status=?,step=?,state=?,error='',updated_at=? WHERE fiber_id=?",
                       (status, step, canonical_json(state), time.time(), fiber_id))
        record = self._row(fiber_id)
        if self.audit:
            self.audit.append("fiber", "fiber_checkpoint", {"fiber_id": fiber_id, "step": step, "status": status})
        return record

    def restore(self, fiber_id: str, step: int, state: Dict[str, Any]) -> FiberRecord:
        """Restore an explicitly verified state after a crash or late regression.

        Unlike checkpoint(), restore may move to an older step, but only through
        this explicit recovery path. The action is auditable and increments the
        attempt counter so recovery cannot masquerade as normal progress.
        """
        current = self._row(fiber_id)
        if step < 0:
            raise ValueError("restore step cannot be negative")
        with self._conn() as db:
            db.execute(
                "UPDATE fibers SET status='restored',step=?,state=?,attempt=attempt+1,error='',updated_at=? WHERE fiber_id=?",
                (step, canonical_json(state), time.time(), fiber_id),
            )
        record = self._row(fiber_id)
        if self.audit:
            self.audit.append("fiber", "fiber_restored", {"fiber_id": fiber_id, "from_step": current.step, "to_step": step})
        return record

    def recoverable(self) -> List[FiberRecord]:
        with self._conn() as db:
            ids = [r["fiber_id"] for r in db.execute("SELECT fiber_id FROM fibers WHERE status IN ('running','interrupted','checkpointed') ORDER BY updated_at")]
        return [self._row(fid) for fid in ids]

    def resume(self, fiber_id: str, runner: Callable[[int, Dict[str, Any], Dict[str, Any]], Dict[str, Any]]) -> FiberRecord:
        current = self._row(fiber_id)
        if current.status == "completed":
            return current
        with self._conn() as db:
            db.execute("UPDATE fibers SET status='running',attempt=attempt+1,error='',updated_at=? WHERE fiber_id=?", (time.time(), fiber_id))
        current = self._row(fiber_id)
        try:
            result = runner(current.step, dict(current.state), dict(current.payload))
            if not isinstance(result, dict) or "step" not in result or "state" not in result:
                raise TypeError("runner must return step and state")
            return self.checkpoint(fiber_id, int(result["step"]), dict(result["state"]), bool(result.get("done", False)))
        except Exception as exc:
            with self._conn() as db:
                db.execute("UPDATE fibers SET status='interrupted',error=?,updated_at=? WHERE fiber_id=?", (type(exc).__name__ + ": " + str(exc), time.time(), fiber_id))
            if self.audit:
                self.audit.append("fiber", "fiber_interrupted", {"fiber_id": fiber_id, "step": current.step, "error": type(exc).__name__})
            raise


__all__ = ["FiberRecord", "FiberInterrupted", "FiberStore"]
