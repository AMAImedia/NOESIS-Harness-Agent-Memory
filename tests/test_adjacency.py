import unittest
from noesis_harness.adjacency import AdjacencyList

class TestAdjacency(unittest.TestCase):
    def test_edge(self): g = AdjacencyList(); g.add_edge(1, 2); self.assertIn(2, g.neighbors(1)); self.assertIn(1, g.neighbors(2))
    def test_nodes(self): g = AdjacencyList(); g.add_edge(1, 2); g.add_edge(2, 3); self.assertEqual(set(g.nodes()), {1, 2, 3})
    def test_neighbors_empty(self): self.assertEqual(AdjacencyList().neighbors(5), [])
    def test_contains(self): g = AdjacencyList(); g.add_edge(1, 2); self.assertIn(1, g); self.assertNotIn(9, g)
    def test_undirected(self): g = AdjacencyList(); g.add_edge(1, 2); self.assertIn(1, g.neighbors(2))
    def test_dedup(self): g = AdjacencyList(); g.add_edge(1, 2); g.add_edge(1, 2); self.assertEqual(len(g.neighbors(1)), 1)
    def test_determinism(self): a = AdjacencyList(); b = AdjacencyList(); a.add_edge(1, 2); b.add_edge(1, 2); self.assertEqual(a.neighbors(1), b.neighbors(1))
    def test_many(self):
        g = AdjacencyList()
        for i in range(5): g.add_edge(i, i+1)
        self.assertEqual(len(g.nodes()), 6)
    def test_self_no_dup(self): g = AdjacencyList(); g.add_edge(1, 1); self.assertEqual(len(g.neighbors(1)), 1)
    def test_no_mutation(self): g = AdjacencyList(); g.add_edge(1, 2); g.neighbors(1); self.assertIn(2, g.neighbors(1))
