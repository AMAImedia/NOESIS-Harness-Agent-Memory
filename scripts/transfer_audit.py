"""Audit the expected composition of a transferred NOESIS evidence directory.

Patterns are adapted from artifact inventories, strict offline verification, and
portable operator runbooks. The audit checks names and file presence only; it
never executes or interprets artifact contents.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

SCHEMA = "noesis.operator-transfer-audit.v1"
REQUIRED = frozenset({
    "artifact-manifest.json",
    "external-evidence-readiness.json",
    "signed-external-evidence-aggregate.json",
    "verification-result.json",
    "chain-summary.json",
    "reproducibility-receipt.json",
})
OPTIONAL = frozenset({"operator-report.zip", "release-gate.json", "release-readiness.json", "signed-readiness-receipt.json", "execution-conformance.json"})


def audit_transfer_set(root: str | Path, report_path: str | None = None, require_readiness_receipt: bool = False) -> dict[str, Any]:
    base = Path(root).resolve()
    if not base.is_dir():
        return {"schema_version": SCHEMA, "status": "blocked", "reason": "transfer_root_missing", "automatic_execution": False}
    names = {path.name for path in base.iterdir() if path.is_file()}
    missing = sorted(REQUIRED - names)
    unexpected = sorted(names - REQUIRED - OPTIONAL)
    if report_path:
        report = Path(report_path).resolve()
        if base not in report.parents or report.name not in OPTIONAL or not report.is_file():
            return {"schema_version": SCHEMA, "status": "blocked", "reason": "transfer_report_invalid", "missing": missing, "unexpected": unexpected, "automatic_execution": False}
    if require_readiness_receipt and "signed-readiness-receipt.json" not in names:
        return {"schema_version": SCHEMA, "status": "blocked", "reason": "transfer_readiness_receipt_missing", "missing": ["signed-readiness-receipt.json"], "unexpected": unexpected, "automatic_execution": False}
    if missing:
        return {"schema_version": SCHEMA, "status": "blocked", "reason": "transfer_required_artifact_missing", "missing": missing, "unexpected": unexpected, "automatic_execution": False}
    if unexpected:
        return {"schema_version": SCHEMA, "status": "blocked", "reason": "transfer_unexpected_artifact", "missing": missing, "unexpected": unexpected, "automatic_execution": False}
    return {"schema_version": SCHEMA, "status": "passed", "required": sorted(REQUIRED), "optional": sorted(OPTIONAL), "present": sorted(names), "automatic_execution": False}
