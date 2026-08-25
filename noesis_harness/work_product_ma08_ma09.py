"""MA-08 and MA-09 workload probes for Gate 4 multi-agent work product loop.

MA-08: Crash injection before write, after write, after read; active-lane workspace
escape probes; repeated runs with deterministic mean/p50/p95 reporting and bounded
repetition count.

MA-09: Four simultaneous active-delegation probes for sibling read/write, absolute
path and traversal denial.

Provenance: extends isolation_holdouts.py patterns (LoopX, agent-teams workspace
isolation, deepseek-harness crash injection, Hermes probe repetition).
"""
from __future__ import annotations

import os
import statistics
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple


from .parallel_agent import (
    AgentLane,
    AgentLaneContext,
    AgentLaneResult,
    ParallelExecutionError,
    SafeParallelExecutor,
)
from .isolation_holdouts import ActiveDelegationLeakageSuite, IsolationHoldoutResult

OP_COST_MS = 0.125


def _deterministic_duration_ms(operations: int) -> float:
    """Deterministic cost-model duration; wall-clock is not reproducible."""
    return round(OP_COST_MS * max(0, int(operations)), 6)


@dataclass(frozen=True)
class CrashInjectionResult:
    """Result of a single crash injection probe run."""
    case_id: str
    phase: str  # "pre_write", "post_write", "pre_read", "post_read", "workspace_escape"
    injected: bool
    survived: bool
    duration_ms: float
    error: str = ""


@dataclass(frozen=True)
class CrashInjectionSummary:
    """Aggregated statistics across repeated crash injection runs."""
    case_id: str
    phase: str
    runs: int
    mean_ms: float
    p50_ms: float
    p95_ms: float
    survival_rate: float
    min_ms: float
    max_ms: float


@dataclass(frozen=True)
class ActiveDelegationProbeResult:
    """Result of a single active-delegation probe."""
    case_id: str
    passed: bool
    observed: str
    duration_ms: float


@dataclass(frozen=True)
class ActiveDelegationSummary:
    """Aggregated results for the four simultaneous active-delegation probes."""
    case_ids: Tuple[str, ...]
    results: Tuple[ActiveDelegationProbeResult, ...]
    all_passed: bool
    mean_duration_ms: float
    max_duration_ms: float


