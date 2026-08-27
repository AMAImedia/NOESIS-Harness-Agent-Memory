"""noesis_harness/seal_log.py

Stdlib-only append-only seal / checkpoint records with a tamper-evident chain.

Borrowed patterns:
  - deepseek-harness: an append-only log where each record carries the digest of
    the previous record (prev_digest). Mutating any stored payload invalidates
    every subsequent self_digest, so the log is verifiable end to end without
    external signing infrastructure. Used in deepseek-harness to make the
    event/replay log trustworthy.
  - LoopX: a deterministic, idempotent append path. The only mutating op is
    seal(), and the canonical digest is a pure function of (prev_digest, label,
    payload). LoopX relies on this for stable replay projections and leases.

This module is part of the deterministic core: it never calls an LLM, never
mutates an already-written record, and seal() is the only mutating operation.
State is always a replay projection of the JSONL file.

Each record stores:
  - entry_id    : stable fingerprint of (label, payload); the idempotency key
  - label       : a short, human-readable category for the seal
  - payload     : arbitrary JSON-serializable content
  - fingerprint : sha256 of the canonical (label, payload)
  - prev_digest : self_digest of the previous record (ZERO_DIGEST if first)
  - self_digest : sha256(prev_digest || canonical(label, payload, fingerprint))
  - ts          : monotonic-ish wall-clock seconds (diagnostic only, not in digest)

A double seal of the same (label, payload) is a no-op: the entry_id collides and
the record is not appended again.
"""

import hashlib
import json
import os
import threading
import time


ZERO_DIGEST = "0" * 64


def _canonical(obj):
    """Return a stable, deterministic UTF-8 encoding of an arbitrary object.

    JSON with sorted keys and no whitespace makes the logical content
    independent of dict ordering or pretty-printing differences.
    """
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _fingerprint(label, payload):
    """Compute the content fingerprint used as the idempotency entry_id."""
    h = hashlib.sha256()
    h.update(_canonical({"label": label, "payload": payload}))
    return h.hexdigest()


def _digest(prev_digest, label, payload, fingerprint):
    """Compute a record's self_digest from its predecessor and content."""
    h = hashlib.sha256()
    h.update(prev_digest.encode("ascii"))
    h.update(b"|")
    h.update(_canonical({"label": label, "payload": payload, "fingerprint": fingerprint}))
    return h.hexdigest()


class SealLog:
    """An append-only, tamper-evident seal log backed by a JSONL file.

    Each seal appends exactly one JSON record. Records form a linked digest
    chain through ``prev_digest`` / ``self_digest`` so that verify() detects any
    modification of a previously written record.
    """

    def __init__(self, path):
        self._path = path
        self._lock = threading.Lock()

    def _load(self):
        """Return all records from the JSONL file (empty list if missing)."""
        if not os.path.exists(self._path):
            return []
        records = []
        with open(self._path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                records.append(json.loads(line))
        return records

    def seal(self, label, payload, entry_id=None):
        """Append a seal record for ``label``/``payload`` and return its entry_id.

        If ``entry_id`` is None it defaults to the content fingerprint, which
        makes re-sealing identical content a no-op. If an entry with the same
        entry_id already exists in the log, nothing is appended and the existing
        entry_id is returned (idempotency on the write path).
        """
        fingerprint = _fingerprint(label, payload)
        if entry_id is None:
            entry_id = fingerprint

        with self._lock:
            records = self._load()
            for rec in records:
                if rec.get("entry_id") == entry_id:
                    return entry_id

            prev_digest = records[-1]["self_digest"] if records else ZERO_DIGEST
            self_digest = _digest(prev_digest, label, payload, fingerprint)
            record = {
                "entry_id": entry_id,
                "label": label,
                "payload": payload,
                "fingerprint": fingerprint,
                "prev_digest": prev_digest,
                "self_digest": self_digest,
                "ts": time.time(),
            }
            with open(self._path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")
            return entry_id

    def head(self):
        """Return the most recent record dict, or None if the log is empty."""
        with self._lock:
            records = self._load()
        return records[-1] if records else None

    def verify(self):
        """Return True if the full chain is intact and untampered.

        A missing file is a clean (empty) chain and verifies as True. Any
        altered payload, prev_digest, fingerprint, or self_digest breaks the
        chain and returns False.
        """
        with self._lock:
            records = self._load()
        expected_prev = ZERO_DIGEST
        for rec in records:
            if rec.get("prev_digest") != expected_prev:
                return False
            recomputed = _digest(
                expected_prev,
                rec.get("label"),
                rec.get("payload"),
                rec.get("fingerprint"),
            )
            if recomputed != rec.get("self_digest"):
                return False
            expected_prev = rec.get("self_digest")
        return True

    def __len__(self):
        with self._lock:
            return len(self._load())
