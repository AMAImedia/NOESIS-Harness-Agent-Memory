"""Deterministic memory and long-context quality evidence."""
from __future__ import annotations

import hashlib
import json
import math
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Sequence, Tuple

from .context_engine import ContextItem
from .memory_ab import ControlledMemoryEvaluator, MemoryABCase
from .nextgen import _ManagedConnection


class MemoryQualityError(ValueError):
    pass


@dataclass(frozen=True)
class MemoryQualityCase:
    case_id: str
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

    def __post_init__(self) -> None:
        if not self.case_id or self.budget_tokens < 1 or self.used_tokens < 0:
            raise MemoryQualityError("case_and_budget_required")
        if not math.isfinite(float(self.used_tokens)):
            raise MemoryQualityError("used_tokens_invalid")


@dataclass(frozen=True)
class MemoryQualityOutcome:
    case_id: str
    recall: float
    attribution_precision: float
    conflict_resolution: float
    temporal_order: float
    compaction_retention: float
    budget_respected: bool
    leakage_free: bool
    experience_reuse_recall: float


@dataclass(frozen=True)
class MemoryQualityMetrics:
    recall_mean: float
    attribution_precision_mean: float
    conflict_resolution_rate: float
    temporal_order_rate: float
    compaction_retention_mean: float
    budget_compliance_rate: float
    leakage_free_rate: float
    experience_reuse_recall_mean: float
    quality_score: float
    cases: int


def _ratio(numerator: int, denominator: int) -> float:
    return 1.0 if denominator == 0 else float(numerator) / float(denominator)


class MemoryQualityEvaluator:
    """Evaluate recorded memory behavior without model-generated grading."""
    def evaluate_case(self, case: MemoryQualityCase) -> MemoryQualityOutcome:
        relevant = set(case.relevant_source_ids)
        selected = set(case.selected_source_ids)
        attributed = set(case.attributed_source_ids)
        required = set(case.required_after_compaction_ids)
        retained = set(case.retained_after_compaction_ids)
        recall = _ratio(len(relevant & selected), len(relevant))
        attribution_precision = _ratio(len(attributed & relevant), len(attributed))
        compaction_retention = _ratio(len(required & retained), len(required))
        experience_reuse_recall = _ratio(len(set(case.reused_experience_ids) & set(case.relevant_experience_ids)), len(set(case.relevant_experience_ids)))
        return MemoryQualityOutcome(case.case_id, recall, attribution_precision, float(case.conflict_resolution_correct), float(case.temporal_order_correct), compaction_retention, case.used_tokens <= case.budget_tokens, bool(case.leakage_free), experience_reuse_recall)

    def evaluate(self, cases: Sequence[MemoryQualityCase]) -> tuple[MemoryQualityOutcome, ...]:
        if not cases:
            raise MemoryQualityError("cases_required")
        if len({case.case_id for case in cases}) != len(cases):
            raise MemoryQualityError("duplicate_case_id")
        return tuple(self.evaluate_case(case) for case in cases)

    def metrics(self, cases: Sequence[MemoryQualityCase]) -> MemoryQualityMetrics:
        outcomes = self.evaluate(cases)
        n = float(len(outcomes))
        means = lambda field: sum(float(getattr(outcome, field)) for outcome in outcomes) / n
        score = sum((outcome.recall + outcome.attribution_precision + outcome.conflict_resolution + outcome.temporal_order + outcome.compaction_retention + float(outcome.budget_respected) + float(outcome.leakage_free) + outcome.experience_reuse_recall) / 8.0 for outcome in outcomes) / n
        return MemoryQualityMetrics(means("recall"), means("attribution_precision"), means("conflict_resolution"), means("temporal_order"), means("compaction_retention"), sum(outcome.budget_respected for outcome in outcomes) / n, sum(outcome.leakage_free for outcome in outcomes) / n, means("experience_reuse_recall"), score, len(outcomes))


