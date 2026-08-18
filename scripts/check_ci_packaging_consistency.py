"""Check CI packaging job and native runbook for aligned evidence gates."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def check(root: str = str(ROOT)) -> dict[str, Any]:
    project = Path(root).resolve()
    workflow = (project / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    runbook_path = project / "docs" / "locales" / "ru" / "NATIVE_PACKAGING_RUNBOOK_RU.md"
    runbook = runbook_path.read_text(encoding="utf-8")
    ci_markers = (
        "python scripts/verify_python314.py --json",
        "python scripts/build_portable_artifact.py",
        "python scripts/verify_portable_artifact.py",
        "python scripts/verify_native_artifact.py --target",
        "for target in windows macos",
        "target_host_or_python_mismatch",
    )
    runbook_markers = (
        "Python 3.14.7",
        "scripts/build_portable_artifact.py",
        "scripts/verify_portable_artifact.py",
        "--development-unsigned",
        "target_host_or_python_mismatch",
        "native evidence",
    )
    missing_ci = [marker for marker in ci_markers if marker not in workflow]
    missing_runbook = [marker for marker in runbook_markers if marker.casefold() not in runbook.casefold()]
    result = {
        "schema_version": "noesis.ci-packaging-consistency.v1",
        "status": "passed" if not missing_ci and not missing_runbook else "failed",
        "ci": {"path": str(project / ".github" / "workflows" / "ci.yml"), "missing_markers": missing_ci},
        "runbook": {"path": str(runbook_path), "missing_markers": missing_runbook},
        "native_claim_policy": "static_and_target_honesty_only_until_native_hosts",
    }
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Check CI/native packaging runbook consistency")
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    report = check(args.root)
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if report["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
