"""Verify a transferred release-gate artifact without rerunning the gate."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.release_gate_artifact import verify_gate_artifact

SCHEMA = "noesis.release-gate-artifact-verification.v1"


def verify_file(path: str | Path) -> dict[str, Any]:
    target = Path(path).resolve()
    if not target.is_file():
        return {"schema_version": SCHEMA, "status": "blocked", "reason": "release_gate_artifact_missing", "automatic_execution": False}
    try:
        artifact = json.loads(target.read_text(encoding="utf-8"))
        result = verify_gate_artifact(artifact)
        return {"schema_version": SCHEMA, "status": result.get("status", "blocked"), "reason": result.get("reason"), "artifact_digest": result.get("artifact_digest", ""), "gate_status": result.get("gate_status"), "automatic_execution": False, "external_execution_claim": False}
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        return {"schema_version": SCHEMA, "status": "blocked", "reason": type(exc).__name__ + ":" + str(exc)[:160], "automatic_execution": False}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify a NOESIS release-gate artifact offline")
    parser.add_argument("--artifact", required=True)
    args = parser.parse_args(argv)
    result = verify_file(args.artifact)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("status") == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
