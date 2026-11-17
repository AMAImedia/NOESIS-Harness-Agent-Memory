"""Run safe local release-readiness verification lanes in parallel.

All callbacks are deterministic local checks. No model, shell, network,
credential, or executable-skill invocation is performed.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from noesis_harness.coordination import Actions
from noesis_harness.execution_bridge import TaskExecutionBridge, TaskExecutionRequest
from noesis_harness.parallel_agent import AgentLane, AgentLaneContext, SafeParallelExecutor
from noesis_harness.task_session_api import SCHEMA_VERSION, TaskSessionStore
from scripts.verify_native_artifact import verify
from scripts.verify_packaging_contract import audit

ROOT = Path(__file__).resolve().parents[1]


def run_lane(ctx: AgentLaneContext) -> dict[str, Any]:
    if ctx.task_id == "packaging-contract":
        report = audit(str(ROOT))
        if report["status"] != "passed" or report["native_builds_executed"] is not False:
            raise AssertionError("packaging_contract_not_passed_or_native_claimed")
        return {"check": "packaging_contract", "status": report["status"], "native_builds_executed": report["native_builds_executed"], "targets": [item["target"] for item in report["manifests"]]}

    if ctx.task_id == "native-target-honesty":
        reports = {}
        for target in ("windows", "macos"):
            result = verify(target, str(ctx.workspace / (target + ".placeholder")))
            if result["evidence_status"] != "not_run" or result.get("reason") != "target_host_or_python_mismatch":
                raise AssertionError("target_mismatch_must_be_not_run:" + target)
            reports[target] = {"evidence_status": result["evidence_status"], "reason": result["reason"], "actual_platform": result["host"]["actual_platform"]}
        return {"check": "native_target_honesty", "targets": reports}

    if ctx.task_id == "command-contract":
        store = TaskSessionStore(str(ctx.workspace / "session_events.jsonl"))
        session = store.create_session("release-lane", session_id="release-session")
        task = store.create_task(session.session_id, "release command contract", "release-agent", task_id="release-task")
        store.transition_task(task.task_id, "planned", reason="parallel_release_check")
        result = store.dispatch({"schema_version": SCHEMA_VERSION, "command_id": "release-request", "command": "task.request_execution", "payload": {"task_id": task.task_id, "reason": "parallel_release_check"}})
        if result["result"].state != "waiting_approval":
            raise AssertionError("command_did_not_enter_waiting_approval")
        return {"check": "command_contract", "status": "passed", "task_state": result["result"].state, "event_count": store.events.count()}

    if ctx.task_id == "execution-bridge":
        store = TaskSessionStore(str(ctx.workspace / "bridge_events.jsonl"))
        actions = Actions(str(ctx.workspace / "actions.db"))
        executor = SafeParallelExecutor(str(ctx.workspace / "agent_workspaces"), max_concurrency=1)
        bridge = TaskExecutionBridge(store, actions, executor)
        session = store.create_session("release-lane", session_id="bridge-session")
        task = store.create_task(session.session_id, "bridge lifecycle", "release-agent", task_id="bridge-task")
        store.transition_task(task.task_id, "planned", reason="parallel_release_check")
        store.dispatch({"schema_version": SCHEMA_VERSION, "command_id": "bridge-request", "command": "task.request_execution", "payload": {"task_id": task.task_id, "reason": "parallel_release_check"}})
        bridge.register_action(task.task_id, task.title)
        events: list[dict[str, object]] = []

        def callback(agent_ctx: AgentLaneContext) -> dict[str, str]:
            path = agent_ctx.path("verified.txt")
            path.write_text("local-release-check\n", encoding="utf-8")
            return {"status": "verified"}

        report = bridge.execute(session.session_id, [TaskExecutionRequest(task.task_id, "release-agent", "release-agent", ("read", "workspace_write", "provenance"))], callback, approval=True, event_sink=events.append)
        if report.results[0].status != "passed" or store.task(task.task_id).state != "review" or actions.counts().get("done") != 1:
            raise AssertionError("execution_bridge_lifecycle_failed")
        return {"check": "execution_bridge", "status": "passed", "task_state": store.task(task.task_id).state, "action_done": actions.counts().get("done", 0), "event_kinds": sorted({str(event["kind"]) for event in events})}

    raise AssertionError("unknown_release_lane:" + ctx.task_id)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run bounded local NOESIS release-readiness lanes")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    root = Path(args.output).expanduser().resolve().parent / "parallel_release_workspaces"
    executor = SafeParallelExecutor(str(root), max_concurrency=4)
    lanes = [
        AgentLane("release-packaging", "packaging-contract", "packaging-contract"),
        AgentLane("release-native", "native-target-honesty", "native-target-honesty"),
        AgentLane("release-command", "command-contract", "command-contract", ("read", "workspace_write", "provenance"), True, True),
        AgentLane("release-bridge", "execution-bridge", "execution-bridge", ("read", "workspace_write", "provenance"), True, True),
    ]
    events: list[dict[str, object]] = []
    results = executor.execute(lanes, run_lane, session_id="parallel-release-session", approval=True, event_sink=events.append)
    report = {
        "schema_version": "noesis.parallel-release-lanes.v1",
        "simulation_only": False,
        "network_allowed": False,
        "credentials_available": False,
        "model_generated_code_executed": False,
        "max_concurrency": executor.max_concurrency,
        "results": [{"task_id": item.task_id, "agent_id": item.agent_id, "workspace": item.workspace, "status": item.status, "output": item.output, "error": item.error} for item in results],
        "event_kinds": sorted({str(event["kind"]) for event in events}),
        "audit_event_count": len(executor.audit),
        "workspace_count": len({item.workspace for item in results}),
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "statuses": [item.status for item in results], "workspace_count": report["workspace_count"]}, ensure_ascii=False))
    return 0 if all(item.status == "passed" for item in results) else 2


if __name__ == "__main__":
    raise SystemExit(main())
