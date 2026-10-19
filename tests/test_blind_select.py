"""Tests for blind_select: anonymised choice and the before/after contrast."""

import tempfile
import unittest
from pathlib import Path

from noesis_harness.blind_select import (
    BlindSelectError,
    Candidate,
    Selection,
    anonym_id,
    assign_ids,
    build_contrast,
    parse_choice,
    render_pool,
    reverse_ids,
    run_selection,
    trivial_selection,
    write_candidates,
)


def _cand(label, body="Total: 85.15\n", files=()):
    return Candidate(label=label, body=body, files=tuple(files))


def _chooser(anon):
    def choose(task):
        return anon, "<why>it reconciled in both checks</why>"

    return choose


class AnonymIdTests(unittest.TestCase):
    def test_ids_walk_a_to_z_then_onwards(self):
        self.assertEqual(anonym_id(0), "A")
        self.assertEqual(anonym_id(25), "Z")
        self.assertEqual(anonym_id(26), "AA")
        self.assertEqual(anonym_id(27), "AB")
        self.assertEqual(anonym_id(701), "ZZ")
        self.assertEqual(anonym_id(702), "AAA")


class AssignIdsTests(unittest.TestCase):
    def test_mapping_is_a_bijection(self):
        labels = ["c1", "c2", "agg1", "base", "dom1"]
        id_map = assign_ids(labels)
        self.assertEqual(len(id_map), len(labels))
        self.assertEqual(set(id_map.values()), set(labels))
        self.assertEqual(len(set(id_map)), len(id_map))

    def test_same_labels_and_salt_give_the_same_mapping(self):
        labels = ["c1", "c2", "agg1"]
        self.assertEqual(assign_ids(labels, salt="s"), assign_ids(list(reversed(labels)), salt="s"))

    def test_a_different_salt_reorders(self):
        labels = ["c%d" % i for i in range(12)]
        self.assertNotEqual(assign_ids(labels, salt="a"), assign_ids(labels, salt="b"))

    def test_original_position_carries_no_information(self):
        # Two different candidate sets that share a label must not place that
        # label at the same id just because it was first on input.
        first = assign_ids(["base", "c1"], salt="s")
        second = assign_ids(["c1", "base"], salt="s")
        self.assertEqual(first, second)

    def test_duplicate_labels_and_empty_pools_are_refused(self):
        with self.assertRaises(BlindSelectError):
            assign_ids(["c1", "c1"])
        with self.assertRaises(BlindSelectError):
            assign_ids([])

    def test_reverse_is_the_inverse(self):
        id_map = assign_ids(["c1", "c2", "c3"])
        self.assertEqual(reverse_ids(id_map), {label: anon for anon, label in id_map.items()})


class CandidateTests(unittest.TestCase):
    def test_empty_body_is_not_an_answer(self):
        self.assertFalse(_cand("c1", "   \n").is_answer)
        self.assertTrue(_cand("c1").is_answer)

    def test_label_is_required(self):
        with self.assertRaises(BlindSelectError):
            Candidate(label="", body="x")

    def test_render_pool_drops_non_answers_with_a_reason(self):
        kept, dropped = render_pool([_cand("c1"), _cand("c2", "  "), _cand("c3")])
        self.assertEqual([c.label for c in kept], ["c1", "c3"])
        self.assertEqual(dropped, [("c2", "no_artifact")])


class ChoiceParsingTests(unittest.TestCase):
    def test_parses_choice_and_why(self):
        anon, why = parse_choice("```choice\nB\n```\n<why>it balanced</why>")
        self.assertEqual(anon, "B")
        self.assertEqual(why, "it balanced")

    def test_why_is_optional(self):
        self.assertEqual(parse_choice("```choice\nA\n```"), ("A", ""))

    def test_a_reply_without_a_choice_block_is_a_failure_not_a_result(self):
        with self.assertRaises(BlindSelectError):
            parse_choice("I think B is best but I will not say so formally")


