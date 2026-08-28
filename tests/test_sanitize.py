"""Tests for noesis_harness.sanitize."""

import unittest

from noesis_harness.sanitize import sanitize


class TestSanitize(unittest.TestCase):

    def test_strips_control_chars(self):
        self.assertEqual(sanitize("a\tb\nc\r"), "abc")

    def test_strips_low_control_codepoints(self):
        self.assertEqual(sanitize("x\x00\x01\x02y"), "xy")

    def test_strips_del_codepoint(self):
        self.assertEqual(sanitize("a\x7fb"), "ab")

    def test_caps_length(self):
        out = sanitize("x" * 2000, max_len=10)
        self.assertEqual(len(out), 13)
        self.assertTrue(out.endswith("..."))

    def test_handles_dict(self):
        out = sanitize({"password": "secret"})
        self.assertIn("password", out)
        self.assertIn("secret", out)
        self.assertNotIn("\n", out)
        self.assertNotIn("\t", out)

    def test_handles_list(self):
        out = sanitize([1, 2, "a\nb"])
        self.assertIn("a", out)
        self.assertNotIn("\n", out)

    def test_handles_none(self):
        self.assertEqual(sanitize(None), "")

    def test_idempotent_on_str(self):
        s = "hello world"
        self.assertEqual(sanitize(s), s)
        self.assertEqual(sanitize(sanitize(s)), s)

    def test_unicode_safe(self):
        s = "héllo 日本語 🌟"
        self.assertEqual(sanitize(s), s)

    def test_no_repr_leak_of_objects(self):
        class Secret:
            def __init__(self):
                self.token = "super-secret-token"

        out = sanitize(Secret())
        self.assertNotIn("super-secret-token", out)
        self.assertNotIn("Secret", out)

    def test_bytes_decoded(self):
        out = sanitize(b"abc\ndef")
        self.assertNotIn("\n", out)
        self.assertIn("abcdef", out)

    def test_max_len_none_uncapped(self):
        out = sanitize("x" * 5000, max_len=None)
        self.assertEqual(len(out), 5000)

    def test_negative_max_len_uncapped(self):
        out = sanitize("x" * 5000, max_len=-1)
        self.assertEqual(len(out), 5000)


if __name__ == "__main__":
    unittest.main()
