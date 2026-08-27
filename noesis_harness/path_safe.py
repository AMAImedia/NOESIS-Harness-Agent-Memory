"""Safe path helpers for NOESIS Harness Agent Memory.

Patterns borrowed from LoopX (path containment checks for untrusted join
operations): never build a filesystem path from untrusted segments without
proving the result stays inside a trusted base directory.

This module is pure: it only manipulates path strings/Path objects and never
touches the filesystem, never resolves symlinks, never raises on a missing
file. That keeps it deterministic and side-effect free for use inside the
agent harness core.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Sequence, Union

PathLike = Union[str, "os.PathLike[str]", "Path"]

_ESCAPE_COMPONENT = ".."
_DRIVE_SEP = ":"


def _abs_base(base: PathLike) -> Path:
    """Return an absolute, normalized base directory (pure string op)."""
    return Path(os.path.normpath(os.path.abspath(os.fspath(base))))


def _basename_under(base_abs: Path, candidate_abs: Path) -> bool:
    """True iff candidate_abs is base_abs itself or a strict sub-path of it."""
    if candidate_abs == base_abs:
        return True
    # Ensure a directory prefix match, not a name prefix match.
    try:
        candidate_abs.relative_to(base_abs)
    except ValueError:
        return False
    return True


def is_safe_under(base: PathLike, path: PathLike) -> bool:
    """Return True if `path` resolves (as a string) under `base`.

    Pure and filesystem-free: symlinks are not followed, missing paths are
    handled. The check is done on normalized absolute strings only.
    """
    base_abs = _abs_base(base)
    path_abs = Path(os.path.normpath(os.path.abspath(os.fspath(path))))
    return _basename_under(base_abs, path_abs)


def join_under(base: PathLike, *parts: PathLike) -> Path:
    """Join untrusted `parts` under a trusted `base`.

    Returns an absolute Path guaranteed to be inside `base`.

    Raises:
        ValueError: if any part is absolute (an escape attempt), contains a
            parent-traversal component (".."), or if the joined result would
            resolve outside `base` for any reason.
    """
    base_abs = _abs_base(base)

    for part in parts:
        part_str = os.fspath(part)
        if os.path.isabs(part_str):
            raise ValueError("absolute path rejected: %r" % (part_str,))
        if _DRIVE_SEP in os.path.splitdrive(part_str)[0]:
            # A drive/root spec in a segment is an escape attempt.
            raise ValueError("drive-relative path rejected: %r" % (part_str,))
        head = os.path.normpath(part_str)
        if head == _ESCAPE_COMPONENT or head.startswith(_ESCAPE_COMPONENT + os.sep):
            raise ValueError("traversal rejected: %r" % (part_str,))
        if _ESCAPE_COMPONENT in head.split(os.sep):
            raise ValueError("traversal rejected: %r" % (part_str,))

    joined = Path(os.path.normpath(os.path.join(str(base_abs), *[os.fspath(p) for p in parts])))
    if not _basename_under(base_abs, joined):
        raise ValueError("joined path escapes base: %r" % (str(joined),))
    return joined
