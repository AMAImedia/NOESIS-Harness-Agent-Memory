import os, tempfile, unittest
from noesis_harness.event_store import EventStore
from noesis_harness.event_filter import filter_by_type, filter_by_payload_key

class TestFilter(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(); self.path = os.path.join(self.tmp, "e.jsonl")
        s = EventStore(self.path); s.append("note", {"k": 1}, event_id="e1"); s.append("task", {"k": 1}, event_id="e2"); s.append("note", {"k": 2}, event_id="e3")
    def test_by_type(self): self.assertEqual(len(filter_by_type(self.path, "note")), 2)
    def test_by_key(self): self.assertEqual(len(filter_by_payload_key(self.path, "k", 1)), 2)
    def test_missing(self): self.assertEqual(filter_by_type(os.path.join(self.tmp, "nope.jsonl"), "note"), [])
    def test_empty(self):
        p2 = os.path.join(self.tmp, "e2.jsonl"); self.assertEqual(filter_by_type(p2, "note"), [])
    def test_no_match(self): self.assertEqual(filter_by_payload_key(self.path, "k", 99), [])
    def test_type_exact(self): self.assertEqual(filter_by_type(self.path, "NOTE"), [])
    def test_determinism(self): self.assertEqual(filter_by_type(self.path, "note"), filter_by_type(self.path, "note"))
    def test_no_mutation(self):
        before = open(self.path, "rb").read(); filter_by_type(self.path, "note"); self.assertEqual(open(self.path, "rb").read(), before)
    def test_payload_key_missing(self): self.assertEqual(filter_by_payload_key(self.path, "nope", 1), [])
    def test_returns_list(self): self.assertIsInstance(filter_by_type(self.path, "note"), list)
