import ast
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "noesis_harness"
patterns = [
    re.compile(r"hf_[A-Za-z0-9]{12,}"),
    re.compile(r"sk-[A-Za-z0-9]{12,}"),
    re.compile(r"ghp_[A-Za-z0-9]{12,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{12,}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
]
actual_eval_exec = []
syntax_errors = []
secret_hits = []
synthetic_fixture_hits = []
for path in sorted(PACKAGE.rglob("*.py")):
    text = path.read_text(encoding="utf-8")
    for pattern in patterns:
        for match in pattern.finditer(text):
            hit = {"file": str(path.relative_to(ROOT)), "pattern": pattern.pattern, "offset": match.start()}
            if path.name == "security_holdouts.py":
                synthetic_fixture_hits.append(hit)
            else:
                secret_hits.append(hit)
    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError as exc:
        syntax_errors.append({"file": str(path.relative_to(ROOT)), "error": str(exc)})
        continue
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in {"eval", "exec"}:
            actual_eval_exec.append({"file": str(path.relative_to(ROOT)), "line": node.lineno, "name": node.func.id})
remote = subprocess.check_output(["git", "ls-remote", "origin", "refs/heads/main"], cwd=str(ROOT), text=True).split()[0]
local = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(ROOT), text=True).strip()
checklist = (ROOT / "docs" / "PROJECT_CHECKLIST_TODO_RU.md").read_text(encoding="utf-8")
result = {
    "local_sha": local,
    "remote_sha": remote,
    "remote_matches_local": local == remote,
    "actual_ast_eval_exec_calls": actual_eval_exec,
    "syntax_errors": syntax_errors,
    "secret_like_hits": secret_hits,
    "synthetic_fixture_hits": synthetic_fixture_hits,
    "clean": local == remote and not actual_eval_exec and not syntax_errors and not secret_hits,
}
print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
