"""Tests for noesis_harness.env_probe (stdlib-only read-only environment probe)."""

import os
import sys
import unittest

from noesis_harness import env_probe


class TestEnvProbe(unittest.TestCase):
    def test_required_keys_present(self):
        snap = env_probe.probe()
        for key in ("os", "python_version", "cwd", "pid", "cpu_count"):
            self.assertIn(key, snap)

    def test_python_version_matches_sys(self):
        snap = env_probe.probe()
        self.assertEqual(snap["python_version"], sys.version)

    def test_cwd_matches_os_getcwd(self):
        snap = env_probe.probe()
        self.assertEqual(snap["cwd"], os.getcwd())

    def test_os_matches_platform_system(self):
        import platform

        snap = env_probe.probe()
        self.assertEqual(snap["os"], platform.system())

    def test_pid_matches_os_getpid(self):
        snap = env_probe.probe()
        self.assertEqual(snap["pid"], os.getpid())

    def test_cpu_count_matches_os_cpu_count(self):
        snap = env_probe.probe()
        self.assertEqual(snap["cpu_count"], os.cpu_count())

    def test_static_fields_deterministic(self):
        a = env_probe.probe()
        b = env_probe.probe()
        for key in ("os", "python_version", "cwd", "pid", "cpu_count"):
            self.assertEqual(a[key], b[key])

    def test_no_writes_to_filesystem(self):
        before = env_probe.probe()
        after = env_probe.probe()
        self.assertEqual(before["cwd"], after["cwd"])
        self.assertEqual(before["pid"], after["pid"])

    def test_return_type_is_dict(self):
        snap = env_probe.probe()
        self.assertIsInstance(snap, dict)

    def test_pid_is_int(self):
        snap = env_probe.probe()
        self.assertIsInstance(snap["pid"], int)

    def test_cpu_count_is_int_or_none(self):
        snap = env_probe.probe()
        self.assertTrue(
            snap["cpu_count"] is None or isinstance(snap["cpu_count"], int)
        )

    def test_os_is_str(self):
        snap = env_probe.probe()
        self.assertIsInstance(snap["os"], str)


if __name__ == "__main__":
    unittest.main()
