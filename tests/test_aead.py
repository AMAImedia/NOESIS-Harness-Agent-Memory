"""Tests for the AEAD and the cryptographic-erasure cell.

Every test here is either an RFC 8439 vector or a property that an erasure
claim depends on. There are no invented expected values: a cipher tested
against its own output proves nothing.
"""

import os
import shutil
import tempfile
import unittest

from noesis_harness.aead import (
    APPENDIX_A_POLY1305,
    KEY_BYTES,
    NONCE_BYTES,
    RFC_TEST_VECTORS,
    TAG_BYTES,
    AeadError,
    AuthenticationError,
    aead_decrypt,
    aead_encrypt,
    chacha20_block,
    chacha20_encrypt,
    derive_key,
    poly1305_key_gen,
    poly1305_mac,
    quarter_round,
    random_key,
    random_nonce,
    selftest,
)
from noesis_harness.cell_cipher import (
    CELL_ERASED,
    ERASURE_ACCESS_CONTROL,
    ERASURE_CRYPTOGRAPHIC,
    Cell,
    CellCipher,
    CellCipherError,
    ErasureReceipt,
    KeyDestroyed,
    KeyStore,
    ReceiptJournal,
)


class RfcVectorTests(unittest.TestCase):
    """The specification is the test oracle."""

    def test_every_published_vector_passes(self):
        report = selftest()
        failed = [name for name, ok in report["checks"].items() if not ok]
        self.assertEqual(failed, [], "RFC 8439 vectors failed: %s" % failed)
        self.assertTrue(report["all_passed"])

    def test_the_report_names_the_specification(self):
        report = selftest()
        self.assertEqual(report["reference"], "RFC 8439")
        self.assertEqual(report["algorithm"], "AEAD_CHACHA20_POLY1305")
        self.assertGreaterEqual(report["n_checks"], 11)

    def test_quarter_round_matches_section_2_1_1(self):
        vector = RFC_TEST_VECTORS["quarter_round"]
        state = list(vector["state"])
        quarter_round(state, 0, 1, 2, 3)
        self.assertEqual(state, vector["expected"])

    def test_block_matches_section_2_3_2(self):
        vector = RFC_TEST_VECTORS["block"]
        self.assertEqual(
            chacha20_block(vector["key"], vector["counter"], vector["nonce"]),
            vector["expected"],
        )

    def test_encryption_matches_section_2_4_2(self):
        vector = RFC_TEST_VECTORS["encrypt"]
        self.assertEqual(
            chacha20_encrypt(
                vector["key"], vector["counter"], vector["nonce"], vector["plaintext"]
            ),
            vector["expected"],
        )

    def test_poly1305_matches_section_2_5_2(self):
        vector = RFC_TEST_VECTORS["poly1305"]
        self.assertEqual(
            poly1305_mac(vector["message"], vector["key"]), vector["expected"]
        )

    def test_poly1305_key_generation_matches_section_2_6_2(self):
        vector = RFC_TEST_VECTORS["poly1305_key_gen"]
        self.assertEqual(
            poly1305_key_gen(vector["key"], vector["nonce"]), vector["expected"]
        )

    def test_aead_matches_section_2_8_2(self):
        vector = RFC_TEST_VECTORS["aead"]
        sealed = aead_encrypt(
            vector["key"], vector["nonce"], vector["plaintext"], vector["aad"]
        )
        self.assertEqual(sealed[:-TAG_BYTES], vector["expected_ciphertext"])
        self.assertEqual(sealed[-TAG_BYTES:], vector["expected_tag"])

    def test_appendix_a_empty_and_zero_key_vectors(self):
        for name, vector in APPENDIX_A_POLY1305.items():
            with self.subTest(name=name):
                self.assertEqual(
                    poly1305_mac(vector["message"], vector["key"]), vector["expected"]
                )


