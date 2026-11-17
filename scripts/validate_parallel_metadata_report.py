from __future__ import annotations

import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert report["schema_version"] == "noesis.parallel-metadata-coverage.v1"
assert report["network_allowed"] is False
assert report["credentials_available"] is False
assert report["model_generated_code_executed"] is False
assert report["native_builds_executed"] is False
assert report["workspace_count"] == 4
assert len(report["results"]) == 4
assert all(item["status"] == "passed" for item in report["results"])
assert len({item["workspace"] for item in report["results"]}) == 4
metadata = next(item for item in report["results"] if item["task_id"] == "release-metadata")["output"]
assert metadata["required_files"] == 7
assert metadata["checks"] == 9
assert metadata["upstreams"] == 5
provenance = next(item for item in report["results"] if item["task_id"] == "license-provenance")["output"]
assert provenance["upstreams"] == 5
assert provenance["code_copied"] is False
assert provenance["runtime_dependency"] is False
changelog = next(item for item in report["results"] if item["task_id"] == "changelog-docs")["output"]
assert changelog["missing"] == []
sbom = next(item for item in report["results"] if item["task_id"] == "portable-sbom")["output"]
assert sbom["status"] == "passed"
encoded = json.dumps(report, ensure_ascii=False).casefold()
for marker in ("api_key=", "bearer ", "password=", "secret=", "token="):
    assert marker not in encoded
print("parallel metadata coverage validation: PASS")
