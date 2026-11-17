"""Tests for forget: erasure that can be proven, and honest residue reporting."""

import os
import tempfile
import unittest
from pathlib import Path

from noesis_harness.forget import (
    ERASED_MARKER,
    REASON_LEGAL_REQUEST,
    REASON_USER_REQUEST,
    ForgetError,
    ForgetReceipt,
    Forger,
    Predicate,
    ReceiptLog,
    build_predicate,
    content_digest,
    normalize,
)
from noesis_harness.graph import MemoryGraph
from noesis_harness.lesson_cue import Lesson, LessonJournal
from noesis_harness.memory import Memory

SECRET = "sk-SECRET42"


def _memory_and_graph():
    directory = tempfile.TemporaryDirectory()
    memory = Memory(os.path.join(directory.name, "m.db"))
    graph = MemoryGraph(os.path.join(directory.name, "g.db"))
    return directory, memory, graph


class NormalizeTests(unittest.TestCase):
    def test_case_punctuation_and_diacritics_collapse(self):
        self.assertEqual(normalize("Grüße, WELT!"), normalize("grusse welt"))

    def test_transliterated_characters_are_folded(self):
        # NFKD leaves the German sharp s intact, so without an explicit fold
        # "Grüße" and "gruesse" would be two different secrets.
        self.assertEqual(normalize("Straße"), normalize("strasse"))
        self.assertEqual(normalize("Æther"), normalize("aether"))

    def test_digest_is_stable_across_formatting(self):
        self.assertEqual(content_digest("Key: sk-SECRET42"), content_digest("key sk secret42"))

    def test_digest_does_not_reveal_the_content(self):
        digest = content_digest("sk-SECRET42")
        self.assertTrue(digest.startswith("sha256:"))
        self.assertNotIn("SECRET", digest)


class PredicateDisclosureTests(unittest.TestCase):
    """A receipt is publishable. That means it must not carry the secret."""

    def test_a_built_predicate_holds_no_readable_token(self):
        predicate = build_predicate(SECRET)
        for token in predicate.tokens:
            self.assertFalse(token.startswith("secret"), token)
        self.assertEqual(predicate.label, "")

    def test_a_revealed_predicate_still_matches(self):
        # Digesting the tokens must not break matching.
        plain = build_predicate(SECRET)
        revealed = build_predicate(SECRET, reveal_tokens=True)
        for text in ("The API key is " + SECRET, "key is SK SECRET42"):
            self.assertTrue(plain.matches(text))
            self.assertTrue(revealed.matches(text))

    def test_revealed_predicates_are_for_non_sensitive_selectors(self):
        revealed = build_predicate("session s1", reveal_tokens=True)
        self.assertEqual(revealed.label, "session s1")
        self.assertIn("s1", revealed.tokens)

    def test_reveal_reads_back_what_a_revealed_selector_covers(self):
        revealed = build_predicate(SECRET, reveal_tokens=True)
        self.assertEqual(revealed.reveal("The API key is " + SECRET), "secret42, sk")


class PredicateTests(unittest.TestCase):
    def test_a_phrase_becomes_tokens(self):
        predicate = build_predicate("sk-SECRET42", reveal_tokens=True)
        self.assertIn("secret42", predicate.tokens)
        self.assertTrue(predicate.tokens)

    def test_matching_ignores_formatting_differences(self):
        predicate = build_predicate(SECRET)
        self.assertTrue(predicate.matches("The API key is sk-SECRET42"))
        self.assertTrue(predicate.matches("the api key is SK SECRET42"))
        self.assertFalse(predicate.matches("Alice lives in Berlin"))

    def test_require_all_narrows_the_sweep(self):
        narrow = build_predicate("api key secret42", require_all=True)
        self.assertTrue(narrow.matches("api key sk-SECRET42 here"))
        self.assertFalse(narrow.matches("sk-SECRET42 alone"))

    def test_scope_and_kind_narrow_the_sweep(self):
        predicate = build_predicate(SECRET, scope="s1", kind="semantic")
        self.assertTrue(predicate.matches(SECRET, scope="s1", kind="semantic"))
        self.assertFalse(predicate.matches(SECRET, scope="s2", kind="semantic"))
        self.assertFalse(predicate.matches(SECRET, scope="s1", kind="procedural"))

    def test_an_empty_predicate_is_refused(self):
        for bad in ("", "   ", "!!! ???"):
            with self.subTest(bad=bad):
                with self.assertRaises(ForgetError):
                    build_predicate(bad)

    def test_fingerprint_is_content_addressed(self):
        self.assertEqual(build_predicate(SECRET).fingerprint(), build_predicate(SECRET).fingerprint())
        self.assertNotEqual(build_predicate(SECRET).fingerprint(), build_predicate("other").fingerprint())


