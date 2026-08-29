import unittest
from noesis_harness.envsubst import subst

class TestEnvSubst(unittest.TestCase):
    def test_brace(self): self.assertEqual(subst("hi ${name}", {"name":"bob"}), "hi bob")
    def test_plain(self): self.assertEqual(subst("hi $name", {"name":"bob"}), "hi bob")
    def test_missing(self): self.assertEqual(subst("${x}", {}), "${x}")
    def test_multi(self): self.assertEqual(subst("$a $b", {"a":"1","b":"2"}), "1 2")
    def test_empty(self): self.assertEqual(subst("", {}), "")
    def test_no_var(self): self.assertEqual(subst("hello", {}), "hello")
    def test_mixed(self): self.assertEqual(subst("${a}/$b", {"a":"x","b":"y"}), "x/y")
    def test_determinism(self): self.assertEqual(subst("$a", {"a":"1"}), subst("$a", {"a":"1"}))
    def test_underscore(self): self.assertEqual(subst("${my_var}", {"my_var":"x"}), "x")
    def test_int(self): self.assertEqual(subst("${n}", {"n":5}), "5")
