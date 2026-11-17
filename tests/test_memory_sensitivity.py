"""Tests for sensitivity-gated memory: store it, but do not serve it.

The decision recorded here: this project does not encrypt memory at rest, and
the reason is that a key stored beside its encrypted file protects against
nothing -- whoever reads the disk reads the key too. Encryption would buy a
better report line without a better guarantee.

What is actually needed is control over what reaches an agent's context, so
this module puts the gate on *recall* rather than on *storage*. The password is
remembered; it cannot be dragged back into a prompt unless the caller names it.
"""

import os
import sqlite3
import tempfile
import unittest

from noesis_harness.memory import (
    DEFAULT_SENSITIVITIES,
    Memory,
    allowed_rows,
    check_sensitivity,
)
from noesis_harness.resource_lineage import SENSITIVITIES


def _memory():
    directory = tempfile.TemporaryDirectory()
    memory = Memory(os.path.join(directory.name, "m.db"))
    return directory, memory


class LabelTests(unittest.TestCase):
    def test_known_labels_are_accepted(self):
        for label in SENSITIVITIES:
            with self.subTest(label=label):
                self.assertEqual(check_sensitivity(label), label)

    def test_labels_are_normalized(self):
        self.assertEqual(check_sensitivity("  SENSITIVE "), "sensitive")

    def test_an_unknown_label_is_refused_not_downgraded(self):
        # Silently storing "top-secret" as "internal" would be the worst
        # possible failure: the caller believes it was restricted and the
        # system served it to everyone.
        for bad in ("top-secret", "secret", "", None):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    check_sensitivity(bad)


class RecallGateTests(unittest.TestCase):
    def setUp(self):
        self.directory, self.memory = _memory()
        self.addCleanup(self.directory.cleanup)
        self.memory.save("the office wifi password is hunter2", "semantic", sensitivity="sensitive")
        self.memory.save("the office is in Berlin", "semantic")
        self.memory.save("the payroll runs on Friday", "semantic", sensitivity="restricted")

    def test_secrets_are_not_recalled_by_default(self):
        hits = self.memory.recall("office wifi password hunter2", limit=10)
        facts = [row["fact"] for row in hits]
        self.assertNotIn("the office wifi password is hunter2", facts)
        self.assertNotIn("the payroll runs on Friday", facts)

    def test_ordinary_memories_still_recall(self):
        facts = [row["fact"] for row in self.memory.recall("office Berlin", limit=10)]
        self.assertIn("the office is in Berlin", facts)

    def test_an_explicit_opt_in_returns_them(self):
        facts = [
            row["fact"]
            for row in self.memory.recall(
                "office wifi password hunter2", limit=10, allowed_sensitivities=SENSITIVITIES
            )
        ]
        self.assertIn("the office wifi password is hunter2", facts)

    def test_the_caller_can_ask_for_sensitive_only(self):
        facts = [
            row["fact"]
            for row in self.memory.recall(
                "office", limit=10, allowed_sensitivities=("sensitive",)
            )
        ]
        self.assertIn("the office wifi password is hunter2", facts)
        self.assertNotIn("the office is in Berlin", facts)

    def test_public_and_internal_are_the_default_gate(self):
        self.assertEqual(tuple(DEFAULT_SENSITIVITIES), ("public", "internal"))

    def test_a_suppressed_row_does_not_accumulate_access_count(self):
        # The counter lives in the same file. If a suppressed match bumped it,
        # a watcher could read back "the agent looked at a sensitive row and
        # found something" without ever seeing the row.
        path = os.path.join(self.directory.name, "m.db")
        row = sqlite3.connect(path).execute(
            "SELECT id, access_count FROM memories WHERE sensitivity='sensitive'"
        ).fetchone()
        before = row[1]
        self.memory.recall("office wifi password hunter2", limit=10)
        after = sqlite3.connect(path).execute(
            "SELECT access_count FROM memories WHERE id=?", (row[0],)
        ).fetchone()[0]
        self.assertEqual(after, before)

    def test_an_opted_in_row_does_become_accessible(self):
        path = os.path.join(self.directory.name, "m.db")
        row = sqlite3.connect(path).execute(
            "SELECT id, access_count FROM memories WHERE sensitivity='sensitive'"
        ).fetchone()
        self.memory.recall(
            "office wifi password hunter2", limit=10, allowed_sensitivities=SENSITIVITIES
        )
        after = sqlite3.connect(path).execute(
            "SELECT access_count FROM memories WHERE id=?", (row[0],)
        ).fetchone()[0]
        self.assertGreater(after, row[1])


class ProfileGateTests(unittest.TestCase):
    def setUp(self):
        self.directory, self.memory = _memory()
        self.addCleanup(self.directory.cleanup)
        self.memory.save("secret worth hiding", "semantic", sensitivity="sensitive")
        self.memory.save("ordinary fact", "semantic")

    def test_profile_hides_sensitive_rows_too(self):
        # If profile returned them while recall did not, the gate would be
        # cosmetic -- one method away from leaking what the other protects.
        facts = [row["fact"] for row in self.memory.profile()]
        self.assertEqual(facts, ["ordinary fact"])

    def test_profile_can_opt_in(self):
        facts = [
            row["fact"] for row in self.memory.profile(allowed_sensitivities=SENSITIVITIES)
        ]
        self.assertIn("secret worth hiding", facts)