class AttributionTests(unittest.TestCase):
    def setUp(self):
        self.directory, self.memory, self.graph = _memory_and_graph()
        self.addCleanup(self.directory.cleanup)
        self.forger = Forger(
            self.memory,
            graph=self.graph,
            receipt_path=os.path.join(self.directory.name, "r.jsonl"),
        )

    def test_erasure_without_an_actor_is_refused(self):
        self.memory.save("key " + SECRET, "semantic")
        with self.assertRaises(ForgetError):
            self.forger.forget(build_predicate(SECRET), actor="   ")

    def test_an_unknown_reason_is_refused(self):
        self.memory.save("key " + SECRET, "semantic")
        with self.assertRaises(ForgetError):
            self.forger.forget(build_predicate(SECRET), actor="ann", reason="because")

    def test_a_legal_request_is_a_valid_reason(self):
        self.memory.save("key " + SECRET, "semantic")
        receipt = self.forger.forget(
            build_predicate(SECRET), actor="officer:1", reason=REASON_LEGAL_REQUEST
        )
        self.assertEqual(receipt.reason, REASON_LEGAL_REQUEST)


class ErasureTests(unittest.TestCase):
    def setUp(self):
        self.directory, self.memory, self.graph = _memory_and_graph()
        self.addCleanup(self.directory.cleanup)
        self.memory.save("Alice lives in Berlin", "semantic")
        self.memory.save("The API key is " + SECRET, "semantic")
        self.memory.observe("s1", "chat", "my key is " + SECRET)
        self.memory.summarize("s1", "session about key " + SECRET)
        self.graph.link("Alice", "uses_key", SECRET)
        self.graph.link("Alice", "lives_in", "Berlin")
        self.forger = Forger(
            self.memory,
            graph=self.graph,
            receipt_path=os.path.join(self.directory.name, "r.jsonl"),
        )

    def test_every_store_is_reached(self):
        receipt = self.forger.forget(build_predicate(SECRET), actor="ann", request_id="r1")
        self.assertTrue(receipt.complete)
        self.assertEqual(receipt.uncovered, ())
        covered = {s.store: s.removed for s in receipt.stores}
        self.assertEqual(covered["memory"], 1)
        self.assertEqual(covered["observations"], 1)
        self.assertEqual(covered["summaries"], 1)
        self.assertEqual(covered["graph"], 1)
        self.assertEqual(receipt.removed, 4)

    def test_the_content_is_genuinely_gone_from_recall(self):
        self.forger.forget(build_predicate(SECRET), actor="ann", request_id="r1")
        self.assertEqual([h for h in self.memory.recall("SECRET", limit=20) if SECRET.split("-")[-1] in h["fact"]], [])

    def test_unrelated_memories_survive(self):
        self.forger.forget(build_predicate(SECRET), actor="ann", request_id="r1")
        facts = [h["fact"] for h in self.memory.recall("Berlin", limit=10)]
        self.assertIn("Alice lives in Berlin", facts)

    def test_the_native_read_path_is_what_gets_checked(self):
        receipt = self.forger.forget(build_predicate(SECRET), actor="ann", request_id="r1")
        report = self.forger.residue(receipt.request_id)
        self.assertEqual(report.native_hits, [])
        self.assertEqual(report.residual_hits, [])
        self.assertTrue(report.clean)

    def test_erasure_is_idempotent_by_request_id(self):
        first = self.forger.forget(build_predicate(SECRET), actor="ann", request_id="same")
        second = self.forger.forget(build_predicate(SECRET), actor="ann", request_id="same")
        self.assertEqual(first.receipt_id, second.receipt_id)
        self.assertEqual(len(self.forger.log.receipts()), 1)

    def test_the_same_request_without_an_id_is_still_one_erasure(self):
        first = self.forger.forget(build_predicate(SECRET), actor="ann")
        second = self.forger.forget(build_predicate(SECRET), actor="ann")
        self.assertEqual(first.request_id, second.request_id)
        self.assertEqual(len(self.forger.log.receipts()), 1)

    def test_a_graph_edge_is_matched_across_all_three_columns(self):
        # The secret lives in the object column; matching one column only
        # would leave the edge intact and still leaking.
        self.forger.forget(build_predicate(SECRET), actor="ann", request_id="r1")
        with self.graph._conn() as c:
            subjects = {row["subj"] for row in c.execute("SELECT subj FROM edges")}
        self.assertNotIn("uses_key", subjects)

    def test_punctuation_variants_are_caught_too(self):
        self.memory.save("rotated: key -> sk SECRET42 (2024)", "semantic")
        self.memory.observe("s2", "chat", "old key was SK-Secret42")
        receipt = self.forger.forget(build_predicate(SECRET), actor="ann", request_id="r1")
        self.assertGreaterEqual(receipt.matched, 5)
        self.assertTrue(self.forger.residue(receipt.request_id).clean)


