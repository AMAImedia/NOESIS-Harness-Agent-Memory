#!/usr/bin/env python3
"""Build and validate connector-neutral external A/B runner records.

The contract stores argv arrays instead of shell strings, pins revisions and
configuration digests, and never starts a third-party process by itself.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

REQUIRED_SYSTEMS = ("noesis", "hermes", "opencode", "deepseek_harness")
REQUIRED_FIELDS = ("system", "revision", "model_provider", "task_manifest_sha256", "protocol_fingerprint", "environment", "workspace", "argv")
ALLOWED_STATUS = frozenset({"passed", "failed", "unsupported", "not_run"})
ALLOWED_EXECUTION = frozenset({"not_started", "denied", "started", "completed", "fixture_only"})
_HEX64 = frozenset("0123456789abcdef")


def _is_sha256(value: object) -> bool:
    text = str(value)
    return len(text) == 64 and text.casefold() and all(char in _HEX64 for char in text.casefold())


def file_sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def make_spec(system: str, revision: str, argv: Sequence[str], task_manifest_sha256: str, model_provider: str = "pinned-by-run-manifest", workspace_mode: str = "disposable") -> dict:
    if system not in REQUIRED_SYSTEMS:
        raise ValueError("unsupported system")
    if not revision or not task_manifest_sha256:
        raise ValueError("revision and task manifest digest are required")
    if not argv or any(not isinstance(item, str) or not item for item in argv):
        raise ValueError("argv must be a non-empty list of strings")
    if workspace_mode != "disposable":
        raise ValueError("workspace must be disposable")
    protocol = {
        "task_manifest_sha256": task_manifest_sha256,
        "model_provider": model_provider,
        "workspace_mode": workspace_mode,
        "outside_access": "deny",
        "credentials": "absent",
    }
    protocol_fingerprint = hashlib.sha256(json.dumps(protocol, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    return {
        "schema_version": "noesis.external-runner.v1",
        "system": system,
        "revision": revision,
        "model_provider": model_provider,
        "task_manifest_sha256": task_manifest_sha256,
        "protocol_fingerprint": protocol_fingerprint,
        "environment": {"python": "%d.%d.%d" % sys.version_info[:3], "platform": platform.platform()},
        "workspace": {"mode": "disposable", "outside_access": "deny", "credentials": "absent"},
        "argv": list(argv),
        "execution": "not_started",
    }


def validate_result(result: Mapping[str, Any]) -> tuple[bool, tuple[str, ...]]:
    errors = []
    for field in REQUIRED_FIELDS:
        if field not in result:
            errors.append("missing:" + field)
    if result.get("system") not in REQUIRED_SYSTEMS:
        errors.append("invalid:system")
    if result.get("status") not in ALLOWED_STATUS:
        errors.append("invalid:status")
    execution = result.get("execution")
    if execution not in ALLOWED_EXECUTION:
        errors.append("invalid:execution")
    elif execution in {"not_started", "denied"} and result.get("status") != "not_run":
        errors.append("execution_status_mismatch:not_run_required")
    elif execution in {"started", "completed", "fixture_only"} and result.get("status") == "not_run":
        errors.append("execution_status_mismatch:completed_or_failed_required")
    if not _is_sha256(result.get("task_manifest_sha256")):
        errors.append("invalid:task_manifest_sha256")
    if not _is_sha256(result.get("protocol_fingerprint")):
        errors.append("invalid:protocol_fingerprint")
    environment = result.get("environment")
    if not isinstance(environment, Mapping) or not environment.get("python") or not environment.get("platform"):
        errors.append("invalid:environment")
    workspace = result.get("workspace")
    if not isinstance(workspace, Mapping) or workspace.get("mode") != "disposable":
        errors.append("workspace_not_disposable")
    if isinstance(result.get("argv"), str) or not isinstance(result.get("argv"), Sequence):
        errors.append("argv_must_be_array")
    return not errors, tuple(errors)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Create or validate NOESIS external runner contract")
    sub = parser.add_subparsers(dest="action", required=True)
    create = sub.add_parser("create")
    create.add_argument("--system", choices=REQUIRED_SYSTEMS, required=True)
    create.add_argument("--revision", required=True)
    create.add_argument("--task-manifest", required=True)
    create.add_argument("--argv", nargs="+", required=True)
    create.add_argument("--output", required=True)
    check = sub.add_parser("validate")
    check.add_argument("--input", required=True)
    args = parser.parse_args(argv)
    if args.action == "create":
        spec = make_spec(args.system, args.revision, args.argv, file_sha256(args.task_manifest))
        Path(args.output).write_text(json.dumps(spec, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({"output": args.output, "execution": "not_started"}))
        return 0
    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    ok, errors = validate_result(data)
    print(json.dumps({"valid": ok, "errors": errors}, ensure_ascii=False))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
