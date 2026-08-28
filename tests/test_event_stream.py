import os, tempfile, unittest
from noesis_harness.event_store import EventStore
from noesis_harness.event_stream import stream

class TestStream(unittest.TestCase):
    def setUp(self): self.tmp = tempfile.mkdtemp(); self.path = os.path.join(self.tmp, "e.jsonl"); s = EventStore(self.path); [s.append("note", {"i": i}, event_id=f"e{i}") for i in range(5)]
    def test_batches(self): self.assertEqual(sum(len(b) for b in stream(self.path, 2)), 5)
    def test_batch_size(self): batches = list(stream(self.path, 2)); self.assertEqual(len(batches[0]), 2)
    def test_single_batch(self): self.assertEqual(len(list(stream(self.path, 10))), 1)
    def test_empty(self): self.assertEqual(list(stream(os.path.join(self.tmp, "nope.jsonl"), 2)), [])
    def test_order(self): batches = list(stream(self.path, 10)); self.assertEqual(batches[0][0]["event_id"], "e0")
    def test_no_mutation(self):
        before = open(self.path, "rb").read(); list(stream(self.path, 2)); self.assertEqual(open(self.path, "rb").read(), before)
    def test_determinism(self): self.assertEqual(list(stream(self.path, 2)), list(stream(self.path, 2)))
    def test_large_batch(self): self.assertEqual(len(list(stream(self.path, 100))[0]), 5)
    def test_batch_size_one(self): self.assertEqual(len(list(stream(self.path, 1))), 5)
    def test_exact(self): batches = list(stream(self.path, 5)); self.assertEqual(len(batches), 1); self.assertEqual(len(batches[0]), 5)
