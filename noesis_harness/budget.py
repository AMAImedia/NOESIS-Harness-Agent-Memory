"""noesis_harness/budget.py

Spend-after-validated-writeback (LoopX). Units never decrement on a failed write.
"""

from __future__ import annotations

import sqlite3
import threading

try:
    from .nextgen import _ManagedConnection
except ImportError:
    from nextgen import _ManagedConnection
import time


class Budget:
    def __init__(self, db_path, daily_cap=100):
        self.db_path = db_path
        self.daily_cap = daily_cap
        self._lock = threading.Lock()
        self._init()

    def _conn(self):
        c = sqlite3.connect(self.db_path, timeout=10, factory=_ManagedConnection)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA journal_mode=WAL")
        return c

    def _init(self):
        with self._conn() as c:
            c.execute(
                "CREATE TABLE IF NOT EXISTS spend ("
                " day TEXT NOT NULL, key TEXT NOT NULL,"
                " units INTEGER NOT NULL, created_at REAL NOT NULL,"
                " PRIMARY KEY(day, key))")

    def _day(self):
        return time.strftime("%Y-%m-%d", time.gmtime())

    def remaining(self):
        day = self._day()
        with self._conn() as c:
            row = c.execute(
                "SELECT COALESCE(SUM(units),0) n FROM spend WHERE day=?",
                (day,)).fetchone()
        used = int(row["n"] if row else 0)
        return max(0, self.daily_cap - used)

    def can_spend(self, units=1):
        return self.remaining() >= int(units)

    def spend(self, key, units=1, validated=False):
        """Only spends if validated=True and budget remains. Idempotent on key."""
        if not validated:
            return {"ok": False, "reason": "not_validated"}
        units = int(units)
        if units <= 0:
            return {"ok": False, "reason": "bad_units"}
        if not self.can_spend(units):
            return {"ok": False, "reason": "exhausted", "remaining": self.remaining()}
        day = self._day()
        with self._lock, self._conn() as c:
            row = c.execute(
                "SELECT units FROM spend WHERE day=? AND key=?", (day, key)).fetchone()
            if row:
                return {"ok": True, "idempotent": True, "remaining": self.remaining()}
            c.execute(
                "INSERT INTO spend (day, key, units, created_at) VALUES (?,?,?,?)",
                (day, key, units, time.time()))
        return {"ok": True, "remaining": self.remaining()}


# ---------------------------------------------------------------------------
# Run-identity ledger
# ---------------------------------------------------------------------------
#
# Patterns borrowed from Harness2 (Google, Apache-2.0, arXiv 2610.14224)
# ``core/ledger.py``. Clean-room: the method was ported, no code copied.
#
# ``Budget`` above answers "how many units is this day allowed to spend".
# That is not the same question as "did this run do what it said it would do".
# A run can spend within its cap and still silently lose work: two stages
# writing the same label means one of them overwrote the other, and the count
# still adds up. ``RunLedger`` closes that hole.
#
# The identity is checked with a closed formula -- expected_rollouts(k) and
# expected_sessions(k) -- rather than a recorded expectation, so the check
# cannot be satisfied by re-stating what happened.


class BudgetIdentityError(AssertionError):
    """The ledger did not land on the budget identity."""


def expected_rollouts(k):
    """R = 4k: k shared base + 2k candidates + k finals."""
    return 4 * int(k)


def expected_sessions(k):
    """P = 3k: k invariant + k domain-specific + k compositions."""
    return 3 * int(k)


class RunEntry:
    """One accounted unit of work: what kind, which label, how much."""

    __slots__ = ("kind", "label", "units", "cached", "attempts")

    def __init__(self, kind, label, units=1, cached=False, attempts=1):
        self.kind = str(kind)
        self.label = str(label)
        self.units = int(units)
        self.cached = bool(cached)
        self.attempts = int(attempts)

    def to_dict(self):
        return {
            "kind": self.kind,
            "label": self.label,
            "units": self.units,
            "cached": self.cached,
            "attempts": self.attempts,
        }


class RunLedger:
    """Everything one run spent on one task, recorded as it happens.

    Callers record every stage as they go, then call
    :meth:`assert_identity` once at the end. Duplicate labels are detected
    before the counts, because a duplicate can satisfy the counts while
    representing a stage that never actually produced anything.
    """

    def __init__(self, task_id="", k=1, mode="", entries=None):
        self.task_id = str(task_id)
        self.k = int(k)
        self.mode = str(mode)
        self.entries = list(entries or ())

    def rollout(self, label, units=1, cached=False):
        """Account one executed run. A repeated label is kept, not merged."""
        self.entries.append(RunEntry("rollout", label, units, cached))
        return self

    def session(self, label, units=1, cached=False, attempts=1):
        """Account one reasoning session. Retries are attempts, not extra units."""
        self.entries.append(RunEntry("session", label, units, cached, attempts))
        return self

    @property
    def R(self):
        return sum(e.units for e in self.entries if e.kind == "rollout")

    @property
    def P(self):
        return sum(e.units for e in self.entries if e.kind == "session")

    def labels(self, kind):
        return [e.label for e in self.entries if e.kind == kind]

    def duplicates(self):
        """Labels recorded more than once, per kind.

        A duplicate is the important finding: it means two stages wrote the
        same id, so one silently overwrote the other and the run did less work
        than its own count claims.
        """
        found = {}
        for kind in ("rollout", "session"):
            labels = self.labels(kind)
            dupes = sorted({label for label in labels if labels.count(label) > 1})
            if dupes:
                found[kind] = dupes
        return found

    def assert_identity(self):
        """Raise unless R == 4k and P == 3k with no duplicate label.

        Duplicates are checked first: a duplicate can satisfy the counts, so
        checking the counts alone would pass a run that silently lost a stage.
        """
        want_r, want_p = expected_rollouts(self.k), expected_sessions(self.k)
        dupes = self.duplicates()
        if not dupes and self.R == want_r and self.P == want_p:
            return self
        detail = [
            "%s-%s %s: R=%d (want %d), P=%d (want %d)"
            % (self.mode, self.k, self.task_id, self.R, want_r, self.P, want_p),
            "  rollouts: %s" % (", ".join(self.labels("rollout")) or "(none)"),
            "  sessions: %s" % (", ".join(self.labels("session")) or "(none)"),
        ]
        if dupes:
            detail.append(
                "  DUPLICATE labels: %s -- a repeated label means two stages wrote "
                "the same run id and one silently overwrote the other, so a stage "
                "the ledger counts was never actually produced"
                % ", ".join("%s=%s" % (kind, ",".join(names)) for kind, names in sorted(dupes.items()))
            )
        raise BudgetIdentityError("\n".join(detail))

    def to_dict(self):
        return {
            "mode": self.mode,
            "task_id": self.task_id,
            "k": self.k,
            "R": self.R,
            "expected_R": expected_rollouts(self.k),
            "P": self.P,
            "expected_P": expected_sessions(self.k),
            "session_attempts": sum(e.attempts for e in self.entries if e.kind == "session"),
            "labels": {kind: self.labels(kind) for kind in ("rollout", "session")},
            "duplicates": self.duplicates(),
            "entries": [e.to_dict() for e in self.entries],
        }
