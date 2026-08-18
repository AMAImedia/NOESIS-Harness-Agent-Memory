from __future__ import annotations

import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert report["schema_version"] == "noesis.parallel-build-policy.v1"
assert report["native_builds_executed"] is False
assert report["network_allowed"] is False
assert report["credentials_available"] is False
assert report["model_generated_code_executed"] is False
assert report["workspace_count"] == 4
assert len(report["results"]) == 4
assert all(item["status"] == "passed" for item in report["results"])
assert len({item["workspace"] for item in report["results"]}) == 4
for target in ("windows-dry-run", "macos-dry-run"):
    item = next(result for result in report["results"] if result["task_id"] == target)
    assert item["output"]["dry_run"] is True
    assert item["output"]["run_permitted"] is False
    assert item["output"]["target_report"]["platform_ok"] is False
    assert item["output"]["target_report"]["python_ok"] is True
signing = next(result for result in report["results"] if result["task_id"] == "signing-policy")
assert signing["output"]["native_builds_executed"] is False
assert all("required" in value["signature_policy"].casefold() for value in signing["output"]["policies"].values())
python_lane = next(result for result in report["results"] if result["task_id"] == "python314-dry-run")
assert python_lane["output"]["actual"] == "3.14.7"
encoded = json.dumps(report, ensure_ascii=False).casefold()
for marker in ("api_key=", "bearer ", "password=", "secret=", "token="):
    assert marker not in encoded
print("parallel build policy report validation: PASS")
