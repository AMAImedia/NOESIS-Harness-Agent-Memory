"""Tests for noesis_harness/memory_revisions.py

Stdlib-only. Exercises CAS replace/delete conflicts, append-only history and
limits, restore semantics, cross-scope provenance mirroring, untrusted marking,
JSONL persistence roundtrip, malformed-tail tolerance, and determinism.
"""

import json
import os
import tempfile
import unittest

from noesis_harness.memory_revisions import (
    SCHEMA_VERSION,
    MemoryRevisions,
    Revision,
    RevisionConflict,
    mark_untrusted,
    read_revision_log,
)


class TestMemoryRevisions(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

    def _path(self, name="log.jsonl"):
        return os.path.join(self._tmp.name, name)

    # -- read_head ----------------------------------------------------------

    def test_read_head_unknown_scope(self):
        mem = MemoryRevisions()
        self.assertEqual(mem.read_head("nowhere"), ("", 0))

    def test_add_then_read_head(self):
        mem = MemoryRevisions()
        rev = mem.add("team", "hello", "alice", 1.0)
        self.assertEqual(rev, 1)
        self.assertEqual(mem.read_head("team"), ("hello", 1))

    # -- compare-and-swap ---------------------------------------------------

    def test_cas_replace_success(self):
        mem = MemoryRevisions()
        mem.add("team", "v1", "alice", 1.0)
        new_rev = mem.replace_if_revision("team", "v2", 1, "bob", 2.0)
        self.assertEqual(new_rev, 2)
        self.assertEqual(mem.read_head("team"), ("v2", 2))

    def test_cas_replace_conflict_raises(self):
        mem = MemoryRevisions()
        mem.add("team", "v1", "alice", 1.0)
        mem.replace_if_revision("team", "v2", 1, "bob", 2.0)
        with self.assertRaises(RevisionConflict):
            mem.replace_if_revision("team", "stale", 1, "carol", 3.0)
        self.assertEqual(mem.read_head("team"), ("v2", 2))

    def test_cas_replace_unknown_scope_zero_succeeds(self):
        mem = MemoryRevisions()
        rev = mem.replace_if_revision("new", "seed", 0, "alice", 1.0)
        self.assertEqual(rev, 1)
        self.assertEqual(mem.read_head("new"), ("seed", 1))

    def test_delete_cas_and_conflict(self):
        mem = MemoryRevisions()
        mem.add("team", "v1", "alice", 1.0)
        new_rev = mem.delete("team", 1, "bob", 2.0)
        self.assertEqual(new_rev, 2)
        self.assertEqual(mem.read_head("team"), ("", 2))
        with self.assertRaises(RevisionConflict):
            mem.delete("team", 1, "carol", 3.0)
        self.assertEqual(mem.read_head("team"), ("", 2))

    # -- history ------------------------------------------------------------

    def test_history_chronological_order(self):
        mem = MemoryRevisions()
        mem.add("team", "a", "alice", 1.0)
        mem.replace_if_revision("team", "b", 1, "bob", 2.0)
        mem.replace_if_revision("team", "c", 2, "carol", 3.0)
        bodies = [rev.body for rev in mem.history("team")]
        self.assertEqual(bodies, ["a", "b", "c"])
        self.assertEqual([rev.op for rev in mem.history("team")], ["add", "update", "update"])

    def test_history_limit_returns_most_recent(self):
        mem = MemoryRevisions()
        mem.add("team", "a", "alice", 1.0)
        mem.replace_if_revision("team", "b", 1, "bob", 2.0)
        mem.replace_if_revision("team", "c", 2, "carol", 3.0)
        recent = mem.history("team", limit=2)
        self.assertEqual([rev.body for rev in recent], ["b", "c"])
        self.assertEqual(mem.history("team", limit=0), mem.history("team"))
        self.assertEqual(mem.history("other"), [])

    # -- restore ------------------------------------------------------------

    def test_restore_reverts_content_and_appends(self):
        mem = MemoryRevisions()
        mem.add("team", "a", "alice", 1.0)
        mem.replace_if_revision("team", "b", 1, "bob", 2.0)
        new_rev = mem.restore("team", 1, "carol", 3.0)
        self.assertEqual(new_rev, 3)
        self.assertEqual(mem.read_head("team"), ("a", 3))
        entries = mem.history("team")
        self.assertEqual(entries[-1].op, "update")
        self.assertIn("restored from revision 1", entries[-1].provenance)

    def test_restore_unknown_revision_raises(self):
        mem = MemoryRevisions()
        mem.add("team", "a", "alice", 1.0)
        with self.assertRaises(RevisionConflict):
            mem.restore("team", 99, "bob", 2.0)
        self.assertEqual(mem.read_head("team"), ("a", 1))

    # -- scopes and mirror --------------------------------------------------

    def test_scopes_sorted_and_unique(self):
        mem = MemoryRevisions()
        mem.add("zeta", "z", "alice", 1.0)
        mem.add("alpha", "a", "alice", 2.0)
        mem.add("zeta", "z2", "alice", 3.0)
        self.assertEqual(mem.scopes(), ["alpha", "zeta"])

    def test_mirror_provenance(self):
        mem = MemoryRevisions()
        mem.add("channel", "shared fact", "alice", 1.0)
        new_rev = mem.mirror("channel", "archive", "bob", 2.0)
        self.assertEqual(new_rev, 2)
        self.assertEqual(mem.read_head("archive"), ("shared fact", 2))
        entry = mem.history("archive")[0]
        self.assertEqual(entry.provenance, "(said in channel)")
        self.assertEqual(entry.op, "update")

    # -- mark_untrusted -----------------------------------------------------

    def test_mark_untrusted_prefix(self):
        self.assertEqual(mark_untrusted("rain tomorrow"), "[claimed source] rain tomorrow")

    def test_mark_untrusted_idempotent(self):
        once = mark_untrusted("rain tomorrow")
        twice = mark_untrusted(once)
        self.assertEqual(once, twice)
        self.assertTrue(twice.startswith("[claimed source] "))

    # -- persistence --------------------------------------------------------

    def test_persistence_roundtrip_replays(self):
        path = self._path()
        mem = MemoryRevisions(path=path)
        mem.add("team", "v1", "alice", 1.0)
        mem.replace_if_revision("team", "v2", 1, "bob", 2.0)
        mem.mirror("team", "archive", "bob", 3.0)

        replayed = MemoryRevisions(path=path)
        self.assertEqual(replayed.read_head("team"), ("v2", 2))
        self.assertEqual(replayed.read_head("archive"), ("v2", 3))
        self.assertEqual(replayed.scopes(), ["archive", "team"])
        self.assertEqual(len(replayed.history("team")), 2)

    def test_malformed_tail_tolerated(self):
        path = self._path()
        mem = MemoryRevisions(path=path)
        mem.add("team", "v1", "alice", 1.0)
        with open(path, "a", encoding="utf-8") as handle:
            handle.write("{\"scope\": \"team\", \"seq\":")
            handle.write("\n")
            handle.write("not json at all\n")
            handle.write("\n")
        replayed = MemoryRevisions(path=path)
        self.assertEqual(replayed.read_head("team"), ("v1", 1))

    def test_read_revision_log_missing_file(self):
        self.assertEqual(read_revision_log(self._path("absent.jsonl")), [])

    def test_schema_version_written_and_stable(self):
        path = self._path()
        mem = MemoryRevisions(path=path)
        mem.add("team", "v1", "alice", 1.0)
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.loads(handle.readline())
        self.assertEqual(payload["schema_version"], SCHEMA_VERSION)
        self.assertEqual(SCHEMA_VERSION, 1)

    # -- determinism --------------------------------------------------------

    def test_determinism_same_inputs_same_revisions(self):
        def run():
            mem = MemoryRevisions()
            mem.add("team", "a", "alice", 1.0)
            mem.replace_if_revision("team", "b", 1, "bob", 2.0)
            mem.restore("team", 1, "carol", 3.0)
            mem.mirror("team", "archive", "carol", 4.0)
            return mem.history("team") + mem.history("archive")

        self.assertEqual(run(), run())

    def test_revision_dataclass_is_frozen(self):
        rev = Revision(scope="s", seq=1, op="add", body="b", author="a", at=1.0)
        with self.assertRaises(Exception):
            rev.body = "changed"


if __name__ == "__main__":
    unittest.main()
