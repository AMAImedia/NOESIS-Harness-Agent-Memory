"""Tests for domain_library: per-domain libraries of adopted artifacts."""

import tempfile
import unittest
from pathlib import Path

from noesis_harness.domain_library import (
    DomainLibrary,
    DomainLibraryError,
    DomainLibraryRoot,
    LibraryEntry,
    domain_dir,
    publish_lesson,
    slug,
)
from noesis_harness.lesson_cue import (
    STATUS_ACTIVE,
    STATUS_CANDIDATE,
    CueSelector,
    Lesson,
    LessonJournal,
)


def _lesson(**kw):
    base = dict(
        lesson_id="les_1",
        cue="the ledger totals do not reconcile",
        lesson="reconcile balances before posting totals",
        evidence="task ledger-1",
        domain="accounting",
        confidence=0.8,
        scope="local",
        sensitivity="internal",
        source_ids=("task:ledger-1",),
        provenance_digest="sha256:" + "a" * 64,
    )
    base.update(kw)
    return Lesson(**base)


def _entry(**kw):
    base = dict(
        task_id="ledger-1",
        domain="accounting",
        cue="the ledger totals do not reconcile",
        why="it reconciled in both base runs",
        artifacts=(("report.md", "# Report\nTotal: 85.15\n"),),
        lesson=_lesson(),
        label="agg1",
        source_ids=("task:ledger-1",),
        approved_by="operator:ann",
    )
    base.update(kw)
    return LibraryEntry(**base)


class SlugTests(unittest.TestCase):
    def test_separators_collapse_to_double_underscore(self):
        self.assertEqual(slug("lab/ledger-1"), "lab__ledger-1")
        self.assertEqual(slug("lab\\ledger-1"), "lab__ledger-1")

    def test_unsafe_characters_are_escaped_not_dropped(self):
        self.assertEqual(slug("a b"), "a%20b")
        self.assertNotEqual(slug("a b"), slug("a%b"))

    def test_empty_task_id_is_refused(self):
        with self.assertRaises(DomainLibraryError):
            slug("  ")


class DomainDirTests(unittest.TestCase):
    def test_plain_domain_maps_to_itself(self):
        self.assertEqual(domain_dir("accounting"), "accounting")

    def test_a_domain_label_cannot_walk_out_of_its_folder(self):
        for hostile in ("..", ".", "../secrets", "/etc", "a/../../b"):
            with self.subTest(hostile=hostile):
                resolved = domain_dir(hostile)
                # A single component that is neither "." nor "..": the join
                # root / resolved cannot leave the root.
                self.assertNotIn("/", resolved)
                self.assertNotEqual(resolved, "..")
                self.assertNotEqual(resolved, ".")
                self.assertFalse(set(resolved) == {"."})

    def test_empty_domain_falls_back(self):
        self.assertEqual(domain_dir(""), "unknown")

    def test_two_hostile_labels_cannot_collapse_onto_one_folder(self):
        self.assertNotEqual(domain_dir(".."), domain_dir("."))


class EntryValidationTests(unittest.TestCase):
    def test_requires_task_id_domain_cue_and_approver(self):
        for field in ("task_id", "domain", "cue", "approved_by"):
            with self.subTest(field=field):
                with self.assertRaises(DomainLibraryError):
                    _entry(**{field: "  "})

    def test_artifact_paths_may_not_escape_the_entry(self):
        for bad in ("../other/leak.txt", "/etc/passwd", "a/../../b.md", "~/x.md"):
            with self.subTest(bad=bad):
                with self.assertRaises(DomainLibraryError):
                    _entry(artifacts=((bad, "body"),))

    def test_lesson_domain_must_match_the_entry_domain(self):
        with self.assertRaises(DomainLibraryError):
            _entry(lesson=_lesson(domain="legal"))

    def test_content_digest_tracks_meaning_not_label(self):
        self.assertEqual(_entry().content_digest, _entry(label="agg9").content_digest)
        self.assertNotEqual(_entry().content_digest, _entry(why="a different why").content_digest)
        self.assertNotEqual(
            _entry().content_digest,
            _entry(artifacts=(("report.md", "# Report\nTotal: 20.25\n"),)).content_digest,
        )

    def test_round_trips_through_dict(self):
        entry = _entry()
        self.assertEqual(LibraryEntry.from_dict(entry.to_dict()), entry)


class DomainLibraryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "library"
        self.library = DomainLibrary(str(self.root), "accounting", clock=lambda: 500.0)

    def test_empty_library_has_no_context_dir(self):
        self.assertFalse(self.library.exists())
        self.assertIsNone(self.library.context_dir())
        self.assertEqual(self.library.task_ids(), [])

    def test_add_stores_the_full_content_not_a_summary(self):
        report = self.library.add(_entry())
        self.assertTrue(report.changed)
        self.assertTrue((self.library.entry_dir("ledger-1") / "artifacts" / "report.md").is_file())
        stored = self.library.read("ledger-1")
        self.assertEqual(dict(stored.artifacts)["report.md"], "# Report\nTotal: 85.15\n")

    def test_add_is_idempotent(self):
        self.library.add(_entry())
        again = self.library.add(_entry())
        self.assertFalse(again.changed)
        self.assertEqual(again.reason, "already_present")
        self.assertEqual(len(self.library.task_ids()), 1)

    def test_same_task_different_content_is_replaced_not_duplicated(self):
        self.library.add(_entry())
        self.library.add(_entry(why="a later, better reason"))
        self.assertEqual(len(self.library.task_ids()), 1)
        self.assertEqual(self.library.read("ledger-1").why, "a later, better reason")

    def test_a_mismatched_domain_is_refused_without_writing(self):
        report = self.library.add(_entry(domain="legal", lesson=None))
        self.assertFalse(report.changed)
        self.assertEqual(report.reason, "domain_mismatch")
        self.assertEqual(self.library.task_ids(), [])

    def test_entries_are_returned_in_stream_order(self):
        for n in (3, 1, 2):
            self.library.add(_entry(task_id="ledger-%d" % n))
        # Write order is the stream order, and both views must agree on it.
        self.assertEqual(self.library.task_ids(), ["ledger-3", "ledger-1", "ledger-2"])
        self.assertEqual(
            [e.task_id for e in self.library.entries()], ["ledger-3", "ledger-1", "ledger-2"]
        )

    def test_retain_keeps_only_the_given_prefix(self):
        for n in (1, 2, 3):
            self.library.add(_entry(task_id="ledger-%d" % n))
        reports = self.library.retain(["ledger-1", "ledger-2"])
        self.assertEqual(self.library.task_ids(), ["ledger-1", "ledger-2"])
        self.assertEqual(sum(1 for r in reports if r.changed), 1)

    def test_forget_ignores_unknown_tasks(self):
        self.library.add(_entry())
        reports = self.library.forget(["ledger-1", "never-existed"])
        self.assertEqual(self.library.task_ids(), [])
        self.assertEqual([r.reason for r in reports], ["dropped", "absent"])

    def test_index_lists_every_entry_with_its_cue(self):
        self.library.add(_entry())
        index = self.library.index.read_text(encoding="utf-8")
        self.assertIn("ledger-1", index)
        self.assertIn(_entry().cue, index)
        self.assertIn(_entry().lesson.lesson, index)

    def test_empty_index_says_so(self):
        self.library.rebuild_index()
        self.assertIn("first task in this domain", self.library.index.read_text(encoding="utf-8"))

    def test_context_dir_exists_once_an_entry_lands(self):
        self.library.add(_entry())
        self.assertEqual(self.library.context_dir(), self.library.dir)

    def test_experience_md_records_the_three_part_lesson_and_the_approver(self):
        self.library.add(_entry())
        body = (self.library.entry_dir("ledger-1") / "EXPERIENCE.md").read_text(encoding="utf-8")
        for expected in ("cue", "lesson", "evidence", "confidence", "operator:ann"):
            self.assertIn(expected, body)


class DomainIsolationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = str(Path(self.tmp.name) / "library")

    def test_two_domains_share_a_root_but_not_an_entry(self):
        accounting = DomainLibrary(self.root, "accounting", clock=lambda: 1.0)
        legal = DomainLibrary(self.root, "legal", clock=lambda: 1.0)
        accounting.add(_entry())
        self.assertEqual(len(accounting.task_ids()), 1)
        self.assertEqual(legal.task_ids(), [])
        # Retrieval is by construction: accounting's directory has no path to
        # legal's, and legal's reader has no path to accounting's.
        self.assertFalse(str(accounting.dir) == str(legal.dir))
        self.assertFalse(
            str(legal.dir).startswith(str(accounting.dir) + "/")
        )

    def test_root_reports_each_domain_separately(self):
        accounting = DomainLibrary(self.root, "accounting", clock=lambda: 1.0)
        legal = DomainLibrary(self.root, "legal", clock=lambda: 1.0)
        accounting.add(_entry())
        legal.add(
            LibraryEntry(
                task_id="case-1",
                domain="legal",
                cue="the filing deadline was misread",
                lesson=_lesson(
                    lesson_id="les_legal",
                    domain="legal",
                    cue="the filing deadline was misread",
                    lesson="confirm the filing date against the docket",
                    evidence="task case-1",
                ),
                approved_by="operator:ann",
            )
        )
        root = DomainLibraryRoot(self.root)
        self.assertEqual(root.domains(), ["accounting", "legal"])
        self.assertEqual(root.total_entries(), 2)
        report = root.report()
        self.assertEqual(report["total_entries"], 2)
        self.assertEqual(len(report["per_domain"]["accounting"]["cues"]), 1)


class PublishLessonTests(unittest.TestCase):
    """The seam between the two halves of NOESIS."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.journal = LessonJournal(str(base / "lessons.jsonl"), clock=lambda: 900.0)
        self.library = DomainLibrary(str(base / "library"), "accounting", clock=lambda: 900.0)

    def test_a_library_entry_becomes_recallable_once_published_and_promoted(self):
        self.library.add(_entry())
        published = publish_lesson(self.journal, self.library.read("ledger-1"), actor="operator:ann")
        self.assertTrue(published)

        selector = CueSelector(min_score=0.0)
        context = "the ledger totals must reconcile"
        # Published but not promoted: still invisible, by design.
        self.assertEqual(selector.select(self.journal.lessons(), context).selected, ())
        self.assertEqual(len(self.journal.replay()), 1)
        self.assertEqual(self.journal.current()["les_1"].status, STATUS_CANDIDATE)

        self.journal.promote("les_1", actor="operator:ann")
        found = selector.select(self.journal.lessons(), context).selected
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].lesson.lesson_id, "les_1")
        self.assertEqual(found[0].lesson.status, STATUS_ACTIVE)

    def test_publishing_twice_is_idempotent(self):
        self.library.add(_entry())
        first = publish_lesson(self.journal, self.library.read("ledger-1"), actor="operator:ann")
        second = publish_lesson(self.journal, self.library.read("ledger-1"), actor="operator:ann")
        self.assertEqual(first, second)
        self.assertEqual(len(self.journal.replay()), 1)

    def test_an_entry_without_a_lesson_publishes_nothing(self):
        self.library.add(_entry(lesson=None))
        self.assertIsNone(publish_lesson(self.journal, self.library.read("ledger-1"), actor="op"))
        self.assertEqual(self.journal.replay(), [])


__all__ = [
    "DomainDirTests",
    "DomainIsolationTests",
    "DomainLibraryTests",
    "EntryValidationTests",
    "PublishLessonTests",
    "SlugTests",
]