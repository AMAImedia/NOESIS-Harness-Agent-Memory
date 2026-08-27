"""tests/test_bounded_cache.py

Unit tests for noesis_harness.bounded_cache.BoundedCache.

Stdlib only. Run: py -3.14 -m unittest tests.test_bounded_cache -v
"""

import threading
import unittest

from noesis_harness.bounded_cache import BoundedCache


class TestBoundedCache(unittest.TestCase):
    def test_put_and_get(self):
        c = BoundedCache(maxsize=3)
        c.put("a", 1)
        self.assertEqual(c.get("a"), 1)

    def test_missing_key_returns_none(self):
        c = BoundedCache(maxsize=3)
        c.put("a", 1)
        self.assertIsNone(c.get("missing"))

    def test_overwrite_updates_value(self):
        c = BoundedCache(maxsize=3)
        c.put("a", 1)
        c.put("a", 2)
        self.assertEqual(c.get("a"), 2)

    def test_overwrite_refreshes_recency(self):
        c = BoundedCache(maxsize=2)
        c.put("a", 1)
        c.put("b", 2)
        c.put("a", 3)  # refresh a; now a is newest
        c.put("c", 4)  # overflow -> evict oldest = b
        self.assertIsNone(c.get("b"))
        self.assertEqual(c.get("a"), 3)
        self.assertEqual(c.get("c"), 4)

    def test_fifo_eviction_order(self):
        c = BoundedCache(maxsize=2)
        c.put("x", 1)
        c.put("y", 2)
        c.put("z", 3)  # overflow -> evict x
        self.assertIsNone(c.get("x"))
        self.assertEqual(c.get("y"), 2)
        self.assertEqual(c.get("z"), 3)

    def test_len_reflects_size(self):
        c = BoundedCache(maxsize=5)
        self.assertEqual(len(c), 0)
        c.put("a", 1)
        c.put("b", 2)
        self.assertEqual(len(c), 2)
        c.put("a", 9)  # overwrite, no size change
        self.assertEqual(len(c), 2)

    def test_keys_returns_insertion_order(self):
        c = BoundedCache(maxsize=4)
        c.put("a", 1)
        c.put("b", 2)
        c.put("c", 3)
        self.assertEqual(c.keys(), ["a", "b", "c"])

    def test_keys_snapshot_isolation(self):
        c = BoundedCache(maxsize=4)
        c.put("a", 1)
        ks = c.keys()
        c.put("b", 2)
        self.assertEqual(ks, ["a"])

    def test_default_maxsize(self):
        c = BoundedCache()
        self.assertEqual(c.maxsize, 128)

    def test_maxsize_zero_raises(self):
        with self.assertRaises(ValueError):
            BoundedCache(maxsize=0)

    def test_eviction_does_not_lose_latest(self):
        c = BoundedCache(maxsize=3)
        for i in range(10):
            c.put("k%d" % i, i)
        self.assertEqual(len(c), 3)
        self.assertEqual(c.get("k9"), 9)
        self.assertEqual(c.get("k7"), 7)

    def test_concurrency_smoke(self):
        c = BoundedCache(maxsize=50)
        errors = []

        def worker(n):
            try:
                for i in range(200):
                    c.put("w%d-%d" % (n, i), i)
                    _ = c.get("w%d-%d" % (n, i))
            except Exception as exc:  # pragma: no cover - defensive
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(n,)) for n in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])
        self.assertLessEqual(len(c), 50)


if __name__ == "__main__":
    unittest.main()
