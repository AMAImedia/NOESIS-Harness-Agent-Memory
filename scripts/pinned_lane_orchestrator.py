"""Prepare and optionally execute the pinned external lane matrix.

The orchestrator is connector-neutral: it never invents a provider command and
never treats a missing executable, revision or host as a pass.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import shutil
import sys
from pathlib import Path
from typing import Any, Mapping

from scripts.external_evidence_readiness import build_matrix as build_readiness_matrix
from scripts.external_runner_contract import REQUIRED_SYSTEMS, make_spec, validate_result
from scripts.run_external_lane import plan

ADAPTERS: dict[str, dict[str, Any]] = {
    "hermes": {
        "repository": "https://github.com/NousResearch/hermes-agent",
        "executable_candidates": ("hermes", "hermes-agent"),
        "host": "any",
    },
    "opencode": {
        "repository": "https://github.com/anomalyco/opencode",
        "executable_candidates": ("opencode",),
        "host": "any",
    },
    "deepseek_harness": {
        "repository": "https://github.com/deepseek-ai/deepseek-harness",
        "executable_candidates": ("dsh", "deepseek-harness"),
        "host": "any",
    },
}


def _sha(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def adapter_inventory() -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for system, metadata in ADAPTERS.items():
        executable = next((shutil.which(candidate) for candidate in metadata["executable_candidates"] if shutil.which(candidate)), None)
        result[system] = {
            "repository": metadata["repository"],
            "host": metadata["host"],
            "executable": executable,
            "available": executable is not None,
            "execution": "not_run",
            "reason": "exact_revision_and_operator_approval_required",
        }
    return result


def prepare_matrix(manifest: Mapping[str, Any], workspace: str) -> dict[str, Any]:
    systems = tuple(manifest.get("systems", ()))
    required = {"hermes", "opencode", "deepseek_harness"}
    missing = sorted(required.difference(systems))
    task_manifest_sha = str(manifest.get("task_manifest_sha256", ""))
    if not task_manifest_sha:
        task_manifest_sha = _sha(manifest.get("tasks", []))
    lanes: dict[str, Any] = {}
    for system in ("hermes", "opencode", "deepseek_harness"):
        adapter = ADAPTERS[system]
        revision = str(manifest.get("revisions", {}).get(system, ""))
        if not revision:
            lanes[system] = {"execution": "not_run", "status": "not_run", "reason": "missing_exact_revision"}
            continue
        executable = next((shutil.which(candidate) for candidate in adapter["executable_candidates"] if shutil.which(candidate)), None)
        argv = [executable or adapter["executable_candidates"][0], "--no-network", "--workspace", workspace]
        spec = make_spec(system, revision, argv, task_manifest_sha)
        ok, errors = validate_result({**spec, "status": "not_run", "execution": "not_started"})
        if not ok:
            lanes[system] = {"execution": "denied", "status": "not_run", "reason": "invalid_generated_spec", "errors": errors}
            continue
        lanes[system] = {
            "execution": "not_started",
            "status": "not_run",
            "revision": revision,
            "spec": spec,
            "plan": plan(spec, workspace),
            "adapter": adapter,
            "available": executable is not None,
        }
    operator_commands = {
        "linux": ["runtime/python-3.14.7/build/bin/python3.14", "scripts/run_task_execution_parity.py", "--output", "artifacts/task_execution_parity.json"],
        "macos": ["python3.14", "scripts/run_task_execution_parity.py", "--output", "artifacts/task_execution_parity.json"],
        "windows": ["py", "-3.14", "scripts\\run_task_execution_parity.py", "--output", "artifacts\\task_execution_parity.json"],
    }
    current_os = platform.system().lower()
    return {
        "schema_version": "noesis.pinned-lane-matrix.v1",
        "scope": "connector_neutral",
        "host": {"python": ".".join(map(str, sys.version_info[:3])), "platform": platform.platform(), "system": current_os},
        "operator_bundle": {
            "schema_version": "noesis.parity-operator-bundle.v1",
            "python_policy": "3.14-only",
            "commands": operator_commands,
            "current_host_execution": "available" if current_os in operator_commands and sys.version_info[:2] == (3, 14) else "not_run",
            "native_host_required_for": ["macos", "windows"],
        },
        "required_systems": sorted(required),
        "manifest_systems": list(systems),
        "missing_manifest_systems": missing,
        "adapter_inventory": adapter_inventory(),
        "lanes": lanes,
        "readiness": build_readiness_matrix(manifest, [], "orchestrator-preflight-key-2026"),
        "external_execution": "not_run",
        "ranking": "not_run",
        "reason": "pinned_environment_and_explicit_operator_approval_required",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare provider-neutral pinned external lane matrix")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    report = prepare_matrix(manifest, args.workspace)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "execution": report["external_execution"], "ranking": report["ranking"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
