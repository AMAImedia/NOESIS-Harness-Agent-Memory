"""Run bounded local native-evidence verification lanes without native builds."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from noesis_harness.parallel_agent import AgentLane, AgentLaneContext, SafeParallelExecutor
from scripts.build_portable_artifact import build
from scripts.verify_native_artifact import verify
from scripts.verify_packaging_contract import audit
from scripts.verify_portable_artifact import verify as verify_portable
from scripts.verify_python314 import verify as verify_python

ROOT = Path(__file__).resolve().parents[1]


def lane(ctx: AgentLaneContext) -> dict[str, Any]:
    if ctx.task_id == "portable-sha-sbom":
        source = ctx.workspace / "fixture"
        source.mkdir()
        (source / "README.md").write_text("native evidence fixture\n", encoding="utf-8")
        (source / "main.py").write_text("print('fixture')\n", encoding="utf-8")
        artifact = ctx.workspace / "portable.zip"
        build(str(source), str(artifact))
        report = verify_portable(str(artifact))
        if report["status"] != "passed":
            raise AssertionError("portable_artifact_verification_failed")
        return {"check": "portable_sha_sbom", "status": report["status"], "file_count": report["file_count"], "artifact_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest()}

    if ctx.task_id == "static-manifests":
        report = audit(str(ROOT))
        if report["status"] != "passed" or report["native_builds_executed"] is not False:
            raise AssertionError("static_manifest_gate_failed")
        return {"check": "static_manifests", "status": report["status"], "native_builds_executed": report["native_builds_executed"], "targets": [item["target"] for item in report["manifests"]]}

    if ctx.task_id == "python314-identity":
        report = verify_python()
        if not report["ok"] or report["required"] != "3.14.x":
            raise AssertionError("python314_gate_failed")
        return {"check": "python314_identity", "status": "passed", "actual": report["actual"], "implementation": report["implementation"]}

    if ctx.task_id == "native-target-matrix":
        targets = {}
        for target in ("windows", "macos"):
            report = verify(target, str(ctx.workspace / (target + ".placeholder")))
            if report["evidence_status"] != "not_run" or report.get("reason") != "target_host_or_python_mismatch":
                raise AssertionError("native_target_honesty_failed:" + target)
            targets[target] = {"evidence_status": report["evidence_status"], "reason": report["reason"], "actual_platform": report["host"]["actual_platform"]}
        return {"check": "native_target_matrix", "status": "passed", "targets": targets}

    raise AssertionError("unknown_native_evidence_lane:" + ctx.task_id)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run bounded NOESIS native evidence lanes")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    root = Path(args.output).expanduser().resolve().parent / "parallel_native_evidence_workspaces"
    executor = SafeParallelExecutor(str(root), max_concurrency=4)
    lanes = [
        AgentLane("evidence-portable", "portable-sha-sbom", "portable-sha-sbom", ("read", "workspace_write", "provenance"), True, True),
        AgentLane("evidence-manifests", "static-manifests", "static-manifests"),
        AgentLane("evidence-python", "python314-identity", "python314-identity"),
        AgentLane("evidence-native", "native-target-matrix", "native-target-matrix"),
    ]
    events: list[dict[str, object]] = []
    results = executor.execute(lanes, lane, session_id="native-evidence-session", approval=True, event_sink=events.append)
    report = {
        "schema_version": "noesis.parallel-native-evidence.v1",
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
