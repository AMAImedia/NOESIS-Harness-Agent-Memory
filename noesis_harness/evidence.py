"""Evidence-weighted memory with provenance and explicit conflict handling."""
from __future__ import annotations

import hashlib
import json
import math
import sqlite3
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

try:
    from .nextgen import AuditChain, _ManagedConnection, canonical_json
except ImportError:
    from noesis_nextgen import AuditChain, _ManagedConnection, canonical_json


@dataclass(frozen=True)
class EvidenceFact:
    fact_id: str
    statement: str
    kind: str
    scope: str
    confidence: float
    observed_at: float
    expires_at: float
    source_ids: Tuple[str, ...]
    status: str = "active"


class EvidenceStore:
    """Facts are never silently replaced; contradictions become explicit proposals."""

    def __init__(self, db_path: str, audit: Optional[AuditChain] = None):
        self.db_path = db_path
        self.audit = audit
        with self._conn() as db:
            db.execute("PRAGMA busy_timeout=5000")
            db.executescript("""
            CREATE TABLE IF NOT EXISTS facts(
                fact_id TEXT PRIMARY KEY, statement TEXT NOT NULL, fingerprint TEXT NOT NULL,
                kind TEXT NOT NULL, scope TEXT NOT NULL, confidence REAL NOT NULL,
                observed_at REAL NOT NULL, expires_at REAL NOT NULL, source_ids TEXT NOT NULL,
                status TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS conflicts(
                conflict_id TEXT PRIMARY KEY, left_id TEXT NOT NULL, right_id TEXT NOT NULL,
                reason TEXT NOT NULL, status TEXT NOT NULL, created_at REAL NOT NULL)
            """)

    def _conn(self):
        db = sqlite3.connect(self.db_path, timeout=5, factory=_ManagedConnection)
        db.row_factory = sqlite3.Row
        return db

    @staticmethod
    def _fingerprint(statement: str, kind: str, scope: str) -> str:
        return hashlib.sha256((scope + "\0" + kind + "\0" + statement.strip().casefold()).encode("utf-8")).hexdigest()

    def add(self, statement: str, source_ids: Sequence[str], kind: str = "semantic", scope: str = "shared", confidence: float = 0.5, ttl: float = 0.0, observed_at: Optional[float] = None) -> str:
        if not statement.strip() or not source_ids or not 0.0 <= confidence <= 1.0:
            raise ValueError("statement, source_ids and confidence are required")
        now = observed_at if observed_at is not None else time.time()
        expires = now + ttl if ttl > 0 else 0.0
        fp = self._fingerprint(statement, kind, scope)
        with self._conn() as db:
            row = db.execute("SELECT fact_id,source_ids,confidence FROM facts WHERE fingerprint=?", (fp,)).fetchone()
            if row:
                merged = sorted(set(json.loads(row["source_ids"])) | set(source_ids))
                db.execute("UPDATE facts SET source_ids=?,confidence=?,observed_at=?,expires_at=?,status='active' WHERE fact_id=?", (canonical_json(merged), max(confidence, row["confidence"]), now, expires, row["fact_id"]))
                fact_id = row["fact_id"]
            else:
                fact_id = uuid.uuid4().hex
                db.execute("INSERT INTO facts VALUES(?,?,?,?,?,?,?,?,?,?)", (fact_id, statement.strip(), fp, kind, scope, confidence, now, expires, canonical_json(sorted(set(source_ids))), "active"))
        if self.audit:
            self.audit.append("memory", "evidence_fact_added", {"fact_id": fact_id, "scope": scope, "source_count": len(set(source_ids))})
        return fact_id

    def get(self, fact_id: str) -> EvidenceFact:
        with self._conn() as db:
            row = db.execute("SELECT * FROM facts WHERE fact_id=?", (fact_id,)).fetchone()
        if row is None:
            raise KeyError(fact_id)
        return EvidenceFact(row["fact_id"], row["statement"], row["kind"], row["scope"], row["confidence"], row["observed_at"], row["expires_at"], tuple(json.loads(row["source_ids"])), row["status"])

    def search(self, query: str, limit: int = 10, scope: str = "", now: Optional[float] = None) -> List[Dict[str, Any]]:
        terms = [x for x in query.casefold().split() if x]
        if not terms:
            return []
        current = now if now is not None else time.time()
        with self._conn() as db:
            rows = db.execute("SELECT * FROM facts WHERE status != 'archived' AND (scope=? OR ?='')", (scope, scope)).fetchall()
        results=[]
        for row in rows:
            statement = row["statement"].casefold()
            hits = sum(1 for term in terms if term in statement)
            if not hits:
                continue
            age_days = max(0.0, (current - row["observed_at"]) / 86400.0)
            decay = math.exp(-age_days / 30.0)
            if row["expires_at"] and current > row["expires_at"]:
                decay *= 0.1
            score = (hits / len(terms)) * 0.55 + row["confidence"] * 0.30 + decay * 0.15
            results.append({"fact_id": row["fact_id"], "statement": row["statement"], "kind": row["kind"], "scope": row["scope"], "confidence": row["confidence"], "freshness": decay, "score": score, "source_ids": json.loads(row["source_ids"]), "reason": {"term_hits": hits, "term_count": len(terms), "confidence": row["confidence"], "freshness": decay}})
        return sorted(results, key=lambda x: (-x["score"], x["fact_id"]))[:limit]

    def mark_conflict(self, left_id: str, right_id: str, reason: str) -> str:
        if left_id == right_id or not reason.strip():
            raise ValueError("two distinct facts and reason required")
        self.get(left_id); self.get(right_id)
        cid = uuid.uuid4().hex
        with self._conn() as db:
            db.execute("INSERT INTO conflicts VALUES(?,?,?,?,?,?)", (cid, left_id, right_id, reason.strip(), "pending", time.time()))
            db.execute("UPDATE facts SET status='contested' WHERE fact_id IN (?,?)", (left_id, right_id))
        if self.audit:
            self.audit.append("memory", "evidence_conflict_marked", {"conflict_id": cid, "left_id": left_id, "right_id": right_id})
        return cid

    def consolidation_proposals(self) -> List[Dict[str, Any]]:
        with self._conn() as db:
            rows = db.execute("SELECT * FROM conflicts WHERE status='pending' ORDER BY created_at").fetchall()
        return [{"conflict_id": r["conflict_id"], "left": self.get(r["left_id"]), "right": self.get(r["right_id"]), "reason": r["reason"], "status": r["status"]} for r in rows]

    def decide_conflict(self, conflict_id: str, winner_id: str = "", resolution: str = "") -> bool:
        if not resolution.strip():
            raise ValueError("resolution is required")
        with self._conn() as db:
            row = db.execute("SELECT left_id,right_id,status FROM conflicts WHERE conflict_id=?", (conflict_id,)).fetchone()
            if row is None or row["status"] != "pending" or winner_id not in (row["left_id"], row["right_id"], ""):
                return False
            db.execute("UPDATE conflicts SET status='resolved',reason=? WHERE conflict_id=?", (resolution.strip(), conflict_id))
            if winner_id:
                db.execute("UPDATE facts SET status='active' WHERE fact_id=?", (winner_id,))
                loser = row["right_id"] if winner_id == row["left_id"] else row["left_id"]
                db.execute("UPDATE facts SET status='superseded' WHERE fact_id=?", (loser,))
        if self.audit:
            self.audit.append("memory", "evidence_conflict_resolved", {"conflict_id": conflict_id, "winner_id": winner_id})
        return True


__all__ = ["EvidenceFact", "EvidenceStore"]
