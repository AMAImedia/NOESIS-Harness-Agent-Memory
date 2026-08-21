"""Durable per-turn checkpoints for bounded local agent loops.

Patterns are borrowed from NOESIS FiberStore, append-only recovery receipts, and
transactional WAL state. The module stores no executable code and never resumes a
checkpoint whose canonical state digest does not verify.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sqlite3
import time
from contextlib import contextmanager
from typing import Any, Mapping, Optional

SCHEMA = "noesis.turn-checkpoint.v1"


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class TurnCheckpoint:
    run_id: str
    turn: int
    status: str
    state: Mapping[str, Any]
    output_digest: str
    state_digest: str
    previous_digest: str
    created_at: float
    schema_version: str = SCHEMA

    def payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "turn": self.turn,
            "status": self.status,
            "state": dict(self.state),
            "output_digest": self.output_digest,
            "state_digest": self.state_digest,
            "previous_digest": self.previous_digest,
            "created_at": self.created_at,
        }


class TurnCheckpointError(ValueError):
    """Raised for invalid, stale, or corrupt checkpoint state."""


class DurableTurnCheckpointStore:
    """Persist every accepted turn atomically and resume only verified state."""

    def __init__(self, path: str, *, clock=time.time) -> None:
        if not path or not callable(clock):
            raise ValueError("checkpoint_configuration_invalid")
        self.path = str(Path(path).expanduser().resolve())
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.clock = clock
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS turn_checkpoints(
                run_id TEXT NOT NULL, turn INTEGER NOT NULL, payload TEXT NOT NULL,
                digest TEXT NOT NULL, PRIMARY KEY(run_id, turn))""")
            db.execute("CREATE TABLE IF NOT EXISTS turn_runs(run_id TEXT PRIMARY KEY, status TEXT NOT NULL, latest_turn INTEGER NOT NULL, latest_digest TEXT NOT NULL)")
            db.commit()

    @contextmanager
    def _connect(self):
        db = sqlite3.connect(self.path, timeout=5.0)
        db.row_factory = sqlite3.Row
        try:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA busy_timeout=5000")
            yield db
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def _decode(row: sqlite3.Row) -> TurnCheckpoint:
        try:
            payload = json.loads(str(row["payload"]))
            if not isinstance(payload, dict) or payload.get("schema_version") != SCHEMA:
                raise ValueError("schema")
            expected = _digest(payload)
            if expected != str(row["digest"]):
                raise ValueError("digest")
            state = payload.get("state")
            if not isinstance(state, dict):
                raise ValueError("state")
            if payload.get("state_digest") != _digest(state):
                raise ValueError("state_digest")
            return TurnCheckpoint(str(payload["run_id"]), int(payload["turn"]), str(payload["status"]), state, str(payload["output_digest"]), str(payload["state_digest"]), str(payload["previous_digest"]), float(payload["created_at"]))
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise TurnCheckpointError("checkpoint_corrupt") from exc

    def begin(self, run_id: str) -> TurnCheckpoint:
        if not isinstance(run_id, str) or not run_id:
            raise TurnCheckpointError("run_id_required")
        with self._connect() as db:
            row = db.execute("SELECT * FROM turn_runs WHERE run_id=?", (run_id,)).fetchone()
            if row is None:
                db.execute("INSERT INTO turn_runs VALUES (?, ?, ?, ?)", (run_id, "running", -1, ""))
                db.commit()
                return TurnCheckpoint(run_id, -1, "running", {}, "", "", "", float(self.clock()))
        return self.latest(run_id)

    def latest(self, run_id: str) -> TurnCheckpoint:
        with self._connect() as db:
            row = db.execute("SELECT * FROM turn_checkpoints WHERE run_id=? ORDER BY turn DESC LIMIT 1", (run_id,)).fetchone()
            run = db.execute("SELECT status, latest_turn, latest_digest FROM turn_runs WHERE run_id=?", (run_id,)).fetchone()
        if run is None:
            raise TurnCheckpointError("run_not_found")
        if row is None:
            return TurnCheckpoint(run_id, int(run["latest_turn"]), str(run["status"]), {}, "", str(run["latest_digest"]), "", 0.0)
        return self._decode(row)

    def commit_turn(self, run_id: str, turn: int, state: Mapping[str, Any], output: Any, *, done: bool = False) -> TurnCheckpoint:
        if not isinstance(turn, int) or isinstance(turn, bool) or turn < 0:
            raise TurnCheckpointError("turn_invalid")
        if not isinstance(state, Mapping):
            raise TurnCheckpointError("state_mapping_required")
        current = self.latest(run_id)
        state_dict = dict(state)
        requested_status = "completed" if done else "checkpointed"
        requested_output_digest = _digest(output)
        if turn <= current.turn:
            with self._connect() as db:
                existing_row = db.execute("SELECT * FROM turn_checkpoints WHERE run_id=? AND turn=?", (run_id, turn)).fetchone()
            if existing_row is None:
                raise TurnCheckpointError("turn_not_sequential")
            existing = self._decode(existing_row)
            if (existing.status, dict(existing.state), existing.output_digest, existing.previous_digest) == (requested_status, state_dict, requested_output_digest, current.previous_digest if turn == current.turn else existing.previous_digest):
                return existing
            raise TurnCheckpointError("checkpoint_replay_conflict")
        if turn != current.turn + 1:
            raise TurnCheckpointError("turn_not_sequential")
        payload = {"schema_version": SCHEMA, "run_id": run_id, "turn": turn, "status": requested_status, "state": state_dict, "output_digest": requested_output_digest, "state_digest": _digest(state_dict), "previous_digest": current.state_digest, "created_at": float(self.clock())}
        digest = _digest(payload)
        record = TurnCheckpoint(run_id, turn, payload["status"], state_dict, payload["output_digest"], payload["state_digest"], payload["previous_digest"], payload["created_at"])
        with self._connect() as db:
            db.execute("INSERT INTO turn_checkpoints VALUES (?, ?, ?, ?)", (run_id, turn, _canonical(payload), digest))
            db.execute("UPDATE turn_runs SET status=?, latest_turn=?, latest_digest=? WHERE run_id=?", (record.status, turn, record.state_digest, run_id))
            db.commit()
        return record

    def interrupt(self, run_id: str, reason: str) -> TurnCheckpoint:
        current = self.latest(run_id)
        if not isinstance(reason, str) or not reason:
            raise TurnCheckpointError("interrupt_reason_required")
        with self._connect() as db:
            db.execute("UPDATE turn_runs SET status=? WHERE run_id=?", ("interrupted", run_id))
            db.commit()
        return TurnCheckpoint(run_id, current.turn, "interrupted", dict(current.state), current.output_digest, current.state_digest, current.previous_digest, current.created_at)

    def recover(self, run_id: str) -> TurnCheckpoint:
        current = self.latest(run_id)
        if current.status == "corrupted":
            raise TurnCheckpointError("checkpoint_quarantined")
        with self._connect() as db:
            row = db.execute("SELECT * FROM turn_checkpoints WHERE run_id=? ORDER BY turn DESC LIMIT 1", (run_id,)).fetchone()
        if row is not None:
            self._decode(row)
        with self._connect() as db:
            db.execute("UPDATE turn_runs SET status=? WHERE run_id=?", ("running", run_id))
            db.commit()
        return TurnCheckpoint(run_id, current.turn, "running", dict(current.state), current.output_digest, current.state_digest, current.previous_digest, current.created_at)

    def verify_chain(self, run_id: str) -> bool:
        with self._connect() as db:
            rows = db.execute("SELECT * FROM turn_checkpoints WHERE run_id=? ORDER BY turn", (run_id,)).fetchall()
        previous = ""
        for row in rows:
            record = self._decode(row)
            if record.previous_digest != previous:
                raise TurnCheckpointError("checkpoint_chain_mismatch")
            previous = record.state_digest
        return True


__all__ = ["SCHEMA", "TurnCheckpoint", "TurnCheckpointError", "DurableTurnCheckpointStore"]


def _self_test_marker() -> None:
    """Keep module import side-effect free; marker exists for audit tooling."""
    return None
