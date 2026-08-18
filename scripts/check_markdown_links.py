"""Check local Markdown links without network access."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import unquote

LINK_RE = re.compile(r"(?<!!)(?:\[[^\]]*\]\(([^)]+)\))")
SKIP_DIRS = {".git", "__pycache__", "runtime", "node_modules", "dist", "build"}


def audit(root: str) -> dict[str, Any]:
    base = Path(root).expanduser().resolve()
    links: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    files = sorted(path for path in base.rglob("*.md") if path.is_file() and not any(part in SKIP_DIRS for part in path.parts))
    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in LINK_RE.finditer(text):
            raw = match.group(1).strip().strip("<>")
            target = raw.split()[0] if raw.split() else ""
            if not target or target.startswith(("https://", "http://", "mailto:", "#")):
                continue
            target_path, _, fragment = target.partition("#")
            resolved = (path.parent / unquote(target_path)).resolve()
            item = {"source": str(path.relative_to(base)), "target": target, "resolved": str(resolved), "fragment": fragment}
            links.append(item)
            try:
                resolved.relative_to(base)
            except ValueError:
                findings.append({**item, "rule": "link_outside_root"})
                continue
            if not resolved.exists():
                findings.append({**item, "rule": "missing_local_target"})
    return {"schema_version": "noesis.markdown-links.v1", "root": str(base), "markdown_files": len(files), "local_links": len(links), "findings": findings, "missing_count": len(findings), "clean": not findings}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Check local Markdown links")
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