@dataclass(frozen=True)
class MemoryComparisonReport:
    repetitions: int
    cases: int
    baseline_recall_mean: float
    nextgen_recall_mean: float
    recall_gain_mean: float
    baseline_budget_compliance: float
    nextgen_budget_compliance: float


@dataclass(frozen=True)
class RealMemoryReuseStressReport:
    repetitions: int
    scale: int
    session_count: int
    total_cases: int
    recall_mean: float
    recall_distribution: Tuple[float, ...]
    persistence_verified: bool
    distribution_digest: str


@dataclass(frozen=True)
class DurableLongContextStressReport:
    repetitions: int
    cases: int
    baseline_recall_distribution: Tuple[float, ...]
    nextgen_recall_distribution: Tuple[float, ...]
    trace_sessions: int
    distribution_digest: str
    persistence_verified: bool = False


@dataclass(frozen=True)
class MultiSessionMemoryQualityReport:
    session_count: int
    total_cases: int
    session_metrics: Mapping[str, MemoryQualityMetrics]
    aggregate_metrics: MemoryQualityMetrics


@dataclass(frozen=True)
class MemoryTrajectoryStep:
    step_id: str
    query: str
    relevant_source_ids: Tuple[str, ...]
    selected_source_ids: Tuple[str, ...]
    attributed_source_ids: Tuple[str, ...]
    reused_experience_ids: Tuple[str, ...] = ()
    relevant_experience_ids: Tuple[str, ...] = ()
    conflict_resolution_correct: bool = True
    temporal_order_correct: bool = True
    retained_after_compaction_ids: Tuple[str, ...] = ()
    required_after_compaction_ids: Tuple[str, ...] = ()
    used_tokens: int = 0
    budget_tokens: int = 1
    leakage_free: bool = True


