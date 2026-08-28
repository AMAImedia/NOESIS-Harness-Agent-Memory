import unittest
from noesis_harness.tree import TreeNode

class TestTree(unittest.TestCase):
    def test_add(self): r = TreeNode("a"); r.add(TreeNode("b")); self.assertEqual(len(r.children), 1)
    def test_find(self): r = TreeNode("a"); c = TreeNode("b"); r.add(c); self.assertIs(r.find("b"), c)
    def test_find_missing(self): r = TreeNode("a"); self.assertIsNone(r.find("z"))
    def test_size(self): r = TreeNode("a"); r.add(TreeNode("b")); r.add(TreeNode("c")); self.assertEqual(r.size(), 3)
    def test_nested(self):
        r = TreeNode("root"); a = TreeNode("a"); b = TreeNode("b"); a.add(b); r.add(a)
        self.assertEqual(r.size(), 3); self.assertIs(r.find("b"), b)
    def test_determinism(self):
        r = TreeNode("x"); r.add(TreeNode("y")); self.assertEqual(r.size(), 2)
    def test_root(self): self.assertEqual(TreeNode("r").value, "r")
    def test_empty_children(self): self.assertEqual(len(TreeNode("a").children), 0)
    def test_many(self):
        r = TreeNode(0)
        for i in range(5): r.add(TreeNode(i))
        self.assertEqual(len(r.children), 5)
    def test_find_self(self): n = TreeNode("a"); self.assertEqual(n.find("a").value, "a")
    def test_find_deep(self):
        r = TreeNode("r")
        for i in range(3): r.add(TreeNode(f"c{i}"))
        self.assertEqual(r.find("c2").value, "c2")
