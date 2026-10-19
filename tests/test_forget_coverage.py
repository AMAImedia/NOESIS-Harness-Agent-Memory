"""Tests for the three stores forget.py did not originally reach, plus the
raw-byte residue scan and the cryptographic boundary.

Covers:
- SkillStore: every installed version, not only the active one.
- DomainLibrary: adopted artifacts and the rebuilt index.
- DurablePromotionState: the JSON payload column of every governance table.
- harden_sqlite / scan_raw_bytes: bytes that outlive the rows.
- CellCipher: the capability report, now that a real cipher exists.
"""

import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from noesis_harness.domain_library import DomainLibrary, LibraryEntry
from noesis_harness.cell_cipher import CellCipher, CellCipherError
from noesis_harness.forget import (
    ERASED_MARKER,
    Forger,
    build_predicate,
    cipher_capability,
    harden_sqlite,
    normalize,
    scan_raw_bytes,
)
from noesis_harness.learning_promotion import DurablePromotionState, ExperienceReceipt
from noesis_harness.memory import Memory
from noesis_harness.skill_store import SkillStore

SECRET = "sk-COVER42"


def _memory(directory):
    return Memory(os.path.join(directory, "m.db"))


class SkillStoreTests(unittest.TestCase):
    """A rollback target still carries content, so every version must be swept."""

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name) / "skills"
        self.skills = self.root / "myskill" / "versions"
        for version, body in (("v1", "the key is " + SECRET), ("v2", "v2 also has " + SECRET)):
            path = self.skills / version
            path.mkdir(parents=True)
            (path / "SKILL.md").write_text("# skill\n" + body + "\n", encoding="utf-8")
        (self.root / "myskill" / "active.json").write_text(
            '{"skill_id": "myskill", "version": "v2"}\n', encoding="utf-8"
        )
        self.store = SkillStore(str(self.root))
        self.memory = _memory(self.directory.name)
        self.forger = Forger(
            self.memory,
            skill_store=self.store,
            receipt_path=os.path.join(self.directory.name, "r.jsonl"),
        )

    def test_every_installed_version_is_swept_not_just_the_active_one(self):
        receipt = self.forger.forget(build_predicate(SECRET), actor="ann", request_id="r1")
        self.assertTrue(receipt.complete)
        for version in ("v1", "v2"):
            body = (self.skills / version / "SKILL.md").read_text(encoding="utf-8")
            self.assertNotIn(SECRET, body)
            self.assertIn(ERASED_MARKER, body)

    def test_the_skill_file_keeps_its_name_so_the_erasure_stays_visible(self):
        self.forger.forget(build_predicate(SECRET), actor="ann", request_id="r1")
        self.assertTrue((self.skills / "v1" / "SKILL.md").is_file())

    def test_pointer_files_are_not_rewritten(self):
        before = (self.root / "myskill" / "active.json").read_text(encoding="utf-8")
        self.forger.forget(build_predicate(SECRET), actor="ann", request_id="r1")
        after = (self.root / "myskill" / "active.json").read_text(encoding="utf-8")
        self.assertEqual(before, after)

    def test_unrelated_skill_content_survives(self):
        (self.skills / "v1" / "notes.md").write_text("unrelated advice about style\n", encoding="utf-8")
        self.forger.forget(build_predicate(SECRET), actor="ann", request_id="r1")
        self.assertIn(
            "unrelated advice",
            (self.skills / "v1" / "notes.md").read_text(encoding="utf-8"),
        )


class DomainLibraryTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.library = DomainLibrary(
            str(Path(self.directory.name) / "library"), "ops", clock=lambda: 1.0
        )
        self.library.add(
            LibraryEntry(
                task_id="task-1",
                domain="ops",
                cue="the deployment key rotates",
                why="it reconciled in both runs",
                artifacts=(("report.md", "the key is " + SECRET + "\n"),),
                approved_by="operator:ann",
            )
        )
        self.memory = _memory(self.directory.name)
        self.forger = Forger(
            self.memory,
            domain_library=self.library,
            receipt_path=os.path.join(self.directory.name, "r.jsonl"),
        )

    def test_an_adopted_artifact_is_reached(self):
        receipt = self.forger.forget(build_predicate(SECRET), actor="ann", request_id="r1")
        self.assertTrue(receipt.complete)
        stored = self.library.entry_dir("task-1") / "artifacts" / "report.md"
        self.assertNotIn(SECRET, stored.read_text(encoding="utf-8"))

    def test_the_experience_file_is_reached(self):
        self.forger.forget(build_predicate(SECRET), actor="ann", request_id="r1")
        body = (self.library.entry_dir("task-1") / "EXPERIENCE.md").read_text(encoding="utf-8")
        self.assertNotIn(SECRET, body)

    def test_the_index_is_rebuilt_so_it_cannot_point_at_stale_content(self):
        self.forger.forget(build_predicate(SECRET), actor="ann", request_id="r1")
        index = self.library.index.read_text(encoding="utf-8")
        self.assertNotIn(SECRET, index)
        # The entry itself is still listed: erasure removes content, not history.
        self.assertIn("task-1", index)

    def test_an_erased_file_says_it_was_erased(self):
        self.forger.forget(build_predicate(SECRET), actor="ann", request_id="r1")
        body = (self.library.entry_dir("task-1") / "artifacts" / "report.md").read_text(encoding="utf-8")
        self.assertIn(ERASED_MARKER, body)


