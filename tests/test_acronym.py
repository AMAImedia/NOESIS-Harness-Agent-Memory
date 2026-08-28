import unittest
from noesis_harness.acronym import acronym

class TestAcronym(unittest.TestCase):
    def test_basic(self): self.assertEqual(acronym("Hello World"), "HW")
    def test_three(self): self.assertEqual(acronym("New York City"), "NYC")
    def test_empty(self): self.assertEqual(acronym(""), "")
    def test_max_len(self): self.assertEqual(acronym("Alpha Beta Gamma Delta", 2), "AB")
    def test_lower(self): self.assertEqual(acronym("foo bar"), "FB")
    def test_dashes(self): self.assertEqual(acronym("read-write-memory"), "RWM")
    def test_determinism(self): self.assertEqual(acronym("a b c"), acronym("a b c"))
    def test_numbers(self): self.assertEqual(acronym("Item 2 Order"), "IO")
    def test_single(self): self.assertEqual(acronym("hello"), "H")
    def test_many(self): self.assertEqual(acronym("one two three four five"), "OTTFF")
