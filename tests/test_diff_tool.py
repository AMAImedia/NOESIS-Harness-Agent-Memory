import unittest
from noesis_harness.diff_tool import diff

class TestDiff(unittest.TestCase):
    def test_added(self): self.assertEqual(diff({}, {"a": 1})["added"], ["a"])
    def test_removed(self): self.assertEqual(diff({"a": 1}, {})["removed"], ["a"])
    def test_changed(self): self.assertEqual(diff({"a": 1}, {"a": 2})["changed"], ["a"])
    def test_same(self): self.assertEqual(diff({"a": 1}, {"a": 1}), {"added": [], "removed": [], "changed": []})
    def test_multiple(self): r = diff({"a": 1, "b": 2}, {"b": 3, "c": 4}); self.assertEqual(r["added"], ["c"]); self.assertEqual(r["removed"], ["a"]); self.assertEqual(r["changed"], ["b"])
    def test_empty(self): self.assertEqual(diff({}, {}), {"added": [], "removed": [], "changed": []})
    def test_determinism(self): self.assertEqual(diff({"a": 1}, {"b": 2}), diff({"a": 1}, {"b": 2}))
    def test_sorted(self): r = diff({}, {"b": 1, "a": 2}); self.assertEqual(r["added"], ["a", "b"])
    def test_no_mutation(self): a = {"x": 1}; b = {"x": 2}; diff(a, b); self.assertEqual(a, {"x": 1})
    def test_nested_same(self): self.assertEqual(diff({"a": {"x": 1}}, {"a": {"x": 1}})["changed"], [])
