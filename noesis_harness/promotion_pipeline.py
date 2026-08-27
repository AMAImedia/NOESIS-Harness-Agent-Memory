"""noesis_harness/promotion_pipeline.py

Thin, read-only orchestration tying the governed holdout check in
``learning_promotion`` to the append-only ``learning_journal``.

This module is a *governance glue* layer. It does NOT execute, evaluate, or
generate any model or skill output. It only:

  1. runs ``learning_promotion.HoldoutEvaluation.accepted`` -- the deterministic,
     human-governed holdout gate -- on a candidate's holdout cases;
  2. records the resulting decision as an append-only event in the
     ``LearningJournal`` (promoted only when the holdout passes);
  3. optionally persists a side-effect-free decision JSON line elsewhere.

Borrowed patterns (provenance):
  - LoopX (event_sourced_state.py): the promotion decision is recorded as an
    immutable event; current truth is a replay projection, never a mutation.
  - agentmemory (leases.py): the decision entry is idempotent on a content
    fingerprint so a double-send is a no-op, not a duplicate promotion.
  - Hermes (snapshot.py): every interaction with the journal is read-only w.r.t.
    the event store; only appends are ever permitted.

Design guarantees (AGENTS.md HARD rules):
  - stdlib only.
  - Append-only safe: never rewrites the journal; only appends.
  - Idempotent: the same candidate yields the same fingerprint; a repeat write
    is absorbed by ``LearningJournal.record``.
  - Deterministic: the holdout gate is a pure function of the candidate cases.
  - Python 3.9+ syntax only (no ``X | None``, no ``match``).

This is a *governance record only*. A recorded "promoted" decision is not a
claim of skill quality; it merely records that a deterministic holdout gate
passed under human-governed rules.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from typing import Any, Dict, List, Optional

from .learning_journal import LearningJournal
from .learning_promotion import HoldoutEvaluation


def _canonical(value: Any) -> str:
    """Deterministic JSON serialization, matching learning_promotion / journal."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _validate_candidate(candidate: Any) -> Dict[str, Any]:
    """Fail-closed structural validation of a candidate (raises on bad input)."""
    if not isinstance(candidate, dict):
        raise ValueError("candidate_must_be_object")
    scope = candidate.get("scope")
    if not isinstance(scope, str) or not scope:
        raise ValueError("candidate_scope_required")
    candidate_id = candidate.get("candidate_id")
    if not isinstance(candidate_id, str) or not candidate_id:
        raise ValueError("candidate_id_required")
    evaluator_version = candidate.get("evaluator_version")
    if not isinstance(evaluator_version, str) or not evaluator_version:
        raise ValueError("evaluator_version_required")
    cases = candidate.get("cases")
    if not isinstance(cases, list) or len(cases) == 0:
        raise ValueError("candidate_cases_required")
    return {
        "scope": scope,
        "candidate_id": candidate_id,
        "evaluator_version": evaluator_version,
        "cases": cases,
    }


def _holdout_check(candidate_id: str, evaluator_version: str, cases: List[Any]) -> HoldoutEvaluation:
    """Run learning_promotion's deterministic holdout gate on normalized cases.

    This is a read-only call: it constructs a ``HoldoutEvaluation`` and relies on
    its ``accepted`` property -- the same canonical gate used by the governed
    promotion state machine. It never writes to the promotion event store.
    """
    normalized: List[Dict[str, Any]] = []
    for case in cases:
        if not isinstance(case, dict):
            raise ValueError("invalid_holdout_case")
        case_id = case.get("case_id")
        if not isinstance(case_id, str) or not case_id:
            raise ValueError("holdout_case_id_required")
        normalized.append({
            "case_id": case_id,
            "passed": bool(case.get("passed", False)),
            "leaked": bool(case.get("leaked", False)),
        })
    normalized.sort(key=lambda item: item["case_id"])
    holdout_digest = hashlib.sha256(_canonical(normalized).encode("utf-8")).hexdigest()
    total = len(normalized)
    passed = sum(1 for item in normalized if item["passed"])
    leaked = sum(1 for item in normalized if item["leaked"])
    status = "passed" if total > 0 and passed == total and leaked == 0 else "blocked"
    evaluation = HoldoutEvaluation(
        evaluation_id="eval-" + holdout_digest[:24],
        receipt_id="cand-" + candidate_id,
        evaluator_version=evaluator_version,
        holdout_digest=holdout_digest,
        total_cases=total,
        passed_cases=passed,
        leaked_cases=leaked,
        status=status,
        evaluated_at=time.time(),
    )
    return evaluation


def _persist_decision(promotion_path: str, decision: Dict[str, Any]) -> None:
    """Write-only, append-only persistence of the decision JSON (never reads it)."""
    parent = os.path.dirname(os.path.abspath(os.path.expanduser(promotion_path)))
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(promotion_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(decision, ensure_ascii=False, default=str) + "\n")


def evaluate(candidate: Any, journal_path: str, promotion_path: Optional[str] = None) -> Dict[str, Any]:
    """Run the governed holdout gate on ``candidate`` and record the decision.

    Args:
        candidate: dict with keys ``scope`` (str), ``candidate_id`` (str),
            ``evaluator_version`` (str), and ``cases`` (list of
            ``{"case_id": str, "passed"?: bool, "leaked"?: bool}``).
        journal_path: path to the append-only ``LearningJournal`` file.
        promotion_path: optional path to append a decision JSON line (separate
            from the event log; side-effect free on the journal).

    Returns:
        dict: ``{"promoted": bool, "holdout_passed": bool, "entry_id": str,
        "reason": str, "holdout": {...}}`` where ``holdout`` carries the
        learning_promotion holdout detail (total/passed/leaked/status/digest).

    The function is read-only w.r.t. the promotion event store: it only appends
    to the journal. A bad candidate fails closed (raises ValueError, no
    promotion recorded). A candidate that fails the holdout is recorded as
    ``reject`` and is NOT marked promoted.
    """
    validated = _validate_candidate(candidate)
    evaluation = _holdout_check(
        validated["candidate_id"],
        validated["evaluator_version"],
        validated["cases"],
    )
    accepted = evaluation.accepted
    action = "promote" if accepted else "reject"
    reason = "holdout_passed" if accepted else "holdout_failed"
    payload = {
        "candidate_id": validated["candidate_id"],
        "evaluator_version": validated["evaluator_version"],
        "decision": "promoted" if accepted else "rejected",
        "holdout": {
            "total_cases": evaluation.total_cases,
            "passed_cases": evaluation.passed_cases,
            "leaked_cases": evaluation.leaked_cases,
            "status": evaluation.status,
            "holdout_digest": evaluation.holdout_digest,
        },
        "governance_claim": "governance_record_only",
    }
    journal = LearningJournal(journal_path)
    entry_id = journal.record(scope=validated["scope"], action=action, payload=payload)
    decision: Dict[str, Any] = {
        "promoted": accepted,
        "holdout_passed": accepted,
        "entry_id": entry_id,
        "reason": reason,
        "holdout": {
            "total_cases": evaluation.total_cases,
            "passed_cases": evaluation.passed_cases,
            "leaked_cases": evaluation.leaked_cases,
            "status": evaluation.status,
            "holdout_digest": evaluation.holdout_digest,
        },
    }
    if promotion_path is not None:
        _persist_decision(promotion_path, decision)
    return decision


__all__ = ["evaluate"]
