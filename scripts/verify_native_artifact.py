#!/usr/bin/env python3
"""Verify native packaging evidence on the target Windows/macOS host.

This script never executes the produced application. It verifies host/runtime
identity, artifact shape, deterministic digest, and platform signing evidence.
Linux dry-runs intentionally fail the target gate.

The Windows signtool locator is a bounded capability probe in the spirit of
the honest-evidence probes used by the agentmemory and deepseek-harness
harnesses: search known layouts, measure the tool version with a fixed
timeout, never let an exception escape, and record absence honestly instead
of guessing.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

SIGNSIGTOOL_PROBE_TIMEOUT_SECONDS = 20


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


def _default_signtool_search_roots() -> list:
    roots = []
    for env_name in ("ProgramFiles(x86)", "ProgramFiles"):
        program_dir = os.environ.get(env_name)
        if program_dir:
            roots.append(str(Path(program_dir) / "Windows Kits" / "10" / "bin"))
    roots.append(r"C:\Program Files (x86)\Windows Kits\10\bin")
    roots.append(r"C:\Program Files\Windows Kits\10\bin")
    unique = []
    for root in roots:
        if root not in unique:
            unique.append(root)
    return unique


def _kits_version_sort_key(name: str):
    # Numeric version directories outrank anything else (descending order);
    # kinds never compare across the leading tag.
    parts = name.split(".")
    if parts and all(part.isdigit() for part in parts):
        return (1, tuple(int(part) for part in parts))
    return (0, name)


def _signtool_version(tool_path: str):
    try:
        completed = subprocess.run(
            [tool_path, "--version"],
            capture_output=True,
            text=True,
            check=False,
            timeout=SIGNSIGTOOL_PROBE_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None
    for line in (completed.stdout or "").splitlines():
        line = line.strip()
        if not line or line.startswith(("SignTool Error", "Usage:", "Valid commands")):
            continue
        return line
    return None


def locate_signtool(search_roots=None) -> Mapping:
    """Locate signtool.exe: PATH first, then Windows Kits versioned layout.

    Deterministic: among Kits candidates the highest numeric version directory
    wins; ties are broken by ascending path. No exception ever escapes.
    """
    try:
        which_hit = shutil.which("signtool")
        if which_hit:
            return {
                "status": "found",
                "source": "path",
                "path": str(Path(which_hit)),
                "version": _signtool_version(which_hit),
            }
        roots = list(_default_signtool_search_roots()) if search_roots is None else list(search_roots)
        candidates = []
        for root in roots:
            for candidate in Path(root).glob("*/x64/signtool.exe"):
                key = _kits_version_sort_key(candidate.parent.parent.name)
                candidates.append((key, str(candidate)))
        # Highest version first; stable sort keeps earlier-listed paths first on ties.
        candidates.sort(key=lambda item: item[1])
        candidates.sort(key=lambda item: item[0], reverse=True)
        for _, candidate_str in candidates:
            candidate_path = Path(candidate_str)
            if not candidate_path.is_file():
                continue
            return {
                "status": "found",
                "source": "windows_kits",
                "path": str(candidate_path),
                "version": _signtool_version(str(candidate_path)),
            }
        return {"status": "missing"}
    except Exception as exc:  # probe must never break evidence generation
        return {"status": "missing", "error": type(exc).__name__}


def signature_evidence(path: Path, target: str) -> dict:
    if target == "windows":
        section = {"status": "not_run", "tool": "signtool"}
        probe = locate_signtool()
        if probe.get("status") == "found":
            section["tool_path"] = probe.get("path")
            section["tool_version"] = probe.get("version")
            section["reason"] = "signtool_present_cert_unavailable"
        else:
            section["reason"] = "signtool_unavailable"
        return section
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
