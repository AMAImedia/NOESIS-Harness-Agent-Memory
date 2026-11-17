"""tests/test_ring_buffer.py

Unit tests for noesis_harness.ring_buffer.RingBuffer.

Stdlib-only (unittest). Covers: push up to capacity, overflow dropping the
oldest, to_list ordering, __len__, is_full, and the capacity=1 edge case.
"""

import unittest

from noesis_harness.ring_buffer import RingBuffer


class TestRingBuffer(unittest.TestCase):
    def test_push_up_to_capacity(self):
        rb = RingBuffer(3)
        rb.push(1)
        rb.push(2)
        rb.push(3)
        self.assertEqual(rb.to_list(), [1, 2, 3])

    def test_len_after_pushes(self):
        rb = RingBuffer(5)
        self.assertEqual(len(rb), 0)
        rb.push("a")
        rb.push("b")
        self.assertEqual(len(rb), 2)

    def test_len_capped_at_capacity(self):
        rb = RingBuffer(2)
        for i in range(10):
            rb.push(i)
        self.assertEqual(len(rb), 2)

    def test_overflow_drops_oldest(self):
        rb = RingBuffer(3)
        for i in range(1, 6):
            rb.push(i)
        self.assertEqual(rb.to_list(), [3, 4, 5])

    def test_to_list_order_oldest_first(self):
        rb = RingBuffer(4)
        for ch in ["x", "y", "z", "w"]:
            rb.push(ch)
        self.assertEqual(rb.to_list(), ["x", "y", "z", "w"])

    def test_to_list_is_snapshot(self):
        rb = RingBuffer(2)
        rb.push(1)
        rb.push(2)
        snapshot = rb.to_list()
        snapshot.append(99)
        self.assertEqual(rb.to_list(), [1, 2])

    def test_is_full_false_before_capacity(self):
        rb = RingBuffer(3)
        rb.push(1)
        rb.push(2)
        self.assertFalse(rb.is_full())

    def test_is_full_true_at_capacity(self):
        rb = RingBuffer(3)
        for i in range(3):
            rb.push(i)
        self.assertTrue(rb.is_full())

    def test_is_full_true_after_overflow(self):
        rb = RingBuffer(2)
        for i in range(5):
            rb.push(i)
        self.assertTrue(rb.is_full())

    def test_capacity_one_edge(self):
        rb = RingBuffer(1)
        rb.push("first")
        self.assertEqual(rb.to_list(), ["first"])
        self.assertTrue(rb.is_full())
        rb.push("second")
        self.assertEqual(rb.to_list(), ["second"])
        self.assertEqual(len(rb), 1)

    def test_empty_buffer(self):
        rb = RingBuffer(3)
        self.assertEqual(rb.to_list(), [])
        self.assertEqual(len(rb), 0)
        self.assertFalse(rb.is_full())

    def test_capacity_invalid_raises(self):
        with self.assertRaises(ValueError):
            RingBuffer(0)
        with self.assertRaises(ValueError):
            RingBuffer(-5)

    def test_overflow_with_object_items(self):
        rb = RingBuffer(2)
        rb.push({"id": 1})
        rb.push({"id": 2})
        rb.push({"id": 3})
        self.assertEqual(rb.to_list(), [{"id": 2}, {"id": 3}])


if __name__ == "__main__":
    unittest.main()