class CrashInjectionProber:
    """MA-08: Crash injection and workspace escape probes with deterministic
    statistical reporting over bounded repetitions."""

    PHASES: Tuple[str, ...] = ("pre_write", "post_write", "pre_read", "post_read", "workspace_escape")
    DEFAULT_REPETITIONS = 10
    MAX_REPETITIONS = 50

    def __init__(
        self,
        repetitions: int = DEFAULT_REPETITIONS,
        *,
        seed: Optional[int] = None,
    ):
        """Initialize the crash injection prober.

        Args:
            repetitions: Number of repeated runs per phase (1-50).
            seed: Optional seed for deterministic crash timing.
        """
        self.repetitions = max(1, min(int(repetitions), self.MAX_REPETITIONS))
        self._seed = seed
        self._rng_state = int(seed) if seed is not None else 0

    def _next_random(self) -> int:
        """Simple deterministic LCG for crash timing (high bits avoid short cycles)."""
        self._rng_state = (self._rng_state * 1103515245 + 12345) & 0xFFFFFFFF
        return (self._rng_state >> 16) & 0x7FFF

    def _should_inject(self, phase: str, run_index: int) -> bool:
        """Deterministically decide whether to inject a crash for this run/phase."""
        # Inject on ~30% of runs, deterministically distributed
        return (self._next_random() % 100) < 30

    def run_pre_write_crash(self, context: AgentLaneContext) -> CrashInjectionResult:
        """Inject crash before any write operation."""
        operations = 1
        try:
            if self._should_inject("pre_write", 0):
                raise ParallelExecutionError("injected_crash:pre_write")
            # Simulate a write operation
            test_file = context.path("pre_write_test.txt")
            test_file.write_text("pre_write")
            survived = True
            error = ""
        except ParallelExecutionError as exc:
            survived = False
            error = str(exc)
        except Exception as exc:
            survived = False
            error = type(exc).__name__ + ": " + str(exc)
        duration_ms = _deterministic_duration_ms(operations)
        return CrashInjectionResult(
            case_id="crash_pre_write",
            phase="pre_write",
            injected=not survived,
            survived=survived,
            duration_ms=duration_ms,
            error=error,
        )

    def run_post_write_crash(self, context: AgentLaneContext) -> CrashInjectionResult:
        """Inject crash after write but before acknowledgment."""
        operations = 3
        try:
            test_file = context.path("post_write_test.txt")
            test_file.write_text("post_write")
            # Flush to ensure write completes
            test_file.flush()
            if self._should_inject("post_write", 0):
                raise ParallelExecutionError("injected_crash:post_write")
            survived = True
            error = ""
        except ParallelExecutionError as exc:
            survived = False
            error = str(exc)
        except Exception as exc:
            survived = False
            error = type(exc).__name__ + ": " + str(exc)
        duration_ms = _deterministic_duration_ms(operations)
        return CrashInjectionResult(
            case_id="crash_post_write",
            phase="post_write",
            injected=not survived,
            survived=survived,
            duration_ms=duration_ms,
            error=error,
        )

    def run_pre_read_crash(self, context: AgentLaneContext) -> CrashInjectionResult:
        """Inject crash before read operation."""
        operations = 3
        try:
            # First write a file to read
            test_file = context.path("pre_read_test.txt")
            test_file.write_text("pre_read_content")
            if self._should_inject("pre_read", 0):
                raise ParallelExecutionError("injected_crash:pre_read")
            content = test_file.read_text()
            survived = content == "pre_read_content"
            error = "" if survived else "content_mismatch"
        except ParallelExecutionError as exc:
            survived = False
            error = str(exc)
        except Exception as exc:
            survived = False
            error = type(exc).__name__ + ": " + str(exc)
        duration_ms = _deterministic_duration_ms(operations)
        return CrashInjectionResult(
            case_id="crash_pre_read",
            phase="pre_read",
            injected=not survived and "injected_crash" in error,
            survived=survived,
            duration_ms=duration_ms,
            error=error,
        )

    def run_post_read_crash(self, context: AgentLaneContext) -> CrashInjectionResult:
        """Inject crash after read operation."""
        operations = 3
        try:
            test_file = context.path("post_read_test.txt")
            test_file.write_text("post_read_content")
            content = test_file.read_text()
            if self._should_inject("post_read", 0):
                raise ParallelExecutionError("injected_crash:post_read")
            survived = content == "post_read_content"
            error = "" if survived else "content_mismatch"
        except ParallelExecutionError as exc:
            survived = False
            error = str(exc)
        except Exception as exc:
            survived = False
            error = type(exc).__name__ + ": " + str(exc)
        duration_ms = _deterministic_duration_ms(operations)
        return CrashInjectionResult(
            case_id="crash_post_read",
            phase="post_read",
            injected=not survived and "injected_crash" in error,
            survived=survived,
            duration_ms=duration_ms,
            error=error,
        )

    def run_workspace_escape_probe(self, context: AgentLaneContext) -> CrashInjectionResult:
        """MA-08: Active-lane workspace escape probe."""
        escape_attempts = [
            "../escape.txt",
            "../../escape.txt",
            "/absolute/escape.txt" if os.name != "nt" else "C:\\escape.txt",
            "subdir/../../escape.txt",
        ]
        observed = "contained"
        survived = True
        error = ""
        for attempt in escape_attempts:
            try:
                context.path(attempt)
                observed = "allowed:" + attempt
                survived = False
                break
            except ParallelExecutionError as exc:
                if "workspace_escape" in str(exc) or "workspace_relative_path_required" in str(exc):
                    continue
                observed = "error:" + str(exc)
                survived = False
                break
            except Exception as exc:
                observed = "exception:" + type(exc).__name__
                survived = False
                break
        duration_ms = _deterministic_duration_ms(len(escape_attempts))
        return CrashInjectionResult(
            case_id="workspace_escape",
            phase="workspace_escape",
            injected=False,
            survived=survived,
            duration_ms=duration_ms,
            error=error,
        )

    def run_single_pass(self) -> Tuple[CrashInjectionResult, ...]:
        """Run one complete pass of all crash injection phases in one real lane."""
        with tempfile.TemporaryDirectory(prefix="noesis-crash-injection-") as root:
            executor = SafeParallelExecutor(root, max_concurrency=1)
            lane = AgentLane("crash-prober", "crash-task", "crash-prober", capabilities=("read", "workspace_write", "provenance"), approval_granted=True)

            def run_all_phases(ctx: AgentLaneContext) -> List[CrashInjectionResult]:
                return [
                    self.run_pre_write_crash(ctx),
                    self.run_post_write_crash(ctx),
                    self.run_pre_read_crash(ctx),
                    self.run_post_read_crash(ctx),
                    self.run_workspace_escape_probe(ctx),
                ]

            lane_result = executor.execute([lane], run_all_phases, session_id="crash-injection-single", approval=True)[0]
            if not isinstance(lane_result.output, list):
                raise ParallelExecutionError("crash_probe_lane_failed:" + lane_result.error)
            return tuple(lane_result.output)

    def run_repeated(self) -> Dict[str, List[CrashInjectionResult]]:
        """Run all phases repeatedly and collect results for statistics."""
        all_results: Dict[str, List[CrashInjectionResult]] = {phase: [] for phase in self.PHASES}
        for _ in range(self.repetitions):
            pass_results = self.run_single_pass()
            for result in pass_results:
                all_results[result.phase].append(result)
        return all_results

    def summarize(self, results: Dict[str, List[CrashInjectionResult]]) -> Tuple[CrashInjectionSummary, ...]:
        """Compute deterministic mean/p50/p95 statistics for each phase."""
        summaries = []
        for phase in self.PHASES:
            phase_results = results.get(phase, [])
            if not phase_results:
                summaries.append(CrashInjectionSummary(
                    case_id=f"crash_{phase}",
                    phase=phase,
                    runs=0,
                    mean_ms=0.0,
                    p50_ms=0.0,
                    p95_ms=0.0,
                    survival_rate=1.0,
                    min_ms=0.0,
                    max_ms=0.0,
                ))
                continue

            durations = [r.duration_ms for r in phase_results]
            survived = sum(1 for r in phase_results if r.survived)
            durations_sorted = sorted(durations)
            n = len(durations_sorted)

            def percentile(sorted_vals: List[float], p: float) -> float:
                if not sorted_vals:
                    return 0.0
                k = (n - 1) * p
                f = int(k)
                c = min(f + 1, n - 1)
                if f == c:
                    return sorted_vals[f]
                return sorted_vals[f] + (k - f) * (sorted_vals[c] - sorted_vals[f])

            summaries.append(CrashInjectionSummary(
                case_id=f"crash_{phase}",
                phase=phase,
                runs=n,
                mean_ms=statistics.mean(durations) if durations else 0.0,
                p50_ms=percentile(durations_sorted, 0.5),
                p95_ms=percentile(durations_sorted, 0.95),
                survival_rate=survived / n if n > 0 else 1.0,
                min_ms=min(durations) if durations else 0.0,
                max_ms=max(durations) if durations else 0.0,
            ))
        return tuple(summaries)

    def run_full(self) -> Tuple[CrashInjectionSummary, ...]:
        """Run complete MA-08 probe suite with repetitions and return summaries."""
        raw_results = self.run_repeated()
        return self.summarize(raw_results)


