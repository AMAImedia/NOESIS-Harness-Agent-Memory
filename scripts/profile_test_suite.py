#!/usr/bin/env python3
"""Profile the full unittest suite with wall-time, memory and per-test timing."""
from __future__ import annotations

import argparse
import json
import re
import resource
import subprocess
import sys
import time
import tracemalloc
import unittest
from pathlib import Path


class TimingResult(unittest.TextTestResult):
    def startTest(self, test: unittest.case.TestCase) -> None:
        self._test_started = time.perf_counter()
        super().startTest(test)

    def stopTest(self, test: unittest.case.TestCase) -> None:
        elapsed = time.perf_counter() - getattr(self, "_test_started", time.perf_counter())
        timings = getattr(self, "timings", [])
        timings.append({"test": self.getDescription(test), "seconds": round(elapsed, 6)})
        self.timings = timings
        super().stopTest(test)


def profile_in_process(root: Path) -> tuple[dict[str, object], int]:
    loader = unittest.defaultTestLoader
    suite = loader.discover(str(root / "tests"))
    stream = __import__("io").StringIO()
    runner = unittest.TextTestRunner(stream=stream, verbosity=0, resultclass=TimingResult)
    tracemalloc.start()
    start = time.perf_counter()
    result = runner.run(suite)
    wall_seconds = time.perf_counter() - start
    _, peak_traced = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    timings = sorted(getattr(result, "timings", []), key=lambda item: item["seconds"], reverse=True)
    return {
        "wall_seconds": round(wall_seconds, 6),
        "peak_tracemalloc_bytes": peak_traced,
        "tests_run": result.testsRun,
        "tests_failed": len(result.failures) + len(result.errors),
        "top_slowest_tests": timings[:20],
        "runner_output_tail": stream.getvalue()[-4000:],
    }, 0 if result.wasSuccessful() else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    python = sys.executable
    command = [python, "-m", "unittest", "discover", "-s", "tests", "-q"]
    child_start = time.perf_counter()
    completed = subprocess.run(command, cwd=root, capture_output=True, text=True, check=False)
    child_wall_seconds = time.perf_counter() - child_start
    max_rss_kib = int(resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)
    in_process, in_process_rc = profile_in_process(root)
    combined_output = completed.stdout + completed.stderr
    match = re.search(r"Ran (\d+) tests", combined_output)
    report = {
        "schema_version": "noesis.test-performance-profile.v2",
        "python": sys.version,
        "python_executable": python,
        "test_command": command,
        "returncode": completed.returncode,
        "tests_run_subprocess": int(match.group(1)) if match else None,
        "wall_seconds": round(child_wall_seconds, 6),
        "peak_tracemalloc_bytes": in_process["peak_tracemalloc_bytes"],
        "child_max_rss_kib": max_rss_kib,
        "resource_semantics": "KiB on Linux; verify units on other hosts",
        "in_process_wall_seconds": in_process["wall_seconds"],
        "tests_run_in_process": in_process["tests_run"],
        "tests_failed_in_process": in_process["tests_failed"],
        "top_slowest_tests": in_process["top_slowest_tests"],
        "stdout_tail": completed.stdout[-4000:],
        "stderr_tail": completed.stderr[-4000:],
        "warning_count": combined_output.count("ResourceWarning"),
        "in_process_returncode": in_process_rc,
    }
    Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("returncode", "tests_run_subprocess", "wall_seconds", "in_process_wall_seconds", "peak_tracemalloc_bytes", "child_max_rss_kib", "warning_count")}, sort_keys=True))
    return 0 if completed.returncode == 0 and in_process_rc == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
