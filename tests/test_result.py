import unittest
from noesis_harness.result import Ok, Err, ok, err

class TestResult(unittest.TestCase):
    def test_ok(self): r = ok(1); self.assertTrue(r.is_ok()); self.assertEqual(r.unwrap(), 1)
    def test_err(self): r = err("e"); self.assertTrue(r.is_err()); self.assertEqual(r.error, "e")
    def test_ok_is_not_err(self): self.assertFalse(ok(1).is_err())
    def test_err_is_not_ok(self): self.assertFalse(err("e").is_ok())
    def test_err_unwrap_raises(self):
        with self.assertRaises(ValueError): err("e").unwrap()
    def test_ok_value(self): self.assertEqual(Ok(5).value, 5)
    def test_err_error(self): self.assertEqual(Err("x").error, "x")
    def test_determinism(self): self.assertEqual(ok(1).unwrap(), ok(1).unwrap())
    def test_none_ok(self): self.assertTrue(ok(None).is_ok())
    def test_empty_err(self): self.assertTrue(err("").is_err())
