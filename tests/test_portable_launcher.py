import tempfile
import unittest
from pathlib import Path

from noesis_harness.portable_launcher import PortableLaunchError, resolve_layout, startup_probe


class PortableLauncherTests(unittest.TestCase):
    def test_layout_keeps_install_and_data_boundaries(self):
        with tempfile.TemporaryDirectory() as root:
            install = Path(root, "install")
            layout = resolve_layout(str(install), env={})
            self.assertNotEqual(layout.install_root, layout.data_root)
            self.assertEqual(layout.data_root, install / "data")
            self.assertEqual(layout.runtime_root, install / "data" / "runtime")

    def test_explicit_noesis_home_and_windows_style_override(self):
        with tempfile.TemporaryDirectory() as root:
            install = Path(root, "install")
            data = Path(root, "user-data")
            layout = resolve_layout(str(install), env={"NOESIS_HOME": str(data)})
            self.assertEqual(layout.data_root, data.resolve())
            self.assertEqual(resolve_layout(str(install), data_root=str(data)).data_root, data.resolve())

    def test_same_path_is_rejected_and_external_host_is_not_allowed_by_probe(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(PortableLaunchError):
                resolve_layout(root, data_root=root)
            layout = resolve_layout(str(Path(root, "install")))
            with self.assertRaises(ValueError):
                startup_probe(layout, host="0.0.0.0", port=0)

    def test_startup_probe_preserves_data_sentinel(self):
        with tempfile.TemporaryDirectory() as root:
            layout = resolve_layout(str(Path(root, "install")))
            address = startup_probe(layout, port=0)
            self.assertEqual(address[0], "127.0.0.1")
            sentinel = layout.data_root / "state" / "portable-startup.sentinel"
            self.assertTrue(sentinel.is_file())
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "noesis-portable-started\n")


if __name__ == "__main__":
    unittest.main()
