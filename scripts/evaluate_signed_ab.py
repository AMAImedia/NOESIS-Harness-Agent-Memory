#!/usr/bin/env python3
"""Compare signed runner evidence only when protocol fingerprints match."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from scripts.ingest_runner_result import verify_evidence

SYSTEMS = ("noesis", "hermes", "opencode")


def evaluate(evidence: Sequence[Mapping[str, Any]], key: str) -> dict:
    rows = []
    for record in evidence:
        valid = verify_evidence(record, key)
        row = dict(record)
        row["signature_valid"] = valid
        rows.append(row)
    accepted = [row for row in rows if row.get("accepted") is True and row.get("signature_valid")]
    fingerprints = {row.get("protocol_fingerprint") for row in accepted}
    systems = {row.get("system") for row in accepted}
    comparable = len(accepted) >= 2 and len(fingerprints) == 1
    reason = "protocol_fingerprint_match" if comparable else "signed evidence incomplete or protocol fingerprints differ"
    metric_names = sorted({name for row in accepted for name in (row.get("metrics") or {})})
    metrics: dict[str, dict[str, Any]] = {}
    for name in metric_names:
        values = []
        statuses = {}
        for row in accepted:
            record = (row.get("metrics") or {}).get(name, {})
            statuses[row.get("system")] = record.get("status", "not_run")
            if comparable and record.get("status") in {"observed", "passed", "failed"} and isinstance(record.get("value"), (int, float)):
                values.append({"system": row.get("system"), "value": record["value"]})
        metrics[name] = {"comparable": comparable and len(values) >= 2, "values": values if comparable else [], "statuses": statuses, "reason": reason if not comparable else "shared protocol fingerprint"}
    return {
        "schema_version": "noesis.signed-ab-evaluation.v1",
        "comparable": comparable,
        "reason": reason,
        "protocol_fingerprints": sorted(str(item) for item in fingerprints if item),
        "systems": sorted(str(item) for item in systems if item),
        "records": [{"system": row.get("system"), "revision": row.get("revision"), "accepted": row.get("accepted"), "signature_valid": row.get("signature_valid")} for row in rows],
        "metrics": metrics,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate signed external A/B evidence")
    parser.add_argument("--evidence", nargs="+", required=True)
    parser.add_argument("--key", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    records = [json.loads(Path(path).read_text(encoding="utf-8")) for path in args.evidence]
    report = evaluate(records, args.key)
    Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": args.output, "comparable": report["comparable"], "reason": report["reason"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
