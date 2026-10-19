"""noesis_harness/sync_watermark.py

Peer-scoped, append-only sync with acknowledged delivery and a dedupe ledger.

Provenance (ported patterns):
  - deja-vu ``internal/index/sync.go`` (``exportRecordsWith`` / ``ExportBoundary``
    / ``Import``): a peer stores a per-(peer, source) watermark; export returns
    records strictly after the watermark plus same-timestamp ties that have not
    already been acknowledged. The watermark advances ONLY after the receiver
    acknowledges the batch, so a crashed transfer re-sends rather than loses.
  - deja-vu ``internal/peers/peers.go``: watermarks are keyed per peer and per
    source feed, since two feeds for the same peer advance independently.
  - deja-vu ``cmd/deja/sync_ssh.go``: imported records are namespaced (given an
    ``imported-`` prefixed id) so remote ids can never collide with local ids,
    and duplicates are dropped by record identity rather than by payload.
  - LoopX-style deterministic content fingerprints: record identity is a pure
    function of (harness, session_id, time), so re-imports are idempotent.

Design guarantees:
  - Standard library only (``hashlib``, ``json``, ``os``, ``tempfile``).
  - Python 3.9 compatible syntax (``from __future__ import annotations``).
  - Deterministic: identical inputs produce identical identities, boundaries,
    ledger keys, and persisted JSON.
  - Append-only / never destructive: imports only add ledger keys; watermarks
    only move forward (smaller or equal cursors are ignored).
  - Fail-safe persistence: ``save`` is atomic (temp file plus ``os.replace``);
    ``load`` tolerates a missing or corrupt file and yields an empty store.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

__all__ = [
    "record_identity",
    "imported_id",
    "watermark_key",
    "PeerWatermarks",
    "DedupeLedger",
    "ExportBatch",
    "export_since",
    "SyncExchange",
]

_UNKNOWN = "unknown"
_IMPORTED_PREFIX = "imported-"


def _field(record: Dict[str, Any], key: str) -> str:
    """Return a stable string for ``record[key]``; missing/None -> ``unknown``."""
    if not isinstance(record, dict):
        return _UNKNOWN
    value = record.get(key)
    if value is None:
        return _UNKNOWN
    if isinstance(value, str):
        return value
    return str(value)


def record_identity(record: Dict[str, Any]) -> str:
    """Return the deterministic identity of a sync record.

    The identity is ``"<harness>:<session_id>:<time>"``. Any of the three
    fields that is missing or ``None`` contributes the literal ``"unknown"``,
    so a malformed record still has a stable, reproducible identity.
    """
    return "%s:%s:%s" % (
        _field(record, "harness"),
        _field(record, "session_id"),
        _field(record, "time"),
    )


def imported_id(identity: str) -> str:
    """Return the namespaced id an imported record is stored under.

    The id is ``"imported-" + sha256(identity)[:12]``. Deterministic and
    collision-resistant, and prefixed so remote ids can never overwrite a local
    id in a shared ledger.
    """
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:12]
    return _IMPORTED_PREFIX + digest


def watermark_key(peer: str, source: str) -> str:
    """Return the composite store key for a (peer, source) watermark.

    A NUL separator is used so peer/source strings containing ``:`` or ``/``
    cannot alias one another.
    """
    return peer + "\x00" + source


def _record_time(record: Dict[str, Any]) -> str:
    """Return the lexicographically comparable ``time`` of a record.

    ``time`` is expected to be an ISO-like string. A missing or ``None`` value
    compares as the empty string (i.e. before every real timestamp).
    """
    if not isinstance(record, dict):
        return ""
    value = record.get("time")
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


def _batch_cursor(records: List[Dict[str, Any]], watermark: Optional[str]) -> str:
    """Return the high-water cursor for a batch of selected records."""
    if records:
        return max(_record_time(record) for record in records)
    return watermark or ""


def _boundary_at(records: List[Dict[str, Any]], cut: str, limit: int) -> List[str]:
    """Return the sorted, unique, capped identities of records at ``cut``."""
    identities = []
    seen = set()
    for record in records:
        if _record_time(record) != cut:
            continue
        identity = record_identity(record)
        if identity in seen:
            continue
        seen.add(identity)
        identities.append(identity)
    identities.sort()
    if isinstance(limit, int) and limit >= 0:
        identities = identities[:limit]
    return identities


def export_since(
    records: List[Dict[str, Any]],
    watermark: Optional[str],
    *,
    boundary_limit: int = 64,
    boundary: Optional[Iterable[str]] = None,
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Select the records a peer has not acknowledged yet.

    Records with ``time`` strictly greater than ``watermark`` are always
    selected. Records whose ``time`` equals ``watermark`` are selected only when
    their identity is not present in ``boundary``; this closes the
    same-timestamp tie gap where a boundary timestamp spans several records.

    A ``watermark`` of ``None`` means "nothing acknowledged yet" and selects
    every record.

    Returns:
        ``(records, boundary_identities_at_cut)`` where the returned boundary is
        the sorted, unique set of identities sharing the new cursor timestamp
        (the cut). The caller persists it and passes it back on the next call so
        already-sent ties are not echoed.
    """
    excluded = set(boundary or [])
    selected = []
    for record in records:
        record_time = _record_time(record)
        if watermark is None or record_time > watermark:
            selected.append(record)
        elif record_time == watermark:
            if record_identity(record) not in excluded:
                selected.append(record)
    cursor = _batch_cursor(selected, watermark)
    new_boundary = _boundary_at(records, cursor, boundary_limit)
    return selected, new_boundary