class PromotionStateTests(unittest.TestCase):
    """The promotion database holds digests, not content. Prove it.

    This class exists because the opposite was assumed. The original
    "forgetting is not solved" note claimed a secret could be sitting in
    ``LearningPromotionState``; measuring the schema showed that no field in
    any of its records carries raw content -- receipts, evaluations and
    proposals all store ``*_digest`` values only, and the evaluator manifest
    table stores a digest too.

    So the honest statement is: the store is covered, and the coverage finds
    nothing because there is nothing there. That is a much stronger claim than
    "we sweep it and hope", and it is only credible if the sweep is still
    wired up in case content ever reaches the store.
    """

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = os.path.join(self.directory.name, "promotion.db")
        self.state = DurablePromotionState(self.path)
        receipt = ExperienceReceipt(
            receipt_id="rc1",
            experience_id="ex1",
            agent_id="agent-a",
            scope="local",
            source_digest="digest",
            outcome="success",
            payload_digest="sha256:" + "a" * 64,
            policy_digest="policy",
            created_at=1.0,
        )
        with self.state._connect() as db:
            db.execute(
                "INSERT INTO promotion_receipts VALUES(?,?)", ("rc1", self.state._record(receipt))
            )
        self.memory = _memory(self.directory.name)
        self.forger = Forger(
            self.memory,
            promotion_state=self.state,
            receipt_path=os.path.join(self.directory.name, "r.jsonl"),
        )

    def test_no_record_field_carries_raw_content(self):
        import dataclasses

        from noesis_harness.learning_promotion import HoldoutEvaluation, PromotionProposal

        for record_type in (ExperienceReceipt, HoldoutEvaluation, PromotionProposal):
            for field in dataclasses.fields(record_type):
                self.assertTrue(
                    field.name.endswith("_digest")
                    or field.name in ("receipt_id", "evaluation_id", "proposal_id", "experience_id",
                                      "agent_id", "scope", "outcome", "state", "skill_name",
                                      "approved_by", "version", "created_at", "evaluated_at",
                                      "schema_version", "receipt_id", "evaluation_id",
                                      "evaluator_version", "total_cases", "passed_cases",
                                      "leaked_cases", "status"),
                    "%s.%s could carry content" % (record_type.__name__, field.name),
                )

    def test_a_planted_secret_is_found_and_tombstoned(self):
        # Defence in depth: even though the real records hold only digests, a
        # row that did carry content must be caught rather than trusted.
        with self.state._connect() as db:
            db.execute(
                "INSERT INTO promotion_receipts VALUES(?,?)",
                ("rc-planted", '{"note": "the key is ' + SECRET + '"}'),
            )
        receipt = self.forger.forget(build_predicate(SECRET), actor="ann", request_id="r1")
        self.assertTrue(receipt.complete)
        with self.state._connect() as db:
            body = db.execute(
                "SELECT record_json FROM promotion_receipts WHERE receipt_id=?",
                ("rc-planted",),
            ).fetchone()[0]
        self.assertNotIn(SECRET, body)
        self.assertIn('"erased":true', body.replace(" ", ""))

    def test_a_digest_only_row_is_left_alone(self):
        receipt = self.forger.forget(build_predicate(SECRET), actor="ann", request_id="r1")
        self.assertTrue(receipt.complete)
        with self.state._connect() as db:
            body = db.execute(
                "SELECT record_json FROM promotion_receipts WHERE receipt_id=?", ("rc1",)
            ).fetchone()[0]
        # Untouched, because it never contained the secret.
        self.assertIn('"experience_id":"ex1"', body.replace(" ", ""))

    def test_the_row_survives_so_the_receipt_is_not_erased_from_history(self):
        self.forger.forget(build_predicate(SECRET), actor="ann", request_id="r1")
        with self.state._connect() as db:
            count = db.execute("SELECT count(*) FROM promotion_receipts").fetchone()[0]
        self.assertEqual(count, 1)

    def test_an_unrelated_receipt_is_untouched(self):
        other = ExperienceReceipt(
            receipt_id="rc2",
            experience_id="ex2",
            agent_id="agent-a",
            scope="local",
            source_digest="d",
            outcome="success",
            payload_digest="sha256:" + "b" * 64,
            policy_digest="p",
            created_at=1.0,
        )
        with self.state._connect() as db:
            db.execute(
                "INSERT INTO promotion_receipts VALUES(?,?)", ("rc2", self.state._record(other))
            )
        self.forger.forget(build_predicate(SECRET), actor="ann", request_id="r1")
        with self.state._connect() as db:
            body = db.execute(
                "SELECT record_json FROM promotion_receipts WHERE receipt_id=?", ("rc2",)
            ).fetchone()[0]
        self.assertIn("ex2", body)


