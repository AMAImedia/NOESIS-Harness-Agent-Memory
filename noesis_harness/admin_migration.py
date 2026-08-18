"""Versioned adoption adapter for legacy append-only and SQLite admin stores."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Mapping, Optional

from .admin_state_sqlite import SQLiteAdministrativeBackend
from .event_store import EventStore
from .promotion_integration import OperatorAuthContext, ReviewerAuthorizationStore, OperatorSessionRegistry

MIGRATION_SCHEMA = "noesis.admin-migration.v1"
MODES = frozenset({"legacy", "dual_read", "sqlite"})


class AdministrativeMigrationError(ValueError):
    """Raised when migration state or dual-read verification fails closed."""


@dataclass(frozen=True)
class MigrationCheck:
    mode: str
    session_match: bool
    reviewer_match: bool
    status: str
    reason: str = ""

    def to_mapping(self) -> dict[str, Any]:
        return {"schema_version": MIGRATION_SCHEMA, "mode": self.mode, "session_match": self.session_match, "reviewer_match": self.reviewer_match, "status": self.status, "reason": self.reason}


class AdministrativeMigrationAdapter:
    """Route administrative reads/writes without silently replacing legacy state."""

    def __init__(self, state_path: str, *, legacy_reviewer: ReviewerAuthorizationStore, legacy_sessions: OperatorSessionRegistry, sqlite_backend: SQLiteAdministrativeBackend, clock=time.time) -> None:
        self.events = EventStore(state_path)
        self.legacy_reviewer = legacy_reviewer
        self.legacy_sessions = legacy_sessions
        self.sqlite = sqlite_backend
        self.clock = clock

    def _state(self) -> Mapping[str, Any]:
        current: dict[str, Any] = {"mode": "legacy", "version": MIGRATION_SCHEMA}
        for event in self.events.iter_events():
            if event.get("type") in {"migration_started", "migration_mode_changed", "migration_rolled_back"}:
                current.update(event.get("payload") or {})
        return current

    @property
    def mode(self) -> str:
        mode = str(self._state().get("mode", "legacy"))
        if mode not in MODES:
            raise AdministrativeMigrationError("unsupported_migration_mode")
        return mode

    def start(self, mode: str, *, operator_id: str, reason: str) -> Mapping[str, Any]:
        if mode not in MODES or not operator_id or not reason:
            raise AdministrativeMigrationError("invalid_migration_start")
        if mode == "sqlite" and self.mode == "legacy":
            raise AdministrativeMigrationError("sqlite_mode_requires_dual_read")
        payload = {"version": MIGRATION_SCHEMA, "mode": mode, "operator_id": operator_id, "reason": str(reason)[:256], "created_at": float(self.clock())}
        self.events.append("migration_started" if self.mode == "legacy" else "migration_mode_changed", payload, event_id="migration-mode:" + mode + ":" + str(self.events.count()))
        return payload

    def _legacy_session(self, session_id: str) -> Optional[Mapping[str, Any]]:
        try:
            record = self.legacy_sessions._records().get(session_id)
        except Exception:
            return None
        if record is None:
            return None
        return {"session_id": session_id, "operator_id": record.get("operator_id"), "scopes": sorted(str(item) for item in record.get("scopes", ())), "expires_at": float(record.get("expires_at", 0.0)), "active": bool(record.get("active", False))}

    def _legacy_reviewer(self, operator_id: str, session_id: str) -> Optional[Mapping[str, Any]]:
        record = self.legacy_reviewer._records().get((operator_id, session_id))
        if record is None:
            return None
        return {"operator_id": operator_id, "session_id": session_id, "scopes": sorted(str(item) for item in record.get("scopes", ())), "active": bool(record.get("active", False))}

    def verify_dual_read(self, *, session_id: str, reviewer_operator_id: str, reviewer_session_id: str) -> MigrationCheck:
        if self.mode not in {"dual_read", "sqlite"}:
            return MigrationCheck(self.mode, True, True, "not_applicable")
        legacy_session = self._legacy_session(session_id)
        sqlite_session = self.sqlite.session_snapshot(session_id)
        session_match = bool(legacy_session and sqlite_session and legacy_session["session_id"] == sqlite_session["session_id"] and legacy_session["operator_id"] == sqlite_session["operator_id"] and legacy_session["scopes"] == sqlite_session["scopes"] and legacy_session["active"] == sqlite_session["active"])
        legacy_reviewer = self._legacy_reviewer(reviewer_operator_id, reviewer_session_id)
        sqlite_reviewer = self.sqlite.reviewer_snapshot(reviewer_operator_id, reviewer_session_id)
        reviewer_match = legacy_reviewer == sqlite_reviewer
        status = "passed" if session_match and reviewer_match else "blocked"
        return MigrationCheck(self.mode, session_match, reviewer_match, status, "state_mismatch" if status == "blocked" else "")

    def require_dual_read(self, **kwargs: str) -> MigrationCheck:
        check = self.verify_dual_read(**kwargs)
        if check.status == "blocked":
            raise AdministrativeMigrationError("dual_read_state_mismatch")
        return check

    def rollback(self, *, operator_id: str, reason: str) -> Mapping[str, Any]:
        if self.mode == "legacy":
            raise AdministrativeMigrationError("migration_not_active")
        payload = {"version": MIGRATION_SCHEMA, "mode": "legacy", "operator_id": operator_id, "reason": str(reason)[:256], "rolled_back_at": float(self.clock())}
        self.events.append("migration_rolled_back", payload, event_id="migration-rollback:" + str(self.events.count()))
        return payload

    def plan(self, *, session_id: str, reviewer_operator_id: str, reviewer_session_id: str) -> Mapping[str, Any]:
        check = self.verify_dual_read(session_id=session_id, reviewer_operator_id=reviewer_operator_id, reviewer_session_id=reviewer_session_id)
        return {"schema_version": MIGRATION_SCHEMA, "mode": self.mode, "action": "route_after_verification", "check": check.to_mapping(), "automatic_cutover": False}


__all__ = ["MIGRATION_SCHEMA", "AdministrativeMigrationError", "MigrationCheck", "AdministrativeMigrationAdapter"]
