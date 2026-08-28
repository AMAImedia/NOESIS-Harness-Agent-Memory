import json, os, tempfile, unittest
from noesis_harness.queue_view import view

class TestQueueView(unittest.TestCase):
    def test_missing(self): self.assertEqual(view("/nope.json")["count"], 0)
    def test_empty_list(self):
        d = tempfile.mkdtemp(); p = os.path.join(d, "q.json"); open(p, "w").write(json.dumps([]))
        self.assertEqual(view(p)["count"], 0)
    def test_items(self):
        d = tempfile.mkdtemp(); p = os.path.join(d, "q.json"); open(p, "w").write(json.dumps([1, 2, 3]))
        self.assertEqual(view(p)["count"], 3); self.assertEqual(view(p)["items"], [1, 2, 3])
    def test_invalid_json(self):
        d = tempfile.mkdtemp(); p = os.path.join(d, "q.json"); open(p, "w").write("{bad")
        self.assertEqual(view(p)["count"], 0)
    def test_non_list(self):
        d = tempfile.mkdtemp(); p = os.path.join(d, "q.json"); open(p, "w").write(json.dumps({"a": 1}))
        self.assertEqual(view(p)["count"], 0)
    def test_determinism(self):
        d = tempfile.mkdtemp(); p = os.path.join(d, "q.json"); open(p, "w").write(json.dumps([1, 2]))
        self.assertEqual(view(p), view(p))
    def test_no_write(self):
        d = tempfile.mkdtemp(); p = os.path.join(d, "q.json"); open(p, "w").write(json.dumps([1]))
        before = open(p).read(); view(p); self.assertEqual(open(p).read(), before)
    def test_returns_dict(self): self.assertIsInstance(view("/nope.json"), dict)
    def test_single(self):
        d = tempfile.mkdtemp(); p = os.path.join(d, "q.json"); open(p, "w").write(json.dumps(["x"]))
        self.assertEqual(view(p)["items"], ["x"])
    def test_large(self):
        d = tempfile.mkdtemp(); p = os.path.join(d, "q.json"); open(p, "w").write(json.dumps(list(range(100))))
        self.assertEqual(view(p)["count"], 100)
