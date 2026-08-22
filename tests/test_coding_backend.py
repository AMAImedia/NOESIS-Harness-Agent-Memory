import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from noesis_harness.coding_backend import BoundedCodingBackend, CodingBackendError


class CodingBackendTests(unittest.TestCase):
    def test_requires_explicit_argv_and_existing_worktree(self):
        with TemporaryDirectory() as root:
            with self.assertRaisesRegex(CodingBackendError, "explicit_argv_required"):
                BoundedCodingBackend([], Path(root))
            with self.assertRaisesRegex(CodingBackendError, "worktree_missing"):
                BoundedCodingBackend([sys.executable, "-c", "pass"], Path(root) / "missing")

    def test_success_and_output_bound(self):
        with TemporaryDirectory() as root:
            result = BoundedCodingBackend([sys.executable, "-c", "print('x' * 100)"], Path(root), output_limit=16).run()
            self.assertEqual(result.status, "passed")
            self.assertEqual(result.returncode, 0)
            self.assertLessEqual(len(result.stdout), 16)
            self.assertEqual(result.reason, "process_completed")

    def test_timeout_is_fail_closed(self):
        with TemporaryDirectory() as root:
            result = BoundedCodingBackend([sys.executable, "-c", "import time; time.sleep(30)"], Path(root), timeout_seconds=0.05).run()
            self.assertEqual(result.status, "timeout")
            self.assertIsNone(result.returncode)
            self.assertEqual(result.reason, "process_timeout")


if __name__ == "__main__":
    unittest.main()