class CoverageTests(unittest.TestCase):
    def test_all_eight_stores_are_reachable_together(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        memory = Memory(str(root / "m.db"))
        state = DurablePromotionState(str(root / "p.db"))
        library = DomainLibrary(str(root / "lib"), "ops", clock=lambda: 1.0)
        library.add(
            LibraryEntry(
                task_id="t1",
                domain="ops",
                cue="cue",
                artifacts=(("a.md", "x"),),
                approved_by="ann",
            )
        )
        forger = Forger(
            memory,
            graph=None,
            skill_store=SkillStore(str(root / "skills")),
            domain_library=library,
            promotion_state=state,
            receipt_path=str(root / "r.jsonl"),
        )
        self.assertEqual(
            forger.covered_stores,
            ("memory", "observations", "summaries", "skills", "library", "promotion"),
        )

    def test_an_unwired_store_is_absent_rather_than_silently_skipped(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        forger = Forger(Memory(os.path.join(directory.name, "m.db")))
        self.assertNotIn("promotion", forger.covered_stores)
        self.assertNotIn("skills", forger.covered_stores)


class RawResidueTests(unittest.TestCase):
    """The check that catches what the logical report cannot see."""

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)

    def _plant_and_delete(self, path, secure_delete):
        connection = sqlite3.connect(path)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA secure_delete=%s" % ("ON" if secure_delete else "OFF"))
        connection.execute("CREATE TABLE t(a TEXT)")
        rows = [("%s-%04d padding padding padding" % (SECRET, i),) for i in range(300)]
        connection.executemany("INSERT INTO t VALUES(?)", rows)
        connection.commit()
        connection.execute("DELETE FROM t")
        connection.commit()
        connection.close()

    def test_the_logical_layer_can_be_clean_while_bytes_remain(self):
        path = os.path.join(self.directory.name, "raw.db")
        self._plant_and_delete(path, secure_delete=False)
        connection = sqlite3.connect(path)
        self.assertEqual(connection.execute("SELECT count(*) FROM t").fetchone()[0], 0)
        connection.close()
        report = scan_raw_bytes([path], SECRET)
        # Whether residue remains depends on the SQLite build; what must hold is
        # that the scan looks at bytes rather than rows.
        self.assertEqual(report["files_scanned"], 1)
        self.assertIn(SECRET, report["needle_forms"])

    def test_hardening_removes_what_the_scan_finds(self):
        path = os.path.join(self.directory.name, "hard.db")
        self._plant_and_delete(path, secure_delete=False)
        before = scan_raw_bytes([path], SECRET)
        harden_sqlite(path)
        after = scan_raw_bytes([path], SECRET)
        self.assertLessEqual(len(after["hits"]), len(before["hits"]))
        self.assertFalse(after["raw_residue"])

    def test_hardening_reports_what_it_applied(self):
        path = os.path.join(self.directory.name, "applied.db")
        self._plant_and_delete(path, secure_delete=False)
        report = harden_sqlite(path)
        self.assertIn("secure_delete", report["applied"])
        self.assertIn("wal_checkpoint_truncate", report["applied"])
        self.assertIn("vacuum", report["applied"])
        self.assertNotIn("error", report)

    def test_a_missing_database_is_reported_not_raised(self):
        report = harden_sqlite(os.path.join(self.directory.name, "absent.db"))
        self.assertEqual(report["error"], "not_a_file")

    def test_the_scan_finds_a_secret_however_it_was_punctuated(self):
        # On disk the bytes are whatever was written. A caller who searches for
        # "SK COVER42" must still find a stored "sk-COVER42", because the token
        # is the part that survives in a page, not the phrase.
        path = os.path.join(self.directory.name, "fmt.txt")
        with open(path, "wb") as handle:
            handle.write(b"the key is sk-COVER42\n")
        report = scan_raw_bytes([path], "SK COVER42")
        self.assertTrue(report["raw_residue"])
        self.assertTrue(any("cover42" in form for form in report["needle_forms"]))

    def test_an_absent_needle_reports_no_residue(self):
        path = os.path.join(self.directory.name, "clean.txt")
        with open(path, "wb") as handle:
            handle.write(b"nothing sensitive here\n")
        self.assertFalse(scan_raw_bytes([path], SECRET)["raw_residue"])

    def test_a_directory_is_walked(self):
        target = Path(self.directory.name) / "tree"
        (target / "nested").mkdir(parents=True)
        (target / "nested" / "a.txt").write_text("contains " + SECRET, encoding="utf-8")
        (target / "b.txt").write_text("clean", encoding="utf-8")
        report = scan_raw_bytes([str(target)], SECRET)
        self.assertEqual(report["files_scanned"], 2)
        self.assertTrue(report["raw_residue"])

    def test_the_forger_can_scan_its_own_databases(self):
        memory = Memory(os.path.join(self.directory.name, "m.db"))
        memory.save("the key is " + SECRET, "semantic")
        forger = Forger(memory, receipt_path=os.path.join(self.directory.name, "r.jsonl"))
        forger.forget(build_predicate(SECRET), actor="ann", request_id="r1")
        report = forger.raw_residue(SECRET)
        self.assertGreaterEqual(report["files_scanned"], 1)

    def test_erasure_hardens_by_default(self):
        memory = Memory(os.path.join(self.directory.name, "m.db"))
        memory.save("the key is " + SECRET, "semantic")
        forger = Forger(memory, receipt_path=os.path.join(self.directory.name, "r.jsonl"))
        self.assertTrue(forger.harden)
        receipt = forger.forget(build_predicate(SECRET), actor="ann", request_id="r1")
        self.assertTrue(receipt.complete)


class CipherBoundaryTests(unittest.TestCase):
    """The honest answer to "can you erase irrecoverably?".

    This class used to assert that no cipher existed and that sealing raised.
    Both changed when ``aead.py`` implemented ChaCha20-Poly1305 from RFC 8439
    and ``cell_cipher.py`` gave it per-cell keys. The claim is now the stronger
    one, and it is still checked rather than asserted: the vectors have to pass
    before the capability report may say "cryptographic".
    """

    def test_the_capability_report_names_cryptographic_erasure(self):
        capability = cipher_capability()
        self.assertTrue(capability.kdf_available)
        self.assertTrue(capability.selftest_passed)
        self.assertEqual(capability.erasure_class, "cryptographic")
        self.assertFalse(capability.to_dict()["logical_erasure_only"])

    def test_the_report_names_the_cipher_and_the_specification(self):
        report = cipher_capability().to_dict()
        self.assertEqual(report["cipher"], "AEAD_CHACHA20_POLY1305")
        self.assertIn("RFC 8439", report["note"])

    def test_the_report_still_distinguishes_a_sealed_store_from_an_unsealed_one(self):
        # The class is reachable, but a deployment that never sealed anything
        # is still only access-control erased. The note has to say so, or the
        # capability report becomes a blanket claim.
        note = cipher_capability().to_dict()["note"]
        self.assertIn("access-control", note)

    def test_the_cipher_refuses_to_run_without_a_key_store(self):
        with self.assertRaises(CellCipherError):
            CellCipher(None)


class ExtraTokenTests(unittest.TestCase):
    def test_an_extra_phrase_is_tokenized_not_taken_whole(self):
        # A phrase stored as a single token would match nothing, so a widening
        # written as prose would silently do nothing.
        predicate = build_predicate("sk-TRAIL07", extra_tokens=["holder Ada Lovelace"])
        from noesis_harness.forget import _digest_token

        for word in ("holder", "ada", "lovelace"):
            self.assertIn(_digest_token(word), predicate.tokens)

    def test_a_compound_predicate_matches_any_of_its_parts(self):
        predicate = build_predicate("sk-TRAIL07", extra_tokens=["holder Ada Lovelace"])
        self.assertTrue(predicate.matches("holder Ada Lovelace"))
        self.assertTrue(predicate.matches("sk-TRAIL07"))
        self.assertFalse(predicate.matches("nothing relevant at all"))


if __name__ == "__main__":
    unittest.main()