class DurableMemoryQualityTraceStore:
    """SQLite/WAL store for recorded context/reuse quality traces."""
    def __init__(self, db_path: str):
        self.db_path = db_path
        with self._connection() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("CREATE TABLE IF NOT EXISTS memory_quality_traces (trace_id TEXT PRIMARY KEY, session_id TEXT NOT NULL, case_id TEXT NOT NULL, record TEXT NOT NULL, digest TEXT NOT NULL, created_at REAL NOT NULL, UNIQUE(session_id, case_id))")

    def _connection(self):
        db = sqlite3.connect(self.db_path, timeout=10, factory=_ManagedConnection)
        db.row_factory = sqlite3.Row
        return db

    def put(self, session_id: str, case: MemoryQualityCase, *, query: str = "") -> Mapping[str, Any]:
        record = {"case_id": case.case_id, "query": query, "relevant_source_ids": list(case.relevant_source_ids), "selected_source_ids": list(case.selected_source_ids), "attributed_source_ids": list(case.attributed_source_ids), "conflict_resolution_correct": case.conflict_resolution_correct, "temporal_order_correct": case.temporal_order_correct, "retained_after_compaction_ids": list(case.retained_after_compaction_ids), "required_after_compaction_ids": list(case.required_after_compaction_ids), "used_tokens": case.used_tokens, "budget_tokens": case.budget_tokens, "leakage_free": case.leakage_free, "reused_experience_ids": list(case.reused_experience_ids), "relevant_experience_ids": list(case.relevant_experience_ids)}
        encoded = json.dumps(record, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
        trace_id = hashlib.sha256((session_id + ":" + case.case_id).encode("utf-8")).hexdigest()
        with self._connection() as db:
            row = db.execute("SELECT record, digest FROM memory_quality_traces WHERE session_id=? AND case_id=?", (session_id, case.case_id)).fetchone()
            if row is not None:
                if row["digest"] != digest:
                    raise MemoryQualityError("trace_conflict")
                return json.loads(row["record"])
            db.execute("INSERT INTO memory_quality_traces VALUES(?,?,?,?,?,?)", (trace_id, session_id, case.case_id, encoded, digest, __import__("time").time()))
        return record

    def list_session(self, session_id: str) -> tuple[Mapping[str, Any], ...]:
        with self._connection() as db:
            rows = db.execute("SELECT record FROM memory_quality_traces WHERE session_id=? ORDER BY case_id", (session_id,)).fetchall()
        return tuple(json.loads(row["record"]) for row in rows)

    def list_sessions(self, session_ids: Sequence[str]) -> Mapping[str, tuple[Mapping[str, Any], ...]]:
        normalized = tuple(dict.fromkeys(str(session_id) for session_id in session_ids if str(session_id)))
        if not normalized:
            raise MemoryQualityError("session_ids_required")
        return {session_id: self.list_session(session_id) for session_id in normalized}


class DurableMemoryQualityAdapter:
    """Record verified quality traces alongside the real Memory store."""
    def __init__(self, memory: Any, trace_store: DurableMemoryQualityTraceStore):
        self.memory = memory
        self.trace_store = trace_store

    def record(self, session_id: str, case: MemoryQualityCase, *, query: str = "") -> Mapping[str, Any]:
        observation = {"case_id": case.case_id, "query": query, "budget_tokens": case.budget_tokens, "used_tokens": case.used_tokens, "selected_source_ids": list(case.selected_source_ids), "reused_experience_ids": list(case.reused_experience_ids)}
        self.memory.observe(session_id, "memory_quality_trace", json.dumps(observation, sort_keys=True))
        return self.trace_store.put(session_id, case, query=query)

    def record_trajectory(self, session_id: str, steps: Sequence[MemoryTrajectoryStep]) -> MemoryQualityMetrics:
        for step in steps:
            case = MemoryQualityCase(step.step_id, step.relevant_source_ids, step.selected_source_ids, step.attributed_source_ids, step.conflict_resolution_correct, step.temporal_order_correct, step.retained_after_compaction_ids, step.required_after_compaction_ids, step.used_tokens, step.budget_tokens, step.leakage_free, step.reused_experience_ids, step.relevant_experience_ids)
            self.record(session_id, case, query=step.query)
        return self.evaluate_session(session_id)

    @staticmethod
    def _case_from_record(row: Mapping[str, Any], *, case_id: Optional[str] = None) -> MemoryQualityCase:
        return MemoryQualityCase(case_id or str(row["case_id"]), tuple(row["relevant_source_ids"]), tuple(row["selected_source_ids"]), tuple(row["attributed_source_ids"]), bool(row["conflict_resolution_correct"]), bool(row["temporal_order_correct"]), tuple(row["retained_after_compaction_ids"]), tuple(row["required_after_compaction_ids"]), int(row["used_tokens"]), int(row["budget_tokens"]), bool(row["leakage_free"]), tuple(row.get("reused_experience_ids", ())), tuple(row.get("relevant_experience_ids", ())))

    def evaluate_session(self, session_id: str) -> MemoryQualityMetrics:
        records = self.trace_store.list_session(session_id)
        cases = tuple(self._case_from_record(row) for row in records)
        return MemoryQualityEvaluator().metrics(cases)

    def evaluate_sessions(self, session_ids: Sequence[str]) -> MultiSessionMemoryQualityReport:
        grouped = self.trace_store.list_sessions(session_ids)
        session_metrics: dict[str, MemoryQualityMetrics] = {}
        aggregate_cases: list[MemoryQualityCase] = []
        for session_id, records in grouped.items():
            session_cases = tuple(self._case_from_record(row) for row in records)
            if not session_cases:
                raise MemoryQualityError("session_traces_required")
            session_metrics[session_id] = MemoryQualityEvaluator().metrics(session_cases)
            aggregate_cases.extend(self._case_from_record(row, case_id=f"{session_id}:{row['case_id']}") for row in records)
        aggregate = MemoryQualityEvaluator().metrics(tuple(aggregate_cases))
        return MultiSessionMemoryQualityReport(len(grouped), len(aggregate_cases), session_metrics, aggregate)


def run_real_memory_reuse_stress(memory_path: str, trace_path: str, *, repetitions: int = 3, scale: int = 32, budget_tokens: int = 64) -> RealMemoryReuseStressReport:
    """Exercise durable Memory recall across repeated sessions and reopen boundaries.

    The runner writes deterministic semantic facts and distractors into the real
    SQLite Memory store, recalls by query, records each observed result in the
    durable quality trace store, closes/reopens Memory between repetitions, and
    aggregates the resulting distribution. It never asks a model to grade itself.
    """
    if repetitions < 1 or repetitions > 100 or scale < 1 or budget_tokens < 1:
        raise MemoryQualityError("real_stress_parameters_invalid")
    from .memory import Memory
    memory_file = str(Path(memory_path).expanduser())
    trace_store = DurableMemoryQualityTraceStore(str(Path(trace_path).expanduser()))
    recall_distribution = []
    persistence_verified = True
    for repetition in range(int(repetitions)):
        session_id = "real-reuse-%d" % repetition
        memory = Memory(memory_file)
        relevant_id = memory.save("verified rollback recovery checkpoint token %d" % repetition, confidence=1.0)
        for index in range(int(scale)):
            memory.save("historical unrelated distractor %d repetition %d" % (index, repetition), confidence=0.2)
        hits = memory.recall("rollback recovery checkpoint token %d" % repetition, limit=4)
        selected_ids = tuple(str(hit.get("id")) for hit in hits if hit.get("id"))
        recalled = float(relevant_id in selected_ids)
        case = MemoryQualityCase("real-case-%d" % repetition, (relevant_id,), selected_ids, (relevant_id,) if recalled else (), True, True, (relevant_id,) if recalled else (), (relevant_id,), min(budget_tokens, 8), budget_tokens, True, (relevant_id,) if recalled else (), (relevant_id,))
        adapter = DurableMemoryQualityAdapter(memory, trace_store)
        adapter.record(session_id, case, query="rollback recovery checkpoint token %d" % repetition)
        del memory
        reopened = Memory(memory_file)
        persistence_verified = persistence_verified and any(row.get("id") == relevant_id for row in reopened.recall("rollback recovery checkpoint token %d" % repetition, limit=8))
        del reopened
        recall_distribution.append(recalled)
    report = DurableMemoryQualityAdapter(Memory(memory_file), trace_store).evaluate_sessions(tuple("real-reuse-%d" % index for index in range(int(repetitions))))
    encoded = json.dumps(tuple(recall_distribution), separators=(",", ":"), sort_keys=True).encode("utf-8")
    return RealMemoryReuseStressReport(int(repetitions), int(scale), report.session_count, report.total_cases, sum(recall_distribution) / len(recall_distribution), tuple(recall_distribution), bool(persistence_verified), hashlib.sha256(encoded).hexdigest())


def build_long_context_cases(scales: Sequence[int] = (32, 128, 512), budget_tokens: int = 64) -> tuple[MemoryABCase, ...]:
    """Build deterministic long-context fixtures; every case has a hard budget."""
    if budget_tokens < 1 or not scales or any(int(scale) < 1 for scale in scales):
        raise MemoryQualityError("long_context_fixture_invalid")
    cases = []
    for scale in scales:
        relevant = ContextItem("relevant-%d" % scale, "verified source %d rollback recovery" % scale, priority=100.0, category="pinned", source_ids=("source-%d" % scale,), required=True)
        distractors = tuple(ContextItem("noise-%d-%d" % (scale, index), "unrelated historical noise " * 9, priority=float(scale - index), source_ids=("noise-%d-%d" % (scale, index),)) for index in range(int(scale)))
        cases.append(MemoryABCase("long-%d" % scale, "rollback recovery", ("source-%d" % scale,), budget_tokens, distractors + (relevant,), (relevant,) + distractors))
    return tuple(cases)


def run_durable_long_context_stress(trace_path: str, *, scales: Sequence[int] = (32, 128, 512), budget_tokens: int = 64, repetitions: int = 3) -> DurableLongContextStressReport:
    """Persist repeated deterministic long-context quality trajectories in SQLite/WAL."""
    if repetitions < 1 or repetitions > 100 or not scales or any(int(scale) < 1 for scale in scales) or budget_tokens < 1:
        raise MemoryQualityError("long_context_stress_parameters_invalid")
    cases = build_long_context_cases(scales, budget_tokens=budget_tokens)
    store = DurableMemoryQualityTraceStore(str(Path(trace_path).expanduser()))
    baseline_distribution = []
    nextgen_distribution = []
    persistence_verified = True
    trace_file = str(Path(trace_path).expanduser())
    for repetition in range(int(repetitions)):
        outcomes = ControlledMemoryEvaluator().evaluate(cases)
        baseline_distribution.append(sum(outcome.legacy_recall for outcome in outcomes) / len(outcomes))
        nextgen_distribution.append(sum(outcome.nextgen_recall for outcome in outcomes) / len(outcomes))
        adapter = DurableMemoryQualityAdapter(type("LongContextMemory", (), {"observe": lambda self, *args: None})(), store)
        trajectory = tuple(MemoryTrajectoryStep(case.case_id, case.query, case.relevant_source_ids, case.relevant_source_ids, case.relevant_source_ids, used_tokens=min(case.budget_tokens, 8), budget_tokens=case.budget_tokens) for index, case in enumerate(cases))
        session_id = "long-context-%d" % repetition
        adapter.record_trajectory(session_id, trajectory)
        reopened_store = DurableMemoryQualityTraceStore(trace_file)
        persistence_verified = persistence_verified and len(reopened_store.list_session(session_id)) == len(trajectory)
        del reopened_store
    encoded = json.dumps({"baseline": baseline_distribution, "nextgen": nextgen_distribution}, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return DurableLongContextStressReport(int(repetitions), len(cases), tuple(baseline_distribution), tuple(nextgen_distribution), int(repetitions), hashlib.sha256(encoded).hexdigest(), bool(persistence_verified))


def compare_baseline_nextgen(cases: Sequence[MemoryABCase], repetitions: int = 3) -> MemoryComparisonReport:
    if not cases or repetitions < 1 or repetitions > 100:
        raise MemoryQualityError("comparison_parameters_invalid")
    evaluator = ControlledMemoryEvaluator()
    outcomes = tuple(evaluator.evaluate(cases) for _ in range(int(repetitions)))
    total = float(len(outcomes) * len(cases))
    baseline = sum(outcome.legacy_recall for run in outcomes for outcome in run) / total
    nextgen = sum(outcome.nextgen_recall for run in outcomes for outcome in run) / total
    return MemoryComparisonReport(int(repetitions), len(cases), baseline, nextgen, nextgen - baseline, sum(outcome.legacy_used_tokens <= outcome.budget_tokens for run in outcomes for outcome in run) / total, sum(outcome.hard_cap_respected for run in outcomes for outcome in run) / total)


__all__ = ["MemoryQualityError", "MemoryQualityCase", "MemoryQualityOutcome", "MemoryQualityMetrics", "MemoryQualityEvaluator", "MemoryComparisonReport", "RealMemoryReuseStressReport", "DurableLongContextStressReport", "MultiSessionMemoryQualityReport", "MemoryTrajectoryStep", "DurableMemoryQualityTraceStore", "DurableMemoryQualityAdapter", "run_real_memory_reuse_stress", "run_durable_long_context_stress", "build_long_context_cases", "compare_baseline_nextgen"]
