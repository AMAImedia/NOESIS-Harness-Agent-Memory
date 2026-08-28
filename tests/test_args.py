import unittest
from noesis_harness.args import parse

class TestArgs(unittest.TestCase):
    def test_positional(self): self.assertEqual(parse(["run", "x"]), {"_": ["run", "x"]})
    def test_flag(self): self.assertEqual(parse(["--help"]), {"_": [], "help": True})
    def test_value(self): self.assertEqual(parse(["--name", "bob"]), {"_": [], "name": "bob"})
    def test_equals(self): self.assertEqual(parse(["--n=5"]), {"_": [], "n": "5"})
    def test_short(self): self.assertEqual(parse(["-v"]), {"_": [], "v": True})
    def test_mixed(self): self.assertEqual(parse(["run", "--a", "1", "-b"]), {"_": ["run"], "a": "1", "b": True})
    def test_empty(self): self.assertEqual(parse([]), {"_": []})
    def test_adjacent_value(self): self.assertEqual(parse(["--x", "y", "z"]), {"_": ["z"], "x": "y"})
    def test_no_flag_value(self): self.assertEqual(parse(["--a", "--b"]), {"_": [], "a": True, "b": True})
    def test_determinism(self): self.assertEqual(parse(["--x=1"]), parse(["--x=1"]))
