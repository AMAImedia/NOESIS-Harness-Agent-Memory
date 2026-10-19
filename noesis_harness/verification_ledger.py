"""noesis_harness/verification_ledger.py

Verification ledger with verify-after dates, a capped fix loop that escalates
to a human, and a pre-run guard that refuses to run while template markers
remain.

Provenance:
  Ported from the AI-Builder-Club/skills repository:
    - skills/seo-growth/assets/seo-loop-template.md
        * applied-change ledger with a verify-after horizon ("+N days")
        * "all gates must hold or ship nothing"
        * "never revert yourself, recommend a revert"
        * pre-run `<FILL:>` marker count guard
    - skills/verifier-setup/assets/verify.template.md
        * cap the fix loop at roughly three rounds, then escalate to a human

Design goals:
  - Deterministic: every time-sensitive method takes an injected ``now`` so
    no wall-clock call is made and replays agree exactly.
  - The ledger records what was applied and when it must be re-checked. It
    never mutates the world: a worse-than-baseline outcome yields a
    ``revert_recommended`` finding for a human, never an automatic revert.
  - The fix loop never weakens its predicate. Each round is a fresh call with
    its round index; exhaustion of the cap is reported as an escalation.
  - The marker guard refuses to run a template that still contains ``<FILL:>``
    placeholders.
  - Standard library only. One file, one job.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Callable, Dict, List, Optional, Tuple

SECONDS_PER_DAY = 86400.0

DEFAULT_MARKER = "<FILL:"


class LedgerError(RuntimeError):
    """A ledger invariant was violated (duplicate, unknown, or bad state)."""


@dataclass(frozen=True)
class AppliedChange:
    """One applied change plus its verification horizon and outcome."""

    change_id: str
    description: str
    applied_at: float
    verify_after: float
    verified: bool = False
    baseline: float = 0.0
    observed: float = 0.0


class VerificationLedger:
    """Applied-change ledger with verify-after dates and revert advice.

    The ledger itself is intentionally passive. It records changes, tells you
    which are due, and flags verified regressions. It NEVER applies a revert
    on its own: :meth:`recommendations` only emits ``revert_recommended``
    findings for a human owner to act on.
    """

    def __init__(self) -> None:
        self._changes: Dict[str, AppliedChange] = {}
        self._clock: float = 0.0

    def _tick(self, now: float) -> None:
        """Advance the internal clock to the latest injected ``now``.

        The clock is only used by :meth:`findings`, which has no ``now``
        parameter. It is the maximum time observed so far, so results are a
        pure function of the injected values.
        """
        if now > self._clock:
            self._clock = now

    def record(
        self,
        change_id: str,
        description: str,
        now: float,
        verify_after_days: float,
        baseline: float = 0.0,
    ) -> AppliedChange:
        """Record the application of a change.

        ``verify_after`` is ``now + verify_after_days * 86400``. A duplicate
        ``change_id`` is a hard error so history cannot be silently rewritten.
        """
        if change_id in self._changes:
            raise LedgerError("change already recorded: %s" % change_id)
        self._tick(now)
        change = AppliedChange(
            change_id=change_id,
            description=description,
            applied_at=now,
            verify_after=now + verify_after_days * SECONDS_PER_DAY,
            verified=False,
            baseline=baseline,
            observed=0.0,
        )
        self._changes[change_id] = change
        return change

    def due(self, now: float) -> List[AppliedChange]:
        """Unverified changes whose ``verify_after`` has arrived, sorted."""
        self._tick(now)
        pending = [
            change
            for change in self._changes.values()
            if not change.verified and change.verify_after <= now
        ]
        pending.sort(key=lambda change: (change.verify_after, change.change_id))
        return pending

    def verify(
        self, change_id: str, observed: float, now: float
    ) -> AppliedChange:
        """Mark a recorded change verified and store its observed value.

        Unknown or already-verified ids raise :class:`LedgerError`.
        """
        change = self._changes.get(change_id)
        if change is None:
            raise LedgerError("unknown change: %s" % change_id)
        if change.verified:
            raise LedgerError("change already verified: %s" % change_id)
        self._tick(now)
        updated = replace(change, verified=True, observed=float(observed))
        self._changes[change_id] = updated
        return updated

    def recommendations(self) -> List[Dict]:
        """Revert advice for verified regressions, sorted by ``change_id``.

        This method never performs a revert. It only reports that the observed
        value fell below the recorded baseline so a human can decide.
        """
        advice: List[Dict] = []
        for change in self._changes.values():
            if change.verified and change.observed < change.baseline:
                advice.append(
                    {
                        "change_id": change.change_id,
                        "kind": "revert_recommended",
                        "delta": change.observed - change.baseline,
                    }
                )
        advice.sort(key=lambda entry: entry["change_id"])
        return advice

    def open_changes(self) -> List[str]:
        """Sorted ids of recorded changes that are not yet verified."""
        return sorted(
            change_id
            for change_id, change in self._changes.items()
            if not change.verified
        )

    def findings(self) -> Dict:
        """Summary counts over the whole ledger.

        ``due_pending`` is computed against the latest injected ``now`` (see
        :meth:`_tick`) because this method takes no time argument.
        """
        total = len(self._changes)
        verified = sum(1 for change in self._changes.values() if change.verified)
        unverified = total - verified
        regressions = sum(
            1
            for change in self._changes.values()
            if change.verified and change.observed < change.baseline
        )
        due_pending = len(self.due(self._clock))
        return {
            "total": total,
            "verified": verified,
            "unverified": unverified,
            "regressions": regressions,
            "due_pending": due_pending,
        }


class FixLoop:
    """A capped retry loop that escalates to a human on exhaustion.

    The loop calls ``attempt(round_index)`` at most ``max_rounds`` times and
    stops on the first ``True``. It never weakens the predicate and never
    caches an attempt result: each round is a fresh call receiving its
    zero-based round index. Running out of rounds is an escalation, not a
    silent failure.
    """

    def __init__(self, max_rounds: int = 3) -> None:
        if not isinstance(max_rounds, int) or isinstance(max_rounds, bool):
            raise ValueError("max_rounds must be an integer")
        if max_rounds < 1:
            raise ValueError("max_rounds must be >= 1")
        self.max_rounds = max_rounds

    def run(self, attempt: Callable[[int], bool]) -> Dict:
        """Run ``attempt`` until success or the cap, then report the outcome."""
        for round_index in range(self.max_rounds):
            if attempt(round_index):
                return {
                    "ok": True,
                    "rounds": round_index + 1,
                    "escalated": False,
                }
        return {"ok": False, "rounds": self.max_rounds, "escalated": True}


class MarkerGuard:
    """Pre-run guard against leftover template markers.

    A template is considered not ready to run while it still contains the
    marker (``<FILL:`` by default). Counting and checking are pure; only
    :meth:`require_clean` raises.
    """

    def __init__(self, marker: str = DEFAULT_MARKER) -> None:
        if not marker:
            raise ValueError("marker must be a non-empty string")
        self.marker = marker

    def count(self, text: str) -> int:
        """Number of marker occurrences in ``text``."""
        return text.count(self.marker)

    def check(self, text: str) -> Tuple[bool, int]:
        """Return ``(True, 0)`` when clean, else ``(False, count)``."""
        found = self.count(text)
        if found == 0:
            return (True, 0)
        return (False, found)

    def require_clean(self, text: str) -> None:
        """Raise :class:`LedgerError` while any marker remains."""
        found = self.count(text)
        if found:
            raise LedgerError("%d template markers remain" % found)


__all__ = [
    "LedgerError",
    "AppliedChange",
    "VerificationLedger",
    "FixLoop",
    "MarkerGuard",
    "SECONDS_PER_DAY",
    "DEFAULT_MARKER",
]
