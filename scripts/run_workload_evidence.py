"""Build deterministic local Gate 4 workload evidence as machine-readable JSON.

Composes existing harness modules into one byte-stable artifact: MA-07 bounded
multi-lane workload replay with injected first-attempt crashes (LoopX
append-only/idempotent aggregate patterns via noesis_harness.work_product_ma07),
MA-08 crash-injection probes with deterministic cost-model statistics
(deepseek-harness crash injection, Hermes probe repetition via
noesis_harness.work_product_ma08_ma09), MA-09 simultaneous active-delegation
isolation probes (agent-teams workspace isolation), and the bounded
no-hidden-reward rubric evaluator (deepseek-harness deterministic rubric via
noesis_harness.work_product_benchmark). CLI/output conventions follow the
sibling generators scripts/run_memory_quality_evidence.py and
scripts/run_task_execution_parity.py.

The output contains no wall-clock value of any kind: generated_at is omitted
entirely and every quantity derives from fixed seeds, fixed fixtures, or the
deterministic cost model. Only the final output_digest depends on the rest of
the document, so identical inputs reproduce identical bytes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from noesis_harness.work_product_benchmark import (
    WorkProductBenchmarkEvaluator,
    WorkProductOutcome,
)
from noesis_harness.work_product_ma07 import (
    LaneSpec,
    WorkloadRunReport,
    WorkProductWorkloadRunner,
)
from noesis_harness.work_product_ma08_ma09 import (
    ActiveDelegationProber,
    CrashInjectionProber,
)

SCHEMA_VERSION = "noesis.workload-evidence.v1"
CLAIM_BOUNDARY = (
    "deterministic_local_workload_replay_crash_injection_active_delegation_"
    "and_bounded_rubric_metrics_only_no_external_model_no_network_no_wall_clock"
)

STATUS_PASSED = "passed"
STATUS_BLOCKED = "blocked"

CRASH_PROBER_REPETITIONS = 10
CRASH_PROBER_SEED = 20260825

INJECTED_TASK_ID = "crash-task-b"
INJECTED_EXPECTED_ATTEMPTS = 2

_CLEAN_SPECS = (
    LaneSpec("agent-clean-a", "clean-task-a"),
    LaneSpec("agent-clean-b", "clean-task-b"),
    LaneSpec("agent-clean-c", "clean-task-c"),
)
_CRASH_SPECS = (
    LaneSpec("agent-crash-a", "crash-task-a"),
    LaneSpec("agent-crash-b", "crash-task-b", crash_first_attempt=True),
    LaneSpec("agent-crash-c", "crash-task-c"),
)

EVALUATOR_OUTCOMES = (
    WorkProductOutcome("wp-case-01", True, True, True, False, attempts=1, reviewer_time_seconds=0.5),
    WorkProductOutcome("wp-case-02", True, True, True, False, attempts=1, reviewer_time_seconds=0.75),
    WorkProductOutcome("wp-case-03", True, True, True, True, attempts=2, reviewer_time_seconds=1.25),
    WorkProductOutcome(
        "wp-case-04", True, True, True, False, attempts=1, reviewer_time_seconds=1.0, review_approved=False
    ),
    WorkProductOutcome("wp-case-05", True, True, True, True, attempts=3, reviewer_time_seconds=2.0),
    WorkProductOutcome(
        "wp-case-06", False, False, True, False, attempts=1, reviewer_time_seconds=0.25, review_approved=False, committed=False
    ),
)


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def canonical_digest(payload: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def _run_report_to_dict(report: WorkloadRunReport) -> Dict[str, Any]:
    return {
        "run_id": report.run_id,
        "statuses": list(report.statuses),
        "attempts": list(report.attempts),
        "recovered_tasks": list(report.recovered_tasks),
        "aggregate_digest": report.aggregate_digest,
    }


def run_ma07_workload() -> Dict[str, Any]:
    """Two real 3-lane runs: one clean, one with an injected first-attempt crash."""
    with tempfile.TemporaryDirectory(prefix="noesis-workload-evidence-ma07-") as tmp:
        root = Path(tmp)
        clean_runner = WorkProductWorkloadRunner(str(root / "clean"), max_concurrency=2)
        crash_runner = WorkProductWorkloadRunner(str(root / "crash"), max_concurrency=2)
        clean_report = clean_runner.run("ma07-clean-run", _CLEAN_SPECS, retry_limit=1)
        crash_report = crash_runner.run("ma07-crash-run", _CRASH_SPECS, retry_limit=1)

    ordered_ids = sorted(spec.task_id for spec in _CRASH_SPECS)
    injected_index = ordered_ids.index(INJECTED_TASK_ID)
    observed_attempts = int(crash_report.attempts[injected_index])
    recovered = INJECTED_TASK_ID in crash_report.recovered_tasks
    asserted = (
        recovered
        and observed_attempts == INJECTED_EXPECTED_ATTEMPTS
        and all(status == STATUS_PASSED for status in crash_report.statuses)
    )
    section: Dict[str, Any] = {
        "clean_run": _run_report_to_dict(clean_report),
        "crash_run": _run_report_to_dict(crash_report),
        "recovery_assertion": {
            "injected_task_id": INJECTED_TASK_ID,
            "expected_attempts": INJECTED_EXPECTED_ATTEMPTS,
            "observed_attempts": observed_attempts,
            "recovered": recovered,
            "asserted": asserted,
        },
        "status": STATUS_PASSED if asserted else STATUS_BLOCKED,
        "blocked_reason": "" if asserted else "injected_first_attempt_crash_not_recovered",
    }
    return section


def run_ma08_crash_injection() -> Dict[str, Any]:
    prober = CrashInjectionProber(repetitions=CRASH_PROBER_REPETITIONS, seed=CRASH_PROBER_SEED)
    summaries = [asdict(summary) for summary in prober.run_full()]
    return {
        "prober": "CrashInjectionProber",
        "repetitions": CRASH_PROBER_REPETITIONS,
        "seed": CRASH_PROBER_SEED,
        "phases": list(prober.PHASES),
        "summaries": summaries,
    }


def run_ma09_active_delegation() -> Dict[str, Any]:
    summary = ActiveDelegationProber().run_simultaneous()
    return asdict(summary)


def run_evaluator_metrics() -> Dict[str, Any]:
    metrics = WorkProductBenchmarkEvaluator().evaluate(EVALUATOR_OUTCOMES)
    return asdict(metrics)


def build_evidence() -> Dict[str, Any]:
    """Assemble the full evidence document; byte-stable across invocations."""
    payload: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "claim_boundary": CLAIM_BOUNDARY,
        "ma07_workload": run_ma07_workload(),
        "ma08_crash_injection": run_ma08_crash_injection(),
        "ma09_active_delegation": run_ma09_active_delegation(),
        "evaluator_metrics": run_evaluator_metrics(),
    }
    payload["output_digest"] = canonical_digest(payload)
    return payload


def _overall_status(evidence: Dict[str, Any]) -> str:
    ma07_ok = evidence["ma07_workload"].get("status") == STATUS_PASSED
    ma08_rows = evidence["ma08_crash_injection"].get("summaries", [])
    ma08_ok = len(ma08_rows) == len(CrashInjectionProber.PHASES) and all(row.get("runs") == CRASH_PROBER_REPETITIONS for row in ma08_rows)
    ma09_ok = bool(evidence["ma09_active_delegation"].get("all_passed"))
    if ma07_ok and ma08_ok and ma09_ok:
        return STATUS_PASSED
    return STATUS_BLOCKED


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Build deterministic NOESIS Gate 4 workload evidence")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    evidence = build_evidence()
    status = _overall_status(evidence)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(output),
        "schema_version": evidence["schema_version"],
        "output_digest": evidence["output_digest"],
        "status": status,
    }, ensure_ascii=False, sort_keys=True))
    return 0 if status == STATUS_PASSED else 2


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "SCHEMA_VERSION",
    "CLAIM_BOUNDARY",
    "EVALUATOR_OUTCOMES",
    "build_evidence",
    "canonical_digest",
    "canonical_json",
    "main",
]
