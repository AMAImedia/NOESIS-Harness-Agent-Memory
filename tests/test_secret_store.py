import unittest
from noesis_harness.secret_store import SecretStore

class TestSecretStore(unittest.TestCase):
    def test_put_get(self): s = SecretStore(); s.put("k", "secret123"); self.assertEqual(s.get("k"), "secret123")
    def test_missing(self): self.assertIsNone(SecretStore().get("nope"))
    def test_redacted(self): s = SecretStore(); s.put("k", "abcdef"); self.assertEqual(s.redacted("k"), "ab***ef")
    def test_short_redacted(self): s = SecretStore(); s.put("k", "ab"); self.assertEqual(s.redacted("k"), "***")
    def test_missing_redacted(self): self.assertEqual(SecretStore().redacted("nope"), "")
    def test_keys(self): s = SecretStore(); s.put("a", "1"); s.put("b", "2"); self.assertEqual(set(s.keys()), {"a", "b"})
    def test_overwrite(self): s = SecretStore(); s.put("k", "a"); s.put("k", "b"); self.assertEqual(s.get("k"), "b")
    def test_no_leak(self): s = SecretStore(); s.put("k", "secret"); r = s.redacted("k"); self.assertNotIn("secret", r)
    def test_determinism(self): s = SecretStore(); s.put("k", "abc"); self.assertEqual(s.redacted("k"), s.redacted("k"))
    def test_empty(self): s = SecretStore(); s.put("k", ""); self.assertEqual(s.redacted("k"), "***")
