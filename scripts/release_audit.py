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
    readiness_path = project / "docs" / "EXTERNAL_EVIDENCE_READINESS_MATRIX.json"
    readiness: dict[str, Any] = {}
    readiness_errors: list[str] = []
    if readiness_path.exists():
        try:
            readiness = json.loads(readiness_path.read_text(encoding="utf-8"))
            if readiness.get("schema_version") != "noesis.external-evidence-readiness.v1":
                readiness_errors.append("readiness_schema_mismatch")
            allowed = {"passed", "not_run", "blocked", "unsupported"}
            lanes = readiness.get("lanes", {})
            if not isinstance(lanes, dict) or not lanes:
                readiness_errors.append("readiness_lanes_missing")
            elif any(item.get("status") not in allowed for item in lanes.values() if isinstance(item, dict)):
                readiness_errors.append("readiness_status_invalid")
            if readiness.get("native_or_external_execution_claim") is not False:
                readiness_errors.append("external_claim_guard_missing")
        except (OSError, json.JSONDecodeError, TypeError):
            readiness_errors.append("readiness_artifact_invalid")
    else:
        readiness_errors.append("readiness_artifact_missing")
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
    clean = not actual_eval_exec and not syntax_errors and not secret_hits and not status and not readiness_errors and (not include_remote or remote_matches_local is True)
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
        "external_readiness": {
            "path": str(readiness_path),
            "overall_status": readiness.get("overall_status"),
            "comparative_ready": readiness.get("comparative_ready"),
            "native_or_external_execution_claim": readiness.get("native_or_external_execution_claim"),
            "errors": readiness_errors,
        },
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
