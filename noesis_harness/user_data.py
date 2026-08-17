"""Cross-platform user-data boundaries for the NOESIS local runtime.

Patterns are borrowed from XDG Base Directory, Windows LocalAppData, and
macOS Application Support conventions, with the NOESIS runtime supervisor's
append-only logs and state kept outside the source tree.
"""

import os
import stat
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional


@dataclass(frozen=True)
class UserDataPaths:
    root: Path
    runtime: Path
    state: Path
    logs: Path
    cache: Path
    config: Path

    def all_paths(self):
        return (self.root, self.runtime, self.state, self.logs, self.cache, self.config)


def _absolute_candidate(value: str, name: str) -> Path:
    candidate = Path(value).expanduser()
    if not candidate.is_absolute():
        raise ValueError("%s must be an absolute path" % name)
    if candidate.exists() and not candidate.is_dir():
        raise ValueError("%s must point to a directory" % name)
    return candidate.resolve()


def _default_root(env: Mapping[str, str], platform: str, home: Path) -> Path:
    explicit = env.get("NOESIS_HOME", "").strip()
    if explicit:
        return _absolute_candidate(explicit, "NOESIS_HOME")
    if platform == "win32":
        base = env.get("LOCALAPPDATA", "").strip()
        return _absolute_candidate(base, "LOCALAPPDATA") / "NOESIS" if base else home / "AppData" / "Local" / "NOESIS"
    if platform == "darwin":
        return home / "Library" / "Application Support" / "NOESIS"
    base = env.get("XDG_DATA_HOME", "").strip()
    return _absolute_candidate(base, "XDG_DATA_HOME") / "NOESIS" if base else home / ".local" / "share" / "NOESIS"


def user_data_paths(*, env: Optional[Mapping[str, str]] = None, platform: Optional[str] = None, home: Optional[str] = None, create: bool = False) -> UserDataPaths:
    """Resolve data paths without ever using the repository as a data root."""
    variables = dict(os.environ if env is None else env)
    system = platform or sys.platform
    home_path = Path(home).expanduser().resolve() if home else Path.home().resolve()
    if not home_path.is_absolute():
        raise ValueError("home must be absolute")
    root = _default_root(variables, system, home_path)
    if root == Path.cwd().resolve() or Path.cwd().resolve() in root.parents:
        raise ValueError("NOESIS data root must not be inside the source tree")
    paths = UserDataPaths(root=root, runtime=root / "runtime", state=root / "state", logs=root / "logs", cache=root / "cache", config=root / "config")
    if create:
        for path in paths.all_paths():
            path.mkdir(parents=True, exist_ok=True)
            if os.name != "nt":
                path.chmod(stat.S_IRWXU)
    return paths


__all__ = ["UserDataPaths", "user_data_paths"]
