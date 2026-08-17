import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

from noesis_harness.runtime_supervisor import ChildRuntimeSupervisor


FIXTURE = Path(__file__).resolve().parent / "fixtures" / "supervised_child.py"


class RuntimeSupervisorTests(unittest.TestCase):
    def factory(self, crash_after=0.0):
        def command(host, port):
            return (sys.executable, str(FIXTURE), "--crash-after", str(crash_after))
        return command

    def test_start_readiness_and_clean_stop(self):
        with tempfile.TemporaryDirectory(prefix="noesis-supervisor-") as root:
            supervisor = ChildRuntimeSupervisor(self.factory(), runtime_dir=root, startup_timeout=3.0)
            started = supervisor.start()
            self.assertEqual(started.state, "ready")
            self.assertEqual(started.host, "127.0.0.1")
            self.assertGreater(started.port, 0)
            self.assertIsNotNone(started.pid)
            self.assertTrue(Path(started.log_path).exists())
            stopped = supervisor.stop()
            self.assertEqual(stopped.state, "stopped")
            self.assertEqual(stopped.reason, "clean_stop")
            self.assertIsNone(stopped.pid)

    def test_crash_recovery_is_bounded_and_reuses_no_fixed_port(self):
        with tempfile.TemporaryDirectory(prefix="noesis-supervisor-") as root:
            supervisor = ChildRuntimeSupervisor(self.factory(crash_after=0.35), runtime_dir=root, startup_timeout=3.0, max_restarts=1)
            first = supervisor.start()
            self.assertEqual(first.state, "ready")
            first_port = first.port
            deadline = time.monotonic() + 3.0
            while time.monotonic() < deadline and supervisor.status.state == "ready":
                time.sleep(0.05)
            recovered = supervisor.recover_if_crashed()
            self.assertEqual(recovered.state, "ready")
            self.assertEqual(recovered.restart_count, 1)
            self.assertNotEqual(recovered.port, first_port)
            deadline = time.monotonic() + 3.0
            while time.monotonic() < deadline and supervisor.status.state == "ready":
                time.sleep(0.05)
            exhausted = supervisor.recover_if_crashed()
            self.assertEqual(exhausted.state, "failed")
            self.assertEqual(exhausted.reason, "restart_budget_exhausted")
            supervisor.stop()

    def test_unready_child_fails_closed(self):
        def bad_command(host, port):
            return (sys.executable, "-c", "import time; time.sleep(0.2)")
        with tempfile.TemporaryDirectory(prefix="noesis-supervisor-") as root:
            supervisor = ChildRuntimeSupervisor(bad_command, runtime_dir=root, startup_timeout=0.8, readiness_interval=0.05)
            result = supervisor.start()
            self.assertIn(result.state, {"crashed", "failed"})
            self.assertIsNone(result.pid)
            supervisor.stop()


if __name__ == "__main__":
    unittest.main()
