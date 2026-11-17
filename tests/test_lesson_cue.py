"""Tests for lesson_cue: cue-addressed lessons and the append-only journal."""

import tempfile
import unittest
from pathlib import Path

from noesis_harness.lesson_cue import (
    STATUS_ACTIVE,
    STATUS_CANDIDATE,
    STATUS_RETIRED,
    STATUS_SUPERSEDED,
    CueSelector,
    Lesson,
    LessonCueError,
    LessonJournal,
    LessonJournalConflict,
    build_lesson,
    extract_lesson,
    match_tier,
    normalize_domain,
    meaningful_tokens,
)


def _lesson(**kw):
    base = dict(
        lesson_id="les_1",
        cue="the ledger totals do not reconcile",
        lesson="reconcile opening and closing balances before posting totals",
        evidence="task ledger-1, totals differed by 60.00 across two runs",
        domain="accounting",
        confidence=0.8,
        scope="local",
        sensitivity="internal",
        source_ids=("task:ledger-1",),
        provenance_digest="sha256:" + "a" * 64,
    )
    base.update(kw)
    return Lesson(**base)


class LessonValidationTests(unittest.TestCase):
    def test_requires_cue_lesson_evidence_and_domain(self):
        for field in ("cue", "lesson", "evidence", "domain"):
            with self.subTest(field=field):
                with self.assertRaises(LessonCueError):
                    _lesson(**{field: "  "})

    def test_requires_id_scope_and_known_sensitivity(self):
        with self.assertRaises(LessonCueError):
            _lesson(lesson_id="")
        with self.assertRaises(LessonCueError):
            _lesson(scope="")
        with self.assertRaises(LessonCueError):
            _lesson(sensitivity="top-secret")

    def test_confidence_must_be_bounded(self):
        for bad in (-0.1, 1.1, "high", True):
            with self.subTest(bad=bad):
                with self.assertRaises(LessonCueError):
                    _lesson(confidence=bad)

    def test_fingerprint_is_content_addressed_not_identity(self):
        self.assertEqual(_lesson().fingerprint, _lesson().fingerprint)
        self.assertEqual(
            _lesson().fingerprint,
            _lesson(lesson_id="les_other").fingerprint,
        )
        self.assertNotEqual(
            _lesson().fingerprint,
            _lesson(cue="the totals do not reconcile").fingerprint,
        )
        self.assertNotEqual(
            _lesson().fingerprint,
            _lesson(confidence=0.79).fingerprint,
        )

    def test_round_trips_through_dict(self):
        lesson = _lesson()
        self.assertEqual(Lesson.from_dict(lesson.to_dict()), lesson)


