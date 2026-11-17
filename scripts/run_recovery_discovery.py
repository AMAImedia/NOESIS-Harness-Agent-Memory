"""Bounded recovery discovery runner using unittest isolation and process timeouts.

Patterns are adapted from NOESIS crash-safe recovery, Python unittest discovery,
process-level cancellation, and the project's honest evidence boundaries.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import unittest
from pathlib import Path
from typing import Any, List, Optional, Union

SCHEMA_VERSION = "noesis.recovery-discovery.v1"
DEFAULT_MODULE = "tests.test_execution_recovery"
DEFAULT_TIMEOUT_SECONDS = 30.0


def _test_ids(module_name: str) -> list[str]:
    suite = unittest.defaultTestLoader.loadTestsFromName(module_name)
    identifiers: list[str] = []

    def visit(item: Union[unittest.TestSuite, unittest.TestCase]) -> None:
        if isinstance(item, unittest.TestSuite):
            for child in item:
                visit(child)
        else:
            identifiers.append(item.id())

    visit(suite)
    return identifiers


def _run_case(test_id: str, timeout_seconds: float) -> dict[str, Any]:
    started = time.monotonic()
    command = [sys.executable, "-m", "unittest", test_id, "-q"]
    try:
        completed = subprocess.run(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            check=False,
        )
        status = "passed" if completed.returncode == 0 else "failed"
        output = completed.stdout[-4096:]
        return {
            "test_id": test_id,
            "status": status,
            "returncode": completed.returncode,
            "duration_ms": round((time.monotonic() - started) * 1000.0, 3),
            "output_tail": output,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "test_id": test_id,
            "status": "timed_out",
            "returncode": None,
            "duration_ms": round((time.monotonic() - started) * 1000.0, 3),
            "output_tail": str(exc.stdout or "")[-4096:],
            "timeout_seconds": timeout_seconds,
        }
    except OSError as exc:
        return {
            "test_id": test_id,
            "status": "failed",
            "returncode": None,
            "duration_ms": round((time.monotonic() - started) * 1000.0, 3),
            "output_tail": "launch_failed:%s" % type(exc).__name__,
        }


def run(module_name: str = DEFAULT_MODULE, timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS) -> dict[str, Any]:
    if timeout_seconds <= 0 or timeout_seconds > 300:
        raise ValueError("timeout_seconds_out_of_bounds")
    tests = _test_ids(module_name)
    results = [_run_case(test_id, timeout_seconds) for test_id in tests]
    counts = {status: sum(item["status"] == status for item in results) for status in ("passed", "failed", "timed_out")}
    return {
        "schema_version": SCHEMA_VERSION,
        "module": module_name,
        "timeout_seconds": timeout_seconds,
        "test_count": len(results),
        "counts": counts,
        "status": "passed" if results and counts["failed"] == 0 and counts["timed_out"] == 0 else "incomplete" if counts["timed_out"] else "failed",
        "results": results,
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run recovery discovery with one bounded process per test")
    parser.add_argument("--module", default=DEFAULT_MODULE)
    parser.add_argument("--timeout-seconds", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    try:
        report = run(args.module, args.timeout_seconds)
    except (ValueError, ImportError, AttributeError) as exc:
        report = {
            "schema_version": SCHEMA_VERSION,
            "module": args.module,
            "timeout_seconds": args.timeout_seconds,
            "test_count": 0,
            "counts": {"passed": 0, "failed": 1, "timed_out": 0},
            "status": "failed",
            "error": type(exc).__name__ + ": " + str(exc),
            "results": [],
        }
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if report["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["DEFAULT_MODULE", "DEFAULT_TIMEOUT_SECONDS", "SCHEMA_VERSION", "run"]

