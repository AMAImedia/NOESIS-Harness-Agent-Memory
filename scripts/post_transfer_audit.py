"""Run the complete NOESIS post-transfer audit without rerunning the pipeline.

The audit performs metadata-only composition, strict artifact-chain, and
reproducibility checks. It never executes artifact contents, providers, child
processes, network requests, or the generation pipeline.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.transfer_audit import audit_transfer_set
from scripts.verify_operator_artifact_set import verify_artifact_set
from scripts.verify_reproducibility_receipt import verify_reproducibility_set

SCHEMA = "noesis.post-transfer-audit.v1"


def audit(root: str | Path, key: str, report: str | None = None) -> dict[str, Any]:
    composition = audit_transfer_set(root, report)
    if composition.get("status") != "passed":
        return {"schema_version": SCHEMA, "status": "blocked", "failed_stage": "composition", "stages": {"composition": composition}, "automatic_execution": False, "external_execution_claim": False}
    chain = verify_artifact_set(root, key, report, require_signed_result=True)
    if chain.get("status") != "passed":
        return {"schema_version": SCHEMA, "status": "blocked", "failed_stage": "artifact_chain", "stages": {"composition": composition, "artifact_chain": chain}, "automatic_execution": False, "external_execution_claim": False}
    reproducibility = verify_reproducibility_set(root, key)
    if reproducibility.get("status") != "passed":
        return {"schema_version": SCHEMA, "status": "blocked", "failed_stage": "reproducibility", "stages": {"composition": composition, "artifact_chain": chain, "reproducibility": reproducibility}, "automatic_execution": False, "external_execution_claim": False}
    return {"schema_version": SCHEMA, "status": "passed", "stages": {"composition": composition, "artifact_chain": chain, "reproducibility": reproducibility}, "automatic_execution": False, "external_execution_claim": False}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run NOESIS post-transfer audit offline")
    parser.add_argument("--root", required=True)
    parser.add_argument("--key", required=True)
    parser.add_argument("--report")
    args = parser.parse_args(argv)
    try:
        result = audit(args.root, args.key, args.report)
    except (OSError, ValueError, json.JSONDecodeError, TypeError) as exc:
        result = {"schema_version": SCHEMA, "status": "blocked", "failed_stage": "input", "reason": type(exc).__name__ + ":" + str(exc)[:160], "automatic_execution": False, "external_execution_claim": False}
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("status") == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