class CueMatchingTests(unittest.TestCase):
    def test_exact_tier_when_every_cue_token_present(self):
        tier, reason = match_tier(meaningful_tokens("the ledger totals must reconcile"), _lesson())
        self.assertEqual(tier, "exact")
        self.assertEqual(reason["reason"], "all_cue_tokens_present")

    def test_stopwords_do_not_block_an_exact_match(self):
        # The cue is prose; "the", "do" and "not" must not have to reappear in
        # the future context for the cue to match itself.
        self.assertEqual(
            meaningful_tokens("the ledger totals do not reconcile"),
            meaningful_tokens("ledger totals reconcile"),
        )

    def test_prefix_tier_when_a_query_token_extends_a_cue_token(self):
        lesson = _lesson(cue="reconcile ledger")
        tier, _reason = match_tier(meaningful_tokens("reconciling ledgers"), lesson)
        self.assertEqual(tier, "prefix")

    def test_fuzzy_tier_within_edit_distance(self):
        lesson = _lesson(cue="reconcilation")
        tier, reason = match_tier(meaningful_tokens("reconciliation"), lesson)
        self.assertEqual(tier, "fuzzy")
        self.assertEqual(reason["distance"], 1)

    def test_an_identical_token_is_never_reported_as_fuzzy(self):
        # Distance 0 is a shared token, not a near miss. Reporting it as
        # fuzzy would make the tier reachable by an exact match and hide the
        # real state of the cue.
        lesson = _lesson(cue="reconciliation required")
        tier, reason = match_tier(meaningful_tokens("reconciliation matters"), lesson)
        self.assertEqual(tier, "overlap")
        self.assertEqual(reason["reason"], "partial_token_overlap")
        self.assertNotEqual(tier, "fuzzy")

    def test_unrelated_context_does_not_match(self):
        tier, _reason = match_tier(meaningful_tokens("banana smoothie"), _lesson())
        self.assertEqual(tier, "none")

    def test_empty_context_never_matches(self):
        self.assertEqual(match_tier([], _lesson())[0], "none")
        self.assertEqual(match_tier(["the", "of"], _lesson())[0], "none")

    def test_score_is_bounded_and_rises_with_confidence(self):
        context = "the ledger totals must reconcile"
        low = Lesson(**{**_lesson().__dict__, "confidence": 0.1})
        high = Lesson(**{**_lesson().__dict__, "confidence": 0.9})
        selector = CueSelector(min_score=0.0, require_active=False)
        score_low = selector.select([low], context).selected[0].score
        score_high = selector.select([high], context).selected[0].score
        self.assertTrue(0.0 <= score_low < score_high <= 1.0)

    def test_score_is_deterministic(self):
        context = "the ledger totals must reconcile"
        selector = CueSelector(min_score=0.0, require_active=False)
        first = selector.select([_lesson()], context).selected[0].score
        second = selector.select([_lesson()], context).selected[0].score
        self.assertEqual(first, second)


class CueSelectorTests(unittest.TestCase):
    def setUp(self):
        self.matched = Lesson(
            **{
                **_lesson().__dict__,
                "lesson_id": "les_match",
                "status": STATUS_ACTIVE,
            }
        )
        self.unrelated = Lesson(
            **{
                **_lesson().__dict__,
                "lesson_id": "les_other",
                "cue": "the deck needs a logo",
                "lesson": "use the brand mark on the title slide",
                "evidence": "task deck-9, reviewer flagged the missing mark",
                "domain": "presentations",
            }
        )

    def test_only_active_lessons_are_recalled_by_default(self):
        selector = CueSelector(min_score=0.0)
        decision = selector.select([self.matched, self.unrelated], "the ledger totals must reconcile")
        self.assertEqual([m.lesson.lesson_id for m in decision.selected], ["les_match"])
        self.assertIn(("les_other", "not_active"), decision.excluded)

    def test_candidate_mode_can_be_requested_explicitly(self):
        selector = CueSelector(min_score=0.0, require_active=False)
        decision = selector.select([self.matched], "the ledger totals must reconcile")
        self.assertEqual(decision.selected[0].lesson.lesson_id, "les_match")

    def test_scope_and_sensitivity_are_deny_by_default(self):
        selector = CueSelector(min_score=0.0)
        decision = selector.select(
            [Lesson(**{**self.matched.__dict__, "scope": "team"})],
            "the ledger totals must reconcile",
        )
        self.assertEqual(decision.selected, ())
        self.assertEqual(decision.excluded[0][1], "scope_denied")

        selector = CueSelector(min_score=0.0)
        decision = selector.select(
            [Lesson(**{**self.matched.__dict__, "sensitivity": "restricted"})],
            "the ledger totals must reconcile",
        )
        self.assertEqual(decision.excluded[0][1], "sensitivity_denied")

    def test_domain_filter_narrows_the_pool(self):
        selector = CueSelector(min_score=0.0, allowed_domains=["legal"])
        decision = selector.select([self.matched], "the ledger totals must reconcile")
        self.assertEqual(decision.excluded[0][1], "domain_denied")

    def test_retired_lessons_are_never_offered(self):
        selector = CueSelector(min_score=0.0, require_active=False)
        decision = selector.select(
            [Lesson(**{**self.matched.__dict__, "status": STATUS_RETIRED})],
            "the ledger totals must reconcile",
        )
        self.assertEqual(decision.excluded[0][1], "retired")

    def test_duplicate_content_is_reported_not_repeated(self):
        selector = CueSelector(min_score=0.0)
        twin = Lesson(**{**self.matched.__dict__, "lesson_id": "les_twin"})
        decision = selector.select([self.matched, twin], "the ledger totals must reconcile")
        self.assertEqual(len(decision.selected), 1)
        self.assertTrue(any(reason.startswith("duplicate_of:") for _id, reason in decision.excluded))

    def test_char_budget_is_enforced_and_reported(self):
        selector = CueSelector(min_score=0.0, max_chars=10)
        decision = selector.select([self.matched], "the ledger totals must reconcile")
        self.assertEqual(decision.selected, ())
        self.assertEqual(decision.excluded[0][1], "char_budget")

    def test_ranking_is_a_total_order_and_reproducible(self):
        selector = CueSelector(min_score=0.0)
        a = Lesson(**{**self.matched.__dict__, "lesson_id": "les_b", "confidence": 0.6})
        b = Lesson(**{**self.matched.__dict__, "lesson_id": "les_a", "confidence": 0.9})
        first = [m.lesson.lesson_id for m in selector.select([a, b], "the ledger totals must reconcile").selected]
        second = [m.lesson.lesson_id for m in selector.select([b, a], "the ledger totals must reconcile").selected]
        self.assertEqual(first, second)
        self.assertEqual(first[0], "les_a")

    def test_empty_context_returns_an_empty_decision(self):
        decision = CueSelector().select([self.matched], "   ")
        self.assertEqual(decision.selected, ())
        self.assertEqual(decision.used_chars, 0)

    def test_prompt_rendering_carries_cue_lesson_evidence(self):
        selector = CueSelector(min_score=0.0)
        decision = selector.select([self.matched], "the ledger totals must reconcile")
        rendered = "\n".join(decision.as_prompt_lines())
        self.assertIn(self.matched.cue, rendered)
        self.assertIn(self.matched.lesson, rendered)
        self.assertIn(self.matched.evidence, rendered)


class LessonJournalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = str(Path(self.tmp.name) / "lessons.jsonl")
        self.journal = LessonJournal(self.path, clock=lambda: 1000.0)

    def test_recording_is_idempotent(self):
        first = self.journal.record(_lesson(), "record")
        second = self.journal.record(_lesson(), "record")
        self.assertEqual(first, second)
        self.assertEqual(len(self.journal.replay()), 1)

    def test_same_id_different_content_is_a_conflict_not_an_overwrite(self):
        self.journal.record(_lesson(), "record")
        with self.assertRaises(LessonJournalConflict):
            self.journal.record(_lesson(lesson="a different lesson"), "record")
        self.assertEqual(len(self.journal.replay()), 1)

    def test_promotion_requires_a_named_actor(self):
        self.journal.record(_lesson(), "record")
        with self.assertRaises(LessonCueError):
            self.journal.promote("les_1", actor="")
        self.assertEqual(self.journal.current()["les_1"].status, STATUS_CANDIDATE)

    def test_promotion_is_explicit_and_idempotent(self):
        self.journal.record(_lesson(), "record")
        promoted = self.journal.promote("les_1", actor="operator:ann", reason="reproduced twice")
        self.assertEqual(promoted.status, STATUS_ACTIVE)
        again = self.journal.promote("les_1", actor="operator:ann")
        self.assertEqual(again.status, STATUS_ACTIVE)
        self.assertEqual(sum(1 for r in self.journal.replay() if r.action == "promote"), 1)

    def test_a_candidate_lesson_is_not_recallable_until_promoted(self):
        selector = CueSelector(min_score=0.0)
        self.journal.record(_lesson(), "record")
        lessons = self.journal.lessons()
        self.assertEqual(selector.select(lessons, "the ledger totals must reconcile").selected, ())
        self.journal.promote("les_1", actor="operator:ann")
        self.assertEqual(
            len(selector.select(self.journal.lessons(), "the ledger totals must reconcile").selected), 1
        )

    def test_supersede_appends_and_keeps_history(self):
        self.journal.record(_lesson(), "record")
        self.journal.promote("les_1", actor="operator:ann")
        self.journal.supersede(
            "les_1",
            _lesson(lesson_id="les_2", lesson="close the period before posting"),
            actor="operator:ann",
            reason="refined after the second review",
        )
        state = self.journal.current()
        self.assertEqual(state["les_1"].status, STATUS_SUPERSEDED)
        self.assertEqual(state["les_2"].status, STATUS_ACTIVE)
        self.assertEqual(state["les_2"].supersedes, "les_1")
        self.assertGreaterEqual(len(self.journal.replay()), 4)

    def test_retire_stops_offering_without_deleting(self):
        self.journal.record(_lesson(), "record")
        self.journal.promote("les_1", actor="operator:ann")
        self.journal.retire("les_1", actor="operator:ann", reason="superseded by policy")
        self.assertEqual(self.journal.current()["les_1"].status, STATUS_RETIRED)
        self.assertTrue(self.path and Path(self.path).exists())
        self.assertGreaterEqual(len(self.journal.replay()), 3)

    def test_truncated_tail_is_skipped_not_fatal(self):
        self.journal.record(_lesson(), "record")
        with open(self.path, "a", encoding="utf-8") as handle:
            handle.write('{"entry_id": "broken"')
        self.assertEqual(len(self.journal.replay()), 1)

    def test_summary_reports_counts_and_a_digest(self):
        self.journal.record(_lesson(), "record")
        self.journal.promote("les_1", actor="operator:ann")
        summary = self.journal.summary()
        self.assertEqual(summary["schema_version"], "noesis.lesson-cue.v1")
        self.assertEqual(summary["total_records"], 2)
        self.assertEqual(summary["counts"], {"record": 1, "promote": 1})
        self.assertTrue(summary["log_digest"].startswith("sha256:"))

    def test_filtering_by_domain_is_case_and_space_insensitive(self):
        self.journal.record(_lesson(), "record")
        self.assertEqual(len(self.journal.lessons(domain="Accounting")), 1)
        self.assertEqual(len(self.journal.lessons(domain="legal")), 0)