class ActiveDelegationProber:
    """MA-09: Four simultaneous active-delegation probes for sibling read/write,
    absolute path and traversal denial. Runs concurrently with deterministic
    timing and bounded execution."""

    CASE_IDS: Tuple[str, ...] = ("sibling_read_denied", "sibling_write_denied", "absolute_path_denied", "traversal_denied")
    MAX_DURATION_SECONDS = 10

    def __init__(
        self,
        *,
        max_duration_seconds: float = MAX_DURATION_SECONDS,
    ):
        self.max_duration_seconds = max_duration_seconds

    def _make_probe_callback(self, case_id: str, probe_path: str) -> Callable[[AgentLaneContext], ActiveDelegationProbeResult]:
        """Create a callback that attempts a specific workspace escape."""
        def probe(ctx: AgentLaneContext) -> ActiveDelegationProbeResult:
            try:
                ctx.path(probe_path)
                observed = "allowed"
                passed = False
            except ParallelExecutionError as exc:
                if "workspace_escape" in str(exc) or "workspace_relative_path_required" in str(exc):
                    observed = "denied:" + type(exc).__name__
                    passed = True
                else:
                    observed = "error:" + str(exc)
                    passed = False
            except Exception as exc:
                observed = "exception:" + type(exc).__name__
                passed = False
            duration_ms = _deterministic_duration_ms(1)
            return ActiveDelegationProbeResult(case_id, passed, observed, duration_ms)
        return probe

    def run_simultaneous(self) -> ActiveDelegationSummary:
        """Run all four active-delegation probes simultaneously."""
        with tempfile.TemporaryDirectory(prefix="noesis-active-delegation-") as root:
            boundary = Path(root).resolve()
            executor = SafeParallelExecutor(root, max_concurrency=4)

            # Create lanes with known workspace layout for sibling probes
            lanes = [
                AgentLane("agent-0", "task-0-sibling-read", "agent-0", capabilities=("read", "workspace_write", "provenance"), approval_granted=True),
                AgentLane("agent-1", "task-1-sibling-write", "agent-1", capabilities=("read", "workspace_write", "provenance"), approval_granted=True),
                AgentLane("agent-2", "task-2-absolute-path", "agent-2", capabilities=("read", "workspace_write", "provenance"), approval_granted=True),
                AgentLane("agent-3", "task-3-traversal", "agent-3", capabilities=("read", "workspace_write", "provenance"), approval_granted=True),
            ]

            # Probe paths for each case
            probes = {
                "sibling_read_denied": "../agent-1/secret.txt",
                "sibling_write_denied": "../agent-2/write.txt",
                "absolute_path_denied": str(boundary.parent / "outside.txt"),
                "traversal_denied": "../../escape.txt",
            }

            results: Dict[str, ActiveDelegationProbeResult] = {}

            def run_probes(ctx: AgentLaneContext) -> ActiveDelegationProbeResult:
                # Extract index from task_id (format: "task-N-...")
                index = int(ctx.task_id.split("-")[1])
                case_id = self.CASE_IDS[index]
                probe_path = probes[case_id]
                try:
                    ctx.path(probe_path)
                    observed = "allowed"
                    passed = False
                except ParallelExecutionError as exc:
                    if "workspace_escape" in str(exc) or "workspace_relative_path_required" in str(exc):
                        observed = "denied:" + type(exc).__name__
                        passed = True
                    else:
                        observed = "error:" + str(exc)
                        passed = False
                except Exception as exc:
                    observed = "exception:" + type(exc).__name__
                    passed = False
                duration_ms = _deterministic_duration_ms(1)
                return ActiveDelegationProbeResult(case_id, passed, observed, duration_ms)

            lane_results = executor.execute(lanes, run_probes, session_id="active-delegation", max_duration_seconds=self.max_duration_seconds, approval=True)
            for lr in lane_results:
                if lr.output and isinstance(lr.output, ActiveDelegationProbeResult):
                    results[lr.output.case_id] = lr.output

            # Ensure all cases have results
            for case_id in self.CASE_IDS:
                if case_id not in results:
                    results[case_id] = ActiveDelegationProbeResult(case_id, False, "missing", 0.0)

            result_tuple = tuple(results[case_id] for case_id in self.CASE_IDS)
            all_passed = all(r.passed for r in result_tuple)
            durations = [r.duration_ms for r in result_tuple]
            return ActiveDelegationSummary(
                case_ids=self.CASE_IDS,
                results=result_tuple,
                all_passed=all_passed,
                mean_duration_ms=statistics.mean(durations) if durations else 0.0,
                max_duration_ms=max(durations) if durations else 0.0,
            )

    def run_repeated(self, repetitions: int = 5) -> List[ActiveDelegationSummary]:
        """Run the simultaneous probe multiple times for stability verification."""
        summaries = []
        for _ in range(max(1, min(repetitions, 20))):
            summaries.append(self.run_simultaneous())
        return summaries


__all__ = [
    "CrashInjectionProber",
    "ActiveDelegationProber",
    "CrashInjectionResult",
    "CrashInjectionSummary",
    "ActiveDelegationProbeResult",
    "ActiveDelegationSummary",
]