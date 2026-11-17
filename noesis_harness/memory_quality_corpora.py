"""Adversarial memory-quality corpora v2 (Gate 5 broader independent corpora).

Deterministic, stdlib-only fixture corpus that widens memory-quality coverage
without touching the core evaluator. Fixture format follows the recorded
trajectory pattern of scripts/run_memory_quality_evidence.py (agentmemory
quality-trace lineage) with fail-closed expectation checks in the spirit of
deepseek-harness adversarial suites. Provenance digests bind every case to its
canonical inputs so recorded evidence stays verifiable even when a modeled
behavior (e.g. conflict resolution) fails.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Callable, Dict, Mapping, Sequence, Tuple

from .memory import Memory
from .memory_quality import MemoryQualityCase, MemoryQualityEvaluator, MemoryTrajectoryStep


CORPUS_SCHEMA_VERSION = "noesis.memory-quality-corpus.v2"


class MemoryQualityCorpusError(ValueError):
    """Raised when the corpus definition or an adapter violates the contract."""


@dataclass(frozen=True)
class AdversarialCorpusCaseV2:
    """One deterministic adversarial case mapped onto evaluator inputs."""

    case_id: str
    category: str
    session_id: str
    query: str
    relevant_source_ids: Tuple[str, ...]
    selected_source_ids: Tuple[str, ...]
    attributed_source_ids: Tuple[str, ...]
    conflict_resolution_correct: bool
    temporal_order_correct: bool
    retained_after_compaction_ids: Tuple[str, ...]
    required_after_compaction_ids: Tuple[str, ...]
    used_tokens: int
    budget_tokens: int
    leakage_free: bool = True
    reused_experience_ids: Tuple[str, ...] = ()
    relevant_experience_ids: Tuple[str, ...] = ()
    decay_base_strengths: Tuple[float, ...] = ()
    decay_periods: int = 0

    def payload(self) -> Dict[str, Any]:
        return {
            "attributed_source_ids": list(self.attributed_source_ids),
            "budget_tokens": int(self.budget_tokens),
            "case_id": self.case_id,
            "category": self.category,
            "conflict_resolution_correct": bool(self.conflict_resolution_correct),
            "decay_base_strengths": list(self.decay_base_strengths),
            "decay_periods": int(self.decay_periods),
            "leakage_free": bool(self.leakage_free),
            "query": self.query,
            "relevant_experience_ids": list(self.relevant_experience_ids),
            "relevant_source_ids": list(self.relevant_source_ids),
            "required_after_compaction_ids": list(self.required_after_compaction_ids),
            "retained_after_compaction_ids": list(self.retained_after_compaction_ids),
            "reused_experience_ids": list(self.reused_experience_ids),
            "selected_source_ids": list(self.selected_source_ids),
            "session_id": self.session_id,
            "temporal_order_correct": bool(self.temporal_order_correct),
            "used_tokens": int(self.used_tokens),
        }

    def provenance_digest(self) -> str:
        encoded = json.dumps(self.payload(), sort_keys=True, separators=(",", ":"))
        return "sha256:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    def to_memory_quality_case(self) -> MemoryQualityCase:
        return MemoryQualityCase(
            self.case_id,
            self.relevant_source_ids,
            self.selected_source_ids,
            self.attributed_source_ids,
            self.conflict_resolution_correct,
            self.temporal_order_correct,
            self.retained_after_compaction_ids,
            self.required_after_compaction_ids,
            self.used_tokens,
            self.budget_tokens,
            self.leakage_free,
            self.reused_experience_ids,
            self.relevant_experience_ids,
        )

    def to_trajectory_step(self) -> MemoryTrajectoryStep:
        return MemoryTrajectoryStep(
            self.case_id,
            self.query,
            self.relevant_source_ids,
            self.selected_source_ids,
            self.attributed_source_ids,
            self.reused_experience_ids,
            self.relevant_experience_ids,
            self.conflict_resolution_correct,
            self.temporal_order_correct,
            self.retained_after_compaction_ids,
            self.required_after_compaction_ids,
            self.used_tokens,
            self.budget_tokens,
            self.leakage_free,
        )


SESSION_ALPHA = "v2-session-alpha"
SESSION_BETA = "v2-session-beta"
BUDGET_TOKENS_V2 = 64
DECAY_AT_FLOOR_BASE = 0.4
DECAY_SUBFLOOR_BASE = 0.3
DECAY_BOUNDARY_PERIODS = 2


def _long_trace_selected(prefix: str, relevant_id: str) -> Tuple[str, ...]:
    return (
        relevant_id,
        prefix + "-trace-01",
        prefix + "-trace-02",
        prefix + "-trace-03",
        prefix + "-trace-04",
        prefix + "-trace-05",
        prefix + "-trace-06",
        prefix + "-trace-07",
    )


def build_adversarial_corpus_v2() -> Tuple[AdversarialCorpusCaseV2, ...]:
    """Return the pinned v2 adversarial corpus (pure constants, no wall clock)."""
    at_floor_retained = "v2-src-decay-at-floor"
    subfloor_evicted = "v2-src-decay-below-floor"
    cases = (
        AdversarialCorpusCaseV2(
            "v2-temporal-inversion-early",
            "temporal_inversion_pair",
            SESSION_ALPHA,
            "event ordering audit first incident report token e10",
            ("v2-src-order-a",),
            ("v2-src-order-a",),
            ("v2-src-order-a",),
            True,
            True,
            ("v2-src-order-a",),
            ("v2-src-order-a",),
            12,
            BUDGET_TOKENS_V2,
        ),
        AdversarialCorpusCaseV2(
            "v2-temporal-inversion-late",
            "temporal_inversion_pair",
            SESSION_ALPHA,
            "event ordering audit later incident report token e11 newer observed older",
            ("v2-src-order-b",),
            ("v2-src-order-b",),
            ("v2-src-order-b",),
            True,
            False,
            ("v2-src-order-b",),
            ("v2-src-order-b",),
            14,
            BUDGET_TOKENS_V2,
        ),
        AdversarialCorpusCaseV2(
            "v2-duplicate-attribution",
            "duplicate_attribution",
            SESSION_ALPHA,
            "isolation child runtime network denial audit",
            ("v2-src-dup",),
            ("v2-src-dup", "v2-src-dup-noise"),
            ("v2-src-dup", "v2-src-dup", "v2-src-dup-noise"),
            True,
            True,
            ("v2-src-dup",),
            ("v2-src-dup",),
            16,
            BUDGET_TOKENS_V2,
        ),
        AdversarialCorpusCaseV2(
            "v2-near-duplicate-query-primary",
            "near_duplicate_query",
            SESSION_ALPHA,
            "rollback recovery signed receipt checkpoint 7f3a",
            ("v2-src-near-primary",),
            ("v2-src-near-primary", "v2-src-near-variant"),
            ("v2-src-near-primary",),
            True,
            True,
            ("v2-src-near-primary",),
            ("v2-src-near-primary",),
            18,
            BUDGET_TOKENS_V2,
        ),
        AdversarialCorpusCaseV2(
            "v2-near-duplicate-query-variant",
            "near_duplicate_query",
            SESSION_ALPHA,
            "rollback recovery signed receipt checkpoint 7f3b",
            ("v2-src-near-variant",),
            ("v2-src-near-primary", "v2-src-near-variant"),
            ("v2-src-near-variant",),
            True,
            True,
            ("v2-src-near-variant",),
            ("v2-src-near-variant",),
            19,
            BUDGET_TOKENS_V2,
        ),
        AdversarialCorpusCaseV2(
            "v2-budget-edge-exact",
            "budget_edge_long_trace",
            SESSION_ALPHA,
            "budget hard cap long trace packing boundary inclusive",
            ("v2-src-budget-edge",),
            _long_trace_selected("v2-edge", "v2-src-budget-edge"),
            ("v2-src-budget-edge",),
            True,
            True,
            ("v2-src-budget-edge",),
            ("v2-src-budget-edge",),
            BUDGET_TOKENS_V2,
            BUDGET_TOKENS_V2,
        ),
        AdversarialCorpusCaseV2(
            "v2-budget-edge-overrun",
            "budget_edge_long_trace",
            SESSION_ALPHA,
            "budget hard cap long trace overrun fails closed",
            ("v2-src-budget-overrun",),
            _long_trace_selected("v2-overrun", "v2-src-budget-overrun"),
            ("v2-src-budget-overrun",),
            True,
            True,
            ("v2-src-budget-overrun",),
            ("v2-src-budget-overrun",),
            BUDGET_TOKENS_V2 + 1,
            BUDGET_TOKENS_V2,
        ),
        AdversarialCorpusCaseV2(
            "v2-conflict-provenance",
            "conflict_with_provenance",
            SESSION_ALPHA,
            "resume lease state conflicting stale versus current receipt",
            ("v2-src-conflict-current",),
            ("v2-src-conflict-stale", "v2-src-conflict-current"),
            ("v2-src-conflict-current",),
            False,
            True,
            ("v2-src-conflict-current",),
            ("v2-src-conflict-current",),
            21,
            BUDGET_TOKENS_V2,
        ),
        AdversarialCorpusCaseV2(
            "v2-decay-floor-boundary",
            "decay_floor_boundary",
            SESSION_ALPHA,
            "decay floor retention boundary at floor survives below evicted",
            (at_floor_retained,),
            (at_floor_retained,),
            (at_floor_retained,),
            True,
            True,
            (at_floor_retained,),
            (at_floor_retained, subfloor_evicted),
            13,
            BUDGET_TOKENS_V2,
            decay_base_strengths=(DECAY_AT_FLOOR_BASE, DECAY_SUBFLOOR_BASE),
            decay_periods=DECAY_BOUNDARY_PERIODS,
        ),
        AdversarialCorpusCaseV2(
            "v2-leakage-decoy",
            "leakage_decoy",
            SESSION_ALPHA,
            "cross scope leak decoy probe unrelated session secret",
            ("v2-src-leak-target",),
            ("v2-src-leak-target", "v2-src-leak-decoy"),
            ("v2-src-leak-target",),
            True,
            True,
            ("v2-src-leak-target",),
            ("v2-src-leak-target",),
            17,
            BUDGET_TOKENS_V2,
            leakage_free=False,
        ),
        AdversarialCorpusCaseV2(
            "v2-cross-session-decoy-alpha",
            "cross_session_decoy_reuse",
            SESSION_BETA,
            "resume durable task lease restore procedure real experience",
            ("v2-src-reuse-alpha",),
            ("v2-src-reuse-alpha",),
            ("v2-src-reuse-alpha",),
            True,
            True,
            ("v2-src-reuse-alpha",),
            ("v2-src-reuse-alpha",),
            15,
            BUDGET_TOKENS_V2,
            reused_experience_ids=("v2-exp-real",),
            relevant_experience_ids=("v2-exp-real",),
        ),
        AdversarialCorpusCaseV2(
            "v2-cross-session-decoy-beta",
            "cross_session_decoy_reuse",
            SESSION_BETA,
            "resume durable task lease restore procedure decoy experience",
            ("v2-src-reuse-beta",),
            ("v2-src-reuse-beta",),
            ("v2-src-reuse-beta",),
            True,
            True,
            ("v2-src-reuse-beta",),
            ("v2-src-reuse-beta",),
            15,
            BUDGET_TOKENS_V2,
            reused_experience_ids=("v2-exp-decoy",),
            relevant_experience_ids=("v2-exp-real",),
        ),
    )
    ids = [case.case_id for case in cases]
    if len(ids) != len(set(ids)):
        raise MemoryQualityCorpusError("duplicate_corpus_case_id")
    return cases


ADVERSARIAL_CORPUS_V2 = build_adversarial_corpus_v2()

EXPECTED_V2: Mapping[str, Mapping[str, Any]] = {
    "v2-temporal-inversion-early": {"temporal_order": 1.0},
    "v2-temporal-inversion-late": {"temporal_order": 0.0},
    "v2-duplicate-attribution": {"attribution_precision": 0.5},
    "v2-near-duplicate-query-primary": {"recall": 1.0, "attribution_precision": 1.0},
    "v2-near-duplicate-query-variant": {"recall": 1.0, "attribution_precision": 1.0},
    "v2-budget-edge-exact": {"budget_respected": True},
    "v2-budget-edge-overrun": {"budget_respected": False},
    "v2-conflict-provenance": {"conflict_resolution": 0.0, "provenance_verified": True},
    "v2-decay-floor-boundary": {"compaction_retention": 0.5, "decay_floor_boundary_respected": True},
    "v2-leakage-decoy": {"leakage_free": False, "attribution_precision": 1.0},
    "v2-cross-session-decoy-alpha": {"experience_reuse_recall": 1.0},
    "v2-cross-session-decoy-beta": {"experience_reuse_recall": 0.0},
}


def project_decay_strengths(base_strengths: Sequence[float], periods: int) -> Tuple[float, ...]:
    """Deterministic exponential decay clamped at the Memory decay floor."""
    floor = float(Memory.DECAY_FLOOR)
    factor = 0.5 ** int(periods)
    return tuple(max(floor, float(base) * factor) for base in base_strengths)


def _canonical_json(mapping: Mapping[str, Any]) -> str:
    return json.dumps(mapping, sort_keys=True, separators=(",", ":"))


def _metrics_dict(metrics: Any) -> Dict[str, Any]:
    return {
        "recall_mean": metrics.recall_mean,
        "attribution_precision_mean": metrics.attribution_precision_mean,
        "conflict_resolution_rate": metrics.conflict_resolution_rate,
        "temporal_order_rate": metrics.temporal_order_rate,
        "compaction_retention_mean": metrics.compaction_retention_mean,
        "budget_compliance_rate": metrics.budget_compliance_rate,
        "leakage_free_rate": metrics.leakage_free_rate,
        "experience_reuse_recall_mean": metrics.experience_reuse_recall_mean,
        "quality_score": metrics.quality_score,
        "cases": metrics.cases,
    }


def _validate_adapter(adapter: Any) -> None:
    record_trajectory = getattr(adapter, "record_trajectory", None)
    evaluate_sessions = getattr(adapter, "evaluate_sessions", None)
    if not callable(record_trajectory) or not callable(evaluate_sessions):
        raise MemoryQualityCorpusError("adapter_contract_invalid")


def _roundtrip_evaluator_payload(case: AdversarialCorpusCaseV2) -> Dict[str, Any]:
    """Rebuild the canonical payload purely from evaluator-bound inputs.

    Gap wrapper: the core ``MemoryQualityCase`` carries no provenance binding,
    so this module proves fixture-to-evaluator fidelity by regenerating the
    payload from the trajectory-step projection and comparing digests.
    """
    step = case.to_trajectory_step()
    return {
        "attributed_source_ids": list(step.attributed_source_ids),
        "budget_tokens": int(step.budget_tokens),
        "case_id": step.step_id,
        "category": case.category,
        "conflict_resolution_correct": bool(step.conflict_resolution_correct),
        "decay_base_strengths": list(case.decay_base_strengths),
        "decay_periods": int(case.decay_periods),
        "leakage_free": bool(step.leakage_free),
        "query": step.query,
        "relevant_experience_ids": list(step.relevant_experience_ids),
        "relevant_source_ids": list(step.relevant_source_ids),
        "required_after_compaction_ids": list(step.required_after_compaction_ids),
        "retained_after_compaction_ids": list(step.retained_after_compaction_ids),
        "reused_experience_ids": list(step.reused_experience_ids),
        "selected_source_ids": list(step.selected_source_ids),
        "session_id": case.session_id,
        "temporal_order_correct": bool(step.temporal_order_correct),
        "used_tokens": int(step.used_tokens),
    }


def verify_case_provenance(case: AdversarialCorpusCaseV2) -> bool:
    """True when the pinned digest matches inputs rebuilt from evaluator fields."""
    digest = case.provenance_digest()
    if not digest.startswith("sha256:") or len(digest) != 71:
        return False
    rebuilt = _roundtrip_evaluator_payload(case)
    rebuilt_digest = "sha256:" + hashlib.sha256(_canonical_json(rebuilt).encode("utf-8")).hexdigest()
    return digest == rebuilt_digest


def _check_decay_boundary(case: AdversarialCorpusCaseV2) -> bool:
    """At-floor record survives exactly on the floor; sub-floor raw decay is evicted."""
    projected = project_decay_strengths(case.decay_base_strengths, case.decay_periods)
    if len(projected) != 2 or len(case.decay_base_strengths) != 2:
        raise MemoryQualityCorpusError("decay_fixture_invalid")
    factor = 0.5 ** int(case.decay_periods)
    raw_at_floor = float(case.decay_base_strengths[0]) * factor
    raw_subfloor = float(case.decay_base_strengths[1]) * factor
    floor = float(Memory.DECAY_FLOOR)
    retained = set(case.retained_after_compaction_ids)
    required = set(case.required_after_compaction_ids)
    floor_id = case.required_after_compaction_ids[0]
    subfloor_id = case.required_after_compaction_ids[1]
    return (
        raw_at_floor == floor
        and projected[0] == floor
        and raw_subfloor < floor
        and projected[1] == floor
        and floor_id in required
        and floor_id in retained
        and subfloor_id in required
        and subfloor_id not in retained
    )


def evaluate_corpus_v2(adapter_factory: Callable[[], Any]) -> Dict[str, Any]:
    """Record every corpus case through the adapter and score it with the core evaluator.

    The adapter factory must return an object exposing ``record_trajectory``
    (per-session) and ``evaluate_sessions``; the durable quality adapter is the
    reference implementation. All outputs derive from pinned constants: no wall
    clock, no randomness, byte-stable report digest across runs and machines.
    """
    if not callable(adapter_factory):
        raise MemoryQualityCorpusError("adapter_factory_invalid")
    adapter = adapter_factory()
    _validate_adapter(adapter)

    sessions = []
    for case in ADVERSARIAL_CORPUS_V2:
        if case.session_id not in sessions:
            sessions.append(case.session_id)
    for session_id in sessions:
        steps = tuple(step.to_trajectory_step() for step in ADVERSARIAL_CORPUS_V2 if step.session_id == session_id)
        adapter.record_trajectory(session_id, steps)
    multi_report = adapter.evaluate_sessions(tuple(sessions))

    evaluator = MemoryQualityEvaluator()
    per_case: Dict[str, Any] = {}
    inflation_detected = False
    for case in ADVERSARIAL_CORPUS_V2:
        outcome = evaluator.evaluate_case(case.to_memory_quality_case())
        raw_attributed = case.attributed_source_ids
        if len(raw_attributed) != len(set(raw_attributed)) and outcome.attribution_precision == 1.0:
            inflation_detected = True
        provenance_verified = verify_case_provenance(case)
        decay_ok = _check_decay_boundary(case) if case.category == "decay_floor_boundary" else True
        actual = {
            "recall": outcome.recall,
            "attribution_precision": outcome.attribution_precision,
            "conflict_resolution": outcome.conflict_resolution,
            "temporal_order": outcome.temporal_order,
            "compaction_retention": outcome.compaction_retention,
            "budget_respected": outcome.budget_respected,
            "leakage_free": outcome.leakage_free,
            "experience_reuse_recall": outcome.experience_reuse_recall,
            "provenance_verified": provenance_verified,
            "decay_floor_boundary_respected": decay_ok,
        }
        violations = []
        for key, expected_value in EXPECTED_V2.get(case.case_id, {}).items():
            if actual[key] != expected_value:
                violations.append("%s!=%r" % (key, expected_value))
        per_case[case.case_id] = {
            "category": case.category,
            "session_id": case.session_id,
            "recall": outcome.recall,
            "attribution_precision": outcome.attribution_precision,
            "conflict_resolution": outcome.conflict_resolution,
            "temporal_order": outcome.temporal_order,
            "compaction_retention": outcome.compaction_retention,
            "budget_respected": outcome.budget_respected,
            "leakage_free": outcome.leakage_free,
            "experience_reuse_recall": outcome.experience_reuse_recall,
            "provenance_verified": provenance_verified,
            "decay_floor_boundary_respected": decay_ok,
            "expectation_violations": violations,
        }

    quality_cases = tuple(case.to_memory_quality_case() for case in ADVERSARIAL_CORPUS_V2)
    aggregate = _metrics_dict(evaluator.metrics(quality_cases))
    digest_payload = {
        "aggregate": aggregate,
        "case_ids": [case.case_id for case in ADVERSARIAL_CORPUS_V2],
        "corpus_size": len(ADVERSARIAL_CORPUS_V2),
        "duplicate_attribution_inflation_detected": inflation_detected,
        "multi_session_total_cases": multi_report.total_cases,
        "per_case": per_case,
        "session_ids": sessions,
    }
    report = dict(digest_payload)
    report["schema_version"] = CORPUS_SCHEMA_VERSION
    report["claim_boundary"] = "deterministic_adversarial_fixture_corpus_local_evaluator_only_not_external_model_benchmark"
    report["categories"] = {category: sum(1 for case in ADVERSARIAL_CORPUS_V2 if case.category == category) for category in sorted({case.category for case in ADVERSARIAL_CORPUS_V2})}
    report["report_digest"] = "sha256:" + hashlib.sha256(_canonical_json(digest_payload).encode("utf-8")).hexdigest()
    return report


__all__ = [
    "ADVERSARIAL_CORPUS_V2",
    "AdversarialCorpusCaseV2",
    "CORPUS_SCHEMA_VERSION",
    "EXPECTED_V2",
    "MemoryQualityCorpusError",
    "build_adversarial_corpus_v2",
    "evaluate_corpus_v2",
    "project_decay_strengths",
    "verify_case_provenance",
]