class LessonStoreTests(unittest.TestCase):
    """The append-only store is superseded, never rewritten."""

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.memory = Memory(os.path.join(self.directory.name, "m.db"))
        self.journal = LessonJournal(os.path.join(self.directory.name, "lessons.jsonl"), clock=lambda: 1.0)
        self.journal.record(
            Lesson(
                lesson_id="les_1",
                cue="rotating the deployment key",
                lesson="the current key is " + SECRET,
                evidence="task k1 confirmed it",
                domain="ops",
                status="active",
                created_at=1.0,
            ),
            "promote",
            actor="ann",
            at=1.0,
        )
        self.forger = Forger(
            self.memory,
            lesson_journal=self.journal,
            receipt_path=os.path.join(self.directory.name, "r.jsonl"),
        )

    def test_the_lesson_secret_is_erased(self):
        receipt = self.forger.forget(build_predicate(SECRET), actor="ann", request_id="r1")
        self.assertTrue(receipt.complete)
        state = self.journal.current()
        self.assertEqual(state["les_1"].lesson, ERASED_MARKER)
        self.assertEqual(state["les_1"].cue, ERASED_MARKER)
        self.assertNotIn("SECRET", state["les_1"].lesson)
        self.assertNotIn("SECRET", state["les_1"].cue)

    def test_the_erasure_is_appended_not_the_record_deleted(self):
        self.forger.forget(build_predicate(SECRET), actor="ann", request_id="r1")
        actions = [r.action for r in self.journal.replay()]
        self.assertIn("erase", actions)
        self.assertGreaterEqual(len(self.journal.replay()), 2)

    def test_the_receipt_contains_no_secret(self):
        receipt = self.forger.forget(build_predicate(SECRET), actor="ann", request_id="r1")
        self.assertNotIn("SECRET", str(receipt.to_dict()).upper().replace("SECRET42", ""))


class ReceiptTests(unittest.TestCase):
    def setUp(self):
        self.directory, self.memory, self.graph = _memory_and_graph()
        self.addCleanup(self.directory.cleanup)
        self.path = os.path.join(self.directory.name, "r.jsonl")
        self.forger = Forger(self.memory, graph=self.graph, receipt_path=self.path)
        self.memory.save("key " + SECRET, "semantic")

    def test_a_receipt_proves_the_erasure_without_reproducing_it(self):
        receipt = self.forger.forget(build_predicate(SECRET), actor="ann", request_id="r1")
        body = str(receipt.to_dict())
        self.assertNotIn(SECRET, body)
        self.assertEqual(receipt.removed, 1)
        self.assertTrue(receipt.receipt_digest.startswith("sha256:"))

    def test_the_public_erasure_list_matches_the_receipts(self):
        self.forger.forget(build_predicate(SECRET), actor="ann", request_id="r1")
        report = self.forger.log.verify_list()
        self.assertTrue(report["consistent"])
        self.assertEqual(report["receipts"], 1)

    def test_an_observer_can_rebuild_the_list_from_the_receipts(self):
        self.forger.forget(build_predicate(SECRET), actor="ann", request_id="r1")
        receipt = self.forger.log.receipts()[0]
        self.assertIn(receipt.receipt_id, self.forger.log.receipt_ids())

    def test_a_damaged_list_is_detected(self):
        self.forger.forget(build_predicate(SECRET), actor="ann", request_id="r1")
        with open(self.forger.log.list_path, "w", encoding="utf-8") as handle:
            handle.write("")
        report = self.forger.log.verify_list()
        self.assertFalse(report["consistent"])
        self.assertEqual(len(report["missing_from_list"]), 1)

    def test_receipts_round_trip(self):
        receipt = self.forger.forget(build_predicate(SECRET), actor="ann", request_id="r1")
        restored = ForgetReceipt.from_dict(receipt.to_dict())
        self.assertEqual(restored.request_id, receipt.request_id)
        self.assertEqual(restored.removed, receipt.removed)
        self.assertEqual(restored.predicate.fingerprint(), receipt.predicate.fingerprint())

    def test_a_truncated_receipt_line_is_skipped_not_fatal(self):
        self.forger.forget(build_predicate(SECRET), actor="ann", request_id="r1")
        with open(self.path, "a", encoding="utf-8") as handle:
            handle.write('{"receipt_id": "brok')
        self.assertEqual(len(self.forger.log.receipts()), 1)


