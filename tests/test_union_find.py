import unittest
from noesis_harness.union_find import DSU

class TestDSU(unittest.TestCase):
    def test_union(self): d=DSU(); d.union("a","b"); self.assertTrue(d.connected("a","b"))
    def test_not(self): d=DSU(); self.assertFalse(d.connected("a","b"))
    def test_transitive(self): d=DSU(); d.union("a","b"); d.union("b","c"); self.assertTrue(d.connected("a","c"))
    def test_dup(self): d=DSU(); d.union("a","b"); self.assertFalse(d.union("a","b"))
    def test_single(self): d=DSU(); d.make("x"); self.assertTrue(d.connected("x","x"))
    def test_many(self):
        d=DSU()
        for i in range(5): d.union(str(i), str(i+1))
        self.assertTrue(d.connected("0","5"))
    def test_isolated(self): d=DSU(); d.make("a"); d.make("b"); self.assertFalse(d.connected("a","b"))
    def test_determinism(self): a=DSU(); b=DSU(); a.union("1","2"); b.union("1","2"); self.assertEqual(a.connected("1","2"), b.connected("1","2"))
    def test_find_create(self): d=DSU(); self.assertEqual(d.find("z"), "z")
    def test_chain(self): d=DSU(); d.union("a","b"); d.union("c","d"); self.assertFalse(d.connected("a","c")); d.union("b","c"); self.assertTrue(d.connected("a","d"))
