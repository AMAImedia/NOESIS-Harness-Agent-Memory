"""noesis_harness/version.py

Deterministic, stdlib-only version and agent identity primitives.

Borrowed patterns:
  - LoopX: stable agent identity derived from a content hash (name + version)
    rather than from mutable host/runtime state, so two runs with the same
    inputs produce the same identity. No clock, no randomness, no I/O writes.

This module never writes to disk. It reads a version from pyproject.toml
(read-only) when present and falls back to the in-source VERSION constant so
that the framework has a stable identity even without packaging metadata.
"""

import hashlib
import os

# In-source fallback version. Tuple-friendly "major.minor.patch[.build]".
VERSION = "0.5.0"

# Project root is two levels up from this file: noesis_harness/version.py
# lives inside the package, so <root>/pyproject.toml is the canonical source.
_PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_PACKAGE_DIR)
_PYPROJECT_PATH = os.path.join(_PROJECT_ROOT, "pyproject.toml")


def _parse_pyproject_version(path):
    """Return the version string from pyproject.toml, or None if absent/uneditable.

    Parses only the simple ``name = "0.5.0"`` assignment form used by this
    project's [project] table. Missing file or unreadable content yields None
    without raising, keeping the read path deterministic and side-effect free.
    """
    try:
        with open(path, "r", encoding="utf-8") as handle:
            text = handle.read()
    except (OSError, ValueError):
        return None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("version"):
            parts = stripped.split("=", 1)
            if len(parts) != 2:
                continue
            value = parts[1].strip().strip('"').strip("'")
            if value:
                return value
    return None


def get_version_string():
    """Return the canonical version string, preferring pyproject over VERSION."""
    pyproject_version = _parse_pyproject_version(_PYPROJECT_PATH)
    if pyproject_version:
        return pyproject_version
    return VERSION


def version_tuple():
    """Return the version as a tuple of ints (major, minor, patch[, build...]).

    Non-numeric segments are coerced to 0 so that malformed or pre-release
    suffixes never raise and never break downstream comparisons.
    """
    raw = get_version_string()
    segments = []
    for piece in raw.split("."):
        digits = "".join(ch for ch in piece if ch.isdigit())
        segments.append(int(digits) if digits else 0)
    if not segments:
        segments = [0]
    return tuple(segments)


def agent_identity(name):
    """Return a stable agent id (sha256 hex) from name + version.

    Pure: identical (name, version) always yields the identical 64-char digest.
    No randomness, no timestamp, no network, no filesystem writes.
    """
    version = get_version_string()
    payload = "{}@{}".format(name, version).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
