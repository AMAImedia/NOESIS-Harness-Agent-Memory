"""Human-governed learning promotion lifecycle.

This module deliberately separates proposal, approval, promotion, and activation.
It never executes skill content. Executable skill entrypoints remain outside the
promotion boundary and must be enabled by a separate reviewed runtime contract.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import sqlite3
import time
import uuid
from contextlib import contextmanager
from typing import Any, Callable, Iterable, Mapping, Optional


_SCHEMA = "noesis.learning-promotion.v1"
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
_STATES = ("review", "approved", "promoted", "rolled_back", "rejected", "blocked")


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _require_id(value: str, field: str) -> str:
    if not isinstance(value, str) or not _SAFE_ID.fullmatch(value):
        raise ValueError(f"invalid_{field}")
    return value


@dataclass(frozen=True)
class ExperienceReceipt:
    receipt_id: str
    experience_id: str
    agent_id: str
    scope: str
    source_digest: str
    outcome: str
    payload_digest: str
    policy_digest: str
    created_at: float
    schema_version: str = _SCHEMA

    def unsigned(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class HoldoutEvaluation:
    evaluation_id: str
    receipt_id: str
    evaluator_version: str
    holdout_digest: str
    total_cases: int
    passed_cases: int
    leaked_cases: int
    status: str
    evaluated_at: float
    schema_version: str = _SCHEMA

    @property
    def accepted(self) -> bool:
        return self.status == "passed" and self.total_cases > 0 and self.passed_cases == self.total_cases and self.leaked_cases == 0


@dataclass(frozen=True)
class PromotionProposal:
    proposal_id: str
    receipt_id: str
    evaluation_id: str
    skill_name: str
    content_digest: str
    state: str
    created_at: float
    approved_by: str = ""
    version: str = ""
    provenance_digest: str = ""
    schema_version: str = _SCHEMA


class LearningPromotionError(ValueError):
    """Raised for invalid or unsafe promotion transitions."""


class DurablePromotionState:
    """SQLite/WAL state store for restart-safe promotion records and evaluator manifests."""

    def __init__(self, path: str) -> None:
        if not path:
            raise ValueError("promotion_state_path_required")
        self.path = str(Path(path).expanduser().resolve())
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _connect(self):
        db = sqlite3.connect(self.path, timeout=5.0)
        db.row_factory = sqlite3.Row
        try:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA busy_timeout=5000")
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def _initialize(self) -> None:
        with self._connect() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS promotion_receipts (
                receipt_id TEXT PRIMARY KEY, record_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS promotion_evaluations (
                evaluation_id TEXT PRIMARY KEY, record_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS promotion_proposals (
                proposal_id TEXT PRIMARY KEY, record_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS promotion_previous_active (
                skill_name TEXT PRIMARY KEY, version TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS promotion_activation_journal (
                proposal_id TEXT PRIMARY KEY, record_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS evaluator_manifests (
                version TEXT PRIMARY KEY, manifest_digest TEXT NOT NULL, registered_at REAL NOT NULL
            );
            """)

    @staticmethod
    def _record(value: Any) -> str:
        return _canonical(asdict(value) if hasattr(value, "__dataclass_fields__") else value)

    def load_records(self, table: str, cls: Any) -> dict[str, Any]:
        allowed = {"promotion_receipts": "receipt_id", "promotion_evaluations": "evaluation_id", "promotion_proposals": "proposal_id"}
        if table not in allowed:
            raise ValueError("invalid_promotion_state_table")
        with self._connect() as db:
            rows = db.execute(f"SELECT {allowed[table]}, record_json FROM {table}").fetchall()
        return {str(row[allowed[table]]): cls(**json.loads(str(row["record_json"]))) for row in rows}

    def put(self, table: str, key: str, value: Any) -> None:
        columns = {"promotion_receipts": "receipt_id", "promotion_evaluations": "evaluation_id", "promotion_proposals": "proposal_id"}
        if table not in columns:
            raise ValueError("invalid_promotion_state_table")
        with self._connect() as db:
            db.execute(f"INSERT INTO {table} ({columns[table]}, record_json) VALUES (?, ?) ON CONFLICT({columns[table]}) DO UPDATE SET record_json=excluded.record_json", (str(key), self._record(value)))

    def put_activation(self, proposal_id: str, record: Mapping[str, Any]) -> None:
        with self._connect() as db:
            db.execute("INSERT INTO promotion_activation_journal(proposal_id, record_json) VALUES (?, ?) ON CONFLICT(proposal_id) DO UPDATE SET record_json=excluded.record_json", (str(proposal_id), self._record(record)))

    def activation_journal(self, proposal_id: Optional[str] = None) -> dict[str, Any]:
        with self._connect() as db:
            if proposal_id is None:
                rows = db.execute("SELECT proposal_id, record_json FROM promotion_activation_journal ORDER BY proposal_id").fetchall()
                return {str(row["proposal_id"]): json.loads(str(row["record_json"])) for row in rows}
            row = db.execute("SELECT record_json FROM promotion_activation_journal WHERE proposal_id=?", (str(proposal_id),)).fetchone()
        return {} if row is None else dict(json.loads(str(row["record_json"])))

    def put_previous_active(self, skill_name: str, version: str) -> None:
        with self._connect() as db:
            db.execute("INSERT INTO promotion_previous_active(skill_name, version) VALUES (?, ?) ON CONFLICT(skill_name) DO UPDATE SET version=excluded.version", (skill_name, version))

    def previous_active(self) -> dict[str, str]:
        with self._connect() as db:
            rows = db.execute("SELECT skill_name, version FROM promotion_previous_active").fetchall()
        return {str(row["skill_name"]): str(row["version"]) for row in rows}

    def register_evaluator(self, version: str, manifest_digest: str, *, registered_at: Optional[float] = None) -> None:
        with self._connect() as db:
            existing = db.execute("SELECT manifest_digest FROM evaluator_manifests WHERE version=?", (version,)).fetchone()
            if existing is not None and str(existing["manifest_digest"]) != manifest_digest:
                raise LearningPromotionError("evaluator_manifest_conflict")
            db.execute("INSERT OR IGNORE INTO evaluator_manifests(version, manifest_digest, registered_at) VALUES (?, ?, ?)", (version, manifest_digest, float(time.time() if registered_at is None else registered_at)))

    def evaluator_manifests(self) -> dict[str, str]:
        with self._connect() as db:
            rows = db.execute("SELECT version, manifest_digest FROM evaluator_manifests ORDER BY version").fetchall()
        return {str(row["version"]): str(row["manifest_digest"]) for row in rows}