class ExtractionTests(unittest.TestCase):
    def test_no_extractor_means_no_lesson(self):
        self.assertIsNone(extract_lesson({"task_id": "t1"}, None))

    def test_extractor_must_return_all_three_parts(self):
        for fields in (
            {"cue": "a", "lesson": "b"},
            {"cue": "a", "evidence": "c"},
            {"lesson": "b", "evidence": "c"},
        ):
            with self.subTest(fields=sorted(fields)):
                self.assertIsNone(extract_lesson({"task_id": "t1"}, lambda _t, f=fields: f))

    def test_a_complete_extraction_becomes_a_candidate_not_an_active_lesson(self):
        fields = {"cue": "a", "lesson": "b", "evidence": "task t1", "domain": "ops"}
        lesson = extract_lesson({"task_id": "t1", "source_ids": ("task:t1",)}, lambda _t: fields)
        self.assertIsNotNone(lesson)
        self.assertEqual(lesson.status, STATUS_CANDIDATE)
        self.assertEqual(lesson.source_ids, ("task:t1",))


class NormalizeDomainTests(unittest.TestCase):
    def test_whitespace_collapses_and_case_folds(self):
        self.assertEqual(normalize_domain("  Accounting   Reports "), "accounting reports")

    def test_empty_normalises_to_empty(self):
        self.assertEqual(normalize_domain(None), "")


__all__ = [
    "CueMatchingTests",
    "CueSelectorTests",
    "ExtractionTests",
    "LessonJournalTests",
    "LessonValidationTests",
    "NormalizeDomainTests",
]