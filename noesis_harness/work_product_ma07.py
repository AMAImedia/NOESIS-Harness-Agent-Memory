"""MA-07 local deterministic workload runner for the Gate 4 work-product loop.

Multiple parallel lanes execute through SafeParallelExecutor with an injected
first-attempt crash on selected tasks, bounded retry with durable action
reclaim, and idempotent SQLite/WAL result aggregation. Completed runs replay
identically from the store; any divergent duplicate aggregate write fails
closed.

Provenance: LoopX append-only event/idempotency patterns via
noesis_harness.event_store, deepseek-harness deterministic rubric workloads,
agent-teams bounded retry/reclaim semantics.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from .coordination import Actions
from .parallel_agent import AgentLane, AgentLaneContext, SafeParallelExecutor

WORKLOAD_SCHEMA = "noesis.workload-ma07.v1"


class WorkloadError(ValueError):
    pass


def _digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class LaneSpec:
    agent_id: str
    task_id: str
    crash_first_attempt: bool = False


@dataclass(frozen=True)
class WorkloadRunReport:
    run_id: str
    statuses: Tuple[str, ...]
    attempts: Tuple[int, ...]
    recovered_tasks: Tuple[str, ...]
    aggregate_digest: str


class WorkloadAggregateStore:
    """Durable SQLite/WAL aggregation of lane results with conflict rejection."""

    def __init__(self, path: str):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("CREATE TABLE IF NOT EXISTS workload_results (run_id TEXT NOT NULL, task_id TEXT NOT NULL, payload TEXT NOT NULL, PRIMARY KEY (run_id, task_id))")
            conn.commit()

    @contextmanager
    def _connection(self):
        conn = sqlite3.connect(self.path)
        try:
            yield conn
        finally:
            conn.close()

    @staticmethod
    def _payload(run_id: str, task_id: str, record: Mapping[str, Any]) -> str:
        return json.dumps({"run_id": str(run_id), "task_id": str(task_id), **dict(record)}, sort_keys=True, separators=(",", ":"))

    def put(self, run_id: str, task_id: str, record: Mapping[str, Any]) -> str:
        if not run_id or not task_id:
            raise WorkloadError("run_and_task_identity_required")
        payload = self._payload(run_id, task_id, record)
        with self._connection() as conn:
            row = conn.execute("SELECT payload FROM workload_results WHERE run_id = ? AND task_id = ?", (str(run_id), str(task_id))).fetchone()
            if row is not None:
                if row[0] != payload:
                    raise WorkloadError("workload_aggregate_conflict")
                return row[0]
            conn.execute("INSERT INTO workload_results(run_id, task_id, payload) VALUES (?, ?, ?)", (str(run_id), str(task_id), payload))
            conn.commit()
        return payload

    def project(self, run_id: str) -> Mapping[str, Any]:
        with self._connection() as conn:
            rows = conn.execute("SELECT task_id, payload FROM workload_results WHERE run_id = ? ORDER BY task_id", (str(run_id),)).fetchall()
        records = {}
        for task_id, payload in rows:
            data = json.loads(payload)
            records[str(task_id)] = {key: value for key, value in data.items() if key not in {"run_id", "task_id"}}
        return {"schema_version": WORKLOAD_SCHEMA, "run_id": str(run_id), "tasks": dict(records), "aggregate_digest": _digest(records)}

    def forget(self, run_id: str) -> None:
        with self._connection() as conn:
            conn.execute("DELETE FROM workload_results WHERE run_id = ?", (str(run_id),))
            conn.commit()


class WorkProductWorkloadRunner:
    """Deterministic multi-lane workload with injected first-attempt crashes."""

    MAX_LANES = 8

    def __init__(self, root: str, *, max_concurrency: int = 2):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.max_concurrency = max(1, min(int(max_concurrency), 8))
        self.aggregate = WorkloadAggregateStore(str(self.root / "workload-aggregate.db"))

    def _lane_callback(self, specs: Sequence[LaneSpec], run_id: str):
        crash_on_first = {spec.task_id for spec in specs if spec.crash_first_attempt}
        attempts: Dict[str, int] = {}

        def callback(ctx: AgentLaneContext) -> Mapping[str, Any]:
            count = attempts.get(ctx.task_id, 0) + 1
            attempts[ctx.task_id] = count
            if count == 1 and ctx.task_id in crash_on_first:
                raise RuntimeError("injected_first_attempt_crash")
            marker = ctx.path("artifact.txt")
            marker.write_text(json.dumps({"run_id": run_id, "task_id": ctx.task_id}), encoding="utf-8")
            return {"status": "completed", "output_digest": _digest({"run_id": run_id, "task_id": ctx.task_id})}

        return callback

    def run(self, run_id: str, specs: Sequence[LaneSpec], *, retry_limit: int = 1) -> WorkloadRunReport:
        if not run_id:
            raise WorkloadError("run_id_required")
        lanes_count = len(tuple(specs))
        if lanes_count < 2 or lanes_count > self.MAX_LANES:
            raise WorkloadError("lane_count_out_of_range")
        ids = [spec.task_id for spec in specs]
        agents = [spec.agent_id for spec in specs]
        if len(set(ids)) != len(ids) or len(set(agents)) != len(agents):
            raise WorkloadError("duplicate_lane_identity")
        actions = Actions(str(self.root / "workload-actions.db"))
        for spec in specs:
            try:
                actions.create(spec.task_id, action_id=spec.task_id)
            except Exception:
                pass  # idempotent re-create on completed-run replay
        executor = SafeParallelExecutor(str(self.root / "workspaces"), max_concurrency=self.max_concurrency)
        lanes = [AgentLane(spec.agent_id, spec.task_id, spec.agent_id, capabilities=("read", "workspace_write", "provenance"), approval_granted=True) for spec in specs]
        results = executor.execute(lanes, self._lane_callback(specs, run_id), session_id=run_id, approval=True, action_store=actions, retry_limit=max(0, min(int(retry_limit), 3)))
        for result in results:
            self.aggregate.put(run_id, result.task_id, {"status": result.status, "attempts": result.attempts, "recovered": result.recovered, "error": result.error})
        return self.report(run_id)

    def report(self, run_id: str) -> WorkloadRunReport:
        projection = self.aggregate.project(run_id)
        tasks = projection["tasks"]
        ordered_ids = sorted(tasks)
        return WorkloadRunReport(
            run_id=str(run_id),
            statuses=tuple(str(tasks[task]["status"]) for task in ordered_ids),
            attempts=tuple(int(tasks[task]["attempts"]) for task in ordered_ids),
            recovered_tasks=tuple(task for task in ordered_ids if tasks[task].get("recovered")),
            aggregate_digest=str(projection["aggregate_digest"]),
        )


__all__ = ["WORKLOAD_SCHEMA", "LaneSpec", "WorkloadError", "WorkloadRunReport", "WorkloadAggregateStore", "WorkProductWorkloadRunner"]
