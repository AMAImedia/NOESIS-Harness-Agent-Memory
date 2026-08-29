import unittest
from noesis_harness.buffer_ring import ByteBuffer

class TestByteBuffer(unittest.TestCase):
    def test_write_read(self): b = ByteBuffer(10); b.write(b"hi"); self.assertEqual(b.read(), b"hi")
    def test_overflow(self): b = ByteBuffer(5); b.write(b"hello world"); self.assertEqual(b.read(), b"hello")
    def test_empty(self): b = ByteBuffer(5); self.assertEqual(b.read(), b"")
    def test_available(self): b = ByteBuffer(10); b.write(b"abc"); self.assertEqual(b.available(), 3)
    def test_free(self): b = ByteBuffer(10); b.write(b"abc"); self.assertEqual(b.free(), 7)
    def test_invalid(self):
        with self.assertRaises(ValueError): ByteBuffer(0)
    def test_partial_write(self): b = ByteBuffer(3); n = b.write(b"hello"); self.assertEqual(n, 3)
    def test_peek(self): b = ByteBuffer(5); b.write(b"data"); self.assertEqual(b.peek(), b"data"); self.assertEqual(b.available(), 4)
    def test_read_partial(self): b = ByteBuffer(5); b.write(b"hello"); self.assertEqual(b.read(3), b"hel")
    def test_deterministic(self): b = ByteBuffer(5); b.write(b"x"); self.assertEqual(b.read(), b"x")
    def test_many(self): b = ByteBuffer(10); [b.write(bytes([i])) for i in range(10)]; self.assertEqual(b.available(), 10)
