from __future__ import annotations

import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert report["schema_version"] == "noesis.parallel-documentation-audit.v1"
assert report["network_allowed"] is False
assert report["credentials_available"] is False
assert report["model_generated_code_executed"] is False
assert report["native_builds_executed"] is False
assert report["workspace_count"] == 4
assert len(report["results"]) == 4
assert all(item["status"] == "passed" for item in report["results"])
assert len({item["workspace"] for item in report["results"]}) == 4
security = next(item for item in report["results"] if item["task_id"] == "docs-security")["output"]
assert security["high"] == 0
assert security["medium"] == 0
links = next(item for item in report["results"] if item["task_id"] == "markdown-links")["output"]
assert links["missing"] == 0
assert links["local_links"] >= 20
schemas = next(item for item in report["results"] if item["task_id"] == "json-evidence")["output"]
assert schemas["files_checked"] >= 11
assert schemas["findings"] == 0
checklist = next(item for item in report["results"] if item["task_id"] == "ru-checklist")["output"]
assert checklist["missing"] == []
encoded = json.dumps(report, ensure_ascii=False).casefold()
for marker in ("api_key=", "bearer ", "password=", "secret=", "token="):
    assert marker not in encoded
print("parallel documentation audit validation: PASS")
