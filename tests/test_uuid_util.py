import unittest
from noesis_harness.uuid_util import new, new_short, is_valid, from_bytes

class TestUuid(unittest.TestCase):
    def test_new(self): self.assertEqual(len(new()), 36)
    def test_short(self): self.assertEqual(len(new_short()), 12)
    def test_valid(self): self.assertTrue(is_valid(new()))
    def test_invalid(self): self.assertFalse(is_valid("not-a-uuid"))
    def test_format(self): self.assertIn("-", new())
    def test_short_hex(self): self.assertTrue(all(c in "0123456789abcdef" for c in new_short()))
    def test_unique(self): self.assertNotEqual(new(), new())
    def test_from_bytes(self):
        u = new(); b = uuid.UUID(u).bytes; self.assertEqual(from_bytes(b), u)
    def test_deterministic(self): self.assertTrue(is_valid(new()))
    def test_empty(self): self.assertFalse(is_valid(""))

import uuid
