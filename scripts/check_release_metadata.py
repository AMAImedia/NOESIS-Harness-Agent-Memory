"""Audit release metadata, license attribution and upstream provenance coverage."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_UPSTREAMS = ("cloudflare-os", "cloudflare-sandbox-sdk", "hermes-agent", "opencode", "claude-code")


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def audit(root: str = str(ROOT)) -> dict[str, Any]:
    project = Path(root).resolve()
    findings: list[str] = []
    required_files = ("LICENSE", "README.md", "CHANGELOG.md", "THIRD_PARTY_NOTICES.md", "pyproject.toml", "docs/README.md", "docs/third_party_provenance.json")
    missing_files = [name for name in required_files if not (project / name).is_file()]
    findings.extend("missing_file:" + name for name in missing_files)

    pyproject = _text(project / "pyproject.toml") if (project / "pyproject.toml").is_file() else ""
    readme = _text(project / "README.md") if (project / "README.md").is_file() else ""
    changelog = _text(project / "CHANGELOG.md") if (project / "CHANGELOG.md").is_file() else ""
    docs_index = _text(project / "docs/README.md") if (project / "docs/README.md").is_file() else ""
    notices = _text(project / "THIRD_PARTY_NOTICES.md") if (project / "THIRD_PARTY_NOTICES.md").is_file() else ""

    checks = {
        "python_policy": 'requires-python = ">=3.14"' in pyproject and "Python 3.14" in readme,
        "license_alignment": 'license = "MIT"' in pyproject and "MIT License" in readme and "LICENSE" in required_files,
        "private_release_boundary": "private GitHub repository" in readme and "owner-approved gates" in readme,
        "readme_provenance_links": "THIRD_PARTY_NOTICES.md" in readme and "third_party_provenance.json" in readme,
        "changelog_unreleased": "## [Unreleased]" in changelog,
        "changelog_current_work": "2026-08-18" in changelog and "Python 3.14" in changelog,
        "docs_index_checklist": "PROJECT_CHECKLIST_TODO_RU.md" in docs_index,
        "docs_index_native": "NATIVE_PACKAGING_RUNBOOK_RU.md" in docs_index,
        "docs_index_provenance": "third_party_provenance.json" in docs_index,
    }
    findings.extend("failed_check:" + name for name, ok in checks.items() if not ok)

    provenance_path = project / "docs" / "third_party_provenance.json"
    provenance: dict[str, Any] = {}
    if provenance_path.is_file():
        try:
            provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            findings.append("provenance_invalid_json")
    upstreams = provenance.get("upstreams", []) if isinstance(provenance, dict) else []
    names = {str(item.get("name")) for item in upstreams if isinstance(item, dict)}
    for name in EXPECTED_UPSTREAMS:
        if name not in names:
            findings.append("provenance_missing:" + name)
        if name.replace("-", " ") not in notices.casefold() and name not in notices.casefold():
            findings.append("notice_missing:" + name)
    for item in upstreams:
        if not isinstance(item, dict):
            findings.append("provenance_entry_invalid")
            continue
        for field in ("name", "source", "license", "status", "code_copied", "runtime_dependency", "required_notices"):
            if field not in item:
                findings.append("provenance_field_missing:%s:%s" % (item.get("name", "unknown"), field))

    result = {
        "schema_version": "noesis.release-metadata-coverage.v1",
        "status": "passed" if not findings else "failed",
        "required_files": list(required_files),
        "missing_files": missing_files,
        "checks": checks,
        "expected_upstreams": list(EXPECTED_UPSTREAMS),
        "provenance_names": sorted(names),
        "findings": sorted(set(findings)),
    }
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Audit NOESIS release metadata and provenance coverage")
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