class LearningPromotionPipeline:
    """Persistent, explicit, fail-closed learning promotion state machine."""

    def __init__(self, root: str, signing_key: bytes, *, state_path: Optional[str] = None):
        if not isinstance(signing_key, bytes) or len(signing_key) < 16:
            raise ValueError("signing_key_too_short")
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self._key = signing_key
        self._state = DurablePromotionState(state_path or str(self.root / "promotion_state.sqlite3"))
        self._receipts: dict[str, ExperienceReceipt] = self._state.load_records("promotion_receipts", ExperienceReceipt)
        self._evaluations: dict[str, HoldoutEvaluation] = self._state.load_records("promotion_evaluations", HoldoutEvaluation)
        self._proposals: dict[str, PromotionProposal] = self._state.load_records("promotion_proposals", PromotionProposal)
        self._previous_active: dict[str, str] = self._state.previous_active()

    @property
    def durable_state(self) -> DurablePromotionState:
        return self._state

    def capture(self, *, experience_id: str, agent_id: str, scope: str,
                source_digest: str, outcome: str, payload: Any,
                policy_digest: str, created_at: Optional[float] = None) -> ExperienceReceipt:
        for value, field in ((experience_id, "experience_id"), (agent_id, "agent_id"), (policy_digest, "policy_digest")):
            _require_id(value, field)
        if not isinstance(scope, str) or not scope or len(scope) > 256:
            raise ValueError("invalid_scope")
        if not isinstance(source_digest, str) or not source_digest or len(source_digest) > 256:
            raise ValueError("invalid_source_digest")
        if not isinstance(outcome, str) or outcome not in ("success", "failure", "partial"):
            raise ValueError("invalid_outcome")
        for existing in self._receipts.values():
            if existing.experience_id == experience_id:
                if existing.source_digest == source_digest and existing.policy_digest == policy_digest and existing.payload_digest == _digest(payload):
                    return existing
                raise LearningPromotionError("experience_receipt_conflict")
        receipt = ExperienceReceipt(
            receipt_id=uuid.uuid4().hex,
            experience_id=experience_id,
            agent_id=agent_id,
            scope=scope,
            source_digest=source_digest,
            outcome=outcome,
            payload_digest=_digest(payload),
            policy_digest=policy_digest,
            created_at=float(time.time() if created_at is None else created_at),
        )
        self._receipts[receipt.receipt_id] = receipt
        self._state.put("promotion_receipts", receipt.receipt_id, receipt)
        return receipt

    def evaluate(self, receipt_id: str, cases: Iterable[Mapping[str, Any]], *, evaluator_version: str) -> HoldoutEvaluation:
        receipt = self._receipts.get(receipt_id)
        if receipt is None:
            raise KeyError(receipt_id)
        _require_id(evaluator_version, "evaluator_version")
        normalized: list[dict[str, Any]] = []
        for case in cases:
            if not isinstance(case, Mapping):
                raise LearningPromotionError("invalid_holdout_case")
            case_id = case.get("case_id")
            if not isinstance(case_id, str) or not case_id:
                raise LearningPromotionError("holdout_case_id_required")
            normalized.append({
                "case_id": case_id,
                "passed": bool(case.get("passed", False)),
                "leaked": bool(case.get("leaked", False)),
            })
        normalized.sort(key=lambda item: item["case_id"])
        holdout_digest = _digest(normalized)
        for existing in self._evaluations.values():
            if existing.receipt_id == receipt_id and existing.evaluator_version == evaluator_version and existing.holdout_digest == holdout_digest:
                return existing
        total = len(normalized)
        passed = sum(1 for item in normalized if item["passed"])
        leaked = sum(1 for item in normalized if item["leaked"])
        status = "passed" if total > 0 and passed == total and leaked == 0 else "blocked"
        evaluation = HoldoutEvaluation(
            evaluation_id=uuid.uuid4().hex,
            receipt_id=receipt_id,
            evaluator_version=evaluator_version,
            holdout_digest=holdout_digest,
            total_cases=total,
            passed_cases=passed,
            leaked_cases=leaked,
            status=status,
            evaluated_at=time.time(),
        )
        self._evaluations[evaluation.evaluation_id] = evaluation
        self._state.put("promotion_evaluations", evaluation.evaluation_id, evaluation)
        return evaluation

    def propose(self, receipt_id: str, evaluation_id: str, *, skill_name: str, content: str) -> PromotionProposal:
        receipt = self._receipts.get(receipt_id)
        evaluation = self._evaluations.get(evaluation_id)
        if receipt is None or evaluation is None or evaluation.receipt_id != receipt_id:
            raise LearningPromotionError("receipt_evaluation_mismatch")
        _require_id(skill_name, "skill_name")
        if not isinstance(content, str) or not content.strip():
            raise LearningPromotionError("empty_skill_content")
        content_digest = _digest(content)
        for existing in self._proposals.values():
            if existing.receipt_id == receipt_id and existing.evaluation_id == evaluation_id and existing.skill_name == skill_name:
                if existing.content_digest == content_digest:
                    return existing
                raise LearningPromotionError("proposal_content_conflict")
        state = "review" if evaluation.accepted else "blocked"
        proposal_id = uuid.uuid4().hex
        provenance_digest = _digest({
            "receipt": receipt.unsigned(),
            "evaluation": asdict(evaluation),
            "skill_name": skill_name,
            "content_digest": content_digest,
        })
        proposal = PromotionProposal(proposal_id, receipt_id, evaluation_id, skill_name, content_digest, state, time.time(), provenance_digest=provenance_digest)
        self._proposals[proposal.proposal_id] = proposal
        self._state.put("promotion_proposals", proposal.proposal_id, proposal)
        if state == "blocked":
            raise LearningPromotionError("holdout_not_accepted")
        return proposal

    def approve(self, proposal_id: str, *, approved_by: str, tests: Callable[[], bool]) -> PromotionProposal:
        proposal = self._proposals.get(proposal_id)
        _require_id(approved_by, "approved_by")
        if proposal is None:
            raise KeyError(proposal_id)
        if proposal.state != "review":
            raise LearningPromotionError("proposal_not_in_review")
        self._require_current_provenance(proposal)
        try:
            passed = bool(tests())
        except Exception:
            passed = False
        if not passed:
            raise LearningPromotionError("approval_tests_failed")
        updated = PromotionProposal(**{**asdict(proposal), "state": "approved", "approved_by": approved_by})
        self._proposals[proposal_id] = updated
        self._state.put("promotion_proposals", proposal_id, updated)
        return updated

    def reject(self, proposal_id: str, *, rejected_by: str) -> PromotionProposal:
        proposal = self._proposals.get(proposal_id)
        _require_id(rejected_by, "rejected_by")
        if proposal is None:
            raise KeyError(proposal_id)
        if proposal.state != "review":
            raise LearningPromotionError("proposal_not_in_review")
        updated = PromotionProposal(**{**asdict(proposal), "state": "rejected", "approved_by": rejected_by})
        self._proposals[proposal_id] = updated
        self._state.put("promotion_proposals", proposal_id, updated)
        return updated

    def _current_provenance(self, proposal: PromotionProposal) -> str:
        receipt = self._receipts.get(proposal.receipt_id)
        evaluation = self._evaluations.get(proposal.evaluation_id)
        if receipt is None or evaluation is None or evaluation.receipt_id != receipt.receipt_id:
            raise LearningPromotionError("proposal_provenance_missing")
        return _digest({"receipt": receipt.unsigned(), "evaluation": asdict(evaluation), "skill_name": proposal.skill_name, "content_digest": proposal.content_digest})

    def _require_current_provenance(self, proposal: PromotionProposal) -> None:
        current = self._current_provenance(proposal)
        if not proposal.provenance_digest or not hmac.compare_digest(current, proposal.provenance_digest):
            raise LearningPromotionError("proposal_provenance_mismatch")

    def review_snapshot(self, *, max_proposals: int = 64) -> dict[str, Any]:
        """Return bounded review metadata only; never returns skill or payload content."""
        if not isinstance(max_proposals, int) or not 1 <= max_proposals <= 256:
            raise ValueError("invalid_review_snapshot_bound")
        proposals = []
        for proposal in sorted(self._proposals.values(), key=lambda item: (item.created_at, item.proposal_id), reverse=True)[:max_proposals]:
            receipt = self._receipts.get(proposal.receipt_id)
            evaluation = self._evaluations.get(proposal.evaluation_id)
            current = ""
            provenance_status = "blocked"
            try:
                current = self._current_provenance(proposal)
                provenance_status = "verified" if proposal.provenance_digest and hmac.compare_digest(current, proposal.provenance_digest) else "mismatch"
            except LearningPromotionError:
                provenance_status = "missing"
            proposals.append({
                "proposal_id": proposal.proposal_id,
                "skill_name": proposal.skill_name,
                "state": proposal.state,
                "created_at": proposal.created_at,
                "approved_by": proposal.approved_by,
                "version": proposal.version,
                "receipt_id": proposal.receipt_id,
                "evaluation_id": proposal.evaluation_id,
                "content_digest": proposal.content_digest,
                "provenance_digest": proposal.provenance_digest,
                "provenance_status": provenance_status,
                "source_digest": receipt.source_digest if receipt else "",
                "policy_digest": receipt.policy_digest if receipt else "",
                "payload_digest": receipt.payload_digest if receipt else "",
                "evaluation_status": evaluation.status if evaluation else "missing",
                "evaluator_version": evaluation.evaluator_version if evaluation else "",
                "holdout_digest": evaluation.holdout_digest if evaluation else "",
                "automatic_activation": False,
            })
        return {"schema_version": "noesis.learning-review-snapshot.v1", "bounded": True, "max_proposals": max_proposals, "proposal_count": len(proposals), "proposals": proposals, "automatic_activation": False, "execution_claim": "read_only_review_metadata"}

    def promote(self, proposal_id: str, *, content: str, verify: Callable[[Path], bool], activate: bool = True) -> tuple[PromotionProposal, str]:
        proposal = self._proposals.get(proposal_id)
        if proposal is None:
            raise KeyError(proposal_id)
        if proposal.state != "approved":
            raise LearningPromotionError("explicit_approval_required")
        self._require_current_provenance(proposal)
        if _digest(content) != proposal.content_digest:
            raise LearningPromotionError("content_digest_mismatch")
        version = "v1-" + proposal.content_digest[:24]
        skill_root = self.root / proposal.skill_name
        skill_dir = skill_root / version
        if skill_dir.exists():
            raise LearningPromotionError("immutable_version_collision")
        skill_dir.mkdir(parents=True, exist_ok=False)
        skill_file = skill_dir / "SKILL.md"
        manifest_file = skill_dir / "VERSION.json"
        manifest = {
            "schema_version": "noesis.immutable-skill-version.v1",
            "skill_name": proposal.skill_name,
            "version": version,
            "proposal_id": proposal_id,
            "content_digest": proposal.content_digest,
            "provenance_digest": proposal.provenance_digest,
            "approved_by": proposal.approved_by,
            "immutable": True,
        }
        skill_file.write_text(content, encoding="utf-8")
        manifest_file.write_text(_canonical(manifest) + "\n", encoding="utf-8")
        try:
            verified = bool(verify(skill_file))
        except Exception:
            verified = False
        if not verified:
            (skill_dir / ".rejected").write_text("promotion_verification_failed\n", encoding="utf-8")
            raise LearningPromotionError("promotion_verification_failed")
        signed_payload = {"schema_version": "noesis.immutable-skill-promotion-receipt.v1", "proposal_id": proposal_id, "skill_name": proposal.skill_name, "version": version, "content_digest": proposal.content_digest, "provenance_digest": proposal.provenance_digest, "immutable": True, "active": bool(activate)}
        legacy_payload = {"proposal_id": proposal_id, "skill_name": proposal.skill_name, "version": version, "active": bool(activate)}
        signed = "v2:" + self._sign(signed_payload) + ":" + self._sign(legacy_payload)
        receipt_path = skill_dir / "PROMOTION_RECEIPT.json"
        receipt_path.write_text(_canonical({"payload": signed_payload, "signature": signed}) + "\n", encoding="utf-8")
        previous = self.active_version(proposal.skill_name)
        self._state.put_activation(proposal_id, {"schema_version": "noesis.promotion-activation-journal.v1", "proposal_id": proposal_id, "skill_name": proposal.skill_name, "version": version, "previous_version": previous or "", "receipt_path": str(receipt_path), "status": "prepared" if activate else "inactive", "updated_at": time.time()})
        updated = PromotionProposal(**{**asdict(proposal), "state": "promoted", "version": version})
        self._proposals[proposal_id] = updated
        self._state.put("promotion_proposals", proposal_id, updated)
        if activate:
            self._previous_active[proposal.skill_name] = previous or ""
            self._state.put_previous_active(proposal.skill_name, previous or "")
            skill_root.mkdir(parents=True, exist_ok=True)
            active_path = skill_root / "ACTIVE"
            active_next = skill_root / "ACTIVE.next"
            active_next.write_text(version + "\n", encoding="utf-8")
            os.replace(str(active_next), str(active_path))
            self._state.put_activation(proposal_id, {"schema_version": "noesis.promotion-activation-journal.v1", "proposal_id": proposal_id, "skill_name": proposal.skill_name, "version": version, "previous_version": previous or "", "receipt_path": str(receipt_path), "status": "activated", "updated_at": time.time()})
        return updated, signed

    def rollback(self, proposal_id: str) -> PromotionProposal:
        proposal = self._proposals.get(proposal_id)
        if proposal is None:
            raise KeyError(proposal_id)
        if proposal.state != "promoted":
            raise LearningPromotionError("rollback_requires_promoted")
        active = self.root / proposal.skill_name / "ACTIVE"
        previous = self._previous_active.get(proposal.skill_name, "")
        if previous:
            active.write_text(previous + "\n", encoding="utf-8")
        elif active.exists():
            active.unlink()
        updated = PromotionProposal(**{**asdict(proposal), "state": "rolled_back"})
        self._proposals[proposal_id] = updated
        self._state.put("promotion_proposals", proposal_id, updated)
        return updated

    def active_version(self, skill_name: str) -> str:
        _require_id(skill_name, "skill_name")
        path = self.root / skill_name / "ACTIVE"
        return path.read_text(encoding="utf-8").strip() if path.is_file() else ""

    def verify_signature(self, payload: Mapping[str, Any], signature: str) -> bool:
        if not isinstance(signature, str):
            return False
        expected = hmac.new(self._key, _canonical(payload).encode("utf-8"), hashlib.sha256).hexdigest()
        if hmac.compare_digest(expected, signature):
            return True
        if signature.startswith("v2:"):
            parts = signature.split(":")
            if len(parts) == 3 and len(parts[1]) == 64 and len(parts[2]) == 64:
                if "content_digest" in payload or payload.get("immutable") is True:
                    return hmac.compare_digest(expected, parts[1])
                return hmac.compare_digest(expected, parts[2])
        return False

    def _sign(self, payload: Mapping[str, Any]) -> str:
        return hmac.new(self._key, _canonical(payload).encode("utf-8"), hashlib.sha256).hexdigest()


__all__ = ["ExperienceReceipt", "HoldoutEvaluation", "PromotionProposal", "LearningPromotionError", "DurablePromotionState", "LearningPromotionPipeline"]
