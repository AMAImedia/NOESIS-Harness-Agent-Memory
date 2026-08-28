import json, os, tempfile, unittest
from noesis_harness.config_view import view, get

class TestConfigView(unittest.TestCase):
    def test_missing(self): v = view("/nope.json"); self.assertEqual(v["config"], {}); self.assertEqual(v["keys"], [])
    def test_load(self):
        d = tempfile.mkdtemp(); p = os.path.join(d, "c.json"); open(p, "w").write(json.dumps({"a": 1, "b": 2}))
        v = view(p); self.assertEqual(v["keys"], ["a", "b"]); self.assertEqual(get(v, "a"), 1)
    def test_digest_stable(self):
        d = tempfile.mkdtemp(); p = os.path.join(d, "c.json"); open(p, "w").write(json.dumps({"a": 1}))
        self.assertEqual(view(p)["digest"], view(p)["digest"])
    def test_get_default(self): self.assertIsNone(get(view("/nope.json"), "x")); self.assertEqual(get(view("/nope.json"), "x", 5), 5)
    def test_invalid_json(self):
        d = tempfile.mkdtemp(); p = os.path.join(d, "c.json"); open(p, "w").write("{bad"); self.assertEqual(view(p)["config"], {})
    def test_non_dict(self):
        d = tempfile.mkdtemp(); p = os.path.join(d, "c.json"); open(p, "w").write(json.dumps([1, 2]))
        v = view(p); self.assertIn("value", v["config"])
    def test_order(self):
        d = tempfile.mkdtemp(); p1 = os.path.join(d, "a.json"); p2 = os.path.join(d, "b.json")
        open(p1, "w").write(json.dumps({"b": 2, "a": 1})); open(p2, "w").write(json.dumps({"a": 1, "b": 2}))
        self.assertEqual(view(p1)["digest"], view(p2)["digest"])
    def test_no_write(self):
        d = tempfile.mkdtemp(); p = os.path.join(d, "c.json"); open(p, "w").write(json.dumps({"a": 1}))
        before = open(p).read(); view(p); self.assertEqual(open(p).read(), before)
    def test_keys_sorted(self):
        d = tempfile.mkdtemp(); p = os.path.join(d, "c.json"); open(p, "w").write(json.dumps({"z": 1, "a": 2}))
        self.assertEqual(view(p)["keys"], ["a", "z"])
    def test_get_present(self):
        d = tempfile.mkdtemp(); p = os.path.join(d, "c.json"); open(p, "w").write(json.dumps({"k": "v"}))
        self.assertEqual(get(view(p), "k"), "v")
