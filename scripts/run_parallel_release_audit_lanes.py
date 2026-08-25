"""Run bounded offline release-audit lanes."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

from noesis_harness.parallel_agent import AgentLane, AgentLaneContext, SafeParallelExecutor
from scripts.release_audit import audit
from scripts.run_workload_evidence import canonical_digest

ROOT = Path(__file__).resolve().parents[1]
EXPORTS = ("AuditChain", "ContextManager", "IsolationBroker", "Gatekeeper", "DAGPlanner", "VaultProjector", "SkillGate", "ExecutionLadder")
WORKLOAD_EVIDENCE_SCHEMA = "noesis.workload-evidence.v1"
WORKLOAD_EVIDENCE_PATH = ROOT / "docs" / "MULTI_AGENT_WORKLOAD_EVIDENCE.json"


def lane(ctx: AgentLaneContext) -> dict[str, Any]:
    if ctx.task_id == "secret-ast-audit":
        report = audit(str(ROOT), include_remote=False)
        if report["actual_ast_eval_exec_calls"] or report["syntax_errors"] or report["secret_like_hits"]:
            raise AssertionError("security_findings_present")
        return {"check": "secret_ast_audit", "status": "passed", "secret_hits": 0, "syntax_errors": 0, "eval_exec_calls": 0, "working_tree_clean": report["working_tree_clean"]}

    if ctx.task_id == "package-exports":
        import noesis_harness
        missing = [name for name in EXPORTS if not hasattr(noesis_harness, name)]
        if missing:
            raise AssertionError("package_exports_missing:" + ",".join(missing))
        return {"check": "package_exports", "status": "passed", "export_count": len(EXPORTS)}

    if ctx.task_id == "git-integrity":
        diff_check = subprocess.run(["git", "diff", "--check"], cwd=str(ROOT), capture_output=True, text=True, check=False)
        if diff_check.returncode != 0:
            raise AssertionError("git_diff_check_failed")
        status = subprocess.check_output(["git", "status", "--porcelain"], cwd=str(ROOT), text=True)
        return {"check": "git_integrity", "status": "passed", "diff_check": True, "working_tree_clean": not bool(status), "changed_entries": len([line for line in status.splitlines() if line])}

    if ctx.task_id == "ru-checklist":
        checklist = (ROOT / "docs" / "locales" / "ru" / "PROJECT_CHECKLIST_TODO_RU.md").read_text(encoding="utf-8")
        markers = ("NAT-", "CI-", "REL-", "EXEC-", "API-", "MA-")
        missing = [marker for marker in markers if marker not in checklist]
        if missing:
            raise AssertionError("checklist_markers_missing:" + ",".join(missing))
        return {"check": "ru_checklist", "status": "passed", "markers": list(markers), "line_count": len(checklist.splitlines())}

    if ctx.task_id == "workload-evidence-audit":
        if not WORKLOAD_EVIDENCE_PATH.is_file():
            raise AssertionError("workload_evidence_missing")
        try:
            document = json.loads(WORKLOAD_EVIDENCE_PATH.read_text(encoding="utf-8"))
        except ValueError as exc:
            raise AssertionError("workload_evidence_invalid_json") from exc
        schema_version = document.get("schema_version")
        if schema_version != WORKLOAD_EVIDENCE_SCHEMA:
            raise AssertionError("workload_schema_mismatch:" + str(schema_version))
        claimed_digest = document.get("output_digest")
        payload = {key: value for key, value in document.items() if key != "output_digest"}
        recomputed = canonical_digest(payload)
        if not isinstance(claimed_digest, str) or claimed_digest != recomputed:
            raise AssertionError("workload_digest_mismatch")
        return {"check": "workload_evidence_audit", "status": "passed", "schema_version": schema_version, "output_digest": claimed_digest}

    raise AssertionError("unknown_release_audit_lane:" + ctx.task_id)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run bounded offline NOESIS release audit lanes")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    workspace_root = Path(args.output).expanduser().resolve().parent / "parallel_release_audit_workspaces"
    executor = SafeParallelExecutor(str(workspace_root), max_concurrency=4)
    lanes = [
        AgentLane("audit-security", "secret-ast-audit", "secret-ast-audit"),
        AgentLane("audit-exports", "package-exports", "package-exports"),
        AgentLane("audit-git", "git-integrity", "git-integrity"),
        AgentLane("audit-checklist", "ru-checklist", "ru-checklist"),
        AgentLane("audit-workload-evidence", "workload-evidence-audit", "workload-evidence-audit"),
    ]
    events: list[dict[str, object]] = []
    results = executor.execute(lanes, lane, session_id="release-audit-session", approval=True, event_sink=events.append)
    report = {
        "schema_version": "noesis.parallel-release-audit.v1",
        "mode": "offline",
        "network_allowed": False,
        "credentials_available": False,
        "model_generated_code_executed": False,
        "remote_parity_checked": False,
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
