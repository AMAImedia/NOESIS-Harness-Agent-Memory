import unittest
from noesis_harness.validate_chain import Chain

class TestChain(unittest.TestCase):
    def test_empty(self): self.assertEqual(Chain().validate("x"), [])
    def test_pass(self):
        c = Chain().add(lambda v: [] if isinstance(v, str) else ["not str"])
        self.assertEqual(c.validate("hello"), [])
    def test_fail(self):
        c = Chain().add(lambda v: [] if isinstance(v, str) else ["not str"])
        self.assertEqual(len(c.validate(123)), 1)
    def test_multiple(self):
        c = Chain()
        c.add(lambda v: [] if isinstance(v, str) else ["not str"])
        c.add(lambda v: [] if len(v) > 0 else ["empty"])
        self.assertEqual(c.validate("hi"), [])
    def test_multiple_fail(self):
        c = Chain()
        c.add(lambda v: ["a"])
        c.add(lambda v: ["b"])
        self.assertEqual(c.validate("x"), ["a", "b"])
    def test_len(self): self.assertEqual(len(Chain().add(lambda v: [])), 1)
    def test_fluent(self): c = Chain().add(lambda v: []).add(lambda v: []); self.assertEqual(len(c), 2)
    def test_no_mutation(self): c = Chain().add(lambda v: []); c.validate("x"); self.assertEqual(len(c), 1)
    def test_deterministic(self): c = Chain().add(lambda v: []); self.assertEqual(c.validate("x"), c.validate("x"))
    def test_many(self):
        c = Chain()
        for _ in range(5): c.add(lambda v: [])
        self.assertEqual(len(c), 5)
