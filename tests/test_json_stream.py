import os, tempfile, unittest
from noesis_harness.json_stream import read_jsonl, write_jsonl, count_jsonl

class TestJsonStream(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.p = os.path.join(self.tmp, "test.jsonl")
    def test_write_read(self):
        write_jsonl(self.p, [{"a": 1}, {"b": 2}])
        self.assertEqual(list(read_jsonl(self.p)), [{"a": 1}, {"b": 2}])
    def test_count(self):
        write_jsonl(self.p, [{"a": 1}, {"b": 2}, {"c": 3}])
        self.assertEqual(count_jsonl(self.p), 3)
    def test_empty(self):
        write_jsonl(self.p, [])
        self.assertEqual(list(read_jsonl(self.p)), [])
    def test_count_empty(self):
        write_jsonl(self.p, [])
        self.assertEqual(count_jsonl(self.p), 0)
    def test_large(self):
        items = [{"i": i} for i in range(100)]
        write_jsonl(self.p, items)
        self.assertEqual(list(read_jsonl(self.p)), items)
    def test_sorted_keys(self):
        write_jsonl(self.p, [{"z": 1, "a": 2}])
        with open(self.p) as f: line = f.readline()
        self.assertEqual(line.strip(), '{"a": 2, "z": 1}')
    def test_deterministic(self):
        write_jsonl(self.p, [{"x": 1}])
        self.assertEqual(list(read_jsonl(self.p)), list(read_jsonl(self.p)))
    def test_many(self):
        items = [{"k": str(i)} for i in range(50)]
        write_jsonl(self.p, items)
        self.assertEqual(count_jsonl(self.p), 50)
    def test_path(self):
        sub = os.path.join(self.tmp, "sub"); os.makedirs(sub); p = os.path.join(sub, "data.jsonl")
        write_jsonl(p, [{"a": 1}])
        self.assertEqual(list(read_jsonl(p)), [{"a": 1}])
    def test_unicode(self):
        write_jsonl(self.p, [{"text": "привет"}])
        self.assertEqual(list(read_jsonl(self.p)), [{"text": "привет"}])