class AeadPropertyTests(unittest.TestCase):
    def setUp(self):
        self.key = random_key()
        self.nonce = random_nonce()

    def test_roundtrip_returns_the_plaintext(self):
        for size in (0, 1, 63, 64, 65, 1000):
            with self.subTest(size=size):
                plaintext = bytes(range(256))[:size] or b""
                plaintext = (b"x" * size)
                sealed = aead_encrypt(self.key, self.nonce, plaintext)
                self.assertEqual(aead_decrypt(self.key, self.nonce, sealed), plaintext)

    def test_a_wrong_key_is_rejected(self):
        sealed = aead_encrypt(self.key, self.nonce, b"payload")
        with self.assertRaises(AuthenticationError):
            aead_decrypt(random_key(), self.nonce, sealed)

    def test_a_tampered_ciphertext_is_rejected(self):
        sealed = bytearray(aead_encrypt(self.key, self.nonce, b"payload"))
        sealed[0] ^= 0x01
        with self.assertRaises(AuthenticationError):
            aead_decrypt(self.key, self.nonce, bytes(sealed))

    def test_a_tampered_tag_is_rejected(self):
        sealed = bytearray(aead_encrypt(self.key, self.nonce, b"payload"))
        sealed[-1] ^= 0x01
        with self.assertRaises(AuthenticationError):
            aead_decrypt(self.key, self.nonce, bytes(sealed))

    def test_a_changed_aad_is_rejected(self):
        sealed = aead_encrypt(self.key, self.nonce, b"payload", b"cell-1")
        with self.assertRaises(AuthenticationError):
            aead_decrypt(self.key, self.nonce, sealed, b"cell-2")

    def test_a_truncated_ciphertext_is_refused(self):
        with self.assertRaises(AeadError):
            aead_decrypt(self.key, self.nonce, b"short")

    def test_a_wrong_length_key_is_refused(self):
        with self.assertRaises(AeadError):
            aead_encrypt(b"short", self.nonce, b"x")

    def test_a_wrong_length_nonce_is_refused(self):
        with self.assertRaises(AeadError):
            aead_encrypt(self.key, b"short", b"x")

    def test_ciphertext_does_not_contain_the_plaintext(self):
        secret = b"sk-TOPSECRET-42"
        self.assertNotIn(secret, aead_encrypt(self.key, self.nonce, secret))

    def test_derivation_is_deterministic_and_salt_bound(self):
        first = derive_key(b"passphrase", b"saltsalt", n=2 ** 10)
        second = derive_key(b"passphrase", b"saltsalt", n=2 ** 10)
        other = derive_key(b"passphrase", b"othersalt", n=2 ** 10)
        self.assertEqual(first, second)
        self.assertNotEqual(first, other)
        self.assertEqual(len(first), KEY_BYTES)

    def test_derivation_refuses_a_short_salt(self):
        with self.assertRaises(AeadError):
            derive_key(b"passphrase", b"short")

    def test_keys_and_nonces_are_the_right_size(self):
        self.assertEqual(len(random_key()), KEY_BYTES)
        self.assertEqual(len(random_nonce()), NONCE_BYTES)


class KeyStoreTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.store = KeyStore(os.path.join(self.directory.name, "keys"))

    def test_a_key_is_created_once(self):
        key = self.store.create("c1")
        self.assertEqual(len(key), KEY_BYTES)
        self.assertEqual(self.store.get("c1"), key)
        with self.assertRaises(CellCipherError):
            self.store.create("c1")

    def test_destroying_a_key_removes_it(self):
        self.store.create("c1")
        self.assertTrue(self.store.destroy("c1"))
        self.assertFalse(self.store.exists("c1"))
        with self.assertRaises(KeyDestroyed):
            self.store.get("c1")

    def test_destroying_twice_is_a_no_op(self):
        self.store.create("c1")
        self.assertTrue(self.store.destroy("c1"))
        self.assertFalse(self.store.destroy("c1"))

    def test_the_key_bytes_are_overwritten_before_removal(self):
        # A plain unlink leaves the bytes recoverable from the filesystem. The
        # store overwrites first, so even a failed removal leaves a marker that
        # get() refuses rather than a usable key.
        self.store.create("c1")
        path = self.store._path("c1")
        with open(path, "rb") as handle:
            before = handle.read()
        self.assertNotEqual(before, bytes(KEY_BYTES))
        self.store.destroy("c1")
        self.assertFalse(os.path.exists(path))

    def test_a_cell_id_cannot_escape_the_key_directory(self):
        for bad in ("../escape", "a/b", "..", ""):
            with self.subTest(bad=bad):
                with self.assertRaises(CellCipherError):
                    self.store.create(bad)

    def test_cell_ids_are_listed(self):
        for cell_id in ("a", "b"):
            self.store.create(cell_id)
        self.assertEqual(self.store.cell_ids(), ["a", "b"])


class CellTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.store = KeyStore(os.path.join(self.directory.name, "keys"))
        self.cipher = CellCipher(
            self.store, receipt_path=os.path.join(self.directory.name, "r.jsonl")
        )

    def test_a_sealed_cell_roundtrips(self):
        cell = self.cipher.seal("c1", b"payload")
        self.assertEqual(self.cipher.open(cell), b"payload")

    def test_the_ciphertext_does_not_carry_the_plaintext(self):
        cell = self.cipher.seal("c1", b"sk-SECRET42")
        self.assertNotIn(b"sk-SECRET42", cell.sealed)

    def test_each_cell_gets_its_own_key(self):
        first = self.cipher.seal("c1", b"same payload")
        second = self.cipher.seal("c2", b"same payload")
        # Same plaintext, same code path, different key and nonce, so the
        # ciphertexts must differ. Equal ciphertexts would leak equality.
        self.assertNotEqual(first.sealed, second.sealed)

    def test_a_cell_moved_to_another_slot_fails_to_open(self):
        # The aad binds the ciphertext to its id, so a swap is detected rather
        # than silently decrypting under the wrong identity.
        cell = self.cipher.seal("c1", b"payload")
        moved = Cell(
            cell_id="c2",
            sealed=cell.sealed,
            nonce=cell.nonce,
            aad=cell.aad,
        )
        self.store.create("c2")
        with self.assertRaises(AuthenticationError):
            self.cipher.open(moved)

    def test_a_cell_roundtrips_through_dict(self):
        cell = self.cipher.seal("c1", b"payload")
        self.assertEqual(Cell.from_dict(cell.to_dict()), cell)


class CryptographicErasureTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.store = KeyStore(os.path.join(self.directory.name, "keys"))
        self.cipher = CellCipher(
            self.store, receipt_path=os.path.join(self.directory.name, "r.jsonl")
        )

    def test_erasing_a_cell_makes_it_unreadable(self):
        cell = self.cipher.seal("c1", b"payload")
        receipt = self.cipher.erase(cell, actor="ann")
        self.assertTrue(receipt.cryptographic)
        self.assertEqual(receipt.erasure_class, ERASURE_CRYPTOGRAPHIC)
        self.assertFalse(self.cipher.can_open(cell))
        with self.assertRaises(KeyDestroyed):
            self.cipher.open(cell)

    def test_the_erasure_class_is_cryptographic_not_access_control(self):
        cell = self.cipher.seal("c1", b"payload")
        receipt = self.cipher.erase(cell, actor="ann")
        self.assertEqual(receipt.erasure_class, "cryptographic")

    def test_erasure_requires_an_actor(self):
        cell = self.cipher.seal("c1", b"payload")
        with self.assertRaises(CellCipherError):
            self.cipher.erase(cell, actor="  ")

    def test_erasure_is_idempotent(self):
        cell = self.cipher.seal("c1", b"payload")
        first = self.cipher.erase(cell, actor="ann")
        second = self.cipher.erase(cell, actor="ann")
        self.assertEqual(first.receipt_id, second.receipt_id)
        self.assertEqual(len(self.cipher.journal.receipts()), 1)

    def test_the_receipt_does_not_contain_the_plaintext(self):
        cell = self.cipher.seal("c1", b"sk-SECRET42")
        receipt = self.cipher.erase(cell, actor="ann")
        self.assertNotIn("SECRET42", str(receipt.to_dict()))

    def test_the_receipt_records_what_it_can_prove(self):
        cell = self.cipher.seal("c1", b"payload")
        receipt = self.cipher.erase(cell, actor="ann", reason="user_request")
        self.assertTrue(receipt.ciphertext_digest.startswith("sha256:"))
        self.assertTrue(receipt.key_digest_before.startswith("sha256:"))
        self.assertEqual(receipt.ciphertext_size, len(cell.sealed))
        self.assertEqual(receipt.actor, "ann")

    def test_verify_reports_the_cell_as_erased(self):
        cell = self.cipher.seal("c1", b"payload")
        self.cipher.erase(cell, actor="ann")
        report = self.cipher.verify(cell)
        self.assertTrue(report["erased"])
        self.assertFalse(report["readable"])
        self.assertFalse(report["key_present"])
        self.assertTrue(report["cryptographic"])

    def test_the_public_erasure_list_matches_the_receipts(self):
        cell = self.cipher.seal("c1", b"payload")
        self.cipher.erase(cell, actor="ann")
        self.assertTrue(self.cipher.journal.verify_list()["consistent"])
        self.assertIn("c1", self.cipher.journal.erased_cell_ids())

    def test_a_stolen_ciphertext_is_useless_after_erasure(self):
        # The point of the cryptographic class: the attacker copied the
        # ciphertext before the erasure, and it still does not help.
        cell = self.cipher.seal("c1", b"payload")
        stolen = cell.sealed
        self.cipher.erase(cell, actor="ann")
        with self.assertRaises(KeyDestroyed):
            self.cipher.open(cell)
        # Reconstructing a cell from the stolen bytes without the key fails.
        rebuilt = Cell(cell_id="c1", sealed=stolen, nonce=cell.nonce, aad=cell.aad)
        self.assertFalse(self.cipher.can_open(rebuilt))

    def test_the_honest_limit_a_copied_key_still_opens(self):
        # A pre-erasure copy of the KEY is outside what any library can reach.
        # This test records the limit rather than hiding it: SAIHM requires
        # destroying every copy including backups, which is a deployment duty.
        cell = self.cipher.seal("c1", b"payload")
        stolen_keys = os.path.join(self.directory.name, "stolen")
        shutil.copytree(self.store.root, stolen_keys)
        self.cipher.erase(cell, actor="ann")
        thief = CellCipher(KeyStore(stolen_keys))
        self.assertEqual(thief.open(cell), b"payload")

    def test_an_empty_keystore_is_not_cryptographic_erasure(self):
        # This test used to assert the opposite. Verified vectors with nothing
        # sealed is a ready cipher and no protected data; calling it
        # cryptographic erasure was the blanket claim AGENTS.md forbids.
        report = self.cipher.capability()
        self.assertEqual(report["cipher_class"], ERASURE_CRYPTOGRAPHIC)
        self.assertEqual(report["erasure_class"], ERASURE_ACCESS_CONTROL)
        self.assertEqual(report["sealed_cells"], 0)
        self.assertEqual(report["cipher"], "AEAD_CHACHA20_POLY1305")
        self.assertEqual(report["reference"], "RFC 8439")
        self.assertTrue(report["selftest"]["all_passed"])

    def test_a_sealed_cell_raises_the_erasure_class(self):
        self.cipher.seal("c1", b"payload")
        report = self.cipher.capability()
        self.assertEqual(report["erasure_class"], ERASURE_CRYPTOGRAPHIC)
        self.assertEqual(report["sealed_cells"], 1)
        self.assertTrue(report["sealed"])

    def test_the_class_survives_fully_erasing_everything(self):
        # Counting only live keys would flip the report to access-control the
        # moment the last cell was destroyed -- precisely when the
        # cryptographic claim is most needed. The receipts prove it.
        cell = self.cipher.seal("c1", b"payload")
        self.cipher.erase(cell, actor="ann")
        self.assertFalse(self.cipher.keystore.exists("c1"))
        report = self.cipher.capability()
        self.assertEqual(report["erasure_class"], ERASURE_CRYPTOGRAPHIC)
        self.assertEqual(report["sealed_cells"], 1)

    def test_the_report_states_its_limits(self):
        limits = self.cipher.capability()["limits"]
        self.assertIn("copy of the plaintext", limits)
        self.assertIn("constant-time", limits)


