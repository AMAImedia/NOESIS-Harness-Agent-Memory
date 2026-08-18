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
from pathlib import Path
import re
import time
import uuid
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
    schema_version: str = _SCHEMA


class LearningPromotionError(ValueError):
    """Raised for invalid or unsafe promotion transitions."""


class LearningPromotionPipeline:
    """Persistent, explicit, fail-closed learning promotion state machine."""

    def __init__(self, root: str, signing_key: bytes):
        if not isinstance(signing_key, bytes) or len(signing_key) < 16:
            raise ValueError("signing_key_too_short")
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self._key = signing_key
        self._receipts: dict[str, ExperienceReceipt] = {}
        self._evaluations: dict[str, HoldoutEvaluation] = {}
        self._proposals: dict[str, PromotionProposal] = {}
        self._previous_active: dict[str, str] = {}

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
        total = len(normalized)
        passed = sum(1 for item in normalized if item["passed"])
        leaked = sum(1 for item in normalized if item["leaked"])
        status = "passed" if total > 0 and passed == total and leaked == 0 else "blocked"
        evaluation = HoldoutEvaluation(
            evaluation_id=uuid.uuid4().hex,
            receipt_id=receipt_id,
            evaluator_version=evaluator_version,
            holdout_digest=_digest(normalized),
            total_cases=total,
            passed_cases=passed,
            leaked_cases=leaked,
            status=status,
            evaluated_at=time.time(),
        )
        self._evaluations[evaluation.evaluation_id] = evaluation
        return evaluation

    def propose(self, receipt_id: str, evaluation_id: str, *, skill_name: str, content: str) -> PromotionProposal:
        receipt = self._receipts.get(receipt_id)
        evaluation = self._evaluations.get(evaluation_id)
        if receipt is None or evaluation is None or evaluation.receipt_id != receipt_id:
            raise LearningPromotionError("receipt_evaluation_mismatch")
        _require_id(skill_name, "skill_name")
        if not isinstance(content, str) or not content.strip():
            raise LearningPromotionError("empty_skill_content")
        state = "review" if evaluation.accepted else "blocked"
        proposal = PromotionProposal(uuid.uuid4().hex, receipt_id, evaluation_id, skill_name, _digest(content), state, time.time())
        self._proposals[proposal.proposal_id] = proposal
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
        try:
            passed = bool(tests())
        except Exception:
            passed = False
        if not passed:
            raise LearningPromotionError("approval_tests_failed")
        updated = PromotionProposal(**{**asdict(proposal), "state": "approved", "approved_by": approved_by})
        self._proposals[proposal_id] = updated
        return updated

    def promote(self, proposal_id: str, *, content: str, verify: Callable[[Path], bool], activate: bool = True) -> tuple[PromotionProposal, str]:
        proposal = self._proposals.get(proposal_id)
        if proposal is None:
            raise KeyError(proposal_id)
        if proposal.state != "approved":
            raise LearningPromotionError("explicit_approval_required")
        if _digest(content) != proposal.content_digest:
            raise LearningPromotionError("content_digest_mismatch")
        version = f"v-{int(time.time())}-{proposal.proposal_id[:8]}"
        skill_dir = self.root / proposal.skill_name / version
        skill_dir.mkdir(parents=True, exist_ok=False)
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(content, encoding="utf-8")
        try:
            verified = bool(verify(skill_file))
        except Exception:
            verified = False
        if not verified:
            import shutil
            shutil.rmtree(skill_dir, ignore_errors=True)
            raise LearningPromotionError("promotion_verification_failed")
        previous = self.active_version(proposal.skill_name)
        if activate:
            self._previous_active[proposal.skill_name] = previous or ""
            (self.root / proposal.skill_name).mkdir(parents=True, exist_ok=True)
            (self.root / proposal.skill_name / "ACTIVE").write_text(version + "\n", encoding="utf-8")
        updated = PromotionProposal(**{**asdict(proposal), "state": "promoted", "version": version})
        self._proposals[proposal_id] = updated
        signed = self._sign({"proposal_id": proposal_id, "skill_name": proposal.skill_name, "version": version, "active": bool(activate)})
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
        return updated

    def active_version(self, skill_name: str) -> str:
        _require_id(skill_name, "skill_name")
        path = self.root / skill_name / "ACTIVE"
        return path.read_text(encoding="utf-8").strip() if path.is_file() else ""

    def verify_signature(self, payload: Mapping[str, Any], signature: str) -> bool:
        expected = hmac.new(self._key, _canonical(payload).encode("utf-8"), hashlib.sha256).hexdigest()
        return isinstance(signature, str) and hmac.compare_digest(expected, signature)

    def _sign(self, payload: Mapping[str, Any]) -> str:
        return hmac.new(self._key, _canonical(payload).encode("utf-8"), hashlib.sha256).hexdigest()


__all__ = ["ExperienceReceipt", "HoldoutEvaluation", "PromotionProposal", "LearningPromotionError", "LearningPromotionPipeline"]
