"""Check selected JSON evidence/manifests for parseability and schema metadata."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def selected_files(base: Path) -> list[Path]:
    candidates: list[Path] = []
    for root in (base / "docs", base / "packaging", base / "benchmarks"):
        if not root.is_dir():
            continue
        for path in root.rglob("*.json"):
            name = path.name.casefold()
            if "evidence" in name or "provenance" in name or "manifest" in name or name in {"windows_manifest.json", "macos_manifest.json"}:
                candidates.append(path)
    return sorted(set(candidates))


def audit(root: str) -> dict[str, Any]:
    base = Path(root).expanduser().resolve()
    files = selected_files(base)
    findings: list[dict[str, str]] = []
    records: list[dict[str, Any]] = []
    for path in files:
        rel = str(path.relative_to(base))
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            findings.append({"file": rel, "rule": "invalid_json", "detail": str(exc)})
            continue
        if not isinstance(value, dict):
            findings.append({"file": rel, "rule": "root_not_object", "detail": type(value).__name__})
            continue
        if "schema_version" not in value:
            findings.append({"file": rel, "rule": "missing_schema_version", "detail": "selected evidence/manifest JSON must declare schema_version"})
        records.append({"file": rel, "schema_version": value.get("schema_version", "")})
    return {"schema_version": "noesis.json-evidence-audit.v1", "files_checked": len(files), "records": records, "findings": findings, "clean": not findings}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Check selected NOESIS JSON evidence/manifests")
    parser.add_argument("--root", default=".")
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    result = audit(args.root)
    rendered = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if result["clean"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