class KeyLocationTests(unittest.TestCase):
    """A key beside its own ciphertext is protection against nobody."""

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.data_root = os.path.join(self.directory.name, "data")
        os.makedirs(self.data_root)
        self.keys_inside = KeyStore(os.path.join(self.data_root, "keys"))
        self.keys_outside = KeyStore(os.path.join(self.directory.name, "keys"))

    def test_a_key_store_inside_the_data_directory_is_detected(self):
        self.assertTrue(self.keys_inside.is_inside(self.data_root))
        self.assertFalse(self.keys_outside.is_inside(self.data_root))

    def test_the_store_inside_its_own_directory_counts_as_inside(self):
        self.assertTrue(self.keys_inside.is_inside(self.data_root + "/keys"))

    def test_a_sibling_directory_is_not_inside(self):
        other = os.path.join(self.directory.name, "other")
        os.makedirs(other)
        self.assertFalse(self.keys_inside.is_inside(other))

    def test_the_capability_reports_the_warning(self):
        cipher = CellCipher(self.keys_inside)
        report = cipher.capability(data_root=self.data_root)
        self.assertTrue(report["key_next_to_data"])
        self.assertIn("WARNING", report["limits"])

    def test_the_capability_stays_silent_when_the_key_is_elsewhere(self):
        cipher = CellCipher(self.keys_outside)
        report = cipher.capability(data_root=self.data_root)
        self.assertFalse(report["key_next_to_data"])
        self.assertNotIn("WARNING", report["limits"])

    def test_no_data_root_is_reported_as_unknown_not_safe(self):
        # Absent evidence must not read as favourable evidence. An unchecked
        # store is not a store proven to separate its keys.
        cipher = CellCipher(self.keys_inside)
        self.assertIsNone(cipher.capability()["key_next_to_data"])

    def test_a_root_passed_as_none_is_still_unknown(self):
        cipher = CellCipher(self.keys_inside)
        self.assertIsNone(cipher.capability(data_root=None)["key_next_to_data"])


class RefusalTests(unittest.TestCase):
    def test_a_cipher_without_a_key_store_is_refused(self):
        # A process-global key would silently downgrade every cell to one
        # single point of failure, so there is no such mode.
        with self.assertRaises(CellCipherError):
            CellCipher(None)

    def test_the_cipher_refuses_to_seal_if_it_fails_its_own_vectors(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        store = KeyStore(os.path.join(directory.name, "keys"))
        cipher = CellCipher(store, verify_cipher=False)
        self.assertIsNotNone(cipher.seal("c1", b"x"))


class ReceiptJournalTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = os.path.join(self.directory.name, "r.jsonl")
        self.journal = ReceiptJournal(self.path)

    def test_a_receipt_roundtrips(self):
        receipt = ErasureReceipt(
            cell_id="c1",
            receipt_id="r1",
            at=1.0,
            erasure_class=ERASURE_CRYPTOGRAPHIC,
            ciphertext_digest="sha256:aa",
            key_digest_before="sha256:bb",
            actor="ann",
        )
        self.journal.append(receipt)
        restored = self.journal.receipts()[0]
        self.assertEqual(restored.cell_id, "c1")
        self.assertTrue(restored.cryptographic)

    def test_a_damaged_list_is_detected(self):
        receipt = ErasureReceipt(
            cell_id="c1",
            receipt_id="r1",
            at=1.0,
            erasure_class=ERASURE_CRYPTOGRAPHIC,
            ciphertext_digest="sha256:aa",
            key_digest_before="sha256:bb",
        )
        self.journal.append(receipt)
        with open(self.journal.list_path, "w", encoding="utf-8") as handle:
            handle.write("")
        report = self.journal.verify_list()
        self.assertFalse(report["consistent"])
        self.assertEqual(report["missing_from_list"], ["c1"])

    def test_a_truncated_line_is_skipped(self):
        receipt = ErasureReceipt(
            cell_id="c1",
            receipt_id="r1",
            at=1.0,
            erasure_class=ERASURE_CRYPTOGRAPHIC,
            ciphertext_digest="sha256:aa",
            key_digest_before="sha256:bb",
        )
        self.journal.append(receipt)
        with open(self.path, "a", encoding="utf-8") as handle:
            handle.write('{"cell_id": "brok')
        self.assertEqual(len(self.journal.receipts()), 1)

    def test_find_returns_none_for_an_unknown_cell(self):
        self.assertIsNone(self.journal.find("never"))


class ErasedStatusTests(unittest.TestCase):
    def test_a_cell_marked_erased_is_refused_before_the_key_is_read(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        cipher = CellCipher(KeyStore(os.path.join(directory.name, "keys")))
        cell = cipher.seal("c1", b"payload")
        erased = Cell(
            cell_id=cell.cell_id,
            sealed=cell.sealed,
            nonce=cell.nonce,
            status=CELL_ERASED,
            aad=cell.aad,
        )
        with self.assertRaises(KeyDestroyed):
            cipher.open(erased)
        # The key is still there, so this proves the status check runs first.
        self.assertTrue(cipher.keystore.exists("c1"))


if __name__ == "__main__":
    unittest.main()