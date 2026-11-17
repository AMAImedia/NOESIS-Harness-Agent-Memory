from __future__ import annotations

import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert report["schema_version"] == "noesis.parallel-ci-consistency.v1"
assert report["native_builds_executed"] is False
assert report["network_allowed"] is False
assert report["credentials_available"] is False
assert report["model_generated_code_executed"] is False
assert report["workspace_count"] == 4
assert len(report["results"]) == 4
assert all(item["status"] == "passed" for item in report["results"])
assert len({item["workspace"] for item in report["results"]}) == 4
for task_id in ("ci-markers", "runbook-markers"):
    item = next(result for result in report["results"] if result["task_id"] == task_id)
    assert item["output"]["missing"] == []
portable = next(result for result in report["results"] if result["task_id"] == "portable-ci-gate")
assert portable["output"]["status"] == "passed"
targets = next(result for result in report["results"] if result["task_id"] == "target-honesty-gate")["output"]["targets"]
assert all(value["evidence_status"] == "not_run" and value["reason"] == "target_host_or_python_mismatch" for value in targets.values())
encoded = json.dumps(report, ensure_ascii=False).casefold()
for marker in ("api_key=", "bearer ", "password=", "secret=", "token="):
    assert marker not in encoded
print("parallel CI consistency report validation: PASS")
