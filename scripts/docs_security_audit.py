#!/usr/bin/env python3
"""Audit Markdown examples for high-risk copy/paste patterns."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

PATTERNS = (
    ("credential_literal", re.compile(r"(?:sk-[A-Za-z0-9]{16,}|ghp_[A-Za-z0-9]{20,}|hf_[A-Za-z0-9]{20,})"), "high"),
    ("pipe_to_shell", re.compile(r"\b(?:curl|wget)\b[^\n|]*\|\s*(?:sh|bash|zsh)\b"), "high"),
    ("destructive_rm", re.compile(r"\brm\s+-rf\s+(?:/|~|\$HOME)"), "high"),
    ("inline_eval_exec", re.compile(r"\b(?:eval|exec)\s*\("), "high"),
    ("shell_interpolation", re.compile(r"(?:shell=True|os\.system\s*\(|subprocess\.run\s*\([^\n]*\+[^\n]*\))"), "medium"),
    ("privileged_command", re.compile(r"\bsudo\s+(?:-S\s+)?(?:rm|chmod|chown|curl|wget|pip|python)\b"), "medium"),
)


def fenced_lines(text: str):
    inside = False
    for number, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith("```"):
            inside = not inside
            continue
        if inside:
            yield number, line


def audit(root: str) -> dict:
    base = Path(root).expanduser().resolve()
    findings = []
    for path in sorted(base.rglob("*.md")) if base.is_dir() else (base,):
        if not path.is_file() or any(part in {".git", "__pycache__"} for part in path.parts):
            continue
        for line_number, line in fenced_lines(path.read_text(encoding="utf-8", errors="replace")):
            for name, pattern, severity in PATTERNS:
                if pattern.search(line):
                    findings.append({"file": str(path), "line": line_number, "rule": name, "severity": severity})
    return {"schema_version": "noesis.docs-security.v1", "root": str(base), "findings": findings, "high_count": sum(item["severity"] == "high" for item in findings), "medium_count": sum(item["severity"] == "medium" for item in findings), "clean": not findings}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Audit Markdown code examples")
    parser.add_argument("--root", default="docs")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = audit(args.root)
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else ("CLEAN" if result["clean"] else "FINDINGS: %d" % len(result["findings"])))
    return 0 if result["clean"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
