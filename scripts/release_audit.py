"""Read-only NOESIS release audit.

Offline by default. Remote SHA parity is opt-in with ``--remote`` so a local
security audit never performs an unexpected network operation.
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "noesis_harness"
PATTERNS = [
    re.compile(r"hf_[A-Za-z0-9]{12,}"),
    re.compile(r"sk-[A-Za-z0-9]{12,}"),
    re.compile(r"ghp_[A-Za-z0-9]{12,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{12,}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
]


def audit(root: str = str(ROOT), *, include_remote: bool = False) -> dict[str, Any]:
    project = Path(root).resolve()
    package = project / "noesis_harness"
    actual_eval_exec: list[dict[str, Any]] = []
    syntax_errors: list[dict[str, Any]] = []
    secret_hits: list[dict[str, Any]] = []
    synthetic_fixture_hits: list[dict[str, Any]] = []
    for path in sorted(package.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        for pattern in PATTERNS:
            for match in pattern.finditer(text):
                hit = {"file": str(path.relative_to(project)), "pattern": pattern.pattern, "offset": match.start()}
                if path.name == "security_holdouts.py":
                    synthetic_fixture_hits.append(hit)
                else:
                    secret_hits.append(hit)
        try:
            tree = ast.parse(text, filename=str(path))
        except SyntaxError as exc:
            syntax_errors.append({"file": str(path.relative_to(project)), "error": str(exc)})
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in {"eval", "exec"}:
                actual_eval_exec.append({"file": str(path.relative_to(project)), "line": node.lineno, "name": node.func.id})

    local = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(project), text=True).strip()
    status = subprocess.check_output(["git", "status", "--porcelain"], cwd=str(project), text=True)
    remote = None
    remote_error = None
    if include_remote:
        try:
            remote = subprocess.check_output(["git", "ls-remote", "origin", "refs/heads/main"], cwd=str(project), text=True).split()[0]
        except (OSError, subprocess.CalledProcessError, IndexError) as exc:
            remote_error = type(exc).__name__ + ": " + str(exc)
    remote_matches_local = None if not include_remote else remote == local
    clean = not actual_eval_exec and not syntax_errors and not secret_hits and not status and (not include_remote or remote_matches_local is True)
    return {
        "schema_version": "noesis.local-release-audit.v1",
        "mode": "remote-parity" if include_remote else "offline",
        "local_sha": local,
        "remote_sha": remote,
        "remote_error": remote_error,
        "remote_matches_local": remote_matches_local,
        "working_tree_clean": not bool(status),
        "actual_ast_eval_exec_calls": actual_eval_exec,
        "syntax_errors": syntax_errors,
        "secret_like_hits": secret_hits,
        "synthetic_fixture_hits": synthetic_fixture_hits,
        "clean": clean,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run read-only NOESIS release audit")
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--remote", action="store_true", help="opt in to git ls-remote parity check")
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    report = audit(args.root, include_remote=args.remote)
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if report["clean"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
