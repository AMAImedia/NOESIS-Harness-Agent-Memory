import tempfile
import unittest
from pathlib import Path

from noesis_harness.portable_launcher import resolve_layout, startup_probe
from noesis_harness.user_data import user_data_paths
from tests._external_home import external_home_dir


class MacOSPortableTests(unittest.TestCase):
    def test_macos_application_support_default(self):
        with tempfile.TemporaryDirectory(dir=external_home_dir()) as root:
            home = Path(root, "home")
            install = Path(root, "app", "NOESIS.app", "Contents", "Resources")
            layout = resolve_layout(str(install), platform="darwin", home=str(home), env={})
            expected = home / "Library" / "Application Support" / "NOESIS"
            self.assertEqual(layout.data_root, expected.resolve())
            paths = user_data_paths(platform="darwin", home=str(home), env={})
            self.assertEqual(paths.root, expected.resolve())

    def test_macos_explicit_noesis_home_overrides_application_support(self):
        with tempfile.TemporaryDirectory(dir=external_home_dir()) as root:
            home = Path(root, "home")
            override = Path(root, "portable-data")
            layout = resolve_layout(str(Path(root, "install")), platform="darwin", home=str(home), env={"NOESIS_HOME": str(override)})
            self.assertEqual(layout.data_root, override.resolve())

    def test_macos_startup_probe_loopback_and_data_preservation(self):
        with tempfile.TemporaryDirectory(dir=external_home_dir()) as root:
            layout = resolve_layout(str(Path(root, "install")), platform="darwin", home=str(Path(root, "home")), env={})
            address = startup_probe(layout, host="127.0.0.1", port=0)
            self.assertEqual(address[0], "127.0.0.1")
            sentinel = layout.data_root / "state" / "portable-startup.sentinel"
            self.assertTrue(sentinel.is_file())
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "noesis-portable-started\n")

    def test_macos_user_data_is_not_install_tree(self):
        with tempfile.TemporaryDirectory(dir=external_home_dir()) as root:
            install = Path(root, "app", "NOESIS.app")
            layout = resolve_layout(str(install), platform="darwin", home=str(Path(root, "home")), env={})
            self.assertNotIn(install.resolve(), layout.data_root.parents)
            self.assertNotEqual(layout.install_root, layout.data_root)


if __name__ == "__main__":
    unittest.main()
