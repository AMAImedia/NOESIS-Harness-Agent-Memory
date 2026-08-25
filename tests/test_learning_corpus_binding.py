"""Learning-corpus binding tests: round-trip, tamper, fail-closed attach, determinism."""
import dataclasses
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from noesis_harness import Memory
from noesis_harness.learning_corpus_binding import (
    BINDING_SCHEMA_VERSION,
    LearningCorpusBindingError,
    TELEMETRY_BINDING_KEY,
    attach_to_telemetry,
    bind_corpus_evidence,
    verify_corpus_binding,
)
from noesis_harness.learning_promotion import LearningPromotionPipeline
from noesis_harness.memory_quality import DurableMemoryQualityAdapter, DurableMemoryQualityTraceStore
from noesis_harness.memory_quality_corpora import CORPUS_SCHEMA_VERSION, evaluate_corpus_v2
from noesis_harness.promotion_integration import PromotionIntegration


def _fake_report(digest_hex="ab" * 32):
    return {"schema_version": CORPUS_SCHEMA_VERSION, "report_digest": "sha256:" + digest_hex}


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _real_corpus_report(tmp):
    def adapter_factory():
        return DurableMemoryQualityAdapter(
            Memory(str(Path(tmp) / "memory.db")),
            DurableMemoryQualityTraceStore(str(Path(tmp) / "quality.db")),
        )

    return evaluate_corpus_v2(adapter_factory)


class _Harness:
    def __init__(self):
        self.pipe = LearningPromotionPipeline(tempfile.mkdtemp(), b"corpus-binding-key-2026")
        receipt = self.pipe.capture(
            experience_id="exp-bind",
            agent_id="agent-a",
            scope="project:demo",
            source_digest="source-bind",
            outcome="success",
            payload={"answer": "safe"},
            policy_digest="policy-bind",
            created_at=1.0,
        )
        evaluation = self.pipe.evaluate(receipt.receipt_id, [{"case_id": "a", "passed": True}], evaluator_version="eval-1")
        self.proposal = self.pipe.propose(receipt.receipt_id, evaluation.evaluation_id, skill_name="bound-skill", content="# bound\n")
        self.receipt_id = receipt.receipt_id
        self.evaluation_id = evaluation.evaluation_id


class BindVerifyRoundTripTests(unittest.TestCase):
    def test_bind_and_verify_round_trip_with_real_report(self):
        harness = _Harness()
        with tempfile.TemporaryDirectory() as tmp:
            report = _real_corpus_report(tmp)
        binding = bind_corpus_evidence(harness.proposal, report)
        self.assertEqual(binding["schema_version"], BINDING_SCHEMA_VERSION)
        self.assertEqual(binding["corpus_schema_version"], CORPUS_SCHEMA_VERSION)
        self.assertEqual(binding["corpus_report_digest"], report["report_digest"])
        self.assertEqual(binding["subject"]["proposal_id"], harness.proposal.proposal_id)
        self.assertEqual(binding["subject"]["skill_digest"], harness.proposal.content_digest)
        self.assertNotIn("bound_at_unix", binding)
        self.assertTrue(verify_corpus_binding(binding))
        self.assertTrue(verify_corpus_binding(binding, corpus_report=report))

    def test_builder_callable_and_mapping_subjects_are_accepted(self):
        harness = _Harness()
        direct = bind_corpus_evidence(harness.proposal, _fake_report())
        from_callable = bind_corpus_evidence(lambda: harness.proposal, _fake_report())
        from_mapping = bind_corpus_evidence(dataclasses.asdict(harness.proposal), _fake_report())
        self.assertEqual(from_callable["subject"], direct["subject"])
        self.assertEqual(from_mapping["subject"], direct["subject"])
        for binding in (direct, from_callable, from_mapping):
            self.assertTrue(verify_corpus_binding(binding))

    def test_invalid_inputs_fail_closed(self):
        harness = _Harness()
        with self.assertRaisesRegex(LearningCorpusBindingError, "corpus_report_invalid"):
            bind_corpus_evidence(harness.proposal, {"schema_version": "other.v1", "report_digest": "sha256:" + "ab" * 32})
        with self.assertRaisesRegex(LearningCorpusBindingError, "corpus_report_invalid"):
            bind_corpus_evidence(harness.proposal, {"schema_version": CORPUS_SCHEMA_VERSION, "report_digest": "deadbeef"})
        with self.assertRaisesRegex(LearningCorpusBindingError, "subject_proposal_id_invalid"):
            bind_corpus_evidence({"proposal_id": "", "content_digest": "x", "provenance_digest": "y"}, _fake_report())
        with self.assertRaisesRegex(LearningCorpusBindingError, "subject_builder_failed"):
            bind_corpus_evidence(lambda: (_ for _ in ()).throw(RuntimeError("boom")), _fake_report())
        with self.assertRaisesRegex(LearningCorpusBindingError, "clock_required_for_max_age"):
            bind_corpus_evidence(harness.proposal, _fake_report(), max_age_seconds=600)


