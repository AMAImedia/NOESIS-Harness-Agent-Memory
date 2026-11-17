import tempfile
import unittest
from pathlib import Path

from noesis_harness.sandbox_bwrap import BubblewrapBackend


class BubblewrapBackendTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tmp.name)
        self.backend = BubblewrapBackend()

    def tearDown(self):
        self.tmp.cleanup()

    def test_backend_is_available_and_command_isolated(self):
        if not self.backend.available:
            self.skipTest("bubblewrap unavailable")
        command = self.backend.command(("/usr/bin/printf", "ok"), self.workspace)
        self.assertIn("--unshare-all", command)
        self.assertIn("--bind", command)
        self.assertNotIn("shell", command)

    def test_argv_execution_and_bounded_result(self):
        if not self.backend.available:
            self.skipTest("bubblewrap unavailable")
        result = self.backend.run(("/usr/bin/printf", "sandbox-ok"), self.workspace)
        self.assertEqual(result.status, "passed")
        self.assertEqual(result.stdout, "sandbox-ok")
        self.assertEqual(result.stderr, "")

    def test_network_and_host_filesystem_are_not_available(self):
        if not self.backend.available:
            self.skipTest("bubblewrap unavailable")
        probe = self.workspace / "probe.py"
        probe.write_text(
            "import pathlib, socket\n"
            "try:\n"
            "    pathlib.Path('/home/ubuntu/noesis-p3/README.md').read_text()\n"
            "    print('host_read=allowed')\n"
            "except Exception:\n"
            "    print('host_read=blocked')\n"
            "try:\n"
            "    socket.create_connection(('1.1.1.1', 80), 0.2)\n"
            "    print('network=allowed')\n"
            "except Exception:\n"
            "    print('network=blocked')\n",
            encoding="utf-8",
        )
        result = self.backend.run(("/usr/bin/python3", "/workspace/probe.py"), self.workspace)
        self.assertEqual(result.status, "passed")
        self.assertIn("host_read=blocked", result.stdout)
        self.assertIn("network=blocked", result.stdout)

    def test_invalid_workspace_fails_closed(self):
        with self.assertRaises(ValueError):
            self.backend.command(("/usr/bin/printf", "x"), self.workspace / "missing")


if __name__ == "__main__":
    unittest.main()
