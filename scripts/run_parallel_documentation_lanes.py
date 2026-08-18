"""Run bounded read-only documentation integrity lanes."""
from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any

from noesis_harness.parallel_agent import AgentLane, AgentLaneContext, SafeParallelExecutor
from scripts.check_json_evidence import audit as audit_json
from scripts.check_markdown_links import audit as audit_links
from scripts.docs_security_audit import audit as audit_docs

ROOT = Path(__file__).resolve().parents[1]


def lane(ctx: AgentLaneContext) -> dict[str, Any]:
    if ctx.task_id == "docs-security":
        report = audit_docs(str(ROOT))
        if not report["clean"]:
            raise AssertionError("docs_security_findings")
        return {"check": "docs_security", "status": "passed", "high": report["high_count"], "medium": report["medium_count"], "markdown_files": report.get("markdown_files", 0)}

    if ctx.task_id == "markdown-links":
        report = audit_links(str(ROOT))
        if not report["clean"]:
            raise AssertionError("markdown_link_findings")
        return {"check": "markdown_links", "status": "passed", "local_links": report["local_links"], "markdown_files": report["markdown_files"], "missing": report["missing_count"]}

    if ctx.task_id == "json-evidence":
        report = audit_json(str(ROOT))
        if not report["clean"]:
            raise AssertionError("json_evidence_findings")
        return {"check": "json_evidence", "status": "passed", "files_checked": len(report["records"]), "findings": len(report["findings"])}

    if ctx.task_id == "ru-checklist":
        checklist = (ROOT / "docs" / "PROJECT_CHECKLIST_TODO_RU.md").read_text(encoding="utf-8")
        required = ("AUD-", "META-", "CI-", "NAT-", "REL-", "PARALLEL_METADATA_EVIDENCE.json", "PARALLEL_RELEASE_AUDIT_EVIDENCE.json")
        missing = [marker for marker in required if marker not in checklist]
        if missing:
            raise AssertionError("checklist_documentation_markers:" + ",".join(missing))
        return {"check": "ru_checklist", "status": "passed", "missing": [], "line_count": len(checklist.splitlines())}

    raise AssertionError("unknown_documentation_lane:" + ctx.task_id)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run bounded NOESIS documentation integrity lanes")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    lanes = [
        AgentLane("docs-security", "docs-security", "docs-security"),
        AgentLane("docs-links", "markdown-links", "markdown-links"),
        AgentLane("docs-json", "json-evidence", "json-evidence"),
        AgentLane("docs-checklist", "ru-checklist", "ru-checklist"),
    ]
    events: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix="noesis-parallel-docs-") as workspace_root:
        executor = SafeParallelExecutor(workspace_root, max_concurrency=4)
        results = executor.execute(lanes, lane, session_id="documentation-audit-session", approval=True, event_sink=events.append)
    report = {
        "schema_version": "noesis.parallel-documentation-audit.v1",
        "network_allowed": False,
        "credentials_available": False,
        "model_generated_code_executed": False,
        "native_builds_executed": False,
        "workspace_count": len({item.workspace for item in results}),
        "results": [{"task_id": item.task_id, "agent_id": item.agent_id, "workspace": Path(item.workspace).name, "status": item.status, "output": item.output, "error": item.error} for item in results],
        "event_kinds": sorted({str(event["kind"]) for event in events}),
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "statuses": [item.status for item in results], "workspace_count": report["workspace_count"]}, ensure_ascii=False))
    return 0 if all(item.status == "passed" for item in results) else 2


if __name__ == "__main__":
    raise SystemExit(main())
