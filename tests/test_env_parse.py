import os, unittest
from importlib import reload
from noesis_harness import env_parse

class TestEnvParse(unittest.TestCase):
    def setUp(self):
        for k in ("T_INT", "T_BOOL", "T_STR", "T_BAD"): os.environ.pop(k, None)
    def test_int(self): os.environ["T_INT"] = "42"; self.assertEqual(env_parse.get_int("T_INT"), 42)
    def test_int_default(self): self.assertEqual(env_parse.get_int("T_MISSING", 7), 7)
    def test_int_bad(self): os.environ["T_BAD"] = "abc"; self.assertEqual(env_parse.get_int("T_BAD", 3), 3)
    def test_bool_true(self): os.environ["T_BOOL"] = "true"; self.assertTrue(env_parse.get_bool("T_BOOL"))
    def test_bool_false(self): os.environ["T_BOOL"] = "0"; self.assertFalse(env_parse.get_bool("T_BOOL"))
    def test_bool_default(self): self.assertFalse(env_parse.get_bool("T_MISSING"))
    def test_str(self): os.environ["T_STR"] = "hi"; self.assertEqual(env_parse.get_str("T_STR"), "hi")
    def test_str_default(self): self.assertEqual(env_parse.get_str("T_MISSING", "x"), "x")
    def test_empty_int(self): os.environ["T_INT"] = ""; self.assertEqual(env_parse.get_int("T_INT", 5), 5)
    def test_bool_yes(self): os.environ["T_BOOL"] = "YES"; self.assertTrue(env_parse.get_bool("T_BOOL"))
    def test_determinism(self): os.environ["T_INT"] = "9"; self.assertEqual(env_parse.get_int("T_INT"), env_parse.get_int("T_INT"))
