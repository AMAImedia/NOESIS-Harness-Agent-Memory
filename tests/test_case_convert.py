import unittest
from noesis_harness.case_convert import to_snake, to_camel, to_kebab

class TestCase(unittest.TestCase):
    def test_snake(self): self.assertEqual(to_snake("CamelCase"), "camel_case")
    def test_camel(self): self.assertEqual(to_camel("snake_case"), "snakeCase")
    def test_kebab(self): self.assertEqual(to_kebab("SnakeCase"), "snake-case")
    def test_already(self): self.assertEqual(to_snake("snake_case"), "snake_case")
    def test_spaces(self): self.assertEqual(to_snake("hello world"), "hello_world")
    def test_dash(self): self.assertEqual(to_camel("kebab-case"), "kebabCase")
    def test_empty(self): self.assertEqual(to_snake(""), "")
    def test_single(self): self.assertEqual(to_camel("hello"), "hello")
    def test_determinism(self): self.assertEqual(to_snake("FooBar"), to_snake("FooBar"))
    def test_roundtrip(self): self.assertEqual(to_snake(to_camel("hello_world")), "hello_world")
