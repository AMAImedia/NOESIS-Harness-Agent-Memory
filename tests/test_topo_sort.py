import unittest
from noesis_harness.topo_sort import topo_sort

class TestTopo(unittest.TestCase):
    def test_linear(self): self.assertEqual(topo_sort(["a","b","c"],[("a","b"),("b","c")]),["a","b","c"])
    def test_branch(self): r=topo_sort(["a","b","c"],[("a","b"),("a","c")]); self.assertEqual(r[0],"a"); self.assertEqual(set(r),{"a","b","c"})
    def test_empty(self): self.assertEqual(topo_sort([],[]),[])
    def test_single(self): self.assertEqual(topo_sort(["a"],[]),["a"])
    def test_cycle(self):
        with self.assertRaises(ValueError): topo_sort(["a","b"],[("a","b"),("b","a")])
    def test_disconnected(self): r=topo_sort(["a","b"],[]); self.assertEqual(set(r),{"a","b"})
    def test_determinism(self): self.assertEqual(topo_sort(["a","b"],[("a","b")]),topo_sort(["a","b"],[("a","b")]))
    def test_diamond(self): r=topo_sort(["a","b","c","d"],[("a","b"),("a","c"),("b","d"),("c","d")]); self.assertEqual(r[0],"a"); self.assertEqual(r[-1],"d")
    def test_no_edges(self): self.assertEqual(set(topo_sort(["x","y","z"],[])),{"x","y","z"})
    def test_many(self): self.assertEqual(topo_sort(["1","2","3","4"],[("1","2"),("2","3"),("3","4")]),["1","2","3","4"])
