import unittest
from noesis_harness.json_patch import apply_patch

class TestPatch(unittest.TestCase):
    def test_add(self): self.assertEqual(apply_patch({}, {"a": 1}), {"a": 1})
    def test_overwrite(self): self.assertEqual(apply_patch({"a": 1}, {"a": 2}), {"a": 2})
    def test_remove(self): self.assertEqual(apply_patch({"a": 1, "b": 2}, {"a": None}), {"b": 2})
    def test_no_mutation(self): d = {"a": 1}; apply_patch(d, {"b": 2}); self.assertEqual(d, {"a": 1})
    def test_empty_patch(self): self.assertEqual(apply_patch({"a": 1}, {}), {"a": 1})
    def test_empty_doc(self): self.assertEqual(apply_patch({}, {"a": None}), {})
    def test_determinism(self): self.assertEqual(apply_patch({"a": 1}, {"b": 2}), apply_patch({"a": 1}, {"b": 2}))
    def test_remove_missing(self): self.assertEqual(apply_patch({}, {"a": None}), {})
    def test_multiple(self): self.assertEqual(apply_patch({"a": 1, "b": 2}, {"b": None, "c": 3}), {"a": 1, "c": 3})
    def test_returns_dict(self): self.assertIsInstance(apply_patch({}, {"a": 1}), dict)
