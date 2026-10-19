"""noesis_harness/cell_cipher.py

Cryptographic erasure: encrypt each cell under its own key, and erase by
destroying that key.

Patterns borrowed from:

- **SAIHM** (IETF draft-saihm-memory-protocol-03, 2026-10-11) section 2.7:
  an erasure MUST stop serving the cell, write a FORGET receipt, and add the
  cell id to a public erasure list; the two erasure classes are *cryptographic*
  (destroy every copy of the wrapped DEK, including backups and replicas) and
  *access-control* (withdraw from service but retain key material). The draft
  insists an operator MUST state which class it provides and MUST NOT describe
  access-control erasure as cryptographic.
- **Deployment-Time Memorization** (arXiv 2606.10062): derived copies stay
  recoverable after raw deletion in about 20% of cases; cryptographic erasure
  is the only mechanism that reaches zero residue no matter how many copies
  exist, because every copy is ciphertext.
- **MemCut** (arXiv 2610.21405): erasure must break every supporting evidence
  combination, not just the record that states the secret. Encrypting the cell
  rather than deleting rows means the supporting records are ciphertext too.
- **Bemula** (arXiv 2610.18052): redundancy across derived forms is why systems
  fail to forget. One key per cell means one destruction covers every form.
- NOESIS ``forget.py``: receipts, idempotency, attributable erasure, and the
  rule that the proof must not contain what it proves was removed.

Clean-room: no upstream code copied. The cipher is RFC 8439 (see ``aead.py``).

What this changes
-----------------

Before this module, ``forget.py`` could only perform *access-control* erasure:
the content is withdrawn from every read path and its bytes zeroed, but anyone
holding a pre-erasure copy can still read it. That is an honest claim, and a
weak one.

With a real AEAD, a cell is stored as ciphertext and its key is held
separately. Destroying the key makes every copy of that cell unreadable --
including copies this process never knew about. That is the *cryptographic*
erasure class, and it is the only mechanism that survives an adversary with a
backup.

Governance invariants:

- One key per cell. A shared key would make destroying one cell destroy
  others, and would make every cell readable once any one key leaked.
- A key is destroyed by overwriting it in the key store and recording the
  destruction. The destruction is attributable and idempotent.
- A destroyed key is never recreated, and a cell whose key is gone reports
  ``ERASED`` rather than an error, so callers cannot accidentally treat an
  erased cell as a missing one and re-populate it.
- ``seal`` refuses to run without a key store. There is no "encrypt with a
  process-global key" mode, because that would silently downgrade every cell to
  a single point of failure.
- Stdlib only.
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import time
from dataclasses import dataclass, field, replace
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

try:
    from .aead import (
        KEY_BYTES,
        NONCE_BYTES,
        TAG_BYTES,
        AeadError,
        AuthenticationError,
        aead_decrypt,
        aead_encrypt,
        random_key,
        random_nonce,
        selftest as aead_selftest,
    )
    from .atomic_write import atomic_append_line, atomic_write_bytes, atomic_write_text
    from .forget import canonical, content_digest
except ImportError:  # pragma: no cover - direct script import
    from noesis_harness.aead import (
        KEY_BYTES,
        NONCE_BYTES,
        TAG_BYTES,
        AeadError,
        AuthenticationError,
        aead_decrypt,
        aead_encrypt,
        random_key,
        random_nonce,
        selftest as aead_selftest,
    )
    from noesis_harness.atomic_write import atomic_append_line, atomic_write_bytes, atomic_write_text
    from noesis_harness.forget import canonical, content_digest


SCHEMA_VERSION = "noesis.cell-cipher.v1"

#: Erasure classes, named exactly as SAIHM names them.
ERASURE_CRYPTOGRAPHIC = "cryptographic"
ERASURE_ACCESS_CONTROL = "access_control"

#: Status of a cell.
CELL_SEALED = "sealed"
CELL_ERASED = "erased"

#: What a destroyed key leaves behind. Not a zero-length value: a zero-length
#: key would still be a key, and an implementation that tried to decrypt with
#: it would either fail confusingly or, worse, succeed against a truncated
#: ciphertext.
DESTROYED_MARKER = b"\x00" * KEY_BYTES


class CellCipherError(ValueError):
    """Raised when a cell operation is malformed."""


class KeyDestroyed(CellCipherError):
    """Raised when a caller tries to open a cell whose key was destroyed."""


class KeyStore:
    """One key per cell, held separately from the ciphertext.

    Keys live in their own directory, one file per cell, so that destroying a
    key is a single file overwrite rather than a row edit that might be undone
    by a backup. The file name is the cell id; the content is the raw key.
    """

    def __init__(self, root: str) -> None:
        self.root = str(root)
        os.makedirs(self.root, exist_ok=True)

    def _path(self, cell_id: str) -> str:
        if not cell_id or "/" in cell_id or "\\" in cell_id or cell_id in (".", ".."):
            raise CellCipherError("invalid_cell_id")
        return os.path.join(self.root, cell_id + ".key")

    def create(self, cell_id: str) -> bytes:
        """Create a fresh key. Refuses to overwrite an existing one."""
        path = self._path(cell_id)
        if os.path.exists(path):
            raise CellCipherError("key_already_exists")
        key = random_key()
        atomic_write_bytes(path, key)
        return key

    def get(self, cell_id: str) -> bytes:
        path = self._path(cell_id)
        try:
            with open(path, "rb") as handle:
                key = handle.read()
        except OSError:
            raise KeyDestroyed("key_absent")
        if key == DESTROYED_MARKER:
            raise KeyDestroyed("key_destroyed")
        if len(key) != KEY_BYTES:
            raise CellCipherError("key_corrupt")
        return key

    def exists(self, cell_id: str) -> bool:
        return os.path.exists(self._path(cell_id))

    def destroy(self, cell_id: str) -> bool:
        """Overwrite the key in place, then remove it.

        Two steps on purpose. Overwriting first means the key bytes are gone
        even if the unlink fails; removing the file second means a subsequent
        ``exists`` reports the truth. A single unlink would leave the bytes
        recoverable from the filesystem, which is the access-control failure
        this class exists to avoid.
        """
        path = self._path(cell_id)
        if not os.path.exists(path):
            return False
        try:
            atomic_write_bytes(path, DESTROYED_MARKER)
            os.remove(path)
        except OSError:
            # The overwrite is the part that matters. If the unlink fails, the
            # marker is still there and get() refuses it.
            return os.path.exists(path)
        return True

    def cell_ids(self) -> List[str]:
        try:
            return sorted(
                name[: -len(".key")]
                for name in os.listdir(self.root)
                if name.endswith(".key")
            )
        except OSError:
            return []


@dataclass(frozen=True)
class Cell:
    """One encrypted memory cell: ciphertext, nonce, and the associated data.

    ``aad`` binds the cell to its own id. A ciphertext moved to another cell's
    slot therefore fails to authenticate, which stops an attacker from
    swapping two cells to make one of them readable again.
    """

    cell_id: str
    sealed: bytes
    nonce: bytes
    status: str = CELL_SEALED
    created_at: float = 0.0
    aad: bytes = b""

    @property
    def size(self) -> int:
        return len(self.sealed)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "cell_id": self.cell_id,
            "sealed_hex": self.sealed.hex(),
            "nonce_hex": self.nonce.hex(),
            "status": self.status,
            "created_at": self.created_at,
            "aad_hex": self.aad.hex(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Cell":
        return cls(
            cell_id=str(data.get("cell_id") or ""),
            sealed=bytes.fromhex(str(data.get("sealed_hex") or "")),
            nonce=bytes.fromhex(str(data.get("nonce_hex") or "")),
            status=str(data.get("status") or CELL_SEALED),
            created_at=float(data.get("created_at") or 0.0),
            aad=bytes.fromhex(str(data.get("aad_hex") or "")),
        )


@dataclass(frozen=True)
class ErasureReceipt:
    """Proof that a cell's key was destroyed, carrying no plaintext."""

    cell_id: str
    receipt_id: str
    at: float
    erasure_class: str
    ciphertext_digest: str
    key_digest_before: str
    plaintext_digest: str = ""
    actor: str = ""
    reason: str = ""
    ciphertext_size: int = 0

    @property
    def cryptographic(self) -> bool:
        return self.erasure_class == ERASURE_CRYPTOGRAPHIC

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "cell_id": self.cell_id,
            "receipt_id": self.receipt_id,
            "at": self.at,
            "erasure_class": self.erasure_class,
            "cryptographic": self.cryptographic,
            "ciphertext_digest": self.ciphertext_digest,
            "key_digest_before": self.key_digest_before,
            "plaintext_digest": self.plaintext_digest,
            "actor": self.actor,
            "reason": self.reason,
            "ciphertext_size": self.ciphertext_size,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ErasureReceipt":
        return cls(
            cell_id=str(data.get("cell_id") or ""),
            receipt_id=str(data.get("receipt_id") or ""),
            at=float(data.get("at") or 0.0),
            erasure_class=str(data.get("erasure_class") or ERASURE_CRYPTOGRAPHIC),
            ciphertext_digest=str(data.get("ciphertext_digest") or ""),
            key_digest_before=str(data.get("key_digest_before") or ""),
            plaintext_digest=str(data.get("plaintext_digest") or ""),
            actor=str(data.get("actor") or ""),
            reason=str(data.get("reason") or ""),
            ciphertext_size=int(data.get("ciphertext_size") or 0),
        )


