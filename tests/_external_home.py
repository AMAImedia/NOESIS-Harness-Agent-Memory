"""Shared test helper: home roots must stay outside the source tree.

When the ambient temp directory lives inside the repository (operator-run
scratch layout), the user-data source-tree guard would reject simulated
homes. Tests therefore anchor such homes to a drive-level directory.
"""
from __future__ import annotations

import tempfile
from pathlib import Path


def external_home_dir(prefix: str = "noesis-home-") -> str:
    temp_root = Path(tempfile.gettempdir()).resolve()
    cwd = Path.cwd().resolve()
    if cwd == temp_root or cwd in temp_root.parents:
        fallback = Path(temp_root.anchor) / "noesis-test-homes"
        fallback.mkdir(parents=True, exist_ok=True)
        return tempfile.mkdtemp(prefix=prefix, dir=str(fallback))
    return tempfile.mkdtemp(prefix=prefix)


__all__ = ["external_home_dir"]
