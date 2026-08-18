"""Run a local end-to-end task/session execution parity smoke.

This is local evidence only. It does not invoke a model or external provider and
never ranks Hermes, OpenCode or DeepSeek Harness.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

from noesis_harness.child_execution import ChildExecutionRuntime, ExecutionRequest
from noesis_harness.coordination import Actions
from noesis_harness.execution_bridge import TaskExecutionBridge, TaskExecutionRequest
from noesis_harness.gatekeeper import CapabilityRequest, Gatekeeper
from noesis_harness.parallel_agent import SafeParallelExecutor
from noesis_harness.sandbox_bwrap import BubblewrapBackend
from noesis_harness.session_stream import SessionEventBuffer
from noesis_harness.task_session_api import TaskSessionStore

SCHEMA = "noesis.task-execution-parity.v1"


def _sha(payload: Any) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def run() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="noesis-parity-") as temp:
        root = Path(temp)
        workspace = root / "workspace"
        workspace.mkdir()
        (workspace / "child.py").write_text("print('parity-child-ok')\n", encoding="utf-8")
        store = TaskSessionStore(str(root / "session.jsonl"))
        actions = Actions(str(root / "actions.db"))
        executor = SafeParallelExecutor(str(root / "agent-workspaces"), max_concurrency=1)
        bridge = TaskExecutionBridge(store, actions, executor)
        session = store.create_session("parity-operator", session_id="parity-session")
        stream = SessionEventBuffer(session.session_id, max_events=64)
        stream.publish("session_started", {"state": session.state})
        task = store.create_task(session.session_id, "local child parity", "parity-agent", task_id="parity-task")
        store.transition_task(task.task_id, "planned", reason="parity_plan")
        store.transition_task(task.task_id, "waiting_approval", reason="parity_request")
        action_id = bridge.register_action(task.task_id, task.title)
        gate = Gatekeeper(str(root / "gate.jsonl"))
        gate_decision = gate.prepare(CapabilityRequest("parity-session", task.task_id, "parity-agent", "skill.execute", "run_child", "child.py", "write", {"target": "child.py"}))
        gate.approve(gate_decision.request_id)
        gate.commit(gate_decision.request_id)
        child = ChildExecutionRuntime(gate)
        backend = BubblewrapBackend()
        events: list[dict[str, Any]] = []

        def sink(event: dict[str, Any]) -> None:
            events.append(dict(event))
            stream.publish(str(event.get("kind", "event")), {key: value for key, value in event.items() if key not in {"kind", "session_id", "task_id"}}, task_id=event.get("task_id"))

        def callback(_context: Any) -> object:
            return child.run(ExecutionRequest(gate_decision.request_id, (sys.executable, "child.py"), str(workspace), (Path(sys.executable).name,), timeout_seconds=2.0))

        report = bridge.execute(session.session_id, [TaskExecutionRequest(task.task_id, "parity-agent", "parity-agent")], callback, approval=True, event_sink=sink)
        for event in report.results:
            stream.publish("execution_result", {"status": event.status, "agent_id": event.agent_id}, task_id=event.task_id)
        recovery_action = actions.create("simulated crash recovery", action_id="parity-recovery")
        actions.claim(recovery_action, "parity-agent")
        requeued = actions.requeue(recovery_action, "parity-agent")
        sse = stream.sse_since(0)
        stream_records = [{"sequence": event.sequence, "kind": event.kind, "task_id": event.task_id} for event in stream.since(0)]
        sequences = [event["sequence"] for event in stream_records]
        local_result = {
            "session_state": store.session(session.session_id).state,
            "task_state": store.task(task.task_id).state,
            "bridge_statuses": [result.status for result in report.results],
            "child_backend": "direct-process-group",
            "child_status": "completed" if report.results and report.results[0].status == "passed" else "failed",
            "sse_monotonic": sequences == list(range(1, len(sequences) + 1)),
            "sse_reconnect_events": len(stream.since(2)),
            "recovery_requeued": requeued and actions.counts().get("pending", 0) >= 1,
            "event_kinds": [event["kind"] for event in events],
        }
        return {
            "schema_version": SCHEMA,
            "execution": "completed",
            "status": "passed" if all((local_result["task_state"] == "review", local_result["child_status"] == "completed", local_result["sse_monotonic"], local_result["recovery_requeued"])) else "failed",
            "scope": "local_only",
            "python": sys.version.split()[0],
            "platform": sys.platform,
            "local": local_result,
            "backend_inventory": {
                "linux_bubblewrap": {"available": backend.available, "execution": "not_run"},
                "macos_sandbox_exec": {"execution": "not_run", "reason": "matching_darwin_host_required"},
                "windows_native": {"execution": "not_run", "reason": "matching_windows_host_required"},
            },
            "external": {
                "hermes": "not_run",
                "opencode": "not_run",
                "deepseek_harness": "not_run",
                "reason": "pinned_external_environment_required",
            },
            "sse_sha256": _sha(stream_records),
            "evidence_sha256": _sha(local_result),
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run local NOESIS task execution parity smoke")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    report = run()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "status": report["status"], "execution": report["execution"]}, ensure_ascii=False))
    return 0 if report["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
