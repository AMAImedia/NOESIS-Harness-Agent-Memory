import os, tempfile, unittest
from noesis_harness.event_store import EventStore
from noesis_harness.tag_index import build, search

class TestTagIndex(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(); self.path = os.path.join(self.tmp, "e.jsonl")
        s = EventStore(self.path); s.append("note", {"text": "hello #foo #bar"}, event_id="e1"); s.append("note", {"text": "world #foo"}, event_id="e2")
    def test_build(self): idx = build(self.path); self.assertIn("foo", idx); self.assertIn("bar", idx)
    def test_search(self): idx = build(self.path); self.assertEqual(set(search(idx, "foo")), {"e1", "e2"})
    def test_case_insensitive(self): idx = build(self.path); self.assertEqual(search(idx, "FOO"), search(idx, "foo"))
    def test_hash_strip(self): idx = build(self.path); self.assertEqual(search(idx, "#foo"), search(idx, "foo"))
    def test_missing(self): idx = build(self.path); self.assertEqual(search(idx, "nope"), [])
    def test_empty(self): self.assertEqual(build(os.path.join(self.tmp, "nope.jsonl")), {})
    def test_determinism(self): self.assertEqual(build(self.path), build(self.path))
    def test_no_mutation(self):
        before = open(self.path, "rb").read(); build(self.path); self.assertEqual(open(self.path, "rb").read(), before)
    def test_single_tag(self):
        p2 = os.path.join(self.tmp, "e2.jsonl"); EventStore(p2).append("note", {"text": "#solo"}, event_id="e9")
        self.assertEqual(search(build(p2), "solo"), ["e9"])
    def test_multiple(self): idx = build(self.path); self.assertEqual(len(search(idx, "foo")), 2)
