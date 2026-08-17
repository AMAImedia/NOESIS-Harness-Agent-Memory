#!/usr/bin/env python3
"""Verify native packaging evidence on the target Windows/macOS host.

This script never executes the produced application. It verifies host/runtime
identity, artifact shape, deterministic digest, and platform signing evidence.
Linux dry-runs intentionally fail the target gate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def normalized_platform() -> str:
    if sys.platform.startswith("win"):
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    return "linux"


def verify_host(target: str) -> dict:
    return {
        "target": target,
        "actual_platform": normalized_platform(),
        "actual_python": "%d.%d.%d" % sys.version_info[:3],
        "architecture": platform.machine(),
        "python_ok": sys.version_info[:2] == (3, 14),
        "platform_ok": normalized_platform() == target,
    }


def artifact_shape(path: Path, target: str) -> tuple[bool, str]:
    if target == "windows":
        return (path.is_file() and path.suffix.casefold() == ".exe", "windows_exe_required")
    if target == "macos":
        return (path.is_dir() and path.name.endswith(".app"), "macos_app_bundle_required")
    return False, "unsupported_target"


def artifact_digest(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    count = 0
    if path.is_file():
        digest.update(path.name.encode("utf-8") + b"\0")
        digest.update(path.read_bytes())
        return digest.hexdigest(), 1
    for child in sorted((item for item in path.rglob("*") if item.is_file()), key=lambda item: item.relative_to(path).as_posix()):
        relative = child.relative_to(path).as_posix().encode("utf-8")
        digest.update(relative + b"\0")
        digest.update(child.read_bytes())
        count += 1
    return digest.hexdigest(), count


def signature_evidence(path: Path, target: str) -> dict:
    if target == "windows":
        tool = shutil.which("signtool")
        if not tool:
            return {"status": "not_run", "tool": "signtool", "reason": "signtool_unavailable"}
        command = [tool, "verify", "/pa", str(path)]
    else:
        tool = shutil.which("codesign")
        if not tool:
            return {"status": "not_run", "tool": "codesign", "reason": "codesign_unavailable"}
        command = [tool, "--verify", "--deep", "--strict", str(path)]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    return {
        "status": "passed" if completed.returncode == 0 else "failed",
        "tool": Path(tool).name,
        "returncode": completed.returncode,
        "stdout_tail": completed.stdout[-500:],
        "stderr_tail": completed.stderr[-500:],
    }


def verify(target: str, artifact: str, development_unsigned: bool = False) -> dict:
    host = verify_host(target)
    path = Path(artifact).expanduser().resolve()
    shape_ok, shape_reason = artifact_shape(path, target)
    report = {
        "schema_version": "noesis.native-artifact-evidence.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "host": host,
        "artifact": str(path),
        "artifact_exists": path.exists(),
        "artifact_shape_ok": shape_ok,
        "artifact_shape_reason": shape_reason,
        "development_unsigned": development_unsigned,
        "evidence_status": "not_run",
    }
    if not host["python_ok"] or not host["platform_ok"]:
        report["reason"] = "target_host_or_python_mismatch"
        return report
    if not path.exists() or not shape_ok:
        report["reason"] = "artifact_missing_or_invalid_shape"
        return report
    digest, file_count = artifact_digest(path)
    report["sha256"] = digest
    report["file_count"] = file_count
    signature = signature_evidence(path, target)
    report["signature"] = signature
    if target == "macos" and signature.get("status") == "passed":
        spctl = shutil.which("spctl")
        if spctl:
            checked = subprocess.run([spctl, "--assess", "--type", "execute", str(path)], capture_output=True, text=True, check=False)
            report["notarization"] = {"status": "passed" if checked.returncode == 0 else "failed", "returncode": checked.returncode, "stderr_tail": checked.stderr[-500:]}
        else:
            report["notarization"] = {"status": "not_run", "reason": "spctl_unavailable"}
    else:
        report["notarization"] = {"status": "not_applicable" if target == "windows" else "not_run"}
    signed_ok = signature.get("status") == "passed"
    notarized_ok = target == "windows" or report["notarization"].get("status") == "passed"
    if development_unsigned:
        report["evidence_status"] = "development_unsigned" if not signed_ok else "signed_dev"
        report["reason"] = "unsigned development evidence explicitly allowed"
    elif signed_ok and notarized_ok:
        report["evidence_status"] = "verified"
    else:
        report["reason"] = "required_signature_or_notarization_missing"
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Verify native NOESIS artifact evidence without executing it")
    parser.add_argument("--target", choices=("windows", "macos"), required=True)
    parser.add_argument("--artifact", required=True)
    parser.add_argument("--development-unsigned", action="store_true")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    report = verify(args.target, args.artifact, args.development_unsigned)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "evidence_status": report["evidence_status"], "reason": report.get("reason", "")}, ensure_ascii=False))
    return 0 if report["evidence_status"] == "verified" or (args.development_unsigned and report["evidence_status"] in {"development_unsigned", "signed_dev"}) else 2


if __name__ == "__main__":
    raise SystemExit(main())
