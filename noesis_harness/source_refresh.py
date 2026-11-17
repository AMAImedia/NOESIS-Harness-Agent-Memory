"""noesis_harness/source_refresh.py

Manifest-as-cache refresh planning for appendable source files.

Pattern ported from the Go repository ``deja-vu``:
  - ``internal/index/manifest.go``: the on-disk manifest records a per-file
    ``FileState`` (size, mtime, safe size, prefix sample) and is used as a
    cache instead of re-reading every file in full.
  - ``internal/index/ingest.go`` (``canAppendIncremental``): an append is only
    taken when the previously indexed byte count is still a valid prefix of
    the new file, which is proved with a cheap prefix sample rather than a
    full-file comparison.
  - ``internal/index/index.go`` (``FileState``): the observed state carries a
    ``safe_size`` boundary so a partially written tail can be excluded.

The prefix sample is what separates a true append from a truncate-and-regrow
that happens to land on the same size: an equal size alone cannot distinguish
them, but a changed prefix can.

The module is pure and deterministic, depends only on the Python standard
library, and never deletes files. One file, one job.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

MANIFEST_VERSION = 1

_UNCHANGED_REASON = "size and prefix match"
_FRESH_REASON = "no prior state"
_APPEND_REASON = "growth with matching prefix"
_NOT_APPENDABLE_REASON = "growth but not appendable"
_PREFIX_CHANGED_REASON = "prefix sample changed (truncate and regrow)"
_SHRINK_REASON = "size shrank"


@dataclass(frozen=True)
class FileState:
    """Observed state of a single source file.

    ``size`` is the full byte length; ``safe_size`` is the length known to be
    fully written (equal to ``size`` for a stat-observed file); ``prefix_sample``
    is the ``sha256:``-prefixed sample of the first bytes.
    """

    path: str
    size: int
    mtime: float
    safe_size: int
    prefix_sample: str


@dataclass(frozen=True)
class RefreshPlan:
    """Decision for one file: how to bring the cache up to date.

    ``mode`` is one of ``"fresh"``, ``"unchanged"``, ``"append"`` or
    ``"rewrite"``. ``offset`` is the byte offset from which the consumer may
    resume processing.
    """

    path: str
    mode: str
    offset: int
    reason: str


def prefix_sample(path: str, n: int = 4096) -> str:
    """Return ``"sha256:" + hexdigest`` over the first ``n`` bytes of ``path``.

    A missing or unreadable file yields the empty string, which is distinct
    from the digest of an existing empty file.
    """
    if n < 0:
        n = 0
    try:
        with open(path, "rb") as handle:
            data = handle.read(n)
    except OSError:
        return ""
    return "sha256:" + hashlib.sha256(data).hexdigest()


def observe(path: str, prefix_bytes: int = 4096) -> FileState:
    """Stat ``path`` and build a :class:`FileState`.

    ``safe_size`` equals the observed ``size``. A missing file yields a zeroed
    state (size 0, mtime 0.0, empty prefix) so planning stays fail-soft.
    """
    try:
        stat = os.stat(path)
    except OSError:
        return FileState(
            path=path,
            size=0,
            mtime=0.0,
            safe_size=0,
            prefix_sample="",
        )
    size = int(stat.st_size)
    return FileState(
        path=path,
        size=size,
        mtime=float(stat.st_mtime),
        safe_size=size,
        prefix_sample=prefix_sample(path, prefix_bytes),
    )


def plan_refresh(
    path: str,
    prior: Optional[FileState],
    observed: FileState,
    appendable: bool,
) -> RefreshPlan:
    """Decide how to refresh ``path`` given prior and observed state.

    Order of checks mirrors the deja-vu ingest path: no prior state is fresh;
    an identical size and prefix is unchanged; growth with a matching prefix
    is an append when the consumer can append, otherwise a rewrite; any prefix
    change is a truncate-and-regrow rewrite; a remaining shrink is a rewrite.
    """
    if prior is None:
        return RefreshPlan(
            path=path,
            mode="fresh",
            offset=0,
            reason=_FRESH_REASON,
        )
    if observed.size == prior.size and observed.prefix_sample == prior.prefix_sample:
        return RefreshPlan(
            path=path,
            mode="unchanged",
            offset=observed.size,
            reason=_UNCHANGED_REASON,
        )
    if observed.size > prior.size and observed.prefix_sample == prior.prefix_sample:
        if appendable:
            return RefreshPlan(
                path=path,
                mode="append",
                offset=prior.size,
                reason=_APPEND_REASON,
            )
        return RefreshPlan(
            path=path,
            mode="rewrite",
            offset=0,
            reason=_NOT_APPENDABLE_REASON,
        )
    if observed.prefix_sample != prior.prefix_sample:
        return RefreshPlan(
            path=path,
            mode="rewrite",
            offset=0,
            reason=_PREFIX_CHANGED_REASON,
        )
    return RefreshPlan(
        path=path,
        mode="rewrite",
        offset=0,
        reason=_SHRINK_REASON,
    )


def _state_to_dict(state: FileState) -> Dict[str, object]:
    """Serializable mapping for a :class:`FileState` with stable field order."""
    return {
        "path": state.path,
        "size": state.size,
        "mtime": state.mtime,
        "safe_size": state.safe_size,
        "prefix_sample": state.prefix_sample,
    }


def _dict_to_state(raw: Dict[str, object]) -> Optional[FileState]:
    """Rebuild a :class:`FileState`, returning ``None`` for malformed records."""
    try:
        return FileState(
            path=str(raw["path"]),
            size=int(raw["size"]),
            mtime=float(raw["mtime"]),
            safe_size=int(raw["safe_size"]),
            prefix_sample=str(raw["prefix_sample"]),
        )
    except (KeyError, TypeError, ValueError):
        return None


def _canonical_states(states: Dict[str, FileState]) -> str:
    """Deterministic JSON for a state map, keyed and ordered by path."""
    payload = {
        str(path): _state_to_dict(states[path]) for path in sorted(states)
    }
    return json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )


class ManifestCache:
    """On-disk manifest of per-file :class:`FileState` records.

    The manifest is a cache: loading is tolerant (a version mismatch, missing
    file or corrupt JSON yields an empty map) so a damaged cache degrades to a
    full refresh rather than an error. Saving is atomic so readers never see a
    partial manifest.
    """

    def __init__(self, path: str) -> None:
        self.path = path
        self._states: Dict[str, FileState] = {}
        self._loaded = False

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self._states = self.load()
            self._loaded = True

    def load(self) -> Dict[str, FileState]:
        """Return the persisted states, or ``{}`` if absent, stale or corrupt."""
        try:
            with open(self.path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, ValueError):
            return {}
        if not isinstance(payload, dict):
            return {}
        if payload.get("version") != MANIFEST_VERSION:
            return {}
        files = payload.get("files")
        if not isinstance(files, dict):
            return {}
        states: Dict[str, FileState] = {}
        for key, raw in files.items():
            if not isinstance(key, str) or not isinstance(raw, dict):
                continue
            state = _dict_to_state(raw)
            if state is not None:
                states[key] = state
        return states

    def save(self, states: Dict[str, FileState]) -> None:
        """Persist ``states`` atomically, stamping the manifest version."""
        payload = {
            "version": MANIFEST_VERSION,
            "files": {
                state.path: _state_to_dict(state) for state in states.values()
            },
        }
        data = json.dumps(
            payload,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        directory = os.path.dirname(os.path.abspath(self.path)) or "."
        os.makedirs(directory, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(
            prefix=".noesis_manifest_", suffix=".tmp", dir=directory
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_path, self.path)
        except BaseException:
            # Never delete files: leave the temp file for forensic inspection.
            raise
        self._states = {state.path: state for state in states.values()}
        self._loaded = True

    def get(self, path: str) -> Optional[FileState]:
        """Return the cached state for ``path``, or ``None``."""
        self._ensure_loaded()
        return self._states.get(path)

    def update(self, state: FileState) -> None:
        """Store ``state`` under its path and persist the manifest."""
        self._ensure_loaded()
        self._states = dict(self._states)
        self._states[state.path] = state
        self.save(self._states)

    def is_valid(self) -> bool:
        """Return True when an on-disk manifest exists with the current version."""
        try:
            with open(self.path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, ValueError):
            return False
        return isinstance(payload, dict) and payload.get("version") == MANIFEST_VERSION

    def digest(self) -> str:
        """Return a stable ``sha256:`` digest over the cached states."""
        self._ensure_loaded()
        canonical = _canonical_states(self._states)
        return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def plan_all(
    cache: ManifestCache,
    paths: Iterable[str],
    appendable: bool = True,
    prefix_bytes: int = 4096,
) -> List[RefreshPlan]:
    """Plan refreshes for ``paths`` in sorted order.

    Each prior state is taken from ``cache`` (``None`` when absent) and the
    observed state from the filesystem. The cache is read, never mutated.
    """
    plans: List[RefreshPlan] = []
    for path in sorted(paths):
        prior = cache.get(path)
        observed = observe(path, prefix_bytes)
        plans.append(plan_refresh(path, prior, observed, appendable))
    return plans


__all__ = [
    "MANIFEST_VERSION",
    "FileState",
    "RefreshPlan",
    "ManifestCache",
    "prefix_sample",
    "observe",
    "plan_refresh",
    "plan_all",
]
