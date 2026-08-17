"""Durable best-state protection and rollback for long-running agent runs.

Inspired by long-horizon evaluation findings: preserve the best verified state,
keep failed or regressing candidates observable, and make recovery measurable.
This module does not execute artifacts or claim OS-level isolation.
"""
from __future__ import annotations

import hashlib
import json
import math
import sqlite3
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterator, Optional, Tuple


class DecisionStatus(Enum):
    BEST_ACCEPTED = "best_accepted"
    ACCEPTED_NOT_BEST = "accepted_not_best"
    REJECTED_VERIFICATION = "rejected_verification"
    REJECTED_SCORE = "rejected_score"


class RecoveryStatus(Enum):
    RECOVERED = "recovered"
    NOOP = "noop"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class StateRecord:
    state_id: str
    run_id: str
    score: float
    payload: Any
    artifact_digest: str
    verifier_status: str
    metadata: Dict[str, Any]
    created_at: float


@dataclass(frozen=True)
class CandidateDecision:
    status: DecisionStatus
    state: StateRecord
    best_state_id: Optional[str]
    best_score: Optional[float]
    revision: int


@dataclass(frozen=True)
class RecoveryResult:
    status: RecoveryStatus
    run_id: str
    from_state_id: Optional[str]
    to_state_id: Optional[str]
    best_score: Optional[float]
    revision: int


