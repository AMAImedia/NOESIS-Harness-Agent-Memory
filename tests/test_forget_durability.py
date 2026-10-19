"""Tests for the round-2 additions to forget.py: sidecars, durability,
backup declaration, and the cryptographic capability report.
"""

import os
import sqlite3
import tempfile
import unittest

from noesis_harness import Memory
from noesis_harness.forget import (
    Forger,
    build_predicate,
    cipher_capability,
    fsync_paths,
    harden_sqlite,
    scan_raw_bytes,
    scrub_sidecars,
    sqlite_sidecars,
)

SECRET = "sk-SIDE42"


class SidecarTests(unittest.TestCase):
    """The WAL and the rollback journal are copies of the database's content."""

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = os.path.join(self.directory.name, "m.db")

    def _leave_a_wal_behind(self):
        """Produce a WAL file that survives, the way a crash leaves one.

        SQLite checkpoints and removes the WAL when the last connection closes
        cleanly, so a clean test cannot reproduce the risk. The risk is a WAL
        left by a crash or held by another reader, which is modelled here by
        writing one directly: it is the same file with the same content.
        """
        connection = sqlite3.connect(self.path)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("CREATE TABLE t(a TEXT)")
        connection.executemany(
            "INSERT INTO t VALUES(?)",
            [("%s-%03d padding" % (SECRET, i),) for i in range(50)],
        )
        connection.commit()
        connection.close()
        with open(self.path + "-wal", "wb") as handle:
            handle.write(b"stale page image " + SECRET.encode("utf-8") + b" " * 512)
        return self.path + "-wal"

    def test_a_surviving_wal_is_recognised(self):
        wal = self._leave_a_wal_behind()
        self.assertTrue(os.path.exists(wal))
        self.assertIn(wal, sqlite_sidecars(self.path))

    def test_scrubbing_removes_the_wal(self):
        wal = self._leave_a_wal_behind()
        report = scrub_sidecars(self.path)
        self.assertTrue(any(name.endswith("-wal") for name in report["removed"]))
        self.assertFalse(os.path.exists(wal))

    def test_scrubbing_is_idempotent(self):
        self._leave_a_wal_behind()
        scrub_sidecars(self.path)
        second = scrub_sidecars(self.path)
        self.assertEqual(second["removed"], [])

    def test_hardening_reports_the_sidecars_it_scrubbed(self):
        self._leave_a_wal_behind()
        report = harden_sqlite(self.path)
        self.assertIn("sidecars", report)
        self.assertTrue(any(name.endswith("-wal") for name in report["sidecars"]["removed"]))

    def test_a_clean_close_leaves_no_sidecar_and_scrubbing_is_a_no_op(self):
        # The ordinary case, recorded so the scrubber's silence is understood
        # as "nothing to do" rather than "the scrubber is broken".
        connection = sqlite3.connect(self.path)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("CREATE TABLE t(a TEXT)")
        connection.commit()
        connection.close()
        self.assertEqual(sqlite_sidecars(self.path), [])
        self.assertEqual(scrub_sidecars(self.path)["removed"], [])

    def test_a_rollback_journal_is_reached_too(self):
        # wal_checkpoint does not touch -journal. A rollback journal from an
        # interrupted transaction holds pre-deletion page images.
        journal = self.path + "-journal"
        with open(journal, "wb") as handle:
            handle.write(b"page image " + SECRET.encode("utf-8"))
        self.assertIn(journal, sqlite_sidecars(self.path))
        report = scrub_sidecars(self.path)
        self.assertTrue(any(name.endswith("-journal") for name in report["removed"]))
        self.assertFalse(os.path.exists(journal))


class DurabilityTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)

    def test_fsync_flushes_the_file_and_its_directory(self):
        path = os.path.join(self.directory.name, "f.txt")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("x")
        report = fsync_paths([path])
        self.assertIn(path, report["fsynced"])
        self.assertIn(self.directory.name, report["fsynced"])
        self.assertEqual(report["errors"], [])

    def test_a_missing_path_is_reported_not_raised(self):
        report = fsync_paths([os.path.join(self.directory.name, "absent.txt")])
        self.assertTrue(report["errors"])

    def test_erasure_is_durable_by_default(self):
        memory = Memory(os.path.join(self.directory.name, "m.db"))
        memory.save("key " + SECRET, "semantic")
        forger = Forger(memory, receipt_path=os.path.join(self.directory.name, "r.jsonl"))
        self.assertTrue(forger.durable)
        receipt = forger.forget(build_predicate(SECRET), actor="ann", request_id="r1")
        self.assertTrue(receipt.complete)

    def test_durability_can_be_disabled_explicitly(self):
        memory = Memory(os.path.join(self.directory.name, "m.db"))
        forger = Forger(memory, durable=False)
        self.assertFalse(forger.durable)


