"""SQLite/WAL transactional administrative state and audit backend.

The backend keeps operator sessions, reviewer grants and signed mutation audit
records in one database so state and evidence commit or roll back together.
It is deliberately independent from provider/tool execution.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import sqlite3
import time


class _ManagedConnection(sqlite3.Connection):
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            if exc_type is None:
                self.commit()
            else:
                self.rollback()
        finally:
            self.close()
        return False
from typing import Any, Callable, Mapping, Optional, Sequence

SCHEMA_VERSION = "noesis.sqlite-admin-state.v1"
RECEIPT_SCHEMA = "noesis.signed-mutation-receipt.v1"


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _sign(key: bytes, value: Mapping[str, Any]) -> str:
    return hmac.new(key, _canonical(value).encode("utf-8"), hashlib.sha256).hexdigest()


class SQLiteAdminStateError(ValueError):
    """Raised for invalid or denied administrative mutations."""


class SQLiteAdministrativeBackend:
    """Transactional SQLite/WAL store for sessions, reviewer policy and audit."""

    def __init__(self, path: str, *, signing_key: bytes, admin_ids: Sequence[str] = (), clock: Callable[[], float] = time.time) -> None:
        if not path or not isinstance(signing_key, bytes) or len(signing_key) < 16:
            raise ValueError("sqlite_admin_configuration_required")
        self.path = path
        self.signing_key = signing_key
        self.admin_ids = frozenset(str(item) for item in admin_ids)
        self.clock = clock
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=10.0, factory=_ManagedConnection)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA busy_timeout=10000")
        return db

    def _initialize(self) -> None:
        with self._connect() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS admin_meta(
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS operator_sessions(
                session_id TEXT PRIMARY KEY,
                operator_id TEXT NOT NULL,
                scopes TEXT NOT NULL,
                expires_at REAL NOT NULL,
                active INTEGER NOT NULL,
                updated_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS reviewer_grants(
                operator_id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                scopes TEXT NOT NULL,
                active INTEGER NOT NULL,
                updated_at REAL NOT NULL,
                PRIMARY KEY(operator_id, session_id)
            );
            CREATE TABLE IF NOT EXISTS mutation_audit(
                action_id TEXT PRIMARY KEY,
                operation TEXT NOT NULL,
                actor_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                previous_state TEXT NOT NULL,
                new_state TEXT NOT NULL,
                payload_digest TEXT NOT NULL,
                signature TEXT NOT NULL,
                created_at REAL NOT NULL
            );
            """)
            db.execute("INSERT OR IGNORE INTO admin_meta(key, value) VALUES('schema_version', ?)", (SCHEMA_VERSION,))

    @staticmethod
    def _scopes(scopes: Sequence[str]) -> str:
        return _canonical(sorted({str(item) for item in scopes}))

    def _active_session(self, db: sqlite3.Connection, operator_id: str, session_id: str, required_scope: str = "") -> sqlite3.Row:
        row = db.execute("SELECT * FROM operator_sessions WHERE session_id=? AND operator_id=?", (session_id, operator_id)).fetchone()
        now = float(self.clock())
        if row is None:
            raise SQLiteAdminStateError("operator_session_inactive_or_expired")
        active = int(row["active"]) == 1
        expires_at = float(row["expires_at"])
        if not active:
            raise SQLiteAdminStateError("operator_session_inactive_or_expired")
        if expires_at <= now:
            raise SQLiteAdminStateError("operator_session_inactive_or_expired")
        scopes = set(json.loads(str(row["scopes"])))
        if required_scope and required_scope not in scopes:
            raise SQLiteAdminStateError("operator_scope_denied")
        return row

    def _receipt(self, *, action_id: str, operation: str, actor_id: str, target_id: str, previous_state: str, new_state: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        unsigned = {"schema_version": RECEIPT_SCHEMA, "action_id": action_id, "operation": operation, "actor_id": actor_id, "target_id": target_id, "previous_state": previous_state, "new_state": new_state, "payload_digest": _digest(payload)}
        return {**unsigned, "signature": _sign(self.signing_key, unsigned)}

    def _audit(self, db: sqlite3.Connection, receipt: Mapping[str, Any]) -> None:
        db.execute("INSERT INTO mutation_audit(action_id, operation, actor_id, target_id, previous_state, new_state, payload_digest, signature, created_at) VALUES(?,?,?,?,?,?,?,?,?)", (receipt["action_id"], receipt["operation"], receipt["actor_id"], receipt["target_id"], receipt["previous_state"], receipt["new_state"], receipt["payload_digest"], receipt["signature"], float(self.clock())))

    def verify_receipt(self, receipt: Mapping[str, Any]) -> bool:
        unsigned = {key: receipt.get(key, "") for key in ("schema_version", "action_id", "operation", "actor_id", "target_id", "previous_state", "new_state", "payload_digest")}
        return receipt.get("schema_version") == RECEIPT_SCHEMA and hmac.compare_digest(str(receipt.get("signature", "")), _sign(self.signing_key, unsigned))

    def bootstrap_session(self, operator_id: str, session_id: str, *, ttl_seconds: float = 900.0, scopes: Sequence[str] = ()) -> Mapping[str, Any]:
        """Create the first session explicitly; later sessions require an active actor."""
        if not operator_id or not session_id or ttl_seconds <= 0 or ttl_seconds > 86400:
            raise SQLiteAdminStateError("invalid_operator_session")
        with self._connect() as db:
            if db.execute("SELECT 1 FROM operator_sessions LIMIT 1").fetchone() is not None:
                raise SQLiteAdminStateError("bootstrap_only_empty_store")
            now = float(self.clock())
            db.execute("BEGIN IMMEDIATE")
            db.execute("INSERT INTO operator_sessions VALUES(?,?,?,?,?,?)", (session_id, operator_id, self._scopes(scopes), now + ttl_seconds, 1, now))
            return {"operator_id": operator_id, "session_id": session_id, "active": True, "scopes": sorted({str(item) for item in scopes}), "expires_at": now + ttl_seconds}

    def open_session(self, *, actor_id: str, actor_session_id: str, target_operator_id: str, target_session_id: str, ttl_seconds: float = 900.0, scopes: Sequence[str] = (), action_id: str) -> Mapping[str, Any]:
        if ttl_seconds <= 0 or ttl_seconds > 86400 or not action_id:
            raise SQLiteAdminStateError("invalid_operator_session")
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            self._active_session(db, actor_id, actor_session_id, "admin:session")
            current = db.execute("SELECT * FROM operator_sessions WHERE session_id=?", (target_session_id,)).fetchone()
            if current is not None and current["active"] and float(current["expires_at"]) > float(self.clock()):
                raise SQLiteAdminStateError("operator_session_conflict")
            now = float(self.clock())
            payload = {"operator_id": target_operator_id, "session_id": target_session_id, "scopes": sorted({str(item) for item in scopes}), "expires_at": now + ttl_seconds}
            receipt = self._receipt(action_id=action_id, operation="operator_session_open", actor_id=actor_id, target_id=target_session_id, previous_state="inactive", new_state="active", payload=payload)
            db.execute("INSERT OR REPLACE INTO operator_sessions VALUES(?,?,?,?,?,?)", (target_session_id, target_operator_id, self._scopes(scopes), now + ttl_seconds, 1, now))
            self._audit(db, receipt)
            return {"state": payload, "audit_receipt": receipt}

    def close_session(self, *, actor_id: str, actor_session_id: str, target_session_id: str, action_id: str) -> Mapping[str, Any]:
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            self._active_session(db, actor_id, actor_session_id, "admin:session")
            current = db.execute("SELECT * FROM operator_sessions WHERE session_id=?", (target_session_id,)).fetchone()
            if current is None or not current["active"] or float(current["expires_at"]) <= float(self.clock()):
                raise SQLiteAdminStateError("operator_session_conflict")
            receipt = self._receipt(action_id=action_id, operation="operator_session_close", actor_id=actor_id, target_id=target_session_id, previous_state="active", new_state="inactive", payload={"session_id": target_session_id})
            db.execute("UPDATE operator_sessions SET active=0, updated_at=? WHERE session_id=?", (float(self.clock()), target_session_id))
            self._audit(db, receipt)
            return {"session_id": target_session_id, "active": False, "audit_receipt": receipt}

    def grant_reviewer(self, *, admin_id: str, admin_session_id: str, target_operator_id: str, target_session_id: str, scopes: Sequence[str], action_id: str) -> Mapping[str, Any]:
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if admin_id not in self.admin_ids:
                raise SQLiteAdminStateError("administrative_policy_denied")
            self._active_session(db, admin_id, admin_session_id, "admin:reviewers")
            current = db.execute("SELECT * FROM reviewer_grants WHERE operator_id=? AND session_id=?", (target_operator_id, target_session_id)).fetchone()
            normalized = sorted({str(item) for item in scopes})
            if current is not None and current["active"] and json.loads(current["scopes"]) == normalized:
                raise SQLiteAdminStateError("administrative_policy_conflict")
            receipt = self._receipt(action_id=action_id, operation="grant_reviewer", actor_id=admin_id, target_id=target_operator_id + ":" + target_session_id, previous_state="active" if current and current["active"] else "inactive", new_state="active", payload={"operator_id": target_operator_id, "session_id": target_session_id, "scopes": normalized})
            db.execute("INSERT OR REPLACE INTO reviewer_grants VALUES(?,?,?,?,?)", (target_operator_id, target_session_id, self._scopes(normalized), 1, float(self.clock())))
            self._audit(db, receipt)
            return {"operator_id": target_operator_id, "session_id": target_session_id, "scopes": normalized, "active": True, "audit_receipt": receipt}

    def revoke_reviewer(self, *, admin_id: str, admin_session_id: str, target_operator_id: str, target_session_id: str, action_id: str) -> Mapping[str, Any]:
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if admin_id not in self.admin_ids:
                raise SQLiteAdminStateError("administrative_policy_denied")
            self._active_session(db, admin_id, admin_session_id, "admin:reviewers")
            current = db.execute("SELECT * FROM reviewer_grants WHERE operator_id=? AND session_id=?", (target_operator_id, target_session_id)).fetchone()
            if current is None or not current["active"]:
                raise SQLiteAdminStateError("administrative_policy_conflict")
            receipt = self._receipt(action_id=action_id, operation="revoke_reviewer", actor_id=admin_id, target_id=target_operator_id + ":" + target_session_id, previous_state="active", new_state="inactive", payload={"operator_id": target_operator_id, "session_id": target_session_id})
            db.execute("UPDATE reviewer_grants SET active=0, updated_at=? WHERE operator_id=? AND session_id=?", (float(self.clock()), target_operator_id, target_session_id))
            self._audit(db, receipt)
            return {"operator_id": target_operator_id, "session_id": target_session_id, "active": False, "audit_receipt": receipt}

    def audit(self, action_id: str) -> Optional[Mapping[str, Any]]:
        with self._connect() as db:
            row = db.execute("SELECT * FROM mutation_audit WHERE action_id=?", (action_id,)).fetchone()
            return dict(row) if row else None

    def session_snapshot(self, session_id: str) -> Optional[Mapping[str, Any]]:
        with self._connect() as db:
            row = db.execute("SELECT * FROM operator_sessions WHERE session_id=?", (session_id,)).fetchone()
            if row is None:
                return None
            return {"session_id": row["session_id"], "operator_id": row["operator_id"], "scopes": json.loads(row["scopes"]), "expires_at": float(row["expires_at"]), "active": bool(row["active"])}

    def reviewer_snapshot(self, operator_id: str, session_id: str) -> Optional[Mapping[str, Any]]:
        with self._connect() as db:
            row = db.execute("SELECT * FROM reviewer_grants WHERE operator_id=? AND session_id=?", (operator_id, session_id)).fetchone()
            if row is None:
                return None
            return {"operator_id": row["operator_id"], "session_id": row["session_id"], "scopes": json.loads(row["scopes"]), "active": bool(row["active"])}


__all__ = ["SCHEMA_VERSION", "RECEIPT_SCHEMA", "SQLiteAdminStateError", "SQLiteAdministrativeBackend"]
