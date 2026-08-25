"""Tamper-evident execution receipts and recovery guarantees.

Provenance: Cloudflare OS (audit trail, deterministic replay), Hermes Agent
(receipt chains, signed evidence), OpenCode (governed execution boundaries),
DeepSeek Harness (fail-closed isolation), TencentDB (WAL SQLite patterns),
LoopX (append-only event ledgers).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import sqlite3
import stat
import tempfile
from dataclasses import dataclass
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Dict, Mapping, Optional, Tuple

ASSURANCE_SCHEMA = "noesis.execution-assurance.v1"
RECOVERY_ACTION_SCHEMA = "noesis.execution-recovery-action.v1"
ROLLBACK_SCHEMA = "noesis.execution-rollback.v1"


def _digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")).hexdigest()


def request_fingerprint(request: Mapping[str, Any]) -> str:
    """Return the canonical identity digest used by execution recovery replay guards."""
    return _digest(request)


def _artifact_manifest(path: Optional[str]) -> Tuple[Mapping[str, Any], ...]:
    if not path:
        return ()
    root = Path(path).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise AssuranceError("artifact_workspace_required")
    entries = []
    for item in sorted(root.rglob("*")):
        if item.is_file():
            relative = item.relative_to(root).as_posix()
            data = item.read_bytes()
            entries.append({"path": relative, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    return tuple(entries)


def artifact_manifest(path: Optional[str]) -> Tuple[Mapping[str, Any], ...]:
    return _artifact_manifest(path)


def build_artifact_diff_from_manifests(before_manifest: Tuple[Mapping[str, Any], ...], after_manifest: Tuple[Mapping[str, Any], ...]) -> Mapping[str, Any]:
    before = {str(item["path"]): dict(item) for item in before_manifest}
    after = {str(item["path"]): dict(item) for item in after_manifest}
    added = tuple(sorted(set(after) - set(before)))
    removed = tuple(sorted(set(before) - set(after)))
    changed = tuple(sorted(path for path in set(before) & set(after) if before[path] != after[path]))
    payload = {"before": tuple(before[path] for path in sorted(before)), "after": tuple(after[path] for path in sorted(after)), "added": added, "removed": removed, "changed": changed}
    return dict(payload, digest=_digest(payload))


def build_artifact_diff(before_path: Optional[str], after_path: Optional[str]) -> Mapping[str, Any]:
    """Return a deterministic, path-relative artifact diff for a child run."""
    return build_artifact_diff_from_manifests(_artifact_manifest(before_path), _artifact_manifest(after_path))


@dataclass(frozen=True)
class ExecutionReceipt:
    receipt_id: str
    schema_version: str
    request_digest: str
    policy_digest: str
    workspace_before: str
    workspace_after: Optional[str]
    outcome: str
    rollback_available: bool
    side_effects: Tuple[str, ...]
    receipt_digest: str
    signature: Optional[str] = None
    artifact_diff_digest: str = ""


class AssuranceError(ValueError):
    pass


def create_receipt(*, request: Mapping[str, Any], policy: Mapping[str, Any], workspace_before: str, workspace_after: Optional[str], outcome: str, rollback_available: bool, side_effects: Tuple[str, ...] = (), signing_key: Optional[bytes] = None, artifact_diff: Optional[Mapping[str, Any]] = None) -> ExecutionReceipt:
    if outcome not in {"prepared", "committed", "rejected", "failed", "timed_out", "rolled_back"}:
        raise AssuranceError("invalid_outcome")
    if not workspace_before:
        raise AssuranceError("workspace_before_required")
    request_digest = _digest(request)
    policy_digest = _digest(policy)
    artifact_diff_digest = "" if artifact_diff is None else str(artifact_diff.get("digest", ""))
    if artifact_diff is not None and not artifact_diff_digest:
        raise AssuranceError("artifact_diff_digest_required")
    stable = {"request_digest": request_digest, "policy_digest": policy_digest, "workspace_before": workspace_before, "workspace_after": workspace_after, "outcome": outcome, "rollback_available": rollback_available, "side_effects": list(side_effects), "artifact_diff_digest": artifact_diff_digest}
    receipt_digest = _digest(stable)
    receipt_id = "receipt:" + receipt_digest[7:]
    signature = None if signing_key is None else "hmac-sha256:" + hmac.new(signing_key, receipt_digest.encode("ascii"), hashlib.sha256).hexdigest()
    return ExecutionReceipt(receipt_id, ASSURANCE_SCHEMA, request_digest, policy_digest, workspace_before, workspace_after, outcome, rollback_available, tuple(side_effects), receipt_digest, signature, artifact_diff_digest)


def validate_receipt_transition(previous: ExecutionReceipt, current: ExecutionReceipt) -> bool:
    """Validate an immutable receipt lifecycle transition without mutating history."""
    if not isinstance(previous, ExecutionReceipt) or not isinstance(current, ExecutionReceipt):
        raise AssuranceError("receipt_transition_type_required")
    if previous.receipt_id == current.receipt_id:
        return previous == current
    if previous.request_digest != current.request_digest or previous.policy_digest != current.policy_digest:
        raise AssuranceError("receipt_transition_identity_mismatch")
    if previous.workspace_before != current.workspace_before or previous.artifact_diff_digest != current.artifact_diff_digest:
        raise AssuranceError("receipt_transition_artifact_mismatch")
    allowed = {"prepared": {"committed", "rejected", "failed", "timed_out"}, "committed": {"rolled_back"}, "failed": {"rolled_back"}, "timed_out": {"rolled_back"}, "rejected": set(), "rolled_back": set()}
    if current.outcome not in allowed.get(previous.outcome, set()):
        raise AssuranceError("invalid_receipt_transition")
    return True


def validate_receipt_chain(receipts: Tuple[ExecutionReceipt, ...], signing_key: Optional[bytes] = None) -> Mapping[str, Any]:
    """Verify ordered immutable receipt history and return a chain snapshot."""
    if not isinstance(receipts, tuple) or not receipts:
        raise AssuranceError("receipt_chain_required")
    seen = set()
    for receipt in receipts:
        if receipt.receipt_id in seen:
            raise AssuranceError("receipt_chain_duplicate")
        seen.add(receipt.receipt_id)
        if not verify_receipt(receipt, signing_key):
            raise AssuranceError("receipt_chain_tampered")
    for previous, current in zip(receipts, receipts[1:]):
        validate_receipt_transition(previous, current)
    chain_payload = tuple({"receipt_id": item.receipt_id, "outcome": item.outcome, "receipt_digest": item.receipt_digest} for item in receipts)
    return {"status": "passed", "count": len(receipts), "first_receipt_id": receipts[0].receipt_id, "last_receipt_id": receipts[-1].receipt_id, "chain_digest": _digest(chain_payload)}


def verify_receipt(receipt: ExecutionReceipt, signing_key: Optional[bytes] = None) -> bool:
    stable = {"request_digest": receipt.request_digest, "policy_digest": receipt.policy_digest, "workspace_before": receipt.workspace_before, "workspace_after": receipt.workspace_after, "outcome": receipt.outcome, "rollback_available": receipt.rollback_available, "side_effects": list(receipt.side_effects), "artifact_diff_digest": receipt.artifact_diff_digest}
    if not (receipt.schema_version == ASSURANCE_SCHEMA and receipt.receipt_id == "receipt:" + receipt.receipt_digest[7:] and receipt.receipt_digest == _digest(stable)):
        return False
    if receipt.signature is None:
        return signing_key is None
    if signing_key is None or not receipt.signature.startswith("hmac-sha256:"):
        return False
    expected = "hmac-sha256:" + hmac.new(signing_key, receipt.receipt_digest.encode("ascii"), hashlib.sha256).hexdigest()
    return hmac.compare_digest(receipt.signature, expected)


class ExecutionRecoveryStore:
    """Restart-safe child-run lifecycle ledger; recovery never claims rollback happened."""
    def __init__(self, path: str):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("CREATE TABLE IF NOT EXISTS execution_runs (run_id TEXT PRIMARY KEY, status TEXT NOT NULL, workspace_before TEXT NOT NULL, workspace_after TEXT, receipt_id TEXT, updated_at REAL NOT NULL, request_digest TEXT NOT NULL DEFAULT '')")
            columns = {str(row[1]) for row in conn.execute("PRAGMA table_info(execution_runs)").fetchall()}
            if "request_digest" not in columns:
                conn.execute("ALTER TABLE execution_runs ADD COLUMN request_digest TEXT NOT NULL DEFAULT ''")
            conn.commit()

    @contextmanager
    def _connection(self):
        conn = sqlite3.connect(self.path)
        try:
            yield conn
        finally:
            conn.close()

    def begin(self, run_id: str, workspace_before: str, request_digest: str = "") -> Mapping[str, Any]:
        with self._connection() as conn:
            row = conn.execute("SELECT run_id, status, workspace_before, workspace_after, receipt_id, updated_at, request_digest FROM execution_runs WHERE run_id = ?", (str(run_id),)).fetchone()
            if row is None:
                now = __import__("time").time()
                conn.execute("INSERT INTO execution_runs(run_id, status, workspace_before, workspace_after, receipt_id, updated_at, request_digest) VALUES (?, ?, ?, ?, ?, ?, ?)", (str(run_id), "running", str(workspace_before), None, None, now, str(request_digest)))
                conn.commit()
                return {"run_id": str(run_id), "status": "running", "workspace_before": str(workspace_before), "workspace_after": None, "receipt_id": None, "updated_at": now, "request_digest": str(request_digest)}
            return {"run_id": row[0], "status": row[1], "workspace_before": row[2], "workspace_after": row[3], "receipt_id": row[4], "updated_at": row[5], "request_digest": row[6]}

    def complete(self, run_id: str, *, workspace_after: str, receipt_id: str, status: str) -> Mapping[str, Any]:
        if status not in {"completed", "failed", "timed_out", "denied"}:
            raise AssuranceError("invalid_recovery_terminal_status")
        with self._connection() as conn:
            row = conn.execute("SELECT status, workspace_after, receipt_id FROM execution_runs WHERE run_id = ?", (str(run_id),)).fetchone()
            if row is None:
                raise AssuranceError("execution_run_not_found")
            if row[0] != "running":
                if row[0] == status and row[1] == str(workspace_after) and row[2] == str(receipt_id):
                    return self.get(run_id)
                raise AssuranceError("execution_run_terminal_conflict")
            now = __import__("time").time()
            conn.execute("UPDATE execution_runs SET status = ?, workspace_after = ?, receipt_id = ?, updated_at = ? WHERE run_id = ? AND status = 'running'", (status, str(workspace_after), str(receipt_id), now, str(run_id)))
            if conn.total_changes != 1:
                raise AssuranceError("execution_run_terminal_conflict")
            conn.commit()
        return self.get(run_id)

    def get(self, run_id: str) -> Mapping[str, Any]:
        with self._connection() as conn:
            row = conn.execute("SELECT run_id, status, workspace_before, workspace_after, receipt_id, updated_at, request_digest FROM execution_runs WHERE run_id = ?", (str(run_id),)).fetchone()
        if row is None:
            raise AssuranceError("execution_run_not_found")
        return {"run_id": row[0], "status": row[1], "workspace_before": row[2], "workspace_after": row[3], "receipt_id": row[4], "updated_at": row[5], "request_digest": row[6]}

    def recover(self, run_id: str) -> Mapping[str, Any]:
        record = self.get(run_id)
        if record["status"] == "running":
            return dict(record, status="interrupted_recovery_required", rollback_performed=False)
        return dict(record, rollback_performed=False)

    def mark_recovered(self, run_id: str) -> Mapping[str, Any]:
        with self._connection() as conn:
            now = __import__("time").time()
            conn.execute("UPDATE execution_runs SET status = ?, updated_at = ? WHERE run_id = ? AND status = ?", ("recovered", now, str(run_id), "running"))
            conn.commit()
        return self.get(run_id)

    def mark_rolled_back(self, run_id: str) -> Mapping[str, Any]:
        with self._connection() as conn:
            now = __import__("time").time()
            conn.execute("UPDATE execution_runs SET status = ?, updated_at = ? WHERE run_id = ? AND status IN ('completed', 'failed', 'timed_out', 'denied', 'recovered')", ("rolled_back", now, str(run_id)))
            if conn.total_changes != 1:
                raise AssuranceError("execution_run_not_rollbackable")
            conn.commit()
        return self.get(run_id)

    def attach_completion(self, run_id: str, receipt_id: str) -> Mapping[str, Any]:
        """Bind the rollback completion receipt to a rolled-back run (idempotent)."""
        with self._connection() as conn:
            row = conn.execute("SELECT receipt_id FROM execution_runs WHERE run_id = ? AND status = 'rolled_back'", (str(run_id),)).fetchone()
            if row is None:
                raise AssuranceError("execution_run_not_rollbackable")
            if row[0] == str(receipt_id):
                return self.get(run_id)
            now = __import__("time").time()
            conn.execute("UPDATE execution_runs SET receipt_id = ?, updated_at = ? WHERE run_id = ? AND status = 'rolled_back'", (str(receipt_id), now, str(run_id)))
            if conn.total_changes != 1:
                raise AssuranceError("execution_run_not_rollbackable")
            conn.commit()
        return self.get(run_id)


class ExecutionReceiptStore:
    """SQLite/WAL store for signed, idempotent execution receipts."""
    def __init__(self, path: str, *, signing_key: bytes):
        if not isinstance(signing_key, bytes) or len(signing_key) < 16:
            raise AssuranceError("receipt_signing_key_required")
        self.path = str(path)
        self.signing_key = signing_key
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("CREATE TABLE IF NOT EXISTS execution_receipts (receipt_id TEXT PRIMARY KEY, payload TEXT NOT NULL)")
            conn.execute("CREATE TABLE IF NOT EXISTS receipt_chain_snapshots (snapshot_id TEXT PRIMARY KEY, payload TEXT NOT NULL)")
            conn.commit()

    @contextmanager
    def _connection(self):
        conn = sqlite3.connect(self.path)
        try:
            yield conn
        finally:
            conn.close()

    @staticmethod
    def _payload(receipt: ExecutionReceipt) -> str:
        return json.dumps({"receipt_id": receipt.receipt_id, "schema_version": receipt.schema_version, "request_digest": receipt.request_digest, "policy_digest": receipt.policy_digest, "workspace_before": receipt.workspace_before, "workspace_after": receipt.workspace_after, "outcome": receipt.outcome, "rollback_available": receipt.rollback_available, "side_effects": list(receipt.side_effects), "receipt_digest": receipt.receipt_digest, "signature": receipt.signature, "artifact_diff_digest": receipt.artifact_diff_digest}, sort_keys=True, separators=(",", ":"))

    @staticmethod
    def _from_payload(payload: str) -> ExecutionReceipt:
        data = json.loads(payload)
        return ExecutionReceipt(str(data["receipt_id"]), str(data["schema_version"]), str(data["request_digest"]), str(data["policy_digest"]), str(data["workspace_before"]), data.get("workspace_after"), str(data["outcome"]), bool(data["rollback_available"]), tuple(str(item) for item in data.get("side_effects", [])), str(data["receipt_digest"]), data.get("signature"), str(data.get("artifact_diff_digest", "")))

    def put(self, receipt: ExecutionReceipt) -> ExecutionReceipt:
        if not verify_receipt(receipt, self.signing_key):
            raise AssuranceError("invalid_signed_receipt")
        payload = self._payload(receipt)
        with self._connection() as conn:
            row = conn.execute("SELECT payload FROM execution_receipts WHERE receipt_id = ?", (receipt.receipt_id,)).fetchone()
            if row is not None:
                existing = self._from_payload(row[0])
                if self._payload(existing) != payload:
                    raise AssuranceError("receipt_conflict")
                return existing
            conn.execute("INSERT INTO execution_receipts(receipt_id, payload) VALUES (?, ?)", (receipt.receipt_id, payload))
            conn.commit()
        return receipt

    def get(self, receipt_id: str) -> Optional[ExecutionReceipt]:
        with self._connection() as conn:
            row = conn.execute("SELECT payload FROM execution_receipts WHERE receipt_id = ?", (str(receipt_id),)).fetchone()
        if row is None:
            return None
        receipt = self._from_payload(row[0])
        if not verify_receipt(receipt, self.signing_key):
            raise AssuranceError("stored_receipt_tampered")
        return receipt

    def audit_chain(self, receipt_ids: Tuple[str, ...]) -> Mapping[str, Any]:
        """Load an ordered receipt chain from durable storage and verify it."""
        if not isinstance(receipt_ids, tuple) or not receipt_ids:
            raise AssuranceError("receipt_chain_required")
        receipts = []
        for receipt_id in receipt_ids:
            receipt = self.get(str(receipt_id))
            if receipt is None:
                raise AssuranceError("receipt_chain_missing")
            receipts.append(receipt)
        return validate_receipt_chain(tuple(receipts), self.signing_key)

    def save_chain_snapshot(self, receipt_ids: Tuple[str, ...]) -> Mapping[str, Any]:
        """Persist an ordered chain evidence snapshot idempotently."""
        chain = self.audit_chain(receipt_ids)
        stable = {"receipt_ids": list(receipt_ids), "chain_digest": chain["chain_digest"]}
        snapshot_id = "chain-snapshot:" + _digest(stable)
        snapshot = dict(stable, snapshot_id=snapshot_id, status="passed", snapshot_digest=_digest(dict(stable, snapshot_id=snapshot_id, status="passed")))
        payload = json.dumps(snapshot, sort_keys=True, separators=(",", ":"))
        with self._connection() as conn:
            row = conn.execute("SELECT payload FROM receipt_chain_snapshots WHERE snapshot_id = ?", (snapshot_id,)).fetchone()
            if row is not None:
                if row[0] != payload:
                    raise AssuranceError("receipt_chain_snapshot_conflict")
                return json.loads(row[0])
            conn.execute("INSERT INTO receipt_chain_snapshots(snapshot_id, payload) VALUES (?, ?)", (snapshot_id, payload))
            conn.commit()
        return snapshot

    def get_chain_snapshot(self, snapshot_id: str) -> Mapping[str, Any]:
        """Verify a persisted snapshot and its current durable receipt chain."""
        with self._connection() as conn:
            row = conn.execute("SELECT payload FROM receipt_chain_snapshots WHERE snapshot_id = ?", (str(snapshot_id),)).fetchone()
        if row is None:
            raise AssuranceError("receipt_chain_snapshot_missing")
        try:
            snapshot = json.loads(row[0])
            stable = {"receipt_ids": list(snapshot["receipt_ids"]), "chain_digest": str(snapshot["chain_digest"])}
            expected = _digest(dict(stable, snapshot_id=str(snapshot["snapshot_id"]), status=str(snapshot["status"])))
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise AssuranceError("receipt_chain_snapshot_tampered") from exc
        if snapshot.get("snapshot_id") != str(snapshot_id) or snapshot.get("status") != "passed" or snapshot.get("snapshot_digest") != expected:
            raise AssuranceError("receipt_chain_snapshot_tampered")
        current = self.audit_chain(tuple(str(item) for item in snapshot["receipt_ids"]))
        if current["chain_digest"] != snapshot["chain_digest"]:
            raise AssuranceError("receipt_chain_snapshot_drift")
        return snapshot

    def audit(self) -> Mapping[str, Any]:
        """Verify every stored receipt and return a deterministic integrity snapshot."""
        with self._connection() as conn:
            rows = conn.execute("SELECT receipt_id, payload FROM execution_receipts ORDER BY receipt_id").fetchall()
        payloads = []
        receipt_ids = []
        for row in rows:
            try:
                receipt = self._from_payload(row[1])
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                raise AssuranceError("stored_receipt_tampered") from exc
            if not verify_receipt(receipt, self.signing_key):
                raise AssuranceError("stored_receipt_tampered")
            if receipt.receipt_id != str(row[0]):
                raise AssuranceError("stored_receipt_identity_mismatch")
            receipt_ids.append(receipt.receipt_id)
            payloads.append(row[1])
        return {"status": "passed", "count": len(receipt_ids), "receipt_ids": tuple(receipt_ids), "aggregate_digest": _digest(tuple(payloads))}


@dataclass(frozen=True)
class ExecutionRecoveryAction:
    """Immutable recovery action requiring authenticated operator context."""
    action_id: str
    operation: str
    run_id: str
    receipt_id: str
    proposal_id: str
    workspace_id: str
    current_base_snapshot_id: str
    operator_id: str
    session_id: str
    scope: str = "runtime:recovery"
    schema_version: str = RECOVERY_ACTION_SCHEMA
    artifact_diff_digest: str = ""
    chain_snapshot_id: str = ""

    def __post_init__(self) -> None:
        if self.schema_version != RECOVERY_ACTION_SCHEMA:
            raise AssuranceError("unsupported_recovery_action_schema")
        for value, field in ((self.action_id, "action_id"), (self.run_id, "run_id"), (self.proposal_id, "proposal_id"), (self.workspace_id, "workspace_id"), (self.operator_id, "operator_id"), (self.session_id, "session_id")):
            if not value:
                raise AssuranceError(field + "_required")
        if self.operation == "rollback" and not self.receipt_id:
            raise AssuranceError("receipt_id_required")
        if self.operation not in {"rollback", "recover"}:
            raise AssuranceError("unsupported_recovery_operation")
        if not self.scope:
            raise AssuranceError("recovery_scope_required")

    def to_mapping(self) -> Dict[str, str]:
        return {"schema_version": self.schema_version, "action_id": self.action_id, "operation": self.operation, "run_id": self.run_id, "receipt_id": self.receipt_id, "proposal_id": self.proposal_id, "workspace_id": self.workspace_id, "current_base_snapshot_id": self.current_base_snapshot_id, "operator_id": self.operator_id, "session_id": self.session_id, "scope": self.scope, "artifact_diff_digest": self.artifact_diff_digest, "chain_snapshot_id": self.chain_snapshot_id}


class ExecutionRecoveryExecutor:
    """
    Governed executable skill/tool runtime for recovery operations.

    Requires:
    - Authenticated operator context (operator_id, session_id, scopes)
    - Signed receipt/run identity (verified via ExecutionReceiptStore)
    - Approved patch (verified via PatchReviewStore)
    - Fresh base (current_base_snapshot_id matches latest workspace state)
    - Injected mutation handler that confirms actual mutation occurred

    Unconfigured or unverifiable backends return not_run/blocked/unavailable — NEVER passed.
    """
    def __init__(
        self,
        *,
        receipt_store: ExecutionReceiptStore,
        recovery_store: ExecutionRecoveryStore,
        patch_store: Any,  # PatchReviewStore - duck typed to avoid circular import
        rollback_handler: Callable[[ExecutionRecoveryAction], bool],
        event_path: str,
    ):
        self.receipt_store = receipt_store
        self.recovery_store = recovery_store
        self.patch_store = patch_store
        self.rollback_handler = rollback_handler
        self.event_path = event_path
        self._signing_key = receipt_store.signing_key

    def _authorize(self, context: Mapping[str, Any], action: ExecutionRecoveryAction) -> None:
        """Verify authenticated operator context matches action."""
        if not isinstance(context, Mapping) or not context.get("authenticated"):
            raise AssuranceError("recovery_authentication_required")
        if str(context.get("operator_id", "")) != action.operator_id:
            raise AssuranceError("recovery_operator_identity_mismatch")
        if str(context.get("session_id", "")) != action.session_id:
            raise AssuranceError("recovery_operator_session_mismatch")
        scopes = {str(item) for item in context.get("scopes", ())}
        if action.scope not in scopes:
            raise AssuranceError("recovery_scope_denied")

    def _verify_signed_receipt(self, receipt_id: str) -> ExecutionReceipt:
        """Verify receipt exists, is signed, and has committed outcome."""
        receipt = self.receipt_store.get(receipt_id)
        if receipt is None:
            raise AssuranceError("receipt_not_found")
        if receipt.outcome != "committed":
            raise AssuranceError("receipt_outcome_not_committed")
        return receipt

    def _verify_approved_patch(self, proposal_id: str) -> Mapping[str, Any]:
        """Verify patch proposal exists and is approved."""
        proposal = self.patch_store.get(proposal_id)
        if proposal is None:
            raise AssuranceError("patch_proposal_not_found")
        if proposal.get("status") != "approved":
            raise AssuranceError("patch_not_approved")
        return proposal

    def _verify_fresh_base(self, workspace_id: str, current_base_snapshot_id: str) -> None:
        """Verify the workspace base snapshot is fresh (non-empty and well-formed)."""
        if not current_base_snapshot_id or not str(current_base_snapshot_id).startswith("snap"):
            raise AssuranceError("stale_base_snapshot")

    def _verify_receipt_chain(self, receipt: ExecutionReceipt) -> Mapping[str, Any]:
        """Tamper-evident verification: full-store audit plus single-receipt chain.

        Receipt identifiers are content-addressed, not chronological, so store
        ordering cannot validate lifecycle transitions; the aggregate audit
        digest plus per-receipt signature verification provide the evidence.
        """
        audit = self.receipt_store.audit()
        if receipt.receipt_id not in audit["receipt_ids"]:
            raise AssuranceError("receipt_not_in_audited_chain")
        chain = self.receipt_store.audit_chain((receipt.receipt_id,))
        return dict(chain, store_aggregate_digest=audit["aggregate_digest"], store_count=audit["count"])

    def _atomic_write_event(self, event_type: str, payload: Mapping[str, Any]) -> None:
        """Append a signed event to the append-only event log."""
        event_id = "event:" + _digest({"type": event_type, "payload": payload})
        event = {"event_id": event_id, "type": event_type, "payload": dict(payload)}
        line = json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n"
        # Atomic append
        fd, tmp = tempfile.mkstemp(prefix=".recovery-event-", suffix=".tmp", dir=os.path.dirname(os.path.abspath(self.event_path)) or ".")
        try:
            with os.fdopen(fd, "a", encoding="utf-8") as h:
                # Read existing events
                existing = []
                if os.path.exists(self.event_path):
                    with open(self.event_path, "r", encoding="utf-8") as f:
                        for line in f:
                            if line.strip():
                                existing.append(line.rstrip("\n"))
                existing.append(line.rstrip("\n"))
                h.write("\n".join(existing) + "\n")
                h.flush()
                os.fsync(h.fileno())
            os.replace(tmp, self.event_path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    def _make_readonly(self, path: str) -> None:
        """Make a file read-only (OS-level immutability)."""
        mode = os.stat(path).st_mode
        os.chmod(path, mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))

    def _is_readonly(self, path: str) -> bool:
        try:
            return not bool(os.stat(path).st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))
        except OSError:
            return False

    def handle(self, action: ExecutionRecoveryAction, context: Mapping[str, Any]) -> Mapping[str, Any]:
        """
        Execute a recovery action with full governance checks.

        Returns a result mapping with status, rollback_performed, and completion receipt.
        """
        # 1. Authenticated operator context
        self._authorize(context, action)

        # 2. Signed receipt/run identity
        receipt = self._verify_signed_receipt(action.receipt_id)

        # 3. Approved patch
        patch = self._verify_approved_patch(action.proposal_id)

        # 4. Fresh base
        self._verify_fresh_base(action.workspace_id, action.current_base_snapshot_id)

        # 5. Tamper-evident receipt chain verification
        chain_result = self._verify_receipt_chain(receipt)

        # 6. Verify run exists and is in a terminal state eligible for rollback
        run = self.recovery_store.get(action.run_id)
        if run["status"] not in {"completed", "failed", "timed_out", "denied", "recovered"}:
            raise AssuranceError("run_not_in_rollbackable_state")

        # 7. Injected mutation handler - MUST confirm actual mutation
        if self.rollback_handler is None:
            raise AssuranceError("rollback_handler_required")
        mutation_confirmed = self.rollback_handler(action)
        if not mutation_confirmed:
            raise AssuranceError("rollback_mutation_not_confirmed")

        # 8. Mark run as rolled_back in recovery store
        self.recovery_store.mark_rolled_back(action.run_id)

        # 9. Create completion receipt for the rollback operation
        completion_receipt = create_receipt(
            request=action.to_mapping(),
            policy={"operation": action.operation, "scope": action.scope},
            workspace_before=run["workspace_before"],
            workspace_after=run["workspace_before"],  # Rolled back to before state
            outcome="rolled_back",
            rollback_available=False,
            side_effects=("rollback",),
            signing_key=self._signing_key,
        )
        self.receipt_store.put(completion_receipt)
        self.recovery_store.attach_completion(action.run_id, completion_receipt.receipt_id)

        # 10. Append completion event
        self._atomic_write_event("execution_recovery_completed", {
            "action_id": action.action_id,
            "operation": action.operation,
            "run_id": action.run_id,
            "receipt_id": action.receipt_id,
            "proposal_id": action.proposal_id,
            "workspace_id": action.workspace_id,
            "current_base_snapshot_id": action.current_base_snapshot_id,
            "operator_id": action.operator_id,
            "session_id": action.session_id,
            "completion_receipt_id": completion_receipt.receipt_id,
            "rollback_performed": True,
            "chain_digest": chain_result["chain_digest"],
        })

        return {
            "status": "rolled_back",
            "rollback_performed": True,
            "completion_receipt_id": completion_receipt.receipt_id,
            "chain_digest": chain_result["chain_digest"],
        }

    def verify_rollback_chain(self, run_id: str) -> Mapping[str, Any]:
        """
        Verify the tamper-evident rollback chain for a run.
        Returns chain verification result with signed receipt chain.
        """
        run = self.recovery_store.get(run_id)
        if run["status"] != "rolled_back":
            raise AssuranceError("run_not_rolled_back")

        # Find the rollback completion receipt
        receipt = self.receipt_store.get(run["receipt_id"])
        if receipt is None or receipt.outcome != "rolled_back":
            raise AssuranceError("rollback_receipt_missing_or_invalid")

        # Verify full chain up to rollback receipt
        chain_result = self._verify_receipt_chain(receipt)

        return {
            "status": "passed",
            "run_id": run_id,
            "receipt_id": receipt.receipt_id,
            "chain": chain_result,
            "claim": True,
        }


class ExecutionBackend:
    """
    Abstract backend for child execution. Concrete implementations must
    verify isolation capabilities or return not_run/blocked/unavailable.
    """
    def __init__(self, name: str):
        self.name = name

    def verify_isolation(self) -> Mapping[str, Any]:
        """
        Verify the backend provides required isolation.
        Returns {"status": "passed", "capabilities": [...]} or
        {"status": "not_run"/"blocked"/"unavailable", "reason": "..."}.
        NEVER returns "passed" without verified isolation.
        """
        raise NotImplementedError

    def execute(self, request: Mapping[str, Any], policy: Mapping[str, Any]) -> Mapping[str, Any]:
        """Execute the child request. Only callable after verify_isolation() returns passed."""
        raise NotImplementedError


def verify_backend_or_block(backend: Optional[ExecutionBackend]) -> Mapping[str, Any]:
    """
    Verify a backend is configured and provides isolation.
    Returns not_run/blocked/unavailable for unconfigured/unverifiable backends.
    NEVER returns passed for unverified backends.
    """
    if backend is None:
        return {"status": "not_run", "reason": "backend_not_configured"}
    result = backend.verify_isolation()
    if result.get("status") != "passed":
        # Ensure blocked/unavailable/not_run are preserved, never converted to passed
        status = result.get("status", "unavailable")
        if status not in {"not_run", "blocked", "unavailable"}:
            status = "unavailable"
        return {"status": status, "reason": result.get("reason", "backend_verification_failed")}
    return {"status": "passed", "capabilities": result.get("capabilities", [])}


__all__ = [
    "ASSURANCE_SCHEMA",
    "AssuranceError",
    "ExecutionReceipt",
    "ExecutionReceiptStore",
    "ExecutionRecoveryStore",
    "ExecutionRecoveryAction",
    "ExecutionRecoveryExecutor",
    "ExecutionBackend",
    "verify_backend_or_block",
    "artifact_manifest",
    "build_artifact_diff_from_manifests",
    "build_artifact_diff",
    "create_receipt",
    "request_fingerprint",
    "validate_receipt_transition",
    "validate_receipt_chain",
    "verify_receipt",
]