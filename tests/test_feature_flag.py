import json, os, tempfile, unittest
from noesis_harness.feature_flag import FeatureFlags, is_enabled, load_flags

class TestFlag(unittest.TestCase):
    def test_missing_file(self): self.assertEqual(load_flags("/nope.json"), {})
    def test_enabled_true(self): self.assertTrue(is_enabled({"a": True}, "a"))
    def test_default(self): self.assertFalse(is_enabled({}, "x")); self.assertTrue(is_enabled({}, "x", True))
    def test_load(self):
        d = tempfile.mkdtemp(); p = os.path.join(d, "f.json"); open(p, "w").write(json.dumps({"a": 1}))
        self.assertEqual(load_flags(p), {"a": 1})
    def test_class(self):
        d = tempfile.mkdtemp(); p = os.path.join(d, "f.json"); open(p, "w").write(json.dumps({"x": True}))
        ff = FeatureFlags(p); self.assertTrue(ff.enabled("x")); self.assertFalse(ff.enabled("y"))
    def test_names(self):
        ff = FeatureFlags(); ff._flags = {"a": 1, "b": 2}; self.assertEqual(set(ff.names()), {"a", "b"})
    def test_invalid_json(self):
        d = tempfile.mkdtemp(); p = os.path.join(d, "f.json"); open(p, "w").write("{bad"); self.assertEqual(load_flags(p), {})
    def test_empty(self): self.assertFalse(FeatureFlags().enabled("x"))
    def test_bool_coerce(self): self.assertTrue(is_enabled({"a": 1}, "a")); self.assertFalse(is_enabled({"a": 0}, "a"))
    def test_no_mutation(self):
        d = {}; is_enabled(d, "a"); self.assertEqual(d, {})
