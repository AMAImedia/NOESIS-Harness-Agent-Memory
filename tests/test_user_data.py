import os
import tempfile
import unittest
from pathlib import Path

from noesis_harness.user_data import user_data_paths
from tests._external_home import external_home_dir


class UserDataPathTests(unittest.TestCase):
    def test_windows_localappdata_default(self):
        with tempfile.TemporaryDirectory(dir=external_home_dir()) as home:
            paths = user_data_paths(env={"LOCALAPPDATA": os.path.join(home, "Local")}, platform="win32", home=home)
            self.assertEqual(paths.root, Path(home).resolve() / "Local" / "NOESIS")
            self.assertEqual(paths.runtime, paths.root / "runtime")

    def test_macos_application_support_default(self):
        with tempfile.TemporaryDirectory(dir=external_home_dir()) as home:
            paths = user_data_paths(env={}, platform="darwin", home=home)
            self.assertEqual(paths.root, Path(home).resolve() / "Library" / "Application Support" / "NOESIS")

    def test_explicit_home_wins_and_create_is_private(self):
        with tempfile.TemporaryDirectory(dir=external_home_dir()) as parent:
            explicit = os.path.join(parent, "noesis-data")
            paths = user_data_paths(env={"NOESIS_HOME": explicit, "LOCALAPPDATA": os.path.join(parent, "ignored")}, platform="win32", home=parent, create=True)
            self.assertEqual(paths.root, Path(explicit).resolve())
            self.assertTrue(all(path.is_dir() for path in paths.all_paths()))
            if os.name != "nt":
                self.assertEqual(paths.root.stat().st_mode & 0o777, 0o700)

    def test_relative_override_is_rejected(self):
        with self.assertRaises(ValueError):
            user_data_paths(env={"NOESIS_HOME": "relative/path"}, platform="darwin", home=tempfile.gettempdir())

    def test_root_inside_current_source_tree_is_rejected(self):
        with tempfile.TemporaryDirectory() as source:
            old = os.getcwd()
            try:
                os.chdir(source)
                with self.assertRaises(ValueError):
                    user_data_paths(env={"NOESIS_HOME": os.path.join(source, "data")}, platform="darwin", home=source)
            finally:
                os.chdir(old)


if __name__ == "__main__":
    unittest.main()
