"""Cross-layer durable recovery for NOESIS runs.

This adapter coordinates three durable primitives without executing artifacts:
BestStateStore protects verified state, FiberStore restores resumable progress,
and WorkCoordinator reclaims only expired leases after a crash.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from .best_state import BestStateStore, RecoveryResult, RecoveryStatus
from .fibers import FiberRecord, FiberStore
from .orchestration import WorkCoordinator


@dataclass(frozen=True)
class DurableRecoveryReport:
    run_id: str
    fiber_id: str
    task_id: Optional[str]
    best_state_id: Optional[str]
    best_score: Optional[float]
    fiber_step: Optional[int]
    fiber_status: str
    recovery_status: str
    reclaimed_leases: int
    recovery_revision: int


class RecoveryCoordinator:
    """Join verified state, resumable fibers and lease recovery."""

    def __init__(self, best: BestStateStore, fibers: FiberStore, work: WorkCoordinator):
        self.best = best
        self.fibers = fibers
        self.work = work

    def recover_after_crash(
        self,
        run_id: str,
        fiber_id: str,
        task_id: Optional[str] = None,
        now: Optional[float] = None,
        reason: str = "crash_or_late_regression",
    ) -> DurableRecoveryReport:
        """Restore best verified state and reclaim expired work leases.

        The adapter is deliberately fail-soft: missing best state or fiber raises
        no false success. A live lease is not reclaimed; the caller must retry
        after its TTL expires or use a human-approved intervention.
        """
        recovery: RecoveryResult = self.best.recover(run_id, reason)
        fiber: Optional[FiberRecord] = None
        if recovery.status is RecoveryStatus.RECOVERED and recovery.to_state_id:
            target = self.best.best(run_id)
            if target is not None:
                fiber = self.fibers.restore(fiber_id, int(target.metadata.get("fiber_step", 0)), dict(target.payload))
        else:
            try:
                fiber = self.fibers.get(fiber_id)
            except KeyError:
                fiber = None
        reclaimed = self.work.reclaim_expired(now) if task_id else 0
        return DurableRecoveryReport(
            run_id=run_id,
            fiber_id=fiber_id,
            task_id=task_id,
            best_state_id=recovery.to_state_id,
            best_score=recovery.best_score,
            fiber_step=None if fiber is None else fiber.step,
            fiber_status="missing" if fiber is None else fiber.status,
            recovery_status=recovery.status.value,
            reclaimed_leases=reclaimed,
            recovery_revision=recovery.revision,
        )


__all__ = ["DurableRecoveryReport", "RecoveryCoordinator"]
