from __future__ import annotations

import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert report["schema_version"] == "noesis.parallel-release-lanes.v1"
assert report["simulation_only"] is False
assert report["network_allowed"] is False
assert report["credentials_available"] is False
assert report["model_generated_code_executed"] is False
assert report["workspace_count"] == 4
assert len(report["results"]) == 4
assert all(item["status"] == "passed" for item in report["results"])
assert len({item["workspace"] for item in report["results"]}) == 4
native = next(item for item in report["results"] if item["task_id"] == "native-target-honesty")
assert all(value["evidence_status"] == "not_run" and value["reason"] == "target_host_or_python_mismatch" for value in native["output"]["targets"].values())
encoded = json.dumps(report, ensure_ascii=False).casefold()
for marker in ("api_key=", "bearer ", "password=", "secret=", "token="):
    assert marker not in encoded
print("parallel release report validation: PASS")
