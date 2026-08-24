"""Read-only NOESIS release audit.

Offline by default. Remote SHA parity is opt-in with ``--remote`` so a local
security audit never performs an unexpected network operation.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "noesis_harness"
def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


PATTERNS = [
    re.compile(r"hf_[A-Za-z0-9]{12,}"),
    re.compile(r"sk-[A-Za-z0-9]{12,}"),
    re.compile(r"ghp_[A-Za-z0-9]{12,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{12,}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
]


def _commit_exists(project: Path, checkpoint: str) -> bool:
    try:
        subprocess.check_output(["git", "cat-file", "-e", checkpoint + "^{commit}"], cwd=str(project), text=True, stderr=subprocess.DEVNULL)
        return True
    except (OSError, subprocess.CalledProcessError):
        return False


def _commit_is_ancestor(project: Path, checkpoint: str, head: str) -> bool:
    try:
        subprocess.check_output(["git", "merge-base", "--is-ancestor", checkpoint, head], cwd=str(project), text=True, stderr=subprocess.DEVNULL)
        return True
    except (OSError, subprocess.CalledProcessError):
        return False


def audit(root: str = str(ROOT), *, include_remote: bool = False, remote_branch: str = "main") -> dict[str, Any]:

    project = Path(root).resolve()
    package = project / "noesis_harness"
    actual_eval_exec: list[dict[str, Any]] = []
    syntax_errors: list[dict[str, Any]] = []
    secret_hits: list[dict[str, Any]] = []
    synthetic_fixture_hits: list[dict[str, Any]] = []
    readiness_path = project / "docs" / "EXTERNAL_EVIDENCE_READINESS_MATRIX.json"
    readiness: dict[str, Any] = {}
    readiness_errors: list[str] = []
    roadmap_errors: list[str] = []
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
            if readiness.get("execution_claim") not in {"not_run", "evidence_ingestion_only"}:
                readiness_errors.append("execution_claim_invalid")
            if readiness.get("comparative_ready") is not False and readiness.get("overall_status") != "passed":
                readiness_errors.append("comparative_status_contradiction")
            expected_digest = readiness.get("matrix_digest")
            canonical_digest = _digest({"lanes": lanes, "global_checks": readiness.get("global_checks", [])})
            if expected_digest != canonical_digest:
                readiness_errors.append("readiness_digest_mismatch")
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
    roadmap_path = project / "docs" / "ROADMAP_RECONCILIATION_EVIDENCE.json"
    if roadmap_path.exists():
        try:
            roadmap = json.loads(roadmap_path.read_text(encoding="utf-8"))
            if roadmap.get("schema_version") != "noesis.roadmap-reconciliation.v1":
                roadmap_errors.append("roadmap_schema_mismatch")
            checkpoint = roadmap.get("checkpoint_commit")
            if not isinstance(checkpoint, str) or len(checkpoint) != 40 or any(character not in "0123456789abcdef" for character in checkpoint.lower()):
                roadmap_errors.append("roadmap_checkpoint_invalid")
            elif not _commit_exists(project, checkpoint):
                roadmap_errors.append("roadmap_checkpoint_unresolvable")
            elif not _commit_is_ancestor(project, checkpoint, local):
                roadmap_errors.append("roadmap_checkpoint_not_ancestor")
            if roadmap.get("status") != "local_reconciliation_and_next03_bounded_verified":
                roadmap_errors.append("roadmap_status_mismatch")
            gate = roadmap.get("next_local_gate")
            if not isinstance(gate, dict) or gate.get("id") != "NEXT-03":
                roadmap_errors.append("roadmap_next_gate_mismatch")
            else:
                if gate.get("automatic_activation") is not False:
                    roadmap_errors.append("roadmap_activation_guard_missing")
                if gate.get("facade_status") != "bounded_local_verified" or gate.get("deployment_binding_status") != "bounded_local_verified" or gate.get("durable_state_status") != "locally_verified":
                    roadmap_errors.append("roadmap_local_status_mismatch")
                if gate.get("child_runtime_status") != "in_progress_bounded_local":
                    roadmap_errors.append("roadmap_child_runtime_status_mismatch")
                if gate.get("open_subgates") != ["native_windows_macos_evidence"]:
                    roadmap_errors.append("roadmap_open_subgates_mismatch")
                required_verified = {"durable_long_context_reuse_trajectories", "broader_active_delegation_leakage_holdouts", "long_context_stress_fixture"}
                if not required_verified.issubset(set(gate.get("verified_subgates", []))):
                    roadmap_errors.append("roadmap_verified_subgates_incomplete")
            boundaries = roadmap.get("external_boundaries")
            if not isinstance(boundaries, dict) or any(boundaries.get(key) != "not_run" for key in ("windows_native", "macos_native", "hermes_external_ab", "opencode_external_ab", "deepseek_harness_external_ab")) or boundaries.get("superiority_claim") is not False:
                roadmap_errors.append("roadmap_external_boundary_mismatch")
        except (OSError, json.JSONDecodeError, TypeError):
            roadmap_errors.append("roadmap_artifact_invalid")
    status = subprocess.check_output(["git", "status", "--porcelain"], cwd=str(project), text=True)
    remote = None

    remote_error = None
    if include_remote:
        try:

            if not remote_branch or remote_branch.startswith("-") or any(character.isspace() for character in remote_branch):
                raise ValueError("invalid remote branch")
            remote = subprocess.check_output(["git", "ls-remote", "origin", "refs/heads/" + remote_branch], cwd=str(project), text=True).split()[0]

        except (OSError, subprocess.CalledProcessError, IndexError, ValueError) as exc:
            remote_error = type(exc).__name__ + ": " + str(exc)

    remote_matches_local = None if not include_remote else remote == local
    clean = not actual_eval_exec and not syntax_errors and not secret_hits and not status and not readiness_errors and not roadmap_errors and (not include_remote or remote_matches_local is True)
    return {
        "schema_version": "noesis.local-release-audit.v1",
        "mode": "remote-parity" if include_remote else "offline",
        "local_sha": local,

        "remote_branch": remote_branch if include_remote else None,

        "remote_sha": remote,

        "remote_error": remote_error,
        "remote_matches_local": remote_matches_local,
        "working_tree_clean": not bool(status),
        "actual_ast_eval_exec_calls": actual_eval_exec,
        "syntax_errors": syntax_errors,
        "secret_like_hits": secret_hits,
        "synthetic_fixture_hits": synthetic_fixture_hits,
        "roadmap_consistency": {"path": str(roadmap_path), "errors": roadmap_errors, "checkpoint_valid": not any(error.startswith("roadmap_checkpoint_") for error in roadmap_errors)},
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

    parser.add_argument("--remote-branch", default="main", help="remote branch for parity check (default: main)")

    parser.add_argument("--output")
    args = parser.parse_args(argv)
    report = audit(args.root, include_remote=args.remote, remote_branch=args.remote_branch)

    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if report["clean"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
