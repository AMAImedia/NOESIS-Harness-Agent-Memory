"""Append-only attestation records for the NOESIS harness.

Patterns borrowed from:
- deepseek-harness: deterministic event fingerprints and append-only logs.
- LoopX: idempotent write paths keyed by content/entry fingerprints.

An attestation record binds a subject to a claim and an evidence hash. Once
written, records are never mutated; state is derived by replaying the log. A
double-send with the same entry_id is a no-op. Tampering with any record is
detectable on replay because each record carries a fingerprint of its own
canonical content.
"""

import hashlib
import json
import os
import time
import uuid


def _canonical(record):
    """Return the canonical JSON string used for fingerprinting a record."""
    return json.dumps(
        {
            "entry_id": record["entry_id"],
            "subject": record["subject"],
            "claim": record["claim"],
            "evidence_hash": record["evidence_hash"],
            "timestamp": record["timestamp"],
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def _fingerprint(record):
    """Compute the SHA-256 fingerprint of a record's canonical form."""
    return hashlib.sha256(_canonical(record).encode("utf-8")).hexdigest()


class AttestationLog:
    """Append-only store of attestation records backed by a JSONL file."""

    def __init__(self, path):
        self.path = path
        if not os.path.exists(self.path):
            self._ensure_parent_dir()

    def _ensure_parent_dir(self):
        parent = os.path.dirname(os.path.abspath(self.path))
        if parent and not os.path.isdir(parent):
            os.makedirs(parent, exist_ok=True)

    def _read_all(self):
        if not os.path.exists(self.path):
            return []
        records = []
        with open(self.path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                records.append(json.loads(line))
        return records

    def attest(self, subject, claim, evidence_hash, entry_id=None):
        """Append an attestation record, or no-op if entry_id already exists.

        Returns the written record (or the existing one when idempotent).
        """
        if entry_id is None:
            entry_id = uuid.uuid4().hex

        for existing in self._read_all():
            if existing.get("entry_id") == entry_id:
                return existing

        record = {
            "entry_id": entry_id,
            "subject": subject,
            "claim": claim,
            "evidence_hash": evidence_hash,
            "timestamp": time.time(),
            "fingerprint": "",
        }
        record["fingerprint"] = _fingerprint(record)

        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
        return record

    def verify(self, subject):
        """Return the latest valid attestation for a subject, or None.

        The latest record for the subject is returned only if its fingerprint
        matches its content; tampered records are skipped.
        """
        latest = None
        for record in self._read_all():
            if record.get("subject") != subject:
                continue
            if record.get("fingerprint") != _fingerprint(record):
                continue
            if latest is None or record["timestamp"] >= latest["timestamp"]:
                latest = record
        if latest is None:
            return None
        return {"claim": latest["claim"], "evidence_hash": latest["evidence_hash"]}

    def replay(self):
        """Replay the log, yielding only records whose fingerprint is valid.

        Tampered records (fingerprint mismatch) are omitted, making tampering
        evident: a downstream consumer expecting N records sees fewer.
        """
        valid = []
        for record in self._read_all():
            if record.get("fingerprint") != _fingerprint(record):
                continue
            valid.append(record)
        return valid
