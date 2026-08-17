#!/usr/bin/env python3
"""Produce a protocol-level simulated A/B report without pretending to run external agents."""
from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "benchmarks" / "external_ab_manifest_v1.json"


def run_noesis_contract_lane() -> dict:
    with tempfile.TemporaryDirectory(prefix="noesis-sim-ab-") as temp_dir:
        result_path = Path(temp_dir) / "noesis-contracts.json"
        proc = subprocess.run([sys.executable, str(ROOT / "scripts" / "benchmark_contracts.py"), "--output", str(result_path)], cwd=ROOT, text=True, capture_output=True, check=False)
        try:
            data = json.loads(result_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            data = {"summary": {"passed": 0, "failed": 1, "not_run": 0}, "parse_error": proc.stderr[-1000:]}
    summary = data.get("summary", {})
    return {"execution": "observed_local", "status": "passed" if summary.get("failed", 1) == 0 else "failed", "metrics": {"contract_cases_passed": summary.get("passed", 0), "contract_cases_failed": summary.get("failed", 0), "contract_cases_not_run": summary.get("not_run", 0)}}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    observed = run_noesis_contract_lane()
    report = {
        "schema_version": "noesis.simulated-external-ab.v1",
        "simulation_only": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "runtime": {"python": platform.python_version(), "platform": platform.platform()},
        "manifest": {"schema_version": manifest["schema_version"], "task_count": len(manifest["tasks"]), "metrics": manifest["metrics"]},
        "systems": {
            "noesis": {**observed, "interpretation": "Observed local contract lane; not a quality ranking."},
            "hermes": {"execution": "not_run", "status": "not_run", "reason": "No pinned Hermes runner was executed in this sandbox."},
            "opencode": {"execution": "not_run", "status": "not_run", "reason": "No pinned OpenCode runner was executed in this sandbox."}
        },
        "comparison": {"performance_comparable": False, "reason": "External runners, exact revisions and same model/provider were not available.", "next_action": "Run the same manifest in disposable native runners and replace not_run records with signed evidence."}
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "simulation_only": True, "noesis_status": observed["status"], "hermes": "not_run", "opencode": "not_run"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