class BackupDeclarationTests(unittest.TestCase):
    """A library cannot delete a replica it does not own. It can refuse to lie."""

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.memory = Memory(os.path.join(self.directory.name, "m.db"))
        self.memory.save("key " + SECRET, "semantic")
        self.forger = Forger(
            self.memory, receipt_path=os.path.join(self.directory.name, "r.jsonl")
        )

    def test_declaring_a_backup_is_recorded(self):
        declared = self.forger.declare_backups([os.path.join(self.directory.name, "b1")])
        self.assertEqual(len(declared), 1)
        self.assertEqual(len(self.forger.backup_roots), 1)

    def test_an_absent_backup_is_unreached_not_ignored(self):
        self.forger.declare_backups([os.path.join(self.directory.name, "remote")])
        report = self.forger.scan_backups(SECRET)
        self.assertEqual(report["reached"], [])
        self.assertEqual(len(report["unreached"]), 1)
        self.assertFalse(report["complete_coverage"])

    def test_a_reachable_backup_is_scanned(self):
        backup = os.path.join(self.directory.name, "backup")
        os.makedirs(backup)
        with open(os.path.join(backup, "copy.txt"), "w", encoding="utf-8") as handle:
            handle.write("the key is " + SECRET)
        self.forger.declare_backups([backup])
        report = self.forger.scan_backups(SECRET)
        self.assertTrue(report["reached"])
        self.assertTrue(report["raw_residue"])

    def test_a_clean_backup_reports_no_residue(self):
        backup = os.path.join(self.directory.name, "backup")
        os.makedirs(backup)
        with open(os.path.join(backup, "copy.txt"), "w", encoding="utf-8") as handle:
            handle.write("nothing relevant")
        self.forger.declare_backups([backup])
        report = self.forger.scan_backups(SECRET)
        self.assertFalse(report["raw_residue"])
        self.assertTrue(report["complete_coverage"])

    def test_with_no_declared_backups_coverage_is_not_claimed(self):
        report = self.forger.scan_backups(SECRET)
        self.assertFalse(report["complete_coverage"])
        self.assertEqual(report["declared"], [])


class CapabilityTests(unittest.TestCase):
    def test_the_cipher_reports_the_cryptographic_class(self):
        capability = cipher_capability()
        self.assertTrue(capability.symmetric_cipher_available)
        self.assertTrue(capability.aead_available)
        self.assertTrue(capability.selftest_passed)
        self.assertEqual(capability.erasure_class, "cryptographic")

    def test_the_report_names_the_cipher_and_the_spec(self):
        report = cipher_capability().to_dict()
        self.assertEqual(report["cipher"], "AEAD_CHACHA20_POLY1305")
        self.assertIn("RFC 8439", report["note"])
        self.assertFalse(report["logical_erasure_only"])

    def test_the_note_does_not_claim_more_than_the_mechanism(self):
        note = cipher_capability().to_dict()["note"]
        # The report must distinguish a sealed store from an unsealed one.
        self.assertIn("access-control", note)


class RawScanCaseTests(unittest.TestCase):
    def test_the_scan_is_case_insensitive_on_bytes(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = os.path.join(directory.name, "x.txt")
        with open(path, "wb") as handle:
            handle.write(b"THE KEY IS SK-SIDE42")
        self.assertTrue(scan_raw_bytes([path], "sk-side42")["raw_residue"])

    def test_the_scan_reports_the_matched_form(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = os.path.join(directory.name, "x.txt")
        with open(path, "wb") as handle:
            handle.write(b"value sk-SIDE42 here")
        report = scan_raw_bytes([path], SECRET)
        self.assertTrue(report["hits"])
        self.assertIn("form", report["hits"][0])


if __name__ == "__main__":
    unittest.main()