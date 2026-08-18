from __future__ import annotations

import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert report["schema_version"] == "noesis.parallel-release-audit.v1"
assert report["mode"] == "offline"
assert report["network_allowed"] is False
assert report["credentials_available"] is False
assert report["model_generated_code_executed"] is False
assert report["remote_parity_checked"] is False
assert report["workspace_count"] == 4
assert len(report["results"]) == 4
assert all(item["status"] == "passed" for item in report["results"])
assert len({item["workspace"] for item in report["results"]}) == 4
security = next(item for item in report["results"] if item["task_id"] == "secret-ast-audit")["output"]
assert security["secret_hits"] == 0
assert security["syntax_errors"] == 0
assert security["eval_exec_calls"] == 0
git_lane = next(item for item in report["results"] if item["task_id"] == "git-integrity")["output"]
assert git_lane["diff_check"] is True
assert git_lane["working_tree_clean"] is True
exports = next(item for item in report["results"] if item["task_id"] == "package-exports")["output"]
assert exports["export_count"] >= 8
encoded = json.dumps(report, ensure_ascii=False).casefold()
for marker in ("api_key=", "bearer ", "password=", "secret=", "token="):
    assert marker not in encoded
print("parallel offline release audit validation: PASS")
