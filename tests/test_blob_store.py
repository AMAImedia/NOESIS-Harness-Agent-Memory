"""Tests for noesis_harness.blob_store."""

from __future__ import annotations

import os
import tempfile
import unittest

from noesis_harness.blob_store import (
    BlobStore,
    BlobStoreError,
    digest_bytes,
    sha256_shard,
)


def _walk_files(root):
    found = []
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            found.append(os.path.join(dirpath, name))
    return found


class TestBlobStore(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = self._tmp.name
        self.store = BlobStore(self.root)

    def test_put_returns_digest_and_has_is_true(self):
        digest = self.store.put(b"hello world")
        self.assertEqual(digest, digest_bytes(b"hello world"))
        self.assertTrue(self.store.has(digest))

    def test_put_same_bytes_twice_is_idempotent(self):
        first = self.store.put(b"repeat me")
        second = self.store.put(b"repeat me")
        self.assertEqual(first, second)
        files = _walk_files(self.root)
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0], self.store.path_for(first))

    def test_put_different_bytes_differ(self):
        a = self.store.put(b"alpha")
        b = self.store.put(b"beta")
        self.assertNotEqual(a, b)
        self.assertEqual(self.store.stats()["count"], 2)

    def test_get_roundtrip_bytes(self):
        payload = b"\x00\x01\x02\xff binary"
        digest = self.store.put(payload)
        self.assertEqual(self.store.get(digest), payload)

    def test_get_text_roundtrip(self):
        digest = self.store.put_text("plain text value")
        self.assertEqual(self.store.get_text(digest), "plain text value")

    def test_get_text_custom_encoding(self):
        digest = self.store.put_text("caf\u00e9", encoding="utf-8")
        self.assertEqual(self.store.get_text(digest, encoding="utf-8"), "caf\u00e9")

    def test_get_missing_raises(self):
        digest = digest_bytes(b"never stored")
        with self.assertRaises(BlobStoreError):
            self.store.get(digest)

    def test_tampered_stored_file_raises_mismatch(self):
        digest = self.store.put(b"original bytes")
        with open(self.store.path_for(digest), "wb") as handle:
            handle.write(b"tampered bytes")
        with self.assertRaises(BlobStoreError) as ctx:
            self.store.get(digest)
        self.assertIn("content hash mismatch", str(ctx.exception))

    def test_invalid_digest_format_raises(self):
        for bad in ("", "xyz", "A" * 64, "0" * 63, "0" * 65, "g" * 64):
            with self.assertRaises(BlobStoreError):
                self.store.has(bad)
            with self.assertRaises(BlobStoreError):
                self.store.path_for(bad)

    def test_path_is_sharded(self):
        digest = self.store.put(b"shard me")
        path = self.store.path_for(digest)
        self.assertEqual(os.path.basename(os.path.dirname(path)), digest[:2])
        self.assertEqual(os.path.basename(path), digest)
        self.assertEqual(sha256_shard(digest), digest[:2])

    def test_list_blobs_sorted(self):
        digests = [self.store.put(("item-%d" % i).encode("ascii")) for i in range(5)]
        listed = self.store.list_blobs()
        self.assertEqual(listed, sorted(digests))
        self.assertEqual(listed, sorted(listed))

    def test_stats_count_and_total_bytes(self):
        self.store.put(b"12345")
        self.store.put(b"1234567890")
        stats = self.store.stats()
        self.assertEqual(stats["count"], 2)
        self.assertEqual(stats["total_bytes"], 15)

    def test_stats_empty_store(self):
        stats = self.store.stats()
        self.assertEqual(stats, {"count": 0, "total_bytes": 0})
        self.assertEqual(self.store.list_blobs(), [])

    def test_empty_bytes_supported(self):
        digest = self.store.put(b"")
        self.assertTrue(self.store.has(digest))
        self.assertEqual(self.store.get(digest), b"")
        self.assertEqual(self.store.size(digest), 0)

    def test_unicode_text(self):
        text = "\u4e2d\u6587 \u0440\u0443\u0441\u0441\u043a\u0438\u0439 \U0001F600 emoji"
        digest = self.store.put_text(text)
        self.assertEqual(self.store.get_text(digest), text)

    def test_size_returns_byte_length(self):
        digest = self.store.put(b"abcde")
        self.assertEqual(self.store.size(digest), 5)

    def test_size_missing_raises(self):
        with self.assertRaises(BlobStoreError):
            self.store.size(digest_bytes(b"absent"))

    def test_no_temp_leftovers_after_put(self):
        for i in range(4):
            self.store.put(("payload-%d" % i).encode("ascii"))
        leftovers = [
            path for path in _walk_files(self.root)
            if os.path.basename(path).startswith(".tmp-")
        ]
        self.assertEqual(leftovers, [])

    def test_idempotent_put_does_not_rewrite(self):
        digest = self.store.put(b"stable")
        path = self.store.path_for(digest)
        before = os.stat(path).st_mtime_ns
        self.store.put(b"stable")
        self.assertEqual(os.stat(path).st_mtime_ns, before)

    def test_put_rejects_non_bytes(self):
        with self.assertRaises(TypeError):
            self.store.put("not bytes")

    def test_put_text_rejects_non_str(self):
        with self.assertRaises(TypeError):
            self.store.put_text(b"not str")

    def test_blob_store_error_is_runtime_error(self):
        self.assertTrue(issubclass(BlobStoreError, RuntimeError))

    def test_root_created_lazily(self):
        nested = os.path.join(self.root, "new", "sub")
        store = BlobStore(nested)
        self.assertFalse(os.path.isdir(nested))
        store.put(b"lazy")
        self.assertTrue(os.path.isdir(nested))


if __name__ == "__main__":
    unittest.main()