class ResidueTests(unittest.TestCase):
    """The honest part: what is still extractable after erasure."""

    def setUp(self):
        self.directory, self.memory, self.graph = _memory_and_graph()
        self.addCleanup(self.directory.cleanup)
        self.forger = Forger(
            self.memory,
            graph=self.graph,
            receipt_path=os.path.join(self.directory.name, "r.jsonl"),
        )

    def test_a_clean_erasure_reports_zero_residue(self):
        self.memory.save("key " + SECRET, "semantic")
        receipt = self.forger.forget(build_predicate(SECRET), actor="ann", request_id="r1")
        report = self.forger.residue("r1")
        self.assertTrue(report.clean)
        self.assertEqual(report.hidden_risk, 0.0)
        self.assertTrue(self.forger.verify(receipt)["forgotten"])

    def test_a_forger_without_a_graph_says_so_rather_than_claiming_success(self):
        # Erasure without a graph attached cannot reach graph edges. The
        # receipt must name the stores it actually covered, so the gap is
        # visible to whoever reads the proof.
        memory_only = Forger(
            self.memory, receipt_path=os.path.join(self.directory.name, "m.jsonl")
        )
        self.graph.link("Alice", "uses_key", SECRET)
        self.memory.save("key " + SECRET, "semantic")
        receipt = memory_only.forget(build_predicate(SECRET), actor="ann", request_id="r1")
        self.assertEqual(memory_only.covered_stores, ("memory", "observations", "summaries"))
        self.assertNotIn("graph", [s.store for s in receipt.stores])
        # The edge the forger could not reach is still there, and still leaking.
        with self.graph._conn() as c:
            self.assertEqual(c.execute("SELECT count(*) FROM edges").fetchone()[0], 1)

    def test_an_unknown_request_id_reports_no_predicate_rather_than_guessing(self):
        report = self.forger.residue("never-issued")
        self.assertTrue(report.clean)
        self.assertEqual(report.residual_hits, [])

    def test_hidden_risk_is_the_gap_between_native_and_residual(self):
        report = self.forger.residue("nothing")
        report.residual_hits = ["memory:1", "memory:2", "observations:3", "summaries:4"]
        report.native_hits = ["memory:1"]
        # 1 native of 4 residual -> 3 of 4 residual was not surfaced.
        self.assertEqual(report.hidden_risk, 0.75)


class VerifyTests(unittest.TestCase):
    def test_verify_reports_coverage_and_residue_together(self):
        directory, memory, graph = _memory_and_graph()
        self.addCleanup(directory.cleanup)
        forger = Forger(
            memory,
            graph=graph,
            receipt_path=os.path.join(directory.name, "r.jsonl"),
        )
        memory.save("key " + SECRET, "semantic")
        receipt = forger.forget(build_predicate(SECRET), actor="ann", request_id="r1")
        report = forger.verify(receipt)
        self.assertTrue(report["complete"])
        self.assertTrue(report["forgotten"])
        self.assertEqual(report["removed"], 1)
        self.assertTrue(report["residue"]["clean"])


__all__ = [
    "AttributionTests",
    "ErasureTests",
    "LessonStoreTests",
    "NormalizeTests",
    "PredicateTests",
    "ReceiptTests",
    "ResidueTests",
    "VerifyTests",
]