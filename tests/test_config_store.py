import json, os, tempfile, unittest
from noesis_harness.config_store import ConfigStore

class TestConfigStore(unittest.TestCase):
    def setUp(self): self.tmp = tempfile.mkdtemp(); self.path = os.path.join(self.tmp, "c.json")
    def test_set_get(self): s = ConfigStore(self.path); s.set("a", 1); self.assertEqual(s.get("a"), 1)
    def test_get_all(self): s = ConfigStore(self.path); s.set("a", 1); s.set("b", 2); self.assertEqual(s.get_all(), {"a": 1, "b": 2})
    def test_overwrite(self): s = ConfigStore(self.path); s.set("a", 1); s.set("a", 2); self.assertEqual(s.get("a"), 2)
    def test_default(self): self.assertIsNone(ConfigStore(self.path).get("nope")); self.assertEqual(ConfigStore(self.path).get("nope", 5), 5)
    def test_missing_file(self): self.assertEqual(ConfigStore(os.path.join(self.tmp, "nope.json")).get_all(), {})
    def test_persistence(self): s = ConfigStore(self.path); s.set("x", 1); s2 = ConfigStore(self.path); self.assertEqual(s2.get("x"), 1)
    def test_invalid_json(self):
        open(self.path, "w").write("{bad"); self.assertEqual(ConfigStore(self.path).get_all(), {})
    def test_determinism(self):
        s = ConfigStore(self.path); s.set("a", 1); self.assertEqual(s.get_all(), {"a": 1})
    def test_many(self):
        s = ConfigStore(self.path)
        for i in range(10): s.set(f"k{i}", i)
        self.assertEqual(len(s.get_all()), 10)
    def test_no_extra_keys(self): s = ConfigStore(self.path); s.set("a", 1); self.assertIn("a", s.get_all())
