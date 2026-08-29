import os, tempfile, unittest
from noesis_harness.chunked_jsonl import read_chunks, write_jsonl, count_jsonl

class TestChunkedJsonl(unittest.TestCase):
    def setUp(self): self.tmp = tempfile.mkdtemp(); self.p = os.path.join(self.tmp, "test.jsonl")
    def test_write_read(self):
        write_jsonl(self.p, [{"a": 1}, {"b": 2}])
        chunks = list(read_chunks(self.p)); self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0], [{"a": 1}, {"b": 2}])
    def test_chunk_size(self):
        write_jsonl(self.p, [{"i": i} for i in range(25)])
        chunks = list(read_chunks(self.p, chunk_size=10))
        self.assertEqual(len(chunks), 3); self.assertEqual(len(chunks[0]), 10)
    def test_empty(self):
        write_jsonl(self.p, []); self.assertEqual(list(read_chunks(self.p)), [])
    def test_count(self):
        write_jsonl(self.p, [{"a": 1}, {"b": 2}, {"c": 3}])
        self.assertEqual(count_jsonl(self.p), 3)
    def test_large(self):
        items = [{"i": i} for i in range(100)]
        write_jsonl(self.p, items)
        all_items = [item for chunk in read_chunks(self.p, 50) for item in chunk]
        self.assertEqual(all_items, items)
    def test_unicode(self):
        write_jsonl(self.p, [{"text": "привет"}])
        chunks = list(read_chunks(self.p)); self.assertEqual(chunks[0][0]["text"], "привет")
    def test_deterministic(self):
        write_jsonl(self.p, [{"x": 1}])
        self.assertEqual(list(read_chunks(self.p)), list(read_chunks(self.p)))
    def test_many(self):
        write_jsonl(self.p, [{"k": str(i)} for i in range(50)])
        self.assertEqual(count_jsonl(self.p), 50)
    def test_single(self):
        write_jsonl(self.p, [{"a": 1}]); self.assertEqual(list(read_chunks(self.p, 10)), [[{"a": 1}]])
    def test_sorted_keys(self):
        write_jsonl(self.p, [{"z": 1, "a": 2}])
        with open(self.p) as f: line = f.readline()
        self.assertEqual(line.strip(), '{"a": 2, "z": 1}')