class LookupTests(unittest.TestCase):
    """Knowing an id means you already have the fact."""

    def test_get_crosses_the_gate_deliberately(self):
        directory, memory = _memory()
        self.addCleanup(directory.cleanup)
        fact_id = memory.save("secret worth hiding", "semantic", sensitivity="restricted")
        self.assertIsNotNone(memory.get(fact_id))
        self.assertEqual(memory.get(fact_id)["fact"], "secret worth hiding")

    def test_get_returns_none_for_an_unknown_id(self):
        directory, memory = _memory()
        self.addCleanup(directory.cleanup)
        self.assertIsNone(memory.get("no-such-id"))


class WriteSideTests(unittest.TestCase):
    def setUp(self):
        self.directory, self.memory = _memory()
        self.addCleanup(self.directory.cleanup)

    def test_observations_carry_a_sensitivity(self):
        self.memory.observe("s1", "chat", "token abc", sensitivity="sensitive")
        with self.memory._conn() as conn:
            value = conn.execute("SELECT sensitivity FROM observations").fetchone()[0]
        self.assertEqual(value, "sensitive")

    def test_summaries_carry_a_sensitivity(self):
        self.memory.summarize("s1", "session about keys", sensitivity="restricted")
        with self.memory._conn() as conn:
            value = conn.execute("SELECT sensitivity FROM summaries").fetchone()[0]
        self.assertEqual(value, "restricted")

    def test_an_unknown_label_on_write_is_refused(self):
        with self.assertRaises(ValueError):
            self.memory.save("x", "semantic", sensitivity="nope")
        with self.assertRaises(ValueError):
            self.memory.observe("s1", "chat", "x", sensitivity="nope")
        with self.assertRaises(ValueError):
            self.memory.summarize("s1", "x", sensitivity="nope")

    def test_saving_the_same_fact_twice_is_still_one_row(self):
        first = self.memory.save("the same fact", "semantic")
        second = self.memory.save("the same fact", "semantic", sensitivity="sensitive")
        self.assertEqual(first, second)


class MigrationTests(unittest.TestCase):
    """An existing database keeps working and keeps recalling."""

    def test_a_database_created_without_the_column_gains_it(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = os.path.join(directory.name, "legacy.db")
        conn = sqlite3.connect(path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript(
            """
            CREATE TABLE memories (
                id TEXT PRIMARY KEY, kind TEXT NOT NULL,
                fact TEXT NOT NULL, confidence REAL NOT NULL DEFAULT 0.5,
                strength REAL NOT NULL DEFAULT 1.0,
                access_count INTEGER NOT NULL DEFAULT 0,
                last_accessed_at REAL NOT NULL DEFAULT 0,
                created_at REAL NOT NULL, embedding BLOB);
            CREATE VIRTUAL TABLE mem_fts USING fts5(
                kind, fact, content='memories', content_rowid='rowid');
            """
        )
        conn.execute(
            "INSERT INTO memories (id, kind, fact, confidence, strength, created_at)"
            " VALUES ('legacy-1','semantic','legacy fact about Berlin',0.5,1.0,1.0)"
        )
        conn.execute("INSERT INTO mem_fts(rowid, kind, fact) VALUES (1, 'semantic', "
                     "'legacy fact about Berlin')")
        conn.commit()
        conn.close()

        memory = Memory(path)
        with memory._conn() as c:
            cols = {r[1] for r in c.execute("PRAGMA table_info(memories)").fetchall()}
        self.assertIn("sensitivity", cols)

        facts = [row["fact"] for row in memory.recall("legacy fact Berlin", limit=5)]
        self.assertIn("legacy fact about Berlin", facts)

    def test_an_old_row_defaults_to_internal_and_remains_recalled(self):
        directory, memory = _memory()
        self.addCleanup(directory.cleanup)
        memory.save("an ordinary fact", "semantic")
        with memory._conn() as c:
            value = c.execute("SELECT sensitivity FROM memories").fetchone()[0]
        self.assertEqual(value, "internal")
        self.assertIn(
            "an ordinary fact",
            [row["fact"] for row in memory.recall("ordinary fact", limit=5)],
        )

    def test_migrating_twice_is_a_no_op(self):
        directory, memory = _memory()
        self.addCleanup(directory.cleanup)
        Memory(os.path.join(directory.name, "m.db"))
        self.assertIsNotNone(memory.stats())


class AllowedRowsTests(unittest.TestCase):
    def test_an_empty_allowed_set_returns_nothing(self):
        rows = [{"sensitivity": "public"}]
        self.assertEqual(allowed_rows(rows, ()), [])

    def test_rows_without_a_label_treated_as_internal(self):
        # A row written by older code has no label; treating it as restricted
        # would make old memories vanish without anyone being told.
        self.assertEqual(len(allowed_rows([{"fact": "x"}], ("internal",))), 1)
        self.assertEqual(len(allowed_rows([{"fact": "x"}], ("public",))), 0)

    def test_the_filter_never_mutates_its_input(self):
        rows = [{"sensitivity": "restricted"}]
        allowed_rows(rows, ("public",))
        self.assertEqual(rows, [{"sensitivity": "restricted"}])


class ProcurementTests(unittest.TestCase):
    """procedures.py reads through profile(), so the gate applies there too."""

    def test_a_sensitive_procedure_is_not_served(self):
        directory, memory = _memory()
        self.addCleanup(directory.cleanup)
        memory.save("when deploy then rotate the key hunter2", "procedural", sensitivity="sensitive")
        memory.save("when deploy then notify the team", "procedural")
        from noesis_harness.procedures import ProcedureRunner

        matched = ProcedureRunner(memory).match("deploy the service", limit=5)
        facts = [item["fact"] for item in matched]
        self.assertNotIn("when deploy then rotate the key hunter2", facts)


if __name__ == "__main__":
    unittest.main()