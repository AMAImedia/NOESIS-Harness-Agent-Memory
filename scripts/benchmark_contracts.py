#!/usr/bin/env python3
"""Run the deterministic NOESIS contract benchmark lane."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

CASES = (
    "tests.test_task_session_api",
    "tests.test_session_stream",
    "tests.test_provider_invocation",
    "tests.test_gatekeeper",
    "tests.test_child_execution",
    "tests.test_skill_runtime",
    "tests.test_workspaces",
    "tests.test_multi_agent_runtime",
    "tests.test_health_session_api",
    "tests.test_terminal_client",
)


def run_case(case: str) -> dict:
    started = time.perf_counter()
    process = subprocess.run([sys.executable, "-m", "unittest", case, "-q"], capture_output=True, text=True, timeout=120)
    return {"case": case, "status": "passed" if process.returncode == 0 else "failed", "duration_ms": round((time.perf_counter() - started) * 1000.0, 2), "stdout_tail": process.stdout[-1000:], "stderr_tail": process.stderr[-1000:]}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run NOESIS deterministic contract benchmark lane")
    parser.add_argument("--output", default="benchmark_contracts.json")
    args = parser.parse_args(argv)
    results = [run_case(case) for case in CASES]
    payload = {"schema_version": "noesis.benchmark.contracts.v1", "runtime": "%d.%d.%d" % sys.version_info[:3], "cases": results, "summary": {"passed": sum(row["status"] == "passed" for row in results), "failed": sum(row["status"] == "failed" for row in results), "not_run": 0}}
    Path(args.output).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload["summary"], sort_keys=True))
    return 0 if payload["summary"]["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
