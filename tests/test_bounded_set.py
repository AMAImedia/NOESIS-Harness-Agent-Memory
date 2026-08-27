"""tests/test_bounded_set.py

Unit tests for noesis_harness.bounded_set.BoundedSet.

Covers membership, FIFO overflow eviction order, length, empty state, a
maxsize of 1, a concurrency smoke test, and deterministic insertion order.
"""

import threading
import unittest

from noesis_harness.bounded_set import BoundedSet


class TestBoundedSet(unittest.TestCase):

    def test_add_and_contains(self):
        s = BoundedSet(maxsize=3)
        s.add("a")
        s.add("b")
        self.assertIn("a", s)
        self.assertIn("b", s)
        self.assertNotIn("c", s)

    def test_len(self):
        s = BoundedSet(maxsize=5)
        self.assertEqual(len(s), 0)
        s.add(1)
        s.add(2)
        s.add(3)
        self.assertEqual(len(s), 3)

    def test_empty(self):
        s = BoundedSet(maxsize=2)
        self.assertEqual(len(s), 0)
        self.assertNotIn("x", s)
        self.assertEqual(s.to_list(), [])

    def test_to_list_insertion_order(self):
        s = BoundedSet(maxsize=4)
        for v in ("a", "b", "c"):
            s.add(v)
        self.assertEqual(s.to_list(), ["a", "b", "c"])

    def test_overflow_evicts_oldest(self):
        s = BoundedSet(maxsize=3)
        for v in ("a", "b", "c"):
            s.add(v)
        s.add("d")
        self.assertEqual(len(s), 3)
        self.assertNotIn("a", s)
        self.assertIn("d", s)
        self.assertEqual(s.to_list(), ["b", "c", "d"])

    def test_re_add_existing_is_noop_for_order(self):
        s = BoundedSet(maxsize=2)
        s.add("a")
        s.add("b")
        s.add("a")  # already present -> no recency change
        s.add("c")  # overflow evicts "a" (still genuinely oldest), not "b"
        self.assertNotIn("a", s)
        self.assertIn("b", s)
        self.assertIn("c", s)
        self.assertEqual(s.to_list(), ["b", "c"])

    def test_full_eviction_chain(self):
        s = BoundedSet(maxsize=2)
        for v in range(10):
            s.add(v)
        self.assertEqual(len(s), 2)
        self.assertEqual(s.to_list(), [8, 9])
        for v in range(8):
            self.assertNotIn(v, s)

    def test_maxsize_one(self):
        s = BoundedSet(maxsize=1)
        s.add("x")
        s.add("y")
        s.add("z")
        self.assertEqual(len(s), 1)
        self.assertNotIn("x", s)
        self.assertNotIn("y", s)
        self.assertIn("z", s)
        self.assertEqual(s.to_list(), ["z"])

    def test_invalid_maxsize(self):
        with self.assertRaises(ValueError):
            BoundedSet(maxsize=0)
        with self.assertRaises(ValueError):
            BoundedSet(maxsize=-5)

    def test_determinism(self):
        # Same inputs must always produce the same snapshot order.
        def build():
            s = BoundedSet(maxsize=3)
            for v in ("a", "b", "c", "d", "e"):
                s.add(v)
            return s.to_list()

        self.assertEqual(build(), build())
        self.assertEqual(build(), ["c", "d", "e"])

    def test_concurrency_smoke(self):
        s = BoundedSet(maxsize=50)
        threads = []
        errors = []

        def worker(start):
            try:
                for i in range(start, start + 100):
                    s.add(i)
            except Exception as exc:  # pragma: no cover - defensive
                errors.append(exc)

        for t in range(8):
            th = threading.Thread(target=worker, args=(t * 100,))
            threads.append(th)
            th.start()
        for th in threads:
            th.join()

        self.assertEqual(errors, [])
        # No member appears twice; total distinct members bounded by maxsize.
        snap = s.to_list()
        self.assertEqual(len(snap), len(set(snap)))
        self.assertLessEqual(len(s), 50)


if __name__ == "__main__":
    unittest.main()
