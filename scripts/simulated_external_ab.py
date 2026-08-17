#!/usr/bin/env python3
"""Produce a protocol-level simulated A/B report without pretending to run external agents."""
from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "benchmarks" / "external_ab_manifest_v1.json"


def run_noesis_contract_lane() -> dict:
    started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="noesis-sim-ab-") as temp_dir:
        result_path = Path(temp_dir) / "noesis-contracts.json"
        proc = subprocess.run([sys.executable, str(ROOT / "scripts" / "benchmark_contracts.py"), "--output", str(result_path)], cwd=ROOT, text=True, capture_output=True, check=False)
        try:
            data = json.loads(result_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            data = {"summary": {"passed": 0, "failed": 1, "not_run": 0}, "parse_error": proc.stderr[-1000:]}
    summary = data.get("summary", {})
    passed = int(summary.get("passed", 0))
    failed = int(summary.get("failed", 0))
    total = passed + failed + int(summary.get("not_run", 0))
    status = "passed" if failed == 0 else "failed"
    latency_ms = round((time.perf_counter() - started) * 1000.0, 2)
    observed = {
        "task_success": {"status": "observed", "value": 1.0 if status == "passed" else 0.0},
        "test_pass_rate": {"status": "observed", "value": round(passed / total, 6) if total else 0.0},
        "latency_ms": {"status": "observed", "value": latency_ms},
    }
    for metric in ("patch_correctness", "token_or_cost_budget", "unauthorized_egress", "credential_exposure", "approval_bypass", "workspace_escape", "kill_timeout_recovery", "human_review_seconds"):
        observed[metric] = {"status": "not_run", "reason": "not measured by deterministic contract lane"}
    return {"execution": "observed_local", "status": status, "metrics": {"contract_cases_passed": passed, "contract_cases_failed": failed, "contract_cases_not_run": int(summary.get("not_run", 0)), "metric_records": observed}}


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
