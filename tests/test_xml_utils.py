import unittest
from noesis_harness.xml_utils import from_string, to_string, find_text, find_all, make_element

class TestXml(unittest.TestCase):
    def test_parse(self): e = from_string("<root><a>hello</a></root>"); self.assertEqual(e.tag, "root")
    def test_text(self): e = from_string("<root>hi</root>"); self.assertEqual(e.text, "hi")
    def test_to_string(self): s = to_string(from_string("<x/>")); self.assertIn("<x", s)
    def test_find_text(self): e = from_string("<root><a>val</a></root>"); self.assertEqual(find_text(e, "a"), "val")
    def test_find_missing(self): e = from_string("<root/>"); self.assertEqual(find_text(e, "x", "d"), "d")
    def test_find_all(self): e = from_string("<root><i>1</i><i>2</i></root>"); self.assertEqual(len(find_all(e, "i")), 2)
    def test_make(self): e = make_element("tag", "text"); self.assertEqual(e.tag, "tag"); self.assertEqual(e.text, "text")
    def test_make_no_text(self): e = make_element("x"); self.assertIsNone(e.text)
    def test_determinism(self): self.assertEqual(to_string(from_string("<a/>")), to_string(from_string("<a/>")))
    def test_children(self): e = from_string("<r><a/><b/><c/></r>"); self.assertEqual(len(list(e)), 3)
