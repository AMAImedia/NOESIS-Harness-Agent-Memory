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
