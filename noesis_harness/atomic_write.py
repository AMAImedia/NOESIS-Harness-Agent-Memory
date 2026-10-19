"""Atomic temp+rename file writer.

Borrowed patterns from:
  - deja-vu (Go), internal/atomicfile/atomicfile.go: write new content to a
    uniquely named temporary file next to the destination, fsync it, then
    atomically rename it over the target with a bounded retry loop on
    permission/OS errors. The destination is never truncated in place, so a
    reader always sees either the previous complete file or the new complete
    file, and a crashed writer leaves at most a stray ``*.tmp-*`` sibling
    (cleaned by ``prune_temp_files``).

This module is stdlib-only and deterministic. The only side effects are the
requested file writes, the optional append, and the explicitly requested
temporary-file pruning. ``prune_temp_files`` is the sole deletion helper and it
removes only files matching this module's own ``*.tmp-*`` pattern; it never
touches any other file.
"""

from __future__ import annotations

import fnmatch
import os
import time
import uuid
from typing import List, Optional

__all__ = [
    "AtomicWriteError",
    "unique_temp_name",
    "atomic_write_bytes",
    "atomic_write_text",
    "atomic_append_line",
    "read_text",
    "prune_temp_files",
]

_TEMP_MARKER = ".tmp-"
_RETRY_DELAY_SECONDS = 0.01


class AtomicWriteError(RuntimeError):
    """Raised when an atomic write cannot complete and has been rolled back."""


def unique_temp_name(path: str) -> str:
    """Return a unique sibling temporary path for ``path``.

    The name has the deterministic shape ``"<name>.tmp-<pid>-<uuid4 hex 8>"``
    and always lives in the same directory as ``path`` (never another
    directory). Only the random suffix varies between calls.
    """
    directory = os.path.dirname(path)
    base = os.path.basename(path)
    suffix = uuid.uuid4().hex[:8]
    temp_name = "%s%s%d-%s" % (base, _TEMP_MARKER, os.getpid(), suffix)
    if directory:
        return os.path.join(directory, temp_name)
    return temp_name


def _replace_with_retry(src: str, dst: str, retries: int) -> None:
    """os.replace(src, dst) with a bounded retry on PermissionError/OSError."""
    attempts = max(0, int(retries)) + 1
    last_error = None
    for attempt in range(attempts):
        try:
            os.replace(src, dst)
            return
        except OSError as exc:
            last_error = exc
            if attempt < attempts - 1:
                time.sleep(_RETRY_DELAY_SECONDS * (attempt + 1))
    raise AtomicWriteError(
        "atomic replace failed for %r after %d attempt(s): %s"
        % (dst, attempts, last_error)
    )


def _remove_quietly(path: str) -> None:
    """Best-effort removal of a temp artifact; never raises."""
    try:
        os.remove(path)
    except OSError:
        pass


def atomic_write_bytes(path: str, data: bytes, *, retries: int = 5) -> str:
    """Atomically write ``data`` to ``path`` and return ``path``.

    Parent directories are created as needed. Bytes are written to a unique
    sibling temp file, flushed and fsynced, then renamed over ``path`` with a
    bounded retry loop. An existing valid target is never truncated before the
    rename succeeds. On final failure the temp file is removed and
    ``AtomicWriteError`` is raised.
    """
    if not isinstance(data, bytes):
        raise TypeError("data must be bytes")

    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)

    temp_path = unique_temp_name(path)
    try:
        handle = open(temp_path, "wb")
        try:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        finally:
            handle.close()
    except OSError as exc:
        _remove_quietly(temp_path)
        raise AtomicWriteError(
            "failed writing temp file %r: %s" % (temp_path, exc)
        )

    try:
        _replace_with_retry(temp_path, path, retries)
    except AtomicWriteError:
        _remove_quietly(temp_path)
        raise
    return path


def atomic_write_text(
    path: str, text: str, encoding: str = "utf-8", *, retries: int = 5
) -> str:
    """Atomically write ``text`` to ``path`` and return ``path``."""
    if not isinstance(text, str):
        raise TypeError("text must be str")
    return atomic_write_bytes(path, text.encode(encoding), retries=retries)


def atomic_append_line(path: str, line: str, encoding: str = "utf-8") -> None:
    """Append a single newline-terminated line using one write call.

    This is an append-only operation and is deliberately NOT an atomic replace:
    it preserves existing content and only adds ``line`` (a trailing newline is
    added if absent). Parent directories are created when missing.
    """
    if not isinstance(line, str):
        raise TypeError("line must be str")
    payload = line if line.endswith("\n") else line + "\n"
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "a", encoding=encoding) as handle:
        handle.write(payload)


def read_text(path: str, encoding: str = "utf-8") -> Optional[str]:
    """Return the decoded contents of ``path``, or None when it is missing."""
    try:
        with open(path, "r", encoding=encoding) as handle:
            return handle.read()
    except FileNotFoundError:
        return None


def prune_temp_files(directory: str, keep: int = 0) -> List[str]:
    """Remove this module's temp files (``*.tmp-*``) from ``directory``.

    Only regular files whose names match the ``*.tmp-*`` pattern produced by
    ``unique_temp_name`` are considered; no other file is ever listed or
    removed. The ``keep`` newest matching files (by modification time, name as
    tie-breaker) are retained and the rest are deleted. Returns the sorted
    basenames of the removed files.
    """
    if not os.path.isdir(directory):
        return []

    matches = []
    for name in os.listdir(directory):
        if not fnmatch.fnmatch(name, "*" + _TEMP_MARKER + "*"):
            continue
        full = os.path.join(directory, name)
        if not os.path.isfile(full):
            continue
        try:
            mtime = os.path.getmtime(full)
        except OSError:
            mtime = 0.0
        matches.append((mtime, name))

    matches.sort(key=lambda item: (item[0], item[1]))
    to_remove = matches[: max(0, len(matches) - max(0, int(keep)))]

    removed = []
    for _mtime, name in to_remove:
        try:
            os.remove(os.path.join(directory, name))
        except OSError:
            continue
        removed.append(name)
    return sorted(removed)
