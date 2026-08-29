import unittest
from noesis_harness.bfs import bfs

class TestBFS(unittest.TestCase):
    def test_linear(self): self.assertEqual(bfs({"a":["b"],"b":["c"],"c":[]}, "a"), ["a","b","c"])
    def test_branch(self): self.assertEqual(set(bfs({"a":["b","c"],"b":[],"c":[]}, "a")), {"a","b","c"})
    def test_cycle(self): self.assertEqual(set(bfs({"a":["b"],"b":["a"]}, "a")), {"a","b"})
    def test_missing(self): self.assertEqual(bfs({}, "x"), [])
    def test_single(self): self.assertEqual(bfs({"a":[]}, "a"), ["a"])
    def test_order(self): self.assertEqual(bfs({"a":["b","c"],"b":["d"],"c":["d"],"d":[]}, "a")[0], "a")
    def test_disconnected(self): self.assertNotIn("c", bfs({"a":["b"],"b":[],"c":[]}, "a"))
    def test_empty_graph(self): self.assertEqual(bfs({}, "a"), [])
    def test_determinism(self): self.assertEqual(bfs({"a":["b"],"b":[]}, "a"), bfs({"a":["b"],"b":[]}, "a"))
    def test_many(self): self.assertEqual(len(bfs({str(i):[str(i+1)] for i in range(5)}, "0")), 6)