class ContrastTests(unittest.TestCase):
    def test_reports_what_the_chosen_artifact_changed(self):
        base = _cand("base", "Total: 20.25\n", files=(("report.md", "old\n"),))
        chosen = _cand("agg1", "Total: 85.15\n", files=(("report.md", "new\n"), ("extra.md", "x\n"),))
        contrast = build_contrast(chosen, base)
        self.assertTrue(contrast.changed)
        self.assertEqual(contrast.added, ("extra.md",))
        self.assertEqual(contrast.removed, ())
        self.assertEqual(contrast.modified, ())
        self.assertEqual(contrast.char_delta, len("Total: 85.15\n") - len("Total: 20.25\n"))
        self.assertIn("-Total: 20.25", contrast.diff)
        self.assertIn("+Total: 85.15", contrast.diff)

    def test_identical_artifacts_show_no_change(self):
        same = _cand("agg1", "Total: 20.25\n")
        contrast = build_contrast(same, _cand("base", "Total: 20.25\n"))
        self.assertFalse(contrast.changed)
        self.assertEqual(contrast.diff, "")

    def test_no_reference_means_no_baseline_not_everything_is_new(self):
        contrast = build_contrast(_cand("agg1", "Total: 85.15\n"), None)
        self.assertEqual(contrast.reference_label, "")
        self.assertEqual(contrast.added, ())

    def test_a_removed_artifact_is_reported(self):
        contrast = build_contrast(_cand("agg1", files=()), _cand("base", files=(("old.md", "x\n"),)))
        self.assertEqual(contrast.removed, ("old.md",))

    def test_diff_digest_is_stable_and_content_bound(self):
        a = build_contrast(_cand("x", "b\n"), _cand("base", "a\n"))
        b = build_contrast(_cand("x", "b\n"), _cand("base", "a\n"))
        c = build_contrast(_cand("x", "c\n"), _cand("base", "a\n"))
        self.assertEqual(a.to_dict()["diff_sha256"], b.to_dict()["diff_sha256"])
        self.assertNotEqual(a.to_dict()["diff_sha256"], c.to_dict()["diff_sha256"])


class RunSelectionTests(unittest.TestCase):
    def setUp(self):
        self.candidates = [_cand("base", "Total: 20.25\n"), _cand("agg1"), _cand("agg2")]

    def test_a_chooser_picks_and_the_choice_is_recorded(self):
        task_id = "t1"
        id_map = assign_ids(["base", "agg1", "agg2"], salt="noesis.blind-select.v1|" + task_id)
        target = next(anon for anon, label in id_map.items() if label == "agg1")

        selection = run_selection(
            task_id, self.candidates, chooser=_chooser(target), salt="noesis.blind-select.v1"
        )
        self.assertTrue(selection.ok)
        self.assertTrue(selection.is_adopted)
        self.assertEqual(selection.chosen_label, "agg1")
        self.assertEqual(selection.chosen_id, target)
        self.assertIn("reconciled", selection.why)
        self.assertEqual(selection.id_map[target], "agg1")

    def test_an_unknown_id_is_a_failure_not_a_crash(self):
        selection = run_selection("t1", self.candidates, chooser=_chooser("ZZ"), salt="s")
        self.assertTrue(selection.ok)
        self.assertFalse(selection.is_adopted)
        self.assertTrue(selection.fallback)
        self.assertIn("not one of", selection.error)

    def test_a_raising_chooser_falls_back_rather_than_propagating(self):
        def boom(_task):
            raise RuntimeError("model timeout")

        selection = run_selection("t1", self.candidates, chooser=boom, salt="s")
        self.assertTrue(selection.ok)
        self.assertFalse(selection.is_adopted)
        self.assertIn("RuntimeError", selection.error)
        self.assertEqual(selection.chosen_label, "base")

    def test_the_fallback_prefers_the_base_label(self):
        selection = run_selection("t1", self.candidates, chooser=_chooser("ZZ"), salt="s")
        self.assertEqual(selection.chosen_label, "base")

    def test_without_a_chooser_the_result_is_flagged_as_a_fallback(self):
        selection = run_selection("t1", self.candidates, salt="s")
        self.assertTrue(selection.ok)
        self.assertFalse(selection.is_adopted)
        self.assertTrue(selection.fallback)

    def test_stored_reasoning_is_de_anonymised(self):
        # A pool big enough that both "A" and "AA" are real ids: the longest is
        # rewritten first, so AA is not corrupted by the A that starts it.
        candidates = [_cand("c%d" % n, "Total: %d.00\n" % n) for n in range(28)]
        selection = run_selection("t1", candidates, chooser=_chooser("AA"), salt="s")
        self.assertIn("AA", selection.id_map)
        selection = run_selection(
            "t1",
            candidates,
            chooser=lambda _t: ("AA", "<why>AA balanced and A did not</why>"),
            salt="s",
        )
        chosen = selection.id_map["AA"]
        other = selection.id_map["A"]
        self.assertNotIn("AA", selection.why)
        self.assertIn(chosen, selection.why)
        self.assertIn(other, selection.why)

    def test_a_pool_with_no_answers_is_an_honest_refusal(self):
        selection = run_selection("t1", [_cand("c1", "  "), _cand("c2", "")], salt="s")
        self.assertFalse(selection.ok)
        self.assertFalse(selection.is_adopted)
        self.assertEqual(selection.error, "no_candidate_produced_an_artifact")
        self.assertEqual(len(selection.dropped), 2)

    def test_caller_errors_still_raise(self):
        with self.assertRaises(BlindSelectError):
            run_selection("", self.candidates, salt="s")
        with self.assertRaises(BlindSelectError):
            run_selection("t1", [], salt="s")

    def test_the_same_pool_and_salt_give_the_same_mapping_twice(self):
        a = run_selection("t1", self.candidates, chooser=_chooser("A"), salt="s")
        b = run_selection("t1", self.candidates, chooser=_chooser("A"), salt="s")
        self.assertEqual(a.id_map, b.id_map)
        self.assertEqual(a.to_dict()["digest"], b.to_dict()["digest"])

    def test_a_different_task_salt_reorders_the_pool(self):
        a = run_selection("t1", self.candidates, chooser=_chooser("A"), salt="s")
        b = run_selection("t2", self.candidates, chooser=_chooser("A"), salt="s")
        self.assertNotEqual(a.id_map, b.id_map)

    def test_the_contrast_is_built_against_the_reference(self):
        reference = _cand("base", "Total: 20.25\n")
        selection = run_selection(
            "t1", self.candidates, chooser=_chooser("A"), salt="s", reference=reference
        )
        self.assertIsNotNone(selection.contrast)
        self.assertEqual(selection.contrast.reference_label, "base")

    def test_round_trips_through_dict(self):
        selection = run_selection("t1", self.candidates, chooser=_chooser("A"), salt="s")
        restored = Selection.from_dict(selection.to_dict())
        self.assertEqual(restored.chosen_label, selection.chosen_label)
        self.assertEqual(restored.id_map, selection.id_map)
        self.assertEqual(restored.is_adopted, selection.is_adopted)


