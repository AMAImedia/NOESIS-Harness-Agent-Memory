"""Run bounded read-only metadata/licensing/provenance coverage lanes."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from noesis_harness.parallel_agent import AgentLane, AgentLaneContext, SafeParallelExecutor
from scripts.build_portable_artifact import build
from scripts.check_release_metadata import audit
from scripts.verify_portable_artifact import verify as verify_portable

ROOT = Path(__file__).resolve().parents[1]


def lane(ctx: AgentLaneContext) -> dict[str, Any]:
    if ctx.task_id == "release-metadata":
        report = audit(str(ROOT))
        if report["status"] != "passed":
            raise AssertionError("release_metadata_failed:" + ";".join(report["findings"]))
        return {"check": "release_metadata", "status": "passed", "required_files": len(report["required_files"]), "checks": len(report["checks"]), "upstreams": len(report["provenance_names"])}

    if ctx.task_id == "license-provenance":
        notices = (ROOT / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8").casefold()
        provenance = json.loads((ROOT / "docs" / "third_party_provenance.json").read_text(encoding="utf-8"))
        upstreams = provenance["upstreams"]
        if not all(item.get("code_copied") is False and item.get("runtime_dependency") is False for item in upstreams):
            raise AssertionError("reference_only_boundary_failed")
        missing = [item["name"] for item in upstreams if item["name"].replace("-", " ") not in notices and item["name"] not in notices]
        if missing:
            raise AssertionError("notice_missing:" + ",".join(missing))
        return {"check": "license_provenance", "status": "passed", "upstreams": len(upstreams), "code_copied": False, "runtime_dependency": False}

    if ctx.task_id == "changelog-docs":
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        docs = (ROOT / "docs" / "README.md").read_text(encoding="utf-8")
        required = ("[Unreleased]", "2026-08-18", "Python 3.14", "PROJECT_CHECKLIST_TODO_RU.md", "NATIVE_PACKAGING_RUNBOOK_RU.md", "third_party_provenance.json")
        missing = [marker for marker in required if marker not in changelog + docs]
        if missing:
            raise AssertionError("changelog_docs_missing:" + ",".join(missing))
        return {"check": "changelog_docs", "status": "passed", "missing": [], "changelog_unreleased": True}

    if ctx.task_id == "portable-sbom":
        source = ctx.workspace / "fixture"
        source.mkdir()
        (source / "README.md").write_text("metadata fixture\n", encoding="utf-8")
        (source / "main.py").write_text("print('metadata')\n", encoding="utf-8")
        artifact = ctx.workspace / "portable.zip"
        build(str(source), str(artifact))
        report = verify_portable(str(artifact))
        if report["status"] != "passed":
            raise AssertionError("portable_sbom_failed")
        return {"check": "portable_sbom", "status": "passed", "file_count": report["file_count"], "artifact_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest()}

    raise AssertionError("unknown_metadata_lane:" + ctx.task_id)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run bounded NOESIS metadata/provenance lanes")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    workspace_root = Path(args.output).expanduser().resolve().parent / "parallel_metadata_workspaces"
    executor = SafeParallelExecutor(str(workspace_root), max_concurrency=4)
    lanes = [
        AgentLane("metadata", "release-metadata", "release-metadata"),
        AgentLane("provenance", "license-provenance", "license-provenance"),
        AgentLane("changelog", "changelog-docs", "changelog-docs"),
        AgentLane("sbom", "portable-sbom", "portable-sbom", ("read", "workspace_write", "provenance"), True, True),
    ]
    events: list[dict[str, object]] = []
    results = executor.execute(lanes, lane, session_id="metadata-coverage-session", approval=True, event_sink=events.append)
    report = {
        "schema_version": "noesis.parallel-metadata-coverage.v1",
        "network_allowed": False,
        "credentials_available": False,
        "model_generated_code_executed": False,
        "native_builds_executed": False,
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
