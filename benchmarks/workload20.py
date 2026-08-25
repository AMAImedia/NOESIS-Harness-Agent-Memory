"""Gate 4 one-line twin of benchmarks/recall20.py.

Scores a fixed deterministic 20-outcome WorkProduct rubric through
WorkProductBenchmarkEvaluator, then folds in one tiny live MA-07 multi-lane
pass (3 lanes, injected first-attempt crash on one, retry_limit=1) executed
inside a tempdir and cleaned up afterwards.

Provenance: deepseek-harness deterministic bounded-rubric fixtures (via
noesis_harness.work_product_benchmark), agent-teams bounded retry/reclaim
semantics (via noesis_harness.work_product_ma07), CLI/output shape follows
benchmarks/recall20.py. Stdlib only; no wall clock, no randomness.
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from noesis_harness.work_product_benchmark import (
    WorkProductBenchmarkEvaluator,
    WorkProductOutcome,
)
from noesis_harness.work_product_ma07 import LaneSpec, WorkProductWorkloadRunner

# (case_id, correct, delivered, leakage_free, recovered, attempts,
#  reviewer_time_seconds, review_approved, committed)


def _fixture():
    rows = [
        ("w20-01", True, True, True, False, 1, 8.0),
        ("w20-02", True, True, True, False, 1, 11.5),
        ("w20-03", True, True, True, False, 1, 6.75),
        ("w20-04", True, True, True, False, 1, 14.25),
        ("w20-05", True, True, True, False, 1, 9.5),
        ("w20-06", True, True, True, False, 1, 7.25),
        ("w20-07", True, True, True, False, 1, 13.0),
        ("w20-08", True, True, True, False, 1, 10.5),
        ("w20-09", True, True, True, False, 1, 8.75),
        ("w20-10", True, True, True, False, 1, 12.25),
        ("w20-11", True, True, True, False, 1, 9.0),
        ("w20-12", True, True, True, False, 1, 15.5),
        ("w20-13", True, True, True, False, 1, 7.5),
        ("w20-14", True, True, True, False, 1, 11.0),
        ("w20-15", True, True, True, True, 2, 22.5),
        ("w20-16", True, True, True, True, 2, 19.0),
        ("w20-17", True, True, True, True, 3, 31.25),
        ("w20-18", True, True, False, True, 2, 27.5),
    ]
    rows.append(("w20-19", False, True, True, False, 1, 12.0, False))
    rows.append(("w20-20", False, False, True, False, 4, 40.0, False, False))
    outcomes = []
    for row in rows:
        kwargs = {
            "case_id": row[0],
            "correct": row[1],
            "delivered": row[2],
            "leakage_free": row[3],
            "recovered": row[4],
            "attempts": row[5],
            "reviewer_time_seconds": row[6],
        }
        if len(row) > 7:
            kwargs["review_approved"] = row[7]
        if len(row) > 8:
            kwargs["committed"] = row[8]
        outcomes.append(WorkProductOutcome(**kwargs))
    return tuple(outcomes)


def _ma07_probe():
    """One tiny live runner pass: 3 lanes, crash on one, retry_limit=1."""
    root = tempfile.mkdtemp(prefix="noesis_w20_ma07_")
    try:
        runner = WorkProductWorkloadRunner(root)
        report = runner.run(
            "workload20-probe",
            (
                LaneSpec("agent-a", "task-a"),
                LaneSpec("agent-b", "task-b", crash_first_attempt=True),
                LaneSpec("agent-c", "task-c"),
            ),
            retry_limit=1,
        )
        return (
            report.statuses == ("passed", "passed", "passed")
            and report.recovered_tasks == ("task-b",)
            and sorted(report.attempts) == [1, 1, 2]
        )
    except Exception:
        return False
    finally:
        shutil.rmtree(root, ignore_errors=True)


def run():
    metrics = WorkProductBenchmarkEvaluator().evaluate(_fixture())
    ma07_ok = _ma07_probe()
    return {
        "score": metrics.work_product_score,
        "correctness": metrics.correctness_rate,
        "leakage_free": metrics.leakage_free_rate,
        "recovery": metrics.recovery_rate,
        "cases": metrics.cases,
        "ma07_ok": bool(ma07_ok),
    }


if __name__ == "__main__":
    out = run()
    print(
        "workload20 score=%.4f correctness=%.2f leakage_free=%.2f recovery=%.2f"
        % (out["score"], out["correctness"], out["leakage_free"], out["recovery"])
    )
    rc = 0 if out["score"] > 0.0 else 2
    if rc == 0 and not out["ma07_ok"]:
        rc = 1
    sys.exit(rc)
