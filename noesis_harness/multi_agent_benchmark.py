"""Deterministic local multi-agent workload runner and durable aggregation."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import tempfile
import time
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from .coordination import Actions
from .nextgen import _ManagedConnection
from .parallel_agent import AgentLane, SafeParallelExecutor
from .work_product_benchmark import WorkProductBenchmarkEvaluator, WorkProductMetrics, WorkProductOutcome


class MultiAgentBenchmarkError(ValueError):
    pass


@dataclass(frozen=True)
class WorkloadCase:
    case_id: str
    agent_id: str
    task_id: str
    expected_output: str
    fail_first: bool = False
    reviewer_time_seconds: float = 0.0
    crash_point: str = "before_write"

    def __post_init__(self) -> None:
        if not self.case_id or not self.agent_id or not self.task_id:
            raise MultiAgentBenchmarkError("workload_identity_required")
        if not self.expected_output:
            raise MultiAgentBenchmarkError("expected_output_required")
        if self.reviewer_time_seconds < 0:
            raise MultiAgentBenchmarkError("reviewer_time_invalid")
        if self.crash_point not in {"before_write", "after_write", "after_read"}:
            raise MultiAgentBenchmarkError("crash_point_invalid")


@dataclass(frozen=True)
class WorkloadRun:
    run_id: str
    results: tuple[Mapping[str, Any], ...]
    metrics: WorkProductMetrics


@dataclass(frozen=True)
class RepeatedWorkloadReport:
    runs: int
    cases: int
    correctness_mean: float
    correctness_p50: float
    correctness_p95: float
    recovery_mean: float
    retry_mean: float
    leakage_free_mean: float
    reviewer_time_mean: float


def _percentile(values: Sequence[float], percentile: float) -> float:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        raise MultiAgentBenchmarkError("percentile_values_required")
    index = min(len(ordered) - 1, max(0, int((percentile / 100.0) * (len(ordered) - 1))))
    return ordered[index]


class DurableWorkloadAggregator:
    """SQLite/WAL aggregation with duplicate identity and content conflict checks."""
    def __init__(self, db_path: str):
        self.db_path = db_path
        with self._connection() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("CREATE TABLE IF NOT EXISTS workload_results (run_id TEXT NOT NULL, task_id TEXT NOT NULL, record TEXT NOT NULL, digest TEXT NOT NULL, created_at REAL NOT NULL, PRIMARY KEY(run_id, task_id))")

    def _connection(self):
        db = sqlite3.connect(self.db_path, timeout=10, factory=_ManagedConnection)
        db.row_factory = sqlite3.Row
        return db

    def put(self, run_id: str, task_id: str, record: Mapping[str, Any]) -> Mapping[str, Any]:
        encoded = json.dumps(dict(record), sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
        with self._connection() as db:
            row = db.execute("SELECT record, digest FROM workload_results WHERE run_id=? AND task_id=?", (run_id, task_id)).fetchone()
            if row is not None:
                if row["digest"] != digest:
                    raise MultiAgentBenchmarkError("workload_result_conflict")
                return json.loads(row["record"])
            db.execute("INSERT INTO workload_results VALUES(?,?,?,?,?)", (run_id, task_id, encoded, digest, time.time()))
        return dict(record)

    def list_run(self, run_id: str) -> tuple[Mapping[str, Any], ...]:
        with self._connection() as db:
            rows = db.execute("SELECT record FROM workload_results WHERE run_id=? ORDER BY task_id", (run_id,)).fetchall()
        return tuple(json.loads(row["record"]) for row in rows)


class MultiAgentWorkloadRunner:
    """Run approved deterministic callbacks in parallel; no model/tool execution."""
    def __init__(self, workspace_root: str, aggregation_db: str, *, max_concurrency: int = 2):
        self.workspace_root = Path(workspace_root).expanduser().resolve()
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        self.aggregator = DurableWorkloadAggregator(aggregation_db)
        self.max_concurrency = max_concurrency

    def run(self, cases: Sequence[WorkloadCase], *, run_id: str, retry_limit: int = 1) -> WorkloadRun:
        if not run_id:
            raise MultiAgentBenchmarkError("run_id_required")
        rows = tuple(cases)
        if not rows:
            raise MultiAgentBenchmarkError("workload_cases_required")
        if len({case.task_id for case in rows}) != len(rows) or len({case.agent_id for case in rows}) != len(rows):
            raise MultiAgentBenchmarkError("workload_identity_collision")
        existing = self.aggregator.list_run(run_id)
        if existing:
            if {row.get("task_id") for row in existing} != {case.task_id for case in rows}:
                raise MultiAgentBenchmarkError("workload_result_set_conflict")
            outcomes = tuple(WorkProductOutcome(row["case_id"], row["correct"], row["delivered"], row["leakage_free"], row["recovered"], row["attempts"], row["reviewer_time_seconds"], row["review_approved"], row["committed"]) for row in existing)
            return WorkloadRun(run_id, existing, WorkProductBenchmarkEvaluator().evaluate(outcomes))
        action_db = self.workspace_root / ("actions-" + run_id + ".db")
        actions = Actions(str(action_db))
        for case in rows:
            actions.create(case.case_id, action_id=case.task_id)
        attempts: dict[str, int] = {case.task_id: 0 for case in rows}
        crashed: set[str] = set()
        leakage_free: dict[str, bool] = {case.task_id: True for case in rows}

        def callback(ctx):
            attempts[ctx.task_id] += 1
            case = next(item for item in rows if item.task_id == ctx.task_id)
            try:
                ctx.path("../agent-other/secret.txt")
                leakage_free[ctx.task_id] = False
            except Exception:
                pass
            point = case.crash_point if case.fail_first else ""
            if point == "before_write" and ctx.task_id not in crashed:
                crashed.add(ctx.task_id)
                raise RuntimeError("injected_worker_crash:before_write")
            target = ctx.path("result.json")
            target.write_text(json.dumps({"case_id": case.case_id, "agent_id": case.agent_id, "output": case.expected_output}, sort_keys=True), encoding="utf-8")
            if point == "after_write" and ctx.task_id not in crashed:
                crashed.add(ctx.task_id)
                raise RuntimeError("injected_worker_crash:after_write")
            output = target.read_text(encoding="utf-8")
            if point == "after_read" and ctx.task_id not in crashed:
                crashed.add(ctx.task_id)
                raise RuntimeError("injected_worker_crash:after_read")
            return output

        lanes = [AgentLane(case.agent_id, case.task_id, case.agent_id, ("read", "workspace_write", "provenance"), True, True) for case in rows]
        executor = SafeParallelExecutor(str(self.workspace_root), max_concurrency=self.max_concurrency)
        execution = executor.execute(lanes, callback, session_id=run_id, approval=True, action_store=actions, retry_limit=retry_limit)
        output_rows = []
        for result, case in zip(sorted(execution, key=lambda item: item.task_id), sorted(rows, key=lambda item: item.task_id)):
            correct = result.status == "passed" and result.output is not None and case.expected_output in str(result.output)
            record = {"run_id": run_id, "case_id": case.case_id, "task_id": case.task_id, "agent_id": case.agent_id, "status": result.status, "attempts": result.attempts, "recovered": result.recovered, "correct": correct, "delivered": result.status == "passed", "leakage_free": leakage_free[case.task_id], "reviewer_time_seconds": case.reviewer_time_seconds, "review_approved": result.status == "passed", "committed": result.status == "passed", "error": result.error}
            output_rows.append(self.aggregator.put(run_id, case.task_id, record))
        outcomes = tuple(WorkProductOutcome(row["case_id"], row["correct"], row["delivered"], row["leakage_free"], row["recovered"], row["attempts"], row["reviewer_time_seconds"], row["review_approved"], row["committed"]) for row in output_rows)
        return WorkloadRun(run_id, tuple(output_rows), WorkProductBenchmarkEvaluator().evaluate(outcomes))

    def run_repeated(self, cases: Sequence[WorkloadCase], *, run_prefix: str, repetitions: int, retry_limit: int = 1) -> RepeatedWorkloadReport:
        if not run_prefix or int(repetitions) < 1 or int(repetitions) > 100:
            raise MultiAgentBenchmarkError("repetition_count_invalid")
        runs = tuple(self.run(cases, run_id=f"{run_prefix}-{index:03d}", retry_limit=retry_limit) for index in range(1, int(repetitions) + 1))
        correctness = tuple(run.metrics.correctness_rate for run in runs)
        recovery = tuple(run.metrics.recovery_rate for run in runs)
        retry = tuple(run.metrics.retry_rate for run in runs)
        leakage = tuple(run.metrics.leakage_free_rate for run in runs)
        reviewer = tuple(run.metrics.mean_reviewer_time_seconds for run in runs)
        return RepeatedWorkloadReport(len(runs), sum(run.metrics.cases for run in runs), statistics.fmean(correctness), _percentile(correctness, 50), _percentile(correctness, 95), statistics.fmean(recovery), statistics.fmean(retry), statistics.fmean(leakage), statistics.fmean(reviewer))


__all__ = ["MultiAgentBenchmarkError", "WorkloadCase", "WorkloadRun", "RepeatedWorkloadReport", "DurableWorkloadAggregator", "MultiAgentWorkloadRunner"]
