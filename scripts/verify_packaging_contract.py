#!/usr/bin/env python3
"""Audit static native packaging contracts without building native artifacts."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_TARGETS = ("windows", "macos")


def audit(root: str = str(ROOT)) -> dict:
    project = Path(root).resolve()
    findings = []
    manifests = []
    for target in REQUIRED_TARGETS:
        path = project / "packaging" / f"{target}_manifest.json"
        if not path.is_file():
            findings.append({"target": target, "status": "failed", "reason": "manifest_missing"})
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        errors = []
        if data.get("schema_version") != "noesis.native-packaging-manifest.v1":
            errors.append("schema_version")
        if data.get("target") != target:
            errors.append("target")
        if data.get("runtime", {}).get("policy") != "python-3.14-only":
            errors.append("python_policy")
        commands = " ".join(item.get("command", "") for item in data.get("backends", []))
        if "scripts/build_native.py" not in commands and "scripts\\build_native.py" not in commands:
            errors.append("build_command")
        verification = " ".join(data.get("verification", []))
        if "verify_native_artifact.py" not in verification:
            errors.append("native_verifier_command")
        if "PORTABLE_SBOM.spdx.json" not in verification:
            errors.append("sbom_gate")
        if "sha256" not in verification.casefold():
            errors.append("sha256_gate")
        if "signature_policy" not in data:
            errors.append("signature_policy")
        manifests.append({"target": target, "path": str(path), "status": "passed" if not errors else "failed", "errors": errors})
        if errors:
            findings.append(manifests[-1])
    return {
        "schema_version": "noesis.packaging-contract.v1",
        "runtime_policy": "python-3.14-only",
        "native_builds_executed": False,
        "status": "passed" if not findings else "failed",
        "manifests": manifests,
        "findings": findings,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Audit NOESIS native packaging contracts")
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    report = audit(args.root)
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if report["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
