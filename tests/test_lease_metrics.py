"""tests/test_lease_metrics.py

Read-only lease metrics tests. Covers active/expired counts, per_holder
aggregation, now override, missing db, determinism, and the read-only contract.
"""

from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest

from noesis_harness import lease_metrics


def _make_store(path, leases):
    # type: (str, list) -> None
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE leases ("
        "task_key TEXT, holder TEXT, acquired_at REAL, expires_at REAL, status TEXT)"
    )
    conn.executemany(
        "INSERT INTO leases (task_key, holder, acquired_at, expires_at, status) "
        "VALUES (?, ?, ?, ?, ?)",
        leases,
    )
    conn.commit()
    conn.close()


class LeaseMetricsTest(unittest.TestCase):

    def setUp(self):
        # type: () -> None
        self.tmp = tempfile.mkdtemp(prefix="lease_metrics_")
        self.db = os.path.join(self.tmp, "leases.db")

    def _path(self, name):
        # type: (str) -> str
        return os.path.join(self.tmp, name)

    def test_empty_store_present_but_zero(self):
        _make_store(self.db, [])
        m = lease_metrics.metrics(self.db, now=1000.0)
        self.assertTrue(m["present"])
        self.assertEqual(m["total"], 0)
        self.assertEqual(m["active"], 0)
        self.assertEqual(m["expired"], 0)
        self.assertEqual(m["per_holder"], {})

    def test_active_and_expired_counts(self):
        _make_store(self.db, [
            ("t1", "h1", 100.0, 200.0, "active"),   # active at now=150
            ("t2", "h2", 100.0, 500.0, "active"),   # active at now=150
            ("t3", "h3", 100.0, 50.0, "active"),    # expired at now=150
            ("t4", "h4", 100.0, 999.0, "released"),  # not active
        ])
        m = lease_metrics.metrics(self.db, now=150.0)
        self.assertEqual(m["total"], 4)
        self.assertEqual(m["active"], 3)
        self.assertEqual(m["expired"], 1)
        self.assertEqual(m["per_holder"], {"h1": 1, "h2": 1, "h3": 1})

    def test_per_holder_aggregation(self):
        _make_store(self.db, [
            ("t1", "h1", 100.0, 500.0, "active"),
            ("t2", "h1", 100.0, 500.0, "active"),
            ("t3", "h2", 100.0, 500.0, "active"),
        ])
        m = lease_metrics.metrics(self.db, now=150.0)
        self.assertEqual(m["active"], 3)
        self.assertEqual(m["per_holder"], {"h1": 2, "h2": 1})

    def test_now_override_expires_more(self):
        _make_store(self.db, [
            ("t1", "h1", 100.0, 200.0, "active"),
            ("t2", "h2", 100.0, 300.0, "active"),
        ])
        m_early = lease_metrics.metrics(self.db, now=150.0)
        m_late = lease_metrics.metrics(self.db, now=350.0)
        self.assertEqual(m_early["expired"], 0)
        self.assertEqual(m_late["expired"], 2)

    def test_default_now_is_latest_acquired(self):
        _make_store(self.db, [
            ("t1", "h1", 100.0, 200.0, "active"),
            ("t2", "h2", 999.0, 1000.0, "active"),
        ])
        # now defaults to max acquired_at = 999, so t1 (expires 200) is expired.
        m = lease_metrics.metrics(self.db)
        self.assertEqual(m["expired"], 1)
        self.assertEqual(m["active"], 2)

    def test_missing_db_is_present_false(self):
        missing = self._path("does_not_exist.db")
        self.assertFalse(os.path.exists(missing))
        m = lease_metrics.metrics(missing, now=1000.0)
        self.assertFalse(m["present"])
        self.assertEqual(m["total"], 0)
        self.assertEqual(m["active"], 0)
        self.assertEqual(m["expired"], 0)
        self.assertEqual(m["per_holder"], {})

    def test_missing_leases_table_is_present_false(self):
        conn = sqlite3.connect(self.db)
        conn.execute("CREATE TABLE other (x INTEGER)")
        conn.commit()
        conn.close()
        m = lease_metrics.metrics(self.db, now=1000.0)
        self.assertFalse(m["present"])
        self.assertEqual(m["total"], 0)
        self.assertEqual(m["active"], 0)

    def test_determinism(self):
        _make_store(self.db, [
            ("t1", "h1", 100.0, 200.0, "active"),
            ("t2", "h1", 100.0, 500.0, "active"),
            ("t3", "h2", 100.0, 50.0, "active"),
        ])
        a = lease_metrics.metrics(self.db, now=150.0)
        b = lease_metrics.metrics(self.db, now=150.0)
        self.assertEqual(a, b)

    def test_read_only_contract_does_not_raise(self):
        _make_store(self.db, [("t1", "h1", 100.0, 500.0, "active")])
        self.assertTrue(lease_metrics.read_only_contract(self.db, now=150.0))
        self.assertTrue(lease_metrics.read_only_contract(self._path("nope.db")))

    def test_read_only_contract_no_write_lock(self):
        # Opening with mode=ro must succeed even when no write is performed;
        # confirm metrics ran without mutating the table contents.
        _make_store(self.db, [
            ("t1", "h1", 100.0, 500.0, "active"),
            ("t2", "h2", 100.0, 50.0, "active"),
        ])
        before = lease_metrics.metrics(self.db, now=150.0)
        after = lease_metrics.metrics(self.db, now=150.0)
        self.assertEqual(before, after)
        self.assertEqual(after["active"], 2)

    def test_unreadable_db_is_present_false(self):
        # A directory in place of a db file is not a valid sqlite store.
        m = lease_metrics.metrics(self.tmp, now=1000.0)
        self.assertFalse(m["present"])
        self.assertEqual(m["total"], 0)


if __name__ == "__main__":
    unittest.main()
