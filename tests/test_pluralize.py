import unittest
from noesis_harness.pluralize import plural

class TestPlural(unittest.TestCase):
    def test_one(self): self.assertEqual(plural(1,"cat"),"cat")
    def test_many(self): self.assertEqual(plural(2,"cat"),"cats")
    def test_y(self): self.assertEqual(plural(2,"city"),"cities")
    def test_es(self): self.assertEqual(plural(2,"box"),"boxes")
    def test_ch(self): self.assertEqual(plural(2,"church"),"churches")
    def test_custom(self): self.assertEqual(plural(2,"person","people"),"people")
    def test_zero(self): self.assertEqual(plural(0,"cat"),"cats")
    def test_vowel_y(self): self.assertEqual(plural(2,"day"),"days")
    def test_determinism(self): self.assertEqual(plural(2,"cat"),plural(2,"cat"))
    def test_s(self): self.assertEqual(plural(2,"bus"),"buses")
