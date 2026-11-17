"""Run bounded CI/runbook consistency lanes without network or native builds."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from noesis_harness.parallel_agent import AgentLane, AgentLaneContext, SafeParallelExecutor
from scripts.build_portable_artifact import build
from scripts.check_ci_packaging_consistency import check
from scripts.verify_native_artifact import verify
from scripts.verify_portable_artifact import verify as verify_portable

ROOT = Path(__file__).resolve().parents[1]


def lane(ctx: AgentLaneContext) -> dict[str, Any]:
    if ctx.task_id == "ci-markers":
        report = check(str(ROOT))
        if report["status"] != "passed" or report["ci"]["missing_markers"]:
            raise AssertionError("ci_markers_missing")
        return {"check": "ci_markers", "status": "passed", "missing": report["ci"]["missing_markers"]}

    if ctx.task_id == "runbook-markers":
        report = check(str(ROOT))
        if report["status"] != "passed" or report["runbook"]["missing_markers"]:
            raise AssertionError("runbook_markers_missing")
        return {"check": "runbook_markers", "status": "passed", "missing": report["runbook"]["missing_markers"]}

    if ctx.task_id == "portable-ci-gate":
        source = ctx.workspace / "fixture"
        source.mkdir()
        (source / "README.md").write_text("ci fixture\n", encoding="utf-8")
        (source / "main.py").write_text("print('ci')\n", encoding="utf-8")
        artifact = ctx.workspace / "portable.zip"
        build(str(source), str(artifact))
        report = verify_portable(str(artifact))
        if report["status"] != "passed":
            raise AssertionError("portable_ci_gate_failed")
        return {"check": "portable_ci_gate", "status": "passed", "file_count": report["file_count"], "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest()}

    if ctx.task_id == "target-honesty-gate":
        targets = {}
        for target in ("windows", "macos"):
            report = verify(target, str(ctx.workspace / (target + ".zip")))
            if report["evidence_status"] != "not_run" or report.get("reason") != "target_host_or_python_mismatch":
                raise AssertionError("target_honesty_failed:" + target)
            targets[target] = {"evidence_status": report["evidence_status"], "reason": report["reason"]}
        return {"check": "target_honesty_gate", "status": "passed", "targets": targets}

    raise AssertionError("unknown_ci_lane:" + ctx.task_id)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run bounded NOESIS CI consistency lanes")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    workspace_root = Path(args.output).expanduser().resolve().parent / "parallel_ci_consistency_workspaces"
    executor = SafeParallelExecutor(str(workspace_root), max_concurrency=4)
    lanes = [
        AgentLane("ci-markers", "ci-markers", "ci-markers"),
        AgentLane("runbook-markers", "runbook-markers", "runbook-markers"),
        AgentLane("portable-ci", "portable-ci-gate", "portable-ci-gate", ("read", "workspace_write", "provenance"), True, True),
        AgentLane("target-honesty", "target-honesty-gate", "target-honesty-gate"),
    ]
    events: list[dict[str, object]] = []
    results = executor.execute(lanes, lane, session_id="ci-consistency-session", approval=True, event_sink=events.append)
    report = {
        "schema_version": "noesis.parallel-ci-consistency.v1",
        "native_builds_executed": False,
        "network_allowed": False,
        "credentials_available": False,
        "model_generated_code_executed": False,
        "workspace_count": len({item.workspace for item in results}),
        "results": [{"task_id": item.task_id, "agent_id": item.agent_id, "workspace": item.workspace, "status": item.status, "output": item.output, "error": item.error} for item in results],
        "event_kinds": sorted({str(event["kind"]) for event in events}),
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "statuses": [item.status for item in results], "workspace_count": report["workspace_count"]}, ensure_ascii=False))
    return 0 if all(item.status == "passed" for item in results) else 2


if __name__ == "__main__":
    raise SystemExit(main())