def _atomic_write_text(path: str, text: str) -> None:
    """Write ``text`` to ``path`` atomically via a temp file plus os.replace."""
    directory = os.path.dirname(os.path.abspath(path)) or "."
    if not os.path.isdir(directory):
        os.makedirs(directory, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=".tmp-", suffix=".part")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def _read_text(path: str) -> Optional[str]:
    """Return the text at ``path`` or ``None`` when it is missing/unreadable."""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return handle.read()
    except (IOError, OSError):
        return None


class PeerWatermarks:
    """A durable, forward-only store of per-(peer, source) sync cursors.

    Watermarks are keyed by :func:`watermark_key`. ``advance`` ignores any
    cursor that is smaller than or equal to the stored value, so an out-of-order
    or replayed acknowledgement can never move a watermark backwards. The store
    persists as a tolerant JSON object and writes atomically.
    """

    def __init__(self, path: str) -> None:
        self.path = path
        self._data: Dict[str, str] = {}
        self.load()

    def get(self, peer: str, source: str) -> Optional[str]:
        """Return the stored cursor for ``(peer, source)`` or ``None``."""
        return self._data.get(watermark_key(peer, source))

    def advance(self, peer: str, source: str, cursor: str) -> None:
        """Move the watermark forward, ignoring smaller or equal cursors.

        Returns ``None``. A ``None`` cursor is ignored. The change is persisted
        immediately when it takes effect.
        """
        if cursor is None:
            return
        key = watermark_key(peer, source)
        current = self._data.get(key)
        if current is not None and cursor <= current:
            return
        self._data[key] = cursor
        self.save()

    def all(self) -> Dict[str, str]:
        """Return a shallow copy of the composite-key to cursor mapping."""
        return dict(self._data)

    def save(self) -> None:
        """Persist the store atomically as sorted, deterministic JSON."""
        text = json.dumps(self._data, sort_keys=True, ensure_ascii=False, indent=2)
        _atomic_write_text(self.path, text)

    def load(self) -> None:
        """Load the store, tolerating a missing or corrupt file.

        A malformed payload resets the in-memory view to empty rather than
        raising, so an interrupted write can never wedge a sync job.
        """
        text = _read_text(self.path)
        if text is None:
            self._data = {}
            return
        try:
            parsed = json.loads(text)
        except (ValueError, TypeError):
            self._data = {}
            return
        if not isinstance(parsed, dict):
            self._data = {}
            return
        clean: Dict[str, str] = {}
        for key, value in parsed.items():
            if isinstance(key, str) and isinstance(value, str):
                clean[key] = value
        self._data = clean


