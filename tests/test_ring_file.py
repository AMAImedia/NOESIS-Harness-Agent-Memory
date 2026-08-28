import os, tempfile, unittest
from noesis_harness.ring_file import RingFile

class TestRingFile(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(); self.path = os.path.join(self.tmp, "ring.jsonl")
    def test_append_up_to_capacity(self):
        rf = RingFile(self.path, 3); rf.append("a"); rf.append("b"); rf.append("c")
        self.assertEqual(rf.read_all(), ["a", "b", "c"])
    def test_overflow_drops_oldest(self):
        rf = RingFile(self.path, 2); rf.append("a"); rf.append("b"); rf.append("c")
        self.assertEqual(rf.read_all(), ["b", "c"])
    def test_order(self):
        rf = RingFile(self.path, 5);
        for x in ["x", "y", "z"]: rf.append(x)
        self.assertEqual(rf.read_all(), ["x", "y", "z"])
    def test_empty(self):
        self.assertEqual(RingFile(self.path, 3).read_all(), [])
    def test_capacity_one(self):
        rf = RingFile(self.path, 1); rf.append("a"); rf.append("b"); self.assertEqual(rf.read_all(), ["b"])
    def test_reopen_persistence(self):
        rf = RingFile(self.path, 3); rf.append("a"); rf.append("b")
        rf2 = RingFile(self.path, 3); self.assertEqual(rf2.read_all(), ["a", "b"])
    def test_invalid_capacity(self):
        with self.assertRaises(ValueError): RingFile(self.path, 0)
    def test_determinism(self):
        rf = RingFile(self.path, 3)
        for x in ["1", "2", "3", "4"]: rf.append(x)
        self.assertEqual(rf.read_all(), ["2", "3", "4"])
    def test_many(self):
        rf = RingFile(self.path, 3)
        for i in range(10): rf.append(str(i))
        self.assertEqual(rf.read_all(), ["7", "8", "9"])
    def test_no_corruption(self):
        rf = RingFile(self.path, 2); rf.append("a"); rf.append("b")
        self.assertTrue(os.path.isfile(self.path))