class DeterminismTests(unittest.TestCase):
    def setUp(self):
        self.harness = _Harness()

    def test_no_clock_output_is_byte_equal_and_timestamp_free(self):
        first = bind_corpus_evidence(self.harness.proposal, _fake_report())
        second = bind_corpus_evidence(lambda: self.harness.proposal, _fake_report())
        self.assertEqual(_canonical(first), _canonical(second))
        self.assertNotIn("bound_at_unix", first)

    def test_injected_clock_adds_bound_at_and_max_age(self):
        binding = bind_corpus_evidence(self.harness.proposal, _fake_report(), clock=lambda: 1780000000.5, max_age_seconds=600)
        self.assertEqual(binding["bound_at_unix"], 1780000000.5)
        self.assertEqual(binding["max_age_seconds"], 600.0)
        self.assertTrue(verify_corpus_binding(binding))
        earlier = bind_corpus_evidence(self.harness.proposal, _fake_report(), clock=lambda: 1779990000.0)
        self.assertNotEqual(_canonical(earlier), _canonical(binding))
        self.assertTrue(verify_corpus_binding(earlier))

    def test_max_age_without_bound_time_fails_verification(self):
        coerced = {
            "schema_version": BINDING_SCHEMA_VERSION,
            "corpus_schema_version": CORPUS_SCHEMA_VERSION,
            "corpus_report_digest": "sha256:" + "ab" * 32,
            "subject": {"kind": "promotion_proposal", "proposal_id": "p-1", "skill_digest": "d", "provenance_digest": ""},
            "max_age_seconds": 600.0,
        }
        unsigned = {key: value for key, value in coerced.items()}
        coerced["binding_digest"] = hashlib.sha256(_canonical(unsigned).encode("utf-8")).hexdigest()
        self.assertFalse(verify_corpus_binding(coerced))


class TamperDetectionTests(unittest.TestCase):
    def setUp(self):
        self.harness = _Harness()
        self.binding = bind_corpus_evidence(self.harness.proposal, _fake_report())

    @staticmethod
    def mutate(binding, path, value):
        mutated = json.loads(_canonical(binding))
        node = mutated
        for key in path[:-1]:
            node = node[key]
        node[path[-1]] = value
        return mutated

    def test_tampered_integrity_digest_fails_closed(self):
        tampered = self.mutate(self.binding, ["binding_digest"], "0" * 64)
        self.assertFalse(verify_corpus_binding(tampered))

    def test_tampered_payload_fields_fail_closed(self):
        cases = [
            (["schema_version"], "noesis.learning-corpus-binding.v0"),
            (["corpus_schema_version"], "noesis.memory-quality-corpus.v1"),
            (["corpus_report_digest"], "sha256:" + "ff" * 32),
            (["subject", "proposal_id"], "bad id with spaces"),
            (["subject", "skill_digest"], "x" + self.binding["subject"]["skill_digest"]),
            (["binding_digest"], None),  # placeholder replaced below
        ]
        for path, value in cases[:-1]:
            self.assertFalse(verify_corpus_binding(self.mutate(self.binding, path, value)), path)

    def test_mismatched_or_foreign_corpus_report_fails_closed(self):
        other = _fake_report("cd" * 32)
        self.assertFalse(verify_corpus_binding(self.binding, corpus_report=other))
        self.assertFalse(verify_corpus_binding(self.binding, corpus_report={"schema_version": "nope.v1", "report_digest": "sha256:" + "ab" * 32}))
        self.assertFalse(verify_corpus_binding(None))
        self.assertFalse(verify_corpus_binding("binding"))

    def test_unknown_extra_key_fails_closed_even_if_digest_rebuilt(self):
        forged = json.loads(_canonical(self.binding))
        del forged["binding_digest"]
        forged["extra"] = True
        forged["binding_digest"] = hashlib.sha256(_canonical(forged).encode("utf-8")).hexdigest()
        self.assertFalse(verify_corpus_binding(forged))


