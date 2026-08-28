import os, tempfile, unittest
from noesis_harness.event_store import EventStore
from noesis_harness.event_aggregator import aggregate

class TestAgg(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(); self.path = os.path.join(self.tmp, "e.jsonl")
        s = EventStore(self.path)
        for i in range(5): s.append("note", {"i": i}, event_id=f"e{i}")
        s.append("task", {"x": 1}, event_id="t1")
    def test_total(self): self.assertEqual(aggregate(self.path)["total"], 6)
    def test_per_type(self): self.assertEqual(aggregate(self.path)["per_type"]["note"], 5)
    def test_top(self): self.assertEqual(aggregate(self.path)["top"][0][0], "note")
    def test_missing(self): self.assertEqual(aggregate(os.path.join(self.tmp, "nope.jsonl"))["total"], 0)
    def test_empty(self):
        p2 = os.path.join(self.tmp, "e2.jsonl"); self.assertEqual(aggregate(p2)["total"], 0)
    def test_determinism(self): self.assertEqual(aggregate(self.path), aggregate(self.path))
    def test_no_mutation(self):
        before = open(self.path, "rb").read(); aggregate(self.path); self.assertEqual(open(self.path, "rb").read(), before)
    def test_returns_dict(self): self.assertIsInstance(aggregate(self.path), dict)
    def test_per_type_complete(self): self.assertIn("task", aggregate(self.path)["per_type"])
    def test_top_length(self): self.assertLessEqual(len(aggregate(self.path)["top"]), 3)
