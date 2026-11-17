"""Circuit breaker and layered recovery ladder for the NOESIS harness.

Provenance (patterns ported, not copied verbatim):
- harness-books, book1 chapter-06 "errors-and-recovery": the idea that the
  recovery machinery itself can fail repeatedly and must be tripped, and the
  ``MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES = 3`` invariant, which is mirrored
  here as ``MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES`` and as the default breaker
  threshold.
- claude-code-book, chapter-07: a circuit breaker on repeated failures so a
  loop stops hammering a broken path and reopens only after a cooldown.

The module also encodes a recovery ladder: an ordered list of remedies from
the cheapest (least destructive) to the most destructive. Escalation is
strictly forward, counted, and never wraps, so a caller cannot silently loop
on the same rung.

Determinism: the breaker never reads the wall clock. Every state transition
takes an injected ``now`` (a caller-supplied monotonic float), which makes the
whole module pure and reproducible in tests. No I/O, no global mutable state,
no randomness, stdlib only.
"""

from __future__ import annotations

from enum import Enum
from typing import Callable, Dict, List, Optional

MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES = 3


class CircuitState(str, Enum):
    """Lifecycle of a guarded operation.

    ``CLOSED`` is the healthy path. ``OPEN`` denies calls for the duration of
    the cooldown. ``HALF_OPEN`` admits a single trial once the cooldown has
    elapsed; a success closes the breaker, a failure re-opens it.
    """

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Consecutive-failure breaker with an injected-clock cooldown.

    ``threshold`` is the number of consecutive failures that opens the
    breaker. ``cooldown`` is the number of seconds (in whatever monotonic unit
    the caller injects) the breaker stays OPEN before a HALF_OPEN trial is
    allowed. The breaker does not track time itself; every observation passes
    ``now`` explicitly.
    """

    def __init__(self, threshold: int = MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES,
                 cooldown: float = 60.0):
        if isinstance(threshold, bool) or not isinstance(threshold, int):
            raise ValueError("circuit_breaker_threshold_invalid")
        if threshold < 1:
            raise ValueError("circuit_breaker_threshold_invalid")
        if cooldown is None:
            raise ValueError("circuit_breaker_cooldown_invalid")
        if cooldown < 0.0:
            raise ValueError("circuit_breaker_cooldown_invalid")
        self._threshold = threshold
        self._cooldown = float(cooldown)
        self._failures = 0
        self._opened_at = None  # type: Optional[float]

    @property
    def threshold(self) -> int:
        return self._threshold

    @property
    def cooldown(self) -> float:
        return self._cooldown

    def consecutive_failures(self) -> int:
        """Return the current run length of consecutive failures."""
        return self._failures

    def state(self, now: float) -> CircuitState:
        """Return the state observed at ``now``.

        Below the threshold the breaker is CLOSED. At or above the threshold it
        is OPEN while ``now - opened_at < cooldown`` and HALF_OPEN once the
        cooldown has elapsed.
        """
        if self._failures < self._threshold or self._opened_at is None:
            return CircuitState.CLOSED
        if now - self._opened_at < self._cooldown:
            return CircuitState.OPEN
        return CircuitState.HALF_OPEN

    def allow(self, now: float) -> bool:
        """Return True when a call may proceed (CLOSED or HALF_OPEN)."""
        return self.state(now) is not CircuitState.OPEN

    def record(self, success: bool, now: float) -> CircuitState:
        """Record one outcome at ``now`` and return the resulting state.

        A success resets the consecutive-failure count to zero and closes the
        breaker. A failure increments the count and opens the breaker when the
        threshold is reached. A failure while HALF_OPEN re-opens the breaker
        and restarts the cooldown. A failure while already OPEN keeps the
        existing cooldown and only increments the counter.
        """
        if success:
            self._failures = 0
            self._opened_at = None
            return CircuitState.CLOSED

        current = self.state(now)
        self._failures += 1
        if current is CircuitState.HALF_OPEN:
            self._opened_at = now
            return CircuitState.OPEN
        if current is CircuitState.OPEN:
            return CircuitState.OPEN
        if self._failures >= self._threshold:
            self._opened_at = now
            return CircuitState.OPEN
        return CircuitState.CLOSED

    def reset(self) -> None:
        """Return the breaker to its initial CLOSED, zero-failure state."""
        self._failures = 0
        self._opened_at = None


class RecoveryLadder:
    """Ordered recovery remedies, cheapest first, escalated at most once each.

    ``steps`` must be non-empty and contain unique names. Escalation advances
    monotonically through the list and never wraps around; once the final rung
    has been consumed ``escalate`` returns ``None`` forever.
    """

    def __init__(self, steps: List[str]):
        if not steps:
            raise ValueError("recovery_ladder_empty")
        ordered = list(steps)
        if len(set(ordered)) != len(ordered):
            raise ValueError("recovery_ladder_duplicate_step")
        self._steps = ordered
        self._index = -1
        self._attempts = 0

    @property
    def steps(self) -> List[str]:
        return list(self._steps)

    def current(self) -> Optional[str]:
        """Return the current rung, or None before any escalation."""
        if 0 <= self._index < len(self._steps):
            return self._steps[self._index]
        return None

    def escalate(self) -> Optional[str]:
        """Advance one rung and return the step just taken.

        Returns ``None`` when the ladder is exhausted; it never wraps around
        and never repeats a rung.
        """
        if self._index >= len(self._steps) - 1:
            return None
        self._index += 1
        self._attempts += 1
        return self._steps[self._index]

    def escalate_until(self, predicate: Callable[[str], bool]) -> Optional[str]:
        """Advance rungs until ``predicate`` accepts a newly taken step.

        Returns the matching step, or ``None`` if the ladder is exhausted
        first. The predicate is only evaluated on freshly escalated rungs, so
        the traversal order is deterministic and strictly forward.
        """
        while True:
            step = self.escalate()
            if step is None:
                return None
            if predicate(step):
                return step

    def exhausted(self) -> bool:
        """Return True when no further rung is available."""
        return self._index >= len(self._steps) - 1

    def attempts(self) -> int:
        """Return the number of rungs escalated so far."""
        return self._attempts

    def reset(self) -> None:
        """Return to the pre-escalation state."""
        self._index = -1
        self._attempts = 0


class GuardedRecovery:
    """Combine a recovery ladder with a circuit breaker.

    ``step`` records the outcome into the breaker. If the breaker denies the
    call the ladder is left untouched and a ``tripped`` result is returned;
    otherwise exactly one rung is escalated. This keeps a failing recovery
    loop from burning through every remedy while the breaker is open.
    """

    def __init__(self, ladder: RecoveryLadder, breaker: CircuitBreaker):
        self._ladder = ladder
        self._breaker = breaker

    @property
    def ladder(self) -> RecoveryLadder:
        return self._ladder

    @property
    def breaker(self) -> CircuitBreaker:
        return self._breaker

    def step(self, success: bool, now: float) -> Dict:
        """Record one outcome and escalate one rung unless the breaker denies.

        Returns a dict with keys ``step`` (the rung taken or None), ``state``
        (the breaker state after recording), ``exhausted`` (whether the ladder
        has no further rung), and ``tripped`` (whether the breaker denied the
        call). When tripped the ladder is not advanced.
        """
        state = self._breaker.record(success, now)
        if not self._breaker.allow(now):
            return {
                "step": None,
                "state": state,
                "exhausted": self._ladder.exhausted(),
                "tripped": True,
            }
        step = self._ladder.escalate()
        return {
            "step": step,
            "state": state,
            "exhausted": self._ladder.exhausted(),
            "tripped": False,
        }


__all__ = [
    "CircuitBreaker",
    "CircuitState",
    "GuardedRecovery",
    "MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES",
    "RecoveryLadder",
]