class BestStateStore:
    """SQLite-backed verified-state ledger with fail-soft recovery semantics."""

    def __init__(self, path: str):
        self.path = str(path)
        self._initialize()

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path, timeout=5.0)
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _initialize(self) -> None:
        parent = Path(self.path).parent
        if str(parent) not in ("", "."):
            parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS run_state (
                    run_id TEXT PRIMARY KEY,
                    best_state_id TEXT,
                    best_score REAL,
                    current_state_id TEXT,
                    revision INTEGER NOT NULL DEFAULT 0,
                    updated_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS states (
                    state_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    score REAL NOT NULL,
                    payload_json TEXT NOT NULL,
                    artifact_digest TEXT NOT NULL,
                    verifier_status TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    created_at REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_states_run_created
                    ON states(run_id, created_at);
                CREATE TABLE IF NOT EXISTS rollback_events (
                    event_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    from_state_id TEXT,
                    to_state_id TEXT,
                    reason TEXT NOT NULL,
                    created_at REAL NOT NULL
                );
                """
            )

    @staticmethod
    def _payload_json(payload: Any) -> str:
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    @staticmethod
    def _digest(payload_json: str) -> str:
        return hashlib.sha256(payload_json.encode("utf-8")).hexdigest()

    @staticmethod
    def _decode_state(row: Tuple[Any, ...]) -> StateRecord:
        return StateRecord(
            state_id=str(row[0]),
            run_id=str(row[1]),
            score=float(row[2]),
            payload=json.loads(row[3]),
            artifact_digest=str(row[4]),
            verifier_status=str(row[5]),
            metadata=json.loads(row[6]),
            created_at=float(row[7]),
        )

    @staticmethod
    def _ensure_run(conn: sqlite3.Connection, run_id: str, now: float) -> None:
        conn.execute(
            "INSERT OR IGNORE INTO run_state(run_id, revision, updated_at) VALUES (?, 0, ?)",
            (run_id, now),
        )

    def record_candidate(
        self,
        run_id: str,
        score: float,
        payload: Any,
        verifier_status: str = "passed",
        artifact_digest: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        state_id: Optional[str] = None,
    ) -> CandidateDecision:
        now = time.time()
        sid = state_id or uuid.uuid4().hex
        payload_json = self._payload_json(payload)
        digest = artifact_digest or self._digest(payload_json)
        meta = dict(metadata or {})
        valid_score = isinstance(score, (int, float)) and math.isfinite(float(score))
        with self._connection() as conn:
            self._ensure_run(conn, run_id, now)
            conn.execute(
                "INSERT INTO states(state_id, run_id, score, payload_json, artifact_digest, verifier_status, metadata_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (sid, run_id, float(score) if valid_score else 0.0, payload_json, digest, verifier_status, self._payload_json(meta), now),
            )
            row = conn.execute(
                "SELECT state_id, run_id, score, payload_json, artifact_digest, verifier_status, metadata_json, created_at FROM states WHERE state_id = ?",
                (sid,),
            ).fetchone()
            state = self._decode_state(row)
            run = conn.execute(
                "SELECT best_state_id, best_score, current_state_id, revision FROM run_state WHERE run_id = ?",
                (run_id,),
            ).fetchone()
            best_id, best_score, current_id, revision = run
            revision = int(revision) + 1
            if not valid_score:
                status = DecisionStatus.REJECTED_SCORE
                conn.execute("UPDATE run_state SET revision = ?, updated_at = ? WHERE run_id = ?", (revision, now, run_id))
            elif verifier_status != "passed":
                status = DecisionStatus.REJECTED_VERIFICATION
                conn.execute("UPDATE run_state SET revision = ?, updated_at = ? WHERE run_id = ?", (revision, now, run_id))
            else:
                conn.execute(
                    "UPDATE run_state SET current_state_id = ?, revision = ?, updated_at = ? WHERE run_id = ?",
                    (sid, revision, now, run_id),
                )
                if best_id is None or float(score) > float(best_score):
                    best_id = sid
                    best_score = float(score)
                    status = DecisionStatus.BEST_ACCEPTED
                    conn.execute(
                        "UPDATE run_state SET best_state_id = ?, best_score = ? WHERE run_id = ?",
                        (best_id, best_score, run_id),
                    )
                else:
                    status = DecisionStatus.ACCEPTED_NOT_BEST
            return CandidateDecision(status, state, best_id, None if best_score is None else float(best_score), revision)

    def best(self, run_id: str) -> Optional[StateRecord]:
        with self._connection() as conn:
            row = conn.execute(
                "SELECT s.state_id, s.run_id, s.score, s.payload_json, s.artifact_digest, s.verifier_status, s.metadata_json, s.created_at FROM states s JOIN run_state r ON r.best_state_id = s.state_id WHERE r.run_id = ?",
                (run_id,),
            ).fetchone()
            return None if row is None else self._decode_state(row)

    def current(self, run_id: str) -> Optional[StateRecord]:
        with self._connection() as conn:
            row = conn.execute(
                "SELECT s.state_id, s.run_id, s.score, s.payload_json, s.artifact_digest, s.verifier_status, s.metadata_json, s.created_at FROM states s JOIN run_state r ON r.current_state_id = s.state_id WHERE r.run_id = ?",
                (run_id,),
            ).fetchone()
            return None if row is None else self._decode_state(row)

    def history(self, run_id: str) -> Tuple[StateRecord, ...]:
        with self._connection() as conn:
            rows = conn.execute(
                "SELECT state_id, run_id, score, payload_json, artifact_digest, verifier_status, metadata_json, created_at FROM states WHERE run_id = ? ORDER BY created_at, state_id",
                (run_id,),
            ).fetchall()
            return tuple(self._decode_state(row) for row in rows)

    def rollback(self, run_id: str, state_id: Optional[str] = None, reason: str = "manual") -> RecoveryResult:
        now = time.time()
        with self._connection() as conn:
            run = conn.execute(
                "SELECT best_state_id, best_score, current_state_id, revision FROM run_state WHERE run_id = ?",
                (run_id,),
            ).fetchone()
            if run is None or run[0] is None:
                return RecoveryResult(RecoveryStatus.UNAVAILABLE, run_id, None, None, None, 0)
            target_id = state_id or str(run[0])
            target = conn.execute(
                "SELECT state_id, verifier_status FROM states WHERE state_id = ? AND run_id = ?",
                (target_id, run_id),
            ).fetchone()
            if target is None or target[1] != "passed":
                return RecoveryResult(RecoveryStatus.UNAVAILABLE, run_id, run[2], None, float(run[1]), int(run[3]))
            revision = int(run[3]) + 1
            from_id = run[2]
            status = RecoveryStatus.NOOP if from_id == target_id else RecoveryStatus.RECOVERED
            if status is RecoveryStatus.RECOVERED:
                conn.execute(
                    "INSERT INTO rollback_events(event_id, run_id, from_state_id, to_state_id, reason, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (uuid.uuid4().hex, run_id, from_id, target_id, str(reason), now),
                )
            conn.execute(
                "UPDATE run_state SET current_state_id = ?, revision = ?, updated_at = ? WHERE run_id = ?",
                (target_id, revision, now, run_id),
            )
            return RecoveryResult(status, run_id, from_id, target_id, float(run[1]), revision)

    def recover(self, run_id: str, reason: str = "automatic_best_state_recovery") -> RecoveryResult:
        return self.rollback(run_id, None, reason)

    def rollback_count(self, run_id: str) -> int:
        with self._connection() as conn:
            row = conn.execute("SELECT COUNT(*) FROM rollback_events WHERE run_id = ?", (run_id,)).fetchone()
            return int(row[0])


__all__ = [
    "BestStateStore",
    "CandidateDecision",
    "DecisionStatus",
    "RecoveryResult",
    "RecoveryStatus",
    "StateRecord",
]
