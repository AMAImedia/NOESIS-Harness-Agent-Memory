import unittest

from noesis_harness.freq_counter import FreqCounter


class TestFreqCounter(unittest.TestCase):

    def test_inc_basic(self):
        fc = FreqCounter()
        fc.inc("a")
        fc.inc("a")
        self.assertEqual(fc._counts["a"], 2)

    def test_inc_with_n(self):
        fc = FreqCounter()
        fc.inc("a", 5)
        self.assertEqual(fc._counts["a"], 5)

    def test_inc_negative(self):
        fc = FreqCounter()
        fc.inc("a", 3)
        fc.inc("a", -1)
        self.assertEqual(fc._counts["a"], 2)

    def test_total(self):
        fc = FreqCounter()
        fc.inc("a", 3)
        fc.inc("b", 2)
        fc.inc("c", 1)
        self.assertEqual(fc.total(), 6)

    def test_total_empty(self):
        fc = FreqCounter()
        self.assertEqual(fc.total(), 0)

    def test_top_ordering(self):
        fc = FreqCounter()
        fc.inc("a", 1)
        fc.inc("b", 3)
        fc.inc("c", 2)
        self.assertEqual(fc.top(3), [("b", 3), ("c", 2), ("a", 1)])

    def test_top_k_less_than_size(self):
        fc = FreqCounter()
        fc.inc("a", 1)
        fc.inc("b", 2)
        self.assertEqual(fc.top(1), [("b", 2)])

    def test_top_zero(self):
        fc = FreqCounter()
        fc.inc("a", 1)
        self.assertEqual(fc.top(0), [])

    def test_tie_handling(self):
        fc = FreqCounter()
        fc.inc("b", 2)
        fc.inc("a", 2)
        fc.inc("c", 2)
        self.assertEqual(fc.top(3), [("a", 2), ("b", 2), ("c", 2)])

    def test_tie_then_ordering(self):
        fc = FreqCounter()
        fc.inc("a", 3)
        fc.inc("b", 2)
        fc.inc("c", 2)
        self.assertEqual(fc.top(3), [("a", 3), ("b", 2), ("c", 2)])

    def test_most_common_empty(self):
        fc = FreqCounter()
        self.assertEqual(fc.most_common(), [])

    def test_merge(self):
        f1 = FreqCounter()
        f1.inc("a", 1)
        f1.inc("b", 2)
        f2 = FreqCounter()
        f2.inc("a", 3)
        f2.inc("c", 4)
        f1.merge(f2)
        self.assertEqual(f1.most_common(), [("a", 4), ("c", 4), ("b", 2)])

    def test_merge_empty(self):
        f1 = FreqCounter()
        f1.inc("a", 1)
        f2 = FreqCounter()
        f1.merge(f2)
        self.assertEqual(f1.most_common(), [("a", 1)])

    def test_determinism(self):
        def build():
            fc = FreqCounter()
            for k, n in [("x", 2), ("y", 2), ("z", 1), ("w", 5)]:
                fc.inc(k, n)
            return fc.most_common()
        self.assertEqual(build(), build())

    def test_empty_top(self):
        fc = FreqCounter()
        self.assertEqual(fc.top(5), [])


if __name__ == "__main__":
    unittest.main()
