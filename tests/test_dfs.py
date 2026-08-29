import unittest
from noesis_harness.dfs import dfs

class TestDFS(unittest.TestCase):
    def test_linear(self): self.assertEqual(dfs({"a":["b"],"b":["c"],"c":[]}, "a"), ["a","b","c"])
    def test_branch(self): self.assertEqual(set(dfs({"a":["b","c"],"b":[],"c":[]}, "a")), {"a","b","c"})
    def test_cycle(self): self.assertEqual(set(dfs({"a":["b"],"b":["a"]}, "a")), {"a","b"})
    def test_missing(self): self.assertEqual(dfs({}, "x"), [])
    def test_single(self): self.assertEqual(dfs({"a":[]}, "a"), ["a"])
    def test_order(self): self.assertEqual(dfs({"a":["b","c"],"b":[],"c":[]}, "a")[0], "a")
    def test_disconnected(self): self.assertNotIn("c", dfs({"a":["b"],"b":[],"c":[]}, "a"))
    def test_empty(self): self.assertEqual(dfs({}, "a"), [])
    def test_determinism(self): self.assertEqual(dfs({"a":["b"],"b":[]}, "a"), dfs({"a":["b"],"b":[]}, "a"))
    def test_many(self): self.assertEqual(len(dfs({str(i):[str(i+1)] for i in range(5)}, "0")), 6)
