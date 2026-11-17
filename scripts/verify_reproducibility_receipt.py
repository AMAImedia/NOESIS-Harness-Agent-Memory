"""Verify a transferred reproducibility receipt independently.

The verifier reads only four JSON metadata files and performs no pipeline,
provider, network, child-runtime, or artifact-content execution.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.reproducibility_receipt import verify_reproducibility_receipt

SCHEMA = "noesis.reproducibility-verification.v1"


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("reproducibility_json_object_required")
    return value


def verify_reproducibility_set(root: str | Path, key: str) -> dict[str, Any]:
    base = Path(root).resolve()
    required = {"artifact-manifest.json", "signed-external-evidence-aggregate.json", "chain-summary.json", "reproducibility-receipt.json"}
    if not base.is_dir():
        return {"schema_version": SCHEMA, "status": "blocked", "reason": "reproducibility_root_missing", "automatic_execution": False}
    missing = sorted(name for name in required if not (base / name).is_file())
    if missing:
        return {"schema_version": SCHEMA, "status": "blocked", "reason": "reproducibility_component_missing", "missing": missing, "automatic_execution": False}
    try:
        inventory = _read(base / "artifact-manifest.json")
        aggregate = _read(base / "signed-external-evidence-aggregate.json")
        chain = _read(base / "chain-summary.json")
        receipt = _read(base / "reproducibility-receipt.json")
        result = verify_reproducibility_receipt(receipt, str(inventory.get("inventory_digest", "")), str(aggregate.get("aggregate_digest", "")), str(chain.get("chain_digest", "")), key)
        return {"schema_version": SCHEMA, "status": result.get("status", "blocked"), "reason": result.get("reason"), "receipt_digest": result.get("receipt_digest", ""), "runtime_fingerprint": result.get("runtime_fingerprint", {}), "automatic_execution": False, "external_execution_claim": False}
    except (OSError, ValueError, json.JSONDecodeError, TypeError) as exc:
        return {"schema_version": SCHEMA, "status": "blocked", "reason": type(exc).__name__ + ":" + str(exc)[:160], "automatic_execution": False}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify a NOESIS reproducibility receipt offline")
    parser.add_argument("--root", required=True)
    parser.add_argument("--key", required=True)
    args = parser.parse_args(argv)
    result = verify_reproducibility_set(args.root, args.key)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("status") == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