class DedupeLedger:
    """An in-memory ledger of record keys already imported.

    ``add`` is the only mutating operation and reports whether the key was new.
    Keys are returned sorted so snapshots are deterministic.
    """

    def __init__(self) -> None:
        self._keys = set()

    def seen(self, key: str) -> bool:
        """Return ``True`` when ``key`` is already present."""
        return key in self._keys

    def add(self, key: str) -> bool:
        """Add ``key``; return ``True`` when newly added, ``False`` if present."""
        if key in self._keys:
            return False
        self._keys.add(key)
        return True

    def keys(self) -> List[str]:
        """Return all ledger keys in sorted order."""
        return sorted(self._keys)

    def merge(self, keys: Iterable[str]) -> int:
        """Add many keys; return the number that were newly added."""
        added = 0
        for key in keys:
            if self.add(key):
                added += 1
        return added


@dataclass(frozen=True)
class ExportBatch:
    """A frozen, ack-gated unit of sync transport.

    ``records`` are the selected records, ``cursor`` is the high-water cursor
    the sender will commit once the receiver acknowledges, and ``boundary`` is
    the set of identities sharing the cursor timestamp already delivered.
    """

    peer: str
    source: str
    cursor: str
    records: List[Dict[str, Any]]
    boundary: List[str]


class SyncExchange:
    """Coordinates export and import for one node.

    The sender side never advances a watermark in ``begin_export``; it only
    advances in ``commit``, which the caller invokes after the receiver
    acknowledges. The receiver side dedupes imports by record identity and
    namespaces every imported id.
    """

    def __init__(self, watermarks: PeerWatermarks, ledger: DedupeLedger) -> None:
        self._watermarks = watermarks
        self._ledger = ledger
        self._boundaries: Dict[str, List[str]] = {}

    def begin_export(
        self, peer: str, source: str, records: List[Dict[str, Any]]
    ) -> ExportBatch:
        """Build an export batch without advancing the watermark.

        Previously delivered same-timestamp ties are excluded using the stored
        boundary for ``(peer, source)``; the returned batch carries the new
        boundary to persist on commit.
        """
        key = watermark_key(peer, source)
        watermark = self._watermarks.get(peer, source)
        boundary = self._boundaries.get(key, [])
        selected, new_boundary = export_since(
            records, watermark, boundary=boundary
        )
        cursor = _batch_cursor(selected, watermark)
        return ExportBatch(
            peer=peer,
            source=source,
            cursor=cursor,
            records=selected,
            boundary=new_boundary,
        )

    def commit(self, batch: ExportBatch) -> None:
        """Acknowledge a batch and advance the watermark to its cursor.

        Called only after the receiver confirms delivery. The batch boundary is
        remembered so a re-export of the same ties yields no echo.
        """
        key = watermark_key(batch.peer, batch.source)
        self._boundaries[key] = list(batch.boundary)
        self._watermarks.advance(batch.peer, batch.source, batch.cursor)

    def import_batch(self, batch: ExportBatch) -> Dict[str, Any]:
        """Import a batch, deduping by identity and namespacing imported ids.

        Returns ``{"accepted", "skipped", "cursor"}``. Every accepted record is
        stored under :func:`imported_id`; the boundary identities are also
        recorded so retransmitted ties are recognized. The sender watermark is
        advanced only here, via :meth:`commit`, since import is the
        acknowledgement.
        """
        accepted = 0
        skipped = 0
        for record in batch.records:
            identity = record_identity(record)
            if self._ledger.add(imported_id(identity)):
                accepted += 1
            else:
                skipped += 1
        for identity in batch.boundary:
            self._ledger.add(imported_id(identity))
        self.commit(batch)
        return {"accepted": accepted, "skipped": skipped, "cursor": batch.cursor}

    def import_batches(self, batches: Iterable[ExportBatch]) -> Dict[str, Any]:
        """Import several batches and aggregate the counts."""
        accepted = 0
        skipped = 0
        cursor = ""
        for batch in batches:
            result = self.import_batch(batch)
            accepted += int(result["accepted"])
            skipped += int(result["skipped"])
            cursor = result["cursor"]
        return {"accepted": accepted, "skipped": skipped, "cursor": cursor}
