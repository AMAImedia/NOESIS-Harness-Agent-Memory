"""Run fail-closed native build-policy lanes without executing native builders."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from noesis_harness.parallel_agent import AgentLane, AgentLaneContext, SafeParallelExecutor
from scripts import build_native
from scripts.verify_packaging_contract import audit
from scripts.verify_python314 import verify as verify_python

ROOT = Path(__file__).resolve().parents[1]


def lane(ctx: AgentLaneContext) -> dict[str, Any]:
    if ctx.task_id in {"windows-dry-run", "macos-dry-run"}:
        target = "windows" if ctx.task_id.startswith("windows") else "macos"
        target_report = build_native.verify_target(target)
        command = build_native.command_for("pyinstaller", target)
        if target_report["platform_ok"]:
            raise AssertionError("unexpected_target_match_on_linux_policy_lane")
        if not command or command[0] != build_native.sys.executable:
            raise AssertionError("native_command_mapping_invalid")
        return {"check": target + "_dry_run", "status": "passed", "dry_run": True, "run_permitted": False, "target_report": target_report, "command": command}

    if ctx.task_id == "signing-policy":
        report = audit(str(ROOT))
        if report["status"] != "passed" or report["native_builds_executed"] is not False:
            raise AssertionError("packaging_contract_failed")
        policies = {}
        for manifest in report["manifests"]:
            data = json.loads(Path(manifest["path"]).read_text(encoding="utf-8"))
            policy = str(data.get("signature_policy", ""))
            if not policy or "required" not in policy.casefold() or "development-unsigned" not in policy:
                raise AssertionError("signing_policy_incomplete:" + manifest["target"])
            policies[manifest["target"]] = {"signature_policy": policy, "evidence_status": data.get("evidence_status")}
        return {"check": "signing_policy", "status": "passed", "native_builds_executed": False, "policies": policies}

    if ctx.task_id == "python314-dry-run":
        report = verify_python()
        if not report["ok"]:
            raise AssertionError("python314_not_active")
        return {"check": "python314_dry_run", "status": "passed", "actual": report["actual"], "required": report["required"]}

    raise AssertionError("unknown_build_policy_lane:" + ctx.task_id)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run bounded NOESIS native build policy lanes")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    workspace_root = Path(args.output).expanduser().resolve().parent / "parallel_build_policy_workspaces"
    executor = SafeParallelExecutor(str(workspace_root), max_concurrency=4)
    lanes = [
        AgentLane("policy-windows", "windows-dry-run", "windows-dry-run"),
        AgentLane("policy-macos", "macos-dry-run", "macos-dry-run"),
        AgentLane("policy-signing", "signing-policy", "signing-policy"),
        AgentLane("policy-python", "python314-dry-run", "python314-dry-run"),
    ]
    events: list[dict[str, object]] = []
    results = executor.execute(lanes, lane, session_id="build-policy-session", approval=True, event_sink=events.append)
    report = {
        "schema_version": "noesis.parallel-build-policy.v1",
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
