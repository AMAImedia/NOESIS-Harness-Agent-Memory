import unittest
from noesis_harness.template import render

class TestTemplate(unittest.TestCase):
    def test_basic(self): self.assertEqual(render("hi {{name}}", {"name":"bob"}), "hi bob")
    def test_missing(self): self.assertEqual(render("{{x}}", {}), "{{x}}")
    def test_spaces(self): self.assertEqual(render("{{ name }}", {"name":"a"}), "a")
    def test_multi(self): self.assertEqual(render("{{a}} {{b}}", {"a":"1","b":"2"}), "1 2")
    def test_empty(self): self.assertEqual(render("", {}), "")
    def test_no_vars(self): self.assertEqual(render("hello", {}), "hello")
    def test_int(self): self.assertEqual(render("{{n}}", {"n":5}), "5")
    def test_determinism(self): self.assertEqual(render("{{a}}", {"a":"1"}), render("{{a}}", {"a":"1"}))
    def test_underscore(self): self.assertEqual(render("{{my_var}}", {"my_var":"x"}), "x")
    def test_many(self): self.assertEqual(render("{{a}}{{a}}", {"a":"x"}), "xx")
