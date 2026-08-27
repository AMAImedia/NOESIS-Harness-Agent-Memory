"""tests/test_ttl_watch.py

Read-only unit tests for noesis_harness.ttl_watch.watch.

The tests build their own temporary SQLite leases table in a temp dir, so they
never touch the project's real state. No threading.Lock is used; the watch is
documented as Lock-free and these tests confirm it reads cleanly under a plain
single-threaded snapshot.

Zero dependencies (stdlib only).
"""

from __future__ import annotations

import os
import sqlite3
import tempfile
import time
import unittest

from noesis_harness import ttl_watch


def _make_db():
    # type: () -> str
    fd, path = tempfile.mkstemp(suffix=".sqlite")
    os.close(fd)
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE leases ("
        "task_key TEXT, holder TEXT, acquired_at REAL, "
        "expires_at REAL, status TEXT)")
    conn.commit()
    conn.close()
    return path


def _insert(path, task_key, holder, acquired_at, expires_at, status):
    # type: (str, str, str, float, Optional[float], str) -> None
    conn = sqlite3.connect(path)
    conn.execute(
        "INSERT INTO leases (task_key, holder, acquired_at, expires_at, status) "
        "VALUES (?, ?, ?, ?, ?)",
        (task_key, holder, acquired_at, expires_at, status))
    conn.commit()
    conn.close()


class TtlWatchTest(unittest.TestCase):
    def setUp(self):
        # type: () -> None
        self.now = 1000.0
        self.path = _make_db()

    def tearDown(self):
        # type: () -> None
        if os.path.exists(self.path):
            os.remove(self.path)

    def test_active_only(self):
        _insert(self.path, "t1", "h1", self.now - 10, self.now + 100, "active")
        _insert(self.path, "t2", "h2", self.now - 10, self.now + 200, "active")
        res = ttl_watch.watch(self.path, now=self.now, window=0)
        self.assertEqual(len(res["active"]), 2)
        self.assertEqual(res["expired_active"]["count"], 0)
        self.assertEqual(len(res["soon_to_expire"]), 0)
        self.assertTrue(res["ok"])

    def test_expired_active(self):
        _insert(self.path, "t1", "h1", self.now - 500, self.now - 5, "active")
        res = ttl_watch.watch(self.path, now=self.now)
        self.assertEqual(res["expired_active"]["count"], 1)
        self.assertEqual(res["expired_active"]["holders"], ["h1"])
        self.assertFalse(res["ok"])

    def test_expired_holder_dedup(self):
        _insert(self.path, "t1", "h1", self.now - 500, self.now - 5, "active")
        _insert(self.path, "t2", "h1", self.now - 500, self.now - 1, "active")
        res = ttl_watch.watch(self.path, now=self.now)
        self.assertEqual(res["expired_active"]["count"], 2)
        self.assertEqual(res["expired_active"]["holders"], ["h1"])

    def test_soon_to_expire_within_window(self):
        _insert(self.path, "t1", "h1", self.now - 10, self.now + 100, "active")
        _insert(self.path, "t2", "h2", self.now - 10, self.now + 1000, "active")
        res = ttl_watch.watch(self.path, now=self.now, window=300)
        soon_keys = {r["task_key"] for r in res["soon_to_expire"]}
        self.assertEqual(soon_keys, {"t1"})
        self.assertEqual(len(res["active"]), 2)
        self.assertTrue(res["ok"])

    def test_soon_window_edge_boundary(self):
        _insert(self.path, "t1", "h1", self.now - 10, self.now + 300, "active")
        _insert(self.path, "t2", "h2", self.now - 10, self.now + 301, "active")
        res = ttl_watch.watch(self.path, now=self.now, window=300)
        soon_keys = {r["task_key"] for r in res["soon_to_expire"]}
        self.assertEqual(soon_keys, {"t1"})

    def test_non_active_ignored(self):
        _insert(self.path, "t1", "h1", self.now - 10, self.now - 5, "released")
        _insert(self.path, "t2", "h2", self.now - 10, self.now - 5, "expired")
        res = ttl_watch.watch(self.path, now=self.now)
        self.assertEqual(len(res["active"]), 0)
        self.assertEqual(res["expired_active"]["count"], 0)
        self.assertTrue(res["ok"])

    def test_missing_db_ok_and_not_present(self):
        missing = self.path + ".does-not-exist"
        if os.path.exists(missing):
            os.remove(missing)
        res = ttl_watch.watch(missing, now=self.now)
        self.assertEqual(res["active"], [])
        self.assertEqual(res["expired_active"]["count"], 0)
        self.assertTrue(res["ok"])
        self.assertFalse(res["present"])

    def test_missing_table(self):
        # db exists but has no leases table
        empty = _make_db()
        conn = sqlite3.connect(empty)
        conn.execute("CREATE TABLE other (x INTEGER)")
        conn.commit()
        conn.close()
        try:
            res = ttl_watch.watch(empty, now=self.now)
            self.assertEqual(res["active"], [])
            self.assertTrue(res["ok"])
            self.assertTrue(res["present"])
        finally:
            os.remove(empty)

    def test_determinism(self):
        _insert(self.path, "t1", "h1", self.now - 10, self.now + 100, "active")
        _insert(self.path, "t2", "h2", self.now - 500, self.now - 5, "active")
        a = ttl_watch.watch(self.path, now=self.now, window=120)
        b = ttl_watch.watch(self.path, now=self.now, window=120)
        self.assertEqual(a, b)

    def test_default_now_is_time_based(self):
        _insert(self.path, "t1", "h1", time.time() - 10, time.time() + 1000, "active")
        res = ttl_watch.watch(self.path)
        self.assertEqual(len(res["active"]), 1)
        self.assertIsInstance(res["now"], float)

    def test_expired_makes_not_ok_even_with_clean_audit(self):
        _insert(self.path, "t1", "h1", self.now - 100, self.now - 1, "active")
        res = ttl_watch.watch(self.path, now=self.now)
        self.assertFalse(res["ok"])
        self.assertTrue(res["present"])


if __name__ == "__main__":
    unittest.main()
