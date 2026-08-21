#!/usr/bin/env python3
"""Aggregate native and external evidence into an explicit cross-platform gate matrix."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

SCHEMA = "noesis.cross-platform-release-gates.v1"
ALLOWED = {"passed", "not_run", "blocked", "unsupported"}


def build(native: dict[str, Any], external: dict[str, Any]) -> dict[str, Any]:
    native_results = {item.get("task_id"): item for item in native.get("results", []) if isinstance(item, dict)}
    native_targets = {}
    target_lane = native_results.get("native-target-matrix", {}).get("output", {}).get("targets", {})
    for target in ("windows", "macos"):
        evidence = target_lane.get(target, {})
        status = evidence.get("evidence_status", "blocked")
        if status not in ALLOWED:
            status = "blocked"
        native_targets[target] = {"status": status, "reason": evidence.get("reason", "missing_target_evidence")}
    local_status = "passed" if all(item.get("status") == "passed" for item in native_results.values()) and native.get("native_builds_executed") is False else "blocked"
    lanes = {
        "linux_local_verifier": {"status": local_status, "reason": "bounded_local_evidence_lanes" if local_status == "passed" else "native_lane_failure"},
        "windows_native": native_targets["windows"],
        "macos_native": native_targets["macos"],
        "hermes_external": {"status": external.get("lanes", {}).get("hermes", {}).get("status", "blocked"), "reason": external.get("lanes", {}).get("hermes", {}).get("reason", "missing_external_lane")},
        "opencode_external": {"status": external.get("lanes", {}).get("opencode", {}).get("status", "blocked"), "reason": external.get("lanes", {}).get("opencode", {}).get("reason", "missing_external_lane")},
        "deepseek_harness_external": {"status": external.get("lanes", {}).get("deepseek_harness", {}).get("status", "blocked"), "reason": external.get("lanes", {}).get("deepseek_harness", {}).get("reason", "missing_external_lane")},
    }
    invalid = [name for name, item in lanes.items() if item["status"] not in ALLOWED]
    external_names = ("hermes_external", "opencode_external", "deepseek_harness_external")
    external_claim = bool(external.get("comparative_ready", False))
    external_lanes_passed = all(lanes[name]["status"] == "passed" for name in external_names)
    claim_errors = ["comparative_readiness_claim_invalid"] if external_claim and not external_lanes_passed else []
    overall = "blocked" if invalid or claim_errors or any(item["status"] == "blocked" for item in lanes.values()) else ("passed" if all(item["status"] == "passed" for item in lanes.values()) else "not_run")
    return {
        "schema_version": SCHEMA,
        "lanes": lanes,
        "overall_status": overall,
        "comparative_ready": external_claim and external_lanes_passed and not claim_errors,
        "native_or_external_execution_claim": False,
        "native_builds_executed": bool(native.get("native_builds_executed", False)),
        "network_allowed": bool(native.get("network_allowed", True)),
        "credentials_available": bool(native.get("credentials_available", True)),
        "invalid_status_lanes": invalid,
        "claim_errors": claim_errors,
        "claim_boundary": "local_verifier_pass_does_not_create_native_or_external_execution_evidence",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build cross-platform release gate matrix")
    parser.add_argument("--native", required=True)
    parser.add_argument("--external", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    native = json.loads(Path(args.native).read_text(encoding="utf-8"))
    external = json.loads(Path(args.external).read_text(encoding="utf-8"))
    report = build(native, external)
    Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": args.output, "overall_status": report["overall_status"], "comparative_ready": report["comparative_ready"]}, ensure_ascii=False))
    return 0 if not report["invalid_status_lanes"] and not report["claim_errors"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