class TelemetryAttachTests(unittest.TestCase):
    def setUp(self):
        self.harness = _Harness()
        self.binding = bind_corpus_evidence(self.harness.proposal, _fake_report())

    def test_attach_then_conflict_is_fail_closed(self):
        payload = {}
        returned = attach_to_telemetry(payload, self.binding)
        self.assertIs(returned, payload)
        self.assertIn(TELEMETRY_BINDING_KEY, payload)
        with self.assertRaisesRegex(LearningCorpusBindingError, "telemetry_binding_conflict"):
            attach_to_telemetry(payload, self.binding)

    def test_attach_rejects_tampered_binding_and_bad_payload(self):
        tampered = json.loads(_canonical(self.binding))
        tampered["corpus_report_digest"] = "sha256:" + "ff" * 32
        with self.assertRaisesRegex(LearningCorpusBindingError, "binding_verification_failed"):
            attach_to_telemetry({}, tampered)
        with self.assertRaisesRegex(LearningCorpusBindingError, "telemetry_payload_invalid"):
            attach_to_telemetry(["not-a-mapping"], self.binding)


class PromotionProposeIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.harness = _Harness()
        self.integration = PromotionIntegration(self.harness.pipe)
        self.binding = bind_corpus_evidence(self.harness.proposal, _fake_report())

    def _proposed_event(self, proposal_id):
        events = [event for event in self.integration.telemetry.snapshot()["events"] if event["event"] == "promotion_proposed" and event.get("proposal_id") == proposal_id]
        return events[0]

    def test_propose_without_binding_keeps_default_payload_shape(self):
        proposal = self.integration.propose(self.harness.receipt_id, self.harness.evaluation_id, skill_name="plain-skill", content="# plain\n")
        event = self._proposed_event(proposal.proposal_id)
        self.assertEqual(set(event.keys()) >= {"proposal_id", "state", "skill_name", "at_epoch", "event"}, True)
        self.assertNotIn(TELEMETRY_BINDING_KEY, event)

    def test_propose_records_verified_binding_in_telemetry(self):
        proposal = self.integration.propose(self.harness.receipt_id, self.harness.evaluation_id, skill_name="bound-telemetry-skill", content="# bt\n", corpus_binding=self.binding)
        carried = self._proposed_event(proposal.proposal_id)[TELEMETRY_BINDING_KEY]
        self.assertEqual(carried, self.binding)
        # Binding survives telemetry redaction verbatim and stays verifiable.
        self.assertEqual(carried["subject"]["skill_digest"], self.harness.proposal.content_digest)
        self.assertTrue(verify_corpus_binding(carried))

    def test_propose_with_invalid_binding_fails_closed_before_pipeline_side_effect(self):
        tampered = json.loads(_canonical(self.binding))
        tampered["subject"]["proposal_id"] = "different-proposal-id"
        proposals_before = set(self.integration.pipeline._proposals)
        with self.assertRaisesRegex(LearningCorpusBindingError, "binding_verification_failed"):
            self.integration.propose(self.harness.receipt_id, self.harness.evaluation_id, skill_name="never-created", content="# n\n", corpus_binding=tampered)
        self.assertEqual(set(self.integration.pipeline._proposals), proposals_before)


if __name__ == "__main__":
    unittest.main()
