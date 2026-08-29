import unittest
from noesis_harness.tree_serialize import tree_to_dict, tree_from_dict

class Node:
    def __init__(self, value, children=None):
        self.value = value; self.children = children or []

class TestTreeSerialize(unittest.TestCase):
    def test_single(self): n = Node(1); self.assertEqual(tree_to_dict(n), {"value": 1})
    def test_children(self):
        n = Node(1, [Node(2), Node(3)])
        d = tree_to_dict(n)
        self.assertEqual(d["value"], 1); self.assertEqual(len(d["children"]), 2)
    def test_roundtrip(self):
        n = Node(1, [Node(2), Node(3)])
        d = tree_to_dict(n); n2 = tree_from_dict(d)
        self.assertEqual(n2["value"], 1); self.assertEqual(len(n2["children"]), 2)
    def test_deep(self):
        n = Node(1, [Node(2, [Node(3)])])
        d = tree_to_dict(n)
        self.assertEqual(d["children"][0]["children"][0]["value"], 3)
    def test_empty(self): self.assertEqual(tree_to_dict(Node(None)), {"value": None})
    def test_string(self): self.assertEqual(tree_to_dict(Node("a")), {"value": "a"})
    def test_deterministic(self): n = Node(1, [Node(2)]); self.assertEqual(tree_to_dict(n), tree_to_dict(n))
    def test_roundtrip_deep(self):
        n = Node(1, [Node(2, [Node(3)])])
        d = tree_to_dict(n); n2 = tree_from_dict(d)
        self.assertEqual(n2["value"], 1)
        self.assertEqual(n2["children"][0]["children"][0]["value"], 3)
    def test_many(self):
        n = Node(0, [Node(i) for i in range(5)])
        self.assertEqual(len(tree_to_dict(n)["children"]), 5)
    def test_no_crash(self): tree_to_dict(Node(42)); tree_from_dict({"value": 42})