class TrivialSelectionTests(unittest.TestCase):
    def test_a_single_candidate_is_adopted_without_a_chooser(self):
        selection = trivial_selection("t1", _cand("c1"))
        self.assertTrue(selection.ok)
        self.assertTrue(selection.trivial)
        self.assertFalse(selection.is_adopted)
        self.assertEqual(selection.chosen_label, "c1")

    def test_a_candidate_with_no_artifact_is_an_honest_refusal(self):
        selection = trivial_selection("t1", _cand("c1", "   "))
        self.assertFalse(selection.ok)
        self.assertEqual(selection.error, "candidate_produced_no_artifact")


class WriteCandidatesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_writes_one_untrimmed_file_per_candidate_plus_the_id_map(self):
        candidates = [_cand("base", "Total: 20.25\n", files=(("report.md", "old\n"),)), _cand("agg1")]
        selection = run_selection("t1", candidates, chooser=_chooser("A"), salt="s")
        from noesis_harness.blind_select import SelectionTask

        task = SelectionTask(task_id="t1", prompt="", id_map=selection.id_map)
        written = write_candidates(self.root / "pool", selection, candidates, task)
        for anon in selection.id_map:
            self.assertTrue((self.root / "pool" / ("%s.md" % anon)).is_file())
            self.assertIn("COMPLETE", (self.root / "pool" / ("%s.md" % anon)).read_text())
        self.assertTrue((self.root / "pool" / "id_map.json").is_file())
        self.assertTrue((self.root / "pool" / "selection.json").is_file())
        self.assertGreaterEqual(written, len(selection.id_map))

    def test_working_dir_renders_the_whole_pool_during_a_run(self):
        candidates = [_cand("base"), _cand("agg1")]
        run_selection("t1", candidates, chooser=_chooser("A"), salt="s", work_dir=str(self.root / "work"))
        self.assertTrue((self.root / "work" / "t1" / "selection.json").is_file())


__all__ = [
    "AnonymIdTests",
    "AssignIdsTests",
    "CandidateTests",
    "ChoiceParsingTests",
    "ContrastTests",
    "RunSelectionTests",
    "TrivialSelectionTests",
    "WriteCandidatesTests",
]