class ReceiptJournal:
    """Append-only erasure receipts plus the public list SAIHM requires."""

    def __init__(self, path: str) -> None:
        self.path = str(path)

    @property
    def list_path(self) -> str:
        return self.path + ".erasure-list"

    def append(self, receipt: ErasureReceipt) -> str:
        atomic_append_line(self.path, canonical(receipt.to_dict()))
        if receipt.cell_id not in self.erased_cell_ids():
            atomic_append_line(self.list_path, receipt.cell_id + "\n")
        return receipt.receipt_id

    def receipts(self) -> List[ErasureReceipt]:
        out: List[ErasureReceipt] = []
        try:
            handle = open(self.path, "r", encoding="utf-8")
        except OSError:
            return out
        with handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(ErasureReceipt.from_dict(json.loads(line)))
                except (ValueError, KeyError, TypeError):
                    continue
        return out

    def erased_cell_ids(self) -> List[str]:
        try:
            handle = open(self.list_path, "r", encoding="utf-8")
        except OSError:
            return []
        with handle:
            return [line.strip() for line in handle if line.strip()]

    def find(self, cell_id: str) -> Optional[ErasureReceipt]:
        for receipt in self.receipts():
            if receipt.cell_id == cell_id:
                return receipt
        return None

    def verify_list(self) -> Dict[str, Any]:
        from_receipts = {r.cell_id for r in self.receipts()}
        from_list = set(self.erased_cell_ids())
        return {
            "receipts": len(from_receipts),
            "listed": len(from_list),
            "missing_from_list": sorted(from_receipts - from_list),
            "missing_receipt": sorted(from_list - from_receipts),
            "consistent": from_receipts == from_list,
        }


