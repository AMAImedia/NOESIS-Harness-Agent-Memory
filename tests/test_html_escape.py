import unittest
from noesis_harness.html_escape import escape, unescape

class TestHtml(unittest.TestCase):
    def test_escape(self): self.assertEqual(escape("<a & b>"), "&lt;a &amp; b&gt;")
    def test_unescape(self): self.assertEqual(unescape("&lt;"), "<")
    def test_roundtrip(self): self.assertEqual(unescape(escape('<x "y">')), '<x "y">')
    def test_quote(self): self.assertIn("&quot;", escape('"hi"'))
    def test_empty(self): self.assertEqual(escape(""), "")
    def test_no_escape(self): self.assertEqual(escape("abc"), "abc")
    def test_amp(self): self.assertEqual(escape("a&b"), "a&amp;b")
    def test_determinism(self): self.assertEqual(escape("<"), escape("<"))
    def test_unicode(self): self.assertEqual(unescape(escape("привет")), "привет")
    def test_many(self): self.assertEqual(unescape(escape("<"*10)), "<"*10)
