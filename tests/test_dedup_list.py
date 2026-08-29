import unittest
from noesis_harness.dedup_list import dedup

class TestDedup(unittest.TestCase):
    def test_basic(self): self.assertEqual(dedup([1,2,1,3,2]),[1,2,3])
    def test_empty(self): self.assertEqual(dedup([]),[])
    def test_no_dup(self): self.assertEqual(dedup([1,2,3]),[1,2,3])
    def test_all_dup(self): self.assertEqual(dedup([1,1,1]),[1])
    def test_order(self): self.assertEqual(dedup(["b","a","b","c"]),["b","a","c"])
    def test_strings(self): self.assertEqual(dedup(["x","y","x"]),["x","y"])
    def test_no_mutate(self): a=[1,1,2]; dedup(a); self.assertEqual(a,[1,1,2])
    def test_determinism(self): self.assertEqual(dedup([1,2,1]), dedup([1,2,1]))
    def test_mixed(self): self.assertEqual(dedup([None,1,None]),[None,1])
    def test_many(self): self.assertEqual(dedup([1]*100+[2]),[1,2])
