"""Content-addressed SHA-256 blob store with atomic writes.

Pattern ported from:
  - qm (TypeScript), ``src/files/durable-byte-store.ts``: a durable,
    content-addressed byte store. Blobs are keyed by the hex SHA-256 of their
    contents and written through a temp-file-plus-rename sequence so a reader
    never observes a partially written blob. File names avoid a flat directory
    by sharding on the first two hex characters of the digest.

The Python port keeps the same guarantees:

  - The digest is the lowercase hex SHA-256 of the bytes, with no algorithm
    prefix.
  - ``put`` is idempotent: storing identical bytes returns the same digest and
    does not rewrite the existing file.
  - Writes are atomic: bytes go to a uniquely named temporary file in the same
    shard directory, are flushed and fsynced, and are then moved into place
    with ``os.replace``. A crashed writer leaves at most a stray temporary
    file; it never leaves a corrupt blob at the final path.
  - ``get`` re-hashes the stored bytes and refuses to return content whose
    digest does not match the requested key.

This module is stdlib-only and deterministic. The only side effects are blob
files created under the configured root, which is created lazily.
"""

from __future__ import annotations

import hashlib
import os
import tempfile
from typing import Dict, List

__all__ = [
    "BlobStoreError",
    "digest_bytes",
    "sha256_shard",
    "BlobStore",
]

_HEX_DIGITS = "0123456789abcdef"
_DIGEST_LENGTH = 64


class BlobStoreError(RuntimeError):
    """Raised for invalid digests, missing blobs, and hash mismatches."""


def digest_bytes(data: bytes) -> str:
    """Return the lowercase hex SHA-256 digest of ``data`` (no prefix)."""
    if not isinstance(data, bytes):
        raise TypeError("data must be bytes")
    return hashlib.sha256(data).hexdigest()


def sha256_shard(digest: str) -> str:
    """Return the 2-character shard directory for ``digest``.

    The shard is the first two hex characters of the digest and is validated
    with the same rules as ``BlobStore`` digests.
    """
    _validate_digest(digest)
    return digest[:2]


def _validate_digest(digest: str) -> None:
    """Raise ``BlobStoreError`` unless ``digest`` is 64 lowercase hex chars."""
    if not isinstance(digest, str):
        raise BlobStoreError("digest must be a str, got %r" % (type(digest),))
    if len(digest) != _DIGEST_LENGTH:
        raise BlobStoreError(
            "digest must be %d hex characters, got %d"
            % (_DIGEST_LENGTH, len(digest))
        )
    for char in digest:
        if char not in _HEX_DIGITS:
            raise BlobStoreError(
                "digest must be lowercase hex, found %r" % (char,)
            )


class BlobStore:
    """A content-addressed SHA-256 blob store rooted at a directory.

    Layout::

        <root>/<aa>/<full-hex-digest>

    where ``<aa>`` is the first two hex characters of the digest. The root and
    shard directories are created lazily on first write.
    """

    def __init__(self, root: str) -> None:
        if not isinstance(root, str):
            raise BlobStoreError("root must be a str")
        self._root = root

    @property
    def root(self) -> str:
        """The configured root directory."""
        return self._root

    def path_for(self, digest: str) -> str:
        """Return the on-disk path for ``digest`` without touching disk."""
        _validate_digest(digest)
        return os.path.join(self._root, digest[:2], digest)

    def has(self, digest: str) -> bool:
        """Return True when a valid blob for ``digest`` exists on disk."""
        _validate_digest(digest)
        return os.path.isfile(self.path_for(digest))

    def put(self, data: bytes) -> str:
        """Store ``data`` and return its digest; idempotent.

        If a blob with the same digest already exists it is left untouched
        (no rewrite). Otherwise the bytes are written atomically.
        """
        if not isinstance(data, bytes):
            raise TypeError("data must be bytes")
        digest = digest_bytes(data)
        path = self.path_for(digest)
        if os.path.isfile(path):
            return digest
        self._atomic_write(path, data)
        return digest

    def put_text(self, text: str, encoding: str = "utf-8") -> str:
        """Encode ``text`` and store the resulting bytes."""
        if not isinstance(text, str):
            raise TypeError("text must be str")
        return self.put(text.encode(encoding))

    def _atomic_write(self, path: str, data: bytes) -> None:
        """Write ``data`` to ``path`` via temp file, fsync, and os.replace."""
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)

        handle = None
        temp_path = None
        try:
            fd, temp_path = tempfile.mkstemp(prefix=".tmp-", dir=directory)
            handle = os.fdopen(fd, "wb")
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
            handle.close()
            handle = None
            os.replace(temp_path, path)
            temp_path = None
        except OSError as exc:
            raise BlobStoreError(
                "failed writing blob %r: %s" % (path, exc)
            )
        finally:
            if handle is not None:
                try:
                    handle.close()
                except OSError:
                    pass
            if temp_path is not None:
                try:
                    os.remove(temp_path)
                except OSError:
                    pass

        if directory:
            self._fsync_directory(directory)

    @staticmethod
    def _fsync_directory(directory: str) -> None:
        """Best-effort fsync of ``directory``; ignored where unsupported."""
        try:
            dir_fd = os.open(directory, os.O_RDONLY)
        except OSError:
            return
        try:
            os.fsync(dir_fd)
        except OSError:
            pass
        finally:
            try:
                os.close(dir_fd)
            except OSError:
                pass

    def get(self, digest: str) -> bytes:
        """Return the bytes for ``digest`` after verifying their hash."""
        _validate_digest(digest)
        path = self.path_for(digest)
        try:
            with open(path, "rb") as handle:
                data = handle.read()
        except FileNotFoundError:
            raise BlobStoreError("blob not found: %s" % (digest,))
        except OSError as exc:
            raise BlobStoreError(
                "failed reading blob %r: %s" % (digest, exc)
            )
        if digest_bytes(data) != digest:
            raise BlobStoreError("content hash mismatch")
        return data

    def get_text(self, digest: str, encoding: str = "utf-8") -> str:
        """Return the decoded text for ``digest``."""
        return self.get(digest).decode(encoding)

    def size(self, digest: str) -> int:
        """Return the byte length of the stored blob for ``digest``."""
        _validate_digest(digest)
        try:
            return os.path.getsize(self.path_for(digest))
        except OSError:
            raise BlobStoreError("blob not found: %s" % (digest,))

    def list_blobs(self) -> List[str]:
        """Return all stored digests, sorted ascending."""
        digests = []
        if not os.path.isdir(self._root):
            return digests
        for shard in os.listdir(self._root):
            shard_dir = os.path.join(self._root, shard)
            if not os.path.isdir(shard_dir):
                continue
            for name in os.listdir(shard_dir):
                if len(name) != _DIGEST_LENGTH:
                    continue
                if any(char not in _HEX_DIGITS for char in name):
                    continue
                if os.path.isfile(os.path.join(shard_dir, name)):
                    digests.append(name)
        return sorted(digests)

    def stats(self) -> Dict[str, int]:
        """Return ``{"count": <int>, "total_bytes": <int>}``."""
        count = 0
        total_bytes = 0
        for digest in self.list_blobs():
            count += 1
            try:
                total_bytes += os.path.getsize(self.path_for(digest))
            except OSError:
                continue
        return {"count": count, "total_bytes": total_bytes}