class CellCipher:
    """Seal cells under per-cell keys; erase by destroying the key.

    This is the mechanism behind the cryptographic erasure class. A cell is
    sealed once, its key is created once, and erasure is one key destruction --
    after which every copy of the ciphertext, wherever it was copied, decrypts
    to nothing.
    """

    def __init__(
        self,
        keystore: KeyStore,
        *,
        receipt_path: str = "",
        clock: Optional[Callable[[], float]] = None,
        verify_cipher: bool = True,
    ) -> None:
        if keystore is None:
            raise CellCipherError("keystore_required_no_implicit_global_key")
        if verify_cipher:
            report = aead_selftest()
            if not report["all_passed"]:
                raise CellCipherError("aead_selftest_failed_refusing_to_seal")
        self.keystore = keystore
        self.clock = clock or time.time
        self.journal = ReceiptJournal(receipt_path) if receipt_path else None

    # -- sealing -----------------------------------------------------------

    def seal(self, cell_id: str, plaintext: bytes, *, aad: bytes = b"") -> Cell:
        """Encrypt one cell under a fresh key and return the sealed cell.

        The associated data defaults to the cell id, which binds the
        ciphertext to its slot. A caller that supplies its own ``aad`` takes
        responsibility for including the id, and the docs say so rather than
        quietly appending it.
        """
        if not isinstance(plaintext, (bytes, bytearray)):
            raise CellCipherError("plaintext_must_be_bytes")
        key = self.keystore.create(cell_id)
        nonce = random_nonce()
        bound = aad if aad else cell_id.encode("utf-8")
        sealed = aead_encrypt(key, nonce, bytes(plaintext), bound)
        return Cell(
            cell_id=cell_id,
            sealed=sealed,
            nonce=nonce,
            status=CELL_SEALED,
            created_at=float(self.clock()),
            aad=bound,
        )

    def open(self, cell: Cell) -> bytes:
        """Decrypt one cell. Raises :class:`KeyDestroyed` after erasure."""
        if cell.status == CELL_ERASED:
            raise KeyDestroyed("cell_erased")
        key = self.keystore.get(cell.cell_id)
        return aead_decrypt(key, cell.nonce, cell.sealed, cell.aad or cell.cell_id.encode("utf-8"))

    def can_open(self, cell: Cell) -> bool:
        """Whether the cell is still readable, without raising."""
        try:
            self.open(cell)
            return True
        except (KeyDestroyed, AuthenticationError, AeadError, CellCipherError):
            return False

    # -- erasure -----------------------------------------------------------

    def erase(
        self,
        cell: Cell,
        *,
        actor: str,
        reason: str = "",
        plaintext_digest: str = "",
    ) -> ErasureReceipt:
        """Destroy the cell's key and record it. Idempotent by cell id.

        Idempotency matters more here than elsewhere: a second erasure request
        for the same cell must not fail, because a retry is exactly what a
        client does when it is unsure whether the first one landed.
        """
        if not str(actor).strip():
            raise CellCipherError("actor_required_erasure_must_be_attributable")
        if self.journal is not None:
            existing = self.journal.find(cell.cell_id)
            if existing is not None:
                return existing

        try:
            key = self.keystore.get(cell.cell_id)
            key_digest = "sha256:" + hashlib.sha256(key).hexdigest()
        except KeyDestroyed:
            key_digest = ""

        destroyed = self.keystore.destroy(cell.cell_id)
        if not destroyed and not key_digest:
            # Nothing to destroy and no evidence it ever existed: still record
            # the request, so the receipt list answers "was this ever erased?"
            # rather than staying silent.
            pass

        at = float(self.clock())
        receipt = ErasureReceipt(
            cell_id=cell.cell_id,
            receipt_id="crc_" + hashlib.sha256(
                canonical([cell.cell_id, at, key_digest]).encode("utf-8")
            ).hexdigest()[:24],
            at=at,
            erasure_class=ERASURE_CRYPTOGRAPHIC,
            ciphertext_digest="sha256:" + hashlib.sha256(cell.sealed).hexdigest(),
            key_digest_before=key_digest,
            plaintext_digest=str(plaintext_digest or ""),
            actor=str(actor),
            reason=str(reason),
            ciphertext_size=len(cell.sealed),
        )
        if self.journal is not None:
            self.journal.append(receipt)
        return receipt

    # -- reporting ---------------------------------------------------------

    def verify(self, cell: Cell) -> Dict[str, Any]:
        """Prove a cell can no longer be opened."""
        readable = self.can_open(cell)
        receipt = self.journal.find(cell.cell_id) if self.journal is not None else None
        return {
            "cell_id": cell.cell_id,
            "erasure_class": ERASURE_CRYPTOGRAPHIC if receipt else ERASURE_ACCESS_CONTROL,
            "cryptographic": receipt.cryptographic if receipt else False,
            "key_present": self.keystore.exists(cell.cell_id),
            "readable": readable,
            "erased": not readable,
            "receipt": receipt.to_dict() if receipt else None,
        }

    def capability(self) -> Dict[str, Any]:
        """What this build can honestly claim, checked rather than asserted."""
        report = aead_selftest()
        return {
            "schema_version": SCHEMA_VERSION,
            "erasure_class": ERASURE_CRYPTOGRAPHIC if report["all_passed"] else ERASURE_ACCESS_CONTROL,
            "cipher": "AEAD_CHACHA20_POLY1305",
            "reference": "RFC 8439",
            "selftest": report,
            "per_cell_keys": True,
            "stdlib_only": True,
            "limits": (
                "Key destruction makes every copy of a cell unreadable. It does "
                "not reach a copy of the plaintext taken before sealing, and it "
                "does not promise constant-time execution under CPython."
            ),
        }


__all__ = [
    "CELL_ERASED",
    "CELL_SEALED",
    "Cell",
    "CellCipher",
    "CellCipherError",
    "DESTROYED_MARKER",
    "ERASURE_ACCESS_CONTROL",
    "ERASURE_CRYPTOGRAPHIC",
    "ErasureReceipt",
    "KeyDestroyed",
    "KeyStore",
    "ReceiptJournal",
    "SCHEMA_VERSION",
]