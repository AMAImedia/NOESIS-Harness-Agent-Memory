"""Adversarial redaction-contract tests pinning PromotionTelemetry._redact.

Gate 1/2 hardening: locks the exact key-masking vocabulary and masked-value
form so future masking changes cannot silently drop binding keys or leak
verification-relevant digests on operator surfaces. Pattern lineage: the
fail-closed adversarial holdout suites of deepseek-harness mirrored in
memory_quality_corpora.verify_case_provenance, plus the agentmemory governance
audit discipline of replayable explicit expectations already ported into
learning_promotion/promotion_integration canonical-digest verification.
"""
import tempfile
import unittest
from collections.abc import Mapping

from noesis_harness.health_server import HealthServer
from noesis_harness.learning_corpus_binding import (
    TELEMETRY_BINDING_KEY,
    attach_to_telemetry,
    bind_corpus_evidence,
    verify_corpus_binding,
)
from noesis_harness.learning_promotion import LearningPromotionPipeline
from noesis_harness.memory_quality_corpora import CORPUS_SCHEMA_VERSION
from noesis_harness.promotion_integration import PromotionTelemetry

REDACTED_MARKER = "[REDACTED]"
FAKE_REPORT_HEX = "ab" * 32
_EVENT_FRAME_KEYS = frozenset({"event", "at_epoch"})


def _fake_report():
    return {"schema_version": CORPUS_SCHEMA_VERSION, "report_digest": "sha256:" + FAKE_REPORT_HEX}


class _Harness:
    def __init__(self):
        self.pipe = LearningPromotionPipeline(tempfile.mkdtemp(), b"redaction-contract-key-2026")
        receipt = self.pipe.capture(
            experience_id="exp-redact-contract",
            agent_id="agent-a",
            scope="project:demo",
            source_digest="source-redact-contract",
            outcome="success",
            payload={"answer": "safe"},
            policy_digest="policy-redact-contract",
            created_at=1.0,
        )
        evaluation = self.pipe.evaluate(receipt.receipt_id, [{"case_id": "a", "passed": True}], evaluator_version="eval-1")
        self.proposal = self.pipe.propose(receipt.receipt_id, evaluation.evaluation_id, skill_name="redaction-probe", content="# probe\n")


def _record_fields(**fields):
    telemetry = PromotionTelemetry()
    telemetry.record("contract_probe", **fields)
    events = telemetry.snapshot()["events"]
    return {key: value for key, value in events[0].items() if key not in _EVENT_FRAME_KEYS}


def _walk(value):
    if isinstance(value, Mapping):
        for key, item in value.items():
            yield str(key), item
            yield from _walk(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _walk(item)


class FixedVocabularyRedactionTests(unittest.TestCase):
    def setUp(self):
        self.harness = _Harness()
        self.binding = bind_corpus_evidence(self.harness.proposal, _fake_report())
        self.payload = {
            "skill_digest": self.harness.proposal.content_digest,
            TELEMETRY_BINDING_KEY: self.binding,
            "content_digest": self.harness.proposal.content_digest,
            "content": "# secret skill body\n",
            "proposal_id": self.harness.proposal.proposal_id,
            "provenance_digest": self.harness.proposal.provenance_digest,
        }

    def test_representative_payload_keeps_exact_post_redaction_key_set(self):
        observed = _record_fields(**self.payload)
        self.assertEqual(set(observed), set(self.payload))

    def test_representative_payload_matches_exact_expected_structure(self):
        expected = {
            "skill_digest": self.payload["skill_digest"],
            TELEMETRY_BINDING_KEY: self.binding,
            "content_digest": REDACTED_MARKER,
            "content": REDACTED_MARKER,
            "proposal_id": self.payload["proposal_id"],
            "provenance_digest": self.payload["provenance_digest"],
        }
        self.assertEqual(_record_fields(**self.payload), expected)

    def test_masked_keys_are_replaced_not_dropped(self):
        observed = _record_fields(**self.payload)
        self.assertEqual(observed["content"], REDACTED_MARKER)
        self.assertEqual(observed["content_digest"], REDACTED_MARKER)
        self.assertIn("content", observed)
        self.assertIn("content_digest", observed)

    def test_unmasked_vocabulary_values_pass_through_byte_identical(self):
        observed = _record_fields(**self.payload)
        self.assertEqual(observed["skill_digest"], self.harness.proposal.content_digest)
        self.assertEqual(observed["proposal_id"], self.harness.proposal.proposal_id)
        self.assertEqual(observed["provenance_digest"], self.harness.proposal.provenance_digest)

    def test_corpus_binding_subdict_survives_verbatim_with_nested_report_digest(self):
        observed = _record_fields(**self.payload)
        carried = observed[TELEMETRY_BINDING_KEY]
        self.assertEqual(carried, self.binding)
        self.assertEqual(carried["corpus_report_digest"], "sha256:" + FAKE_REPORT_HEX)
        self.assertEqual(carried["subject"]["skill_digest"], self.harness.proposal.content_digest)
        self.assertEqual(carried["subject"]["provenance_digest"], self.harness.proposal.provenance_digest)
        self.assertEqual(carried["binding_digest"], self.binding["binding_digest"])
        self.assertTrue(verify_corpus_binding(carried))


class RedactedBindingRoundTripTests(unittest.TestCase):
    def setUp(self):
        self.harness = _Harness()
        self.binding = bind_corpus_evidence(self.harness.proposal, _fake_report())

    def _attached_and_recorded_event(self):
        fields = {"proposal_id": self.harness.proposal.proposal_id}
        attach_to_telemetry(fields, self.binding)
        telemetry = PromotionTelemetry()
        telemetry.record("promotion_proposed", **fields)
        return telemetry.snapshot()["events"][0]

    def test_bind_attach_redact_verify_round_trip_on_redacted_copy(self):
        event = self._attached_and_recorded_event()
        redacted_copy = event[TELEMETRY_BINDING_KEY]
        self.assertEqual(redacted_copy, self.binding)
        self.assertTrue(verify_corpus_binding(redacted_copy))

    def test_redacted_copy_still_verifies_against_source_corpus_report(self):
        event = self._attached_and_recorded_event()
        self.assertTrue(verify_corpus_binding(event[TELEMETRY_BINDING_KEY], corpus_report=_fake_report()))

    def test_redacted_copy_survives_health_server_second_pass_verifiable(self):
        event = self._attached_and_recorded_event()
        twice = HealthServer._redact_telemetry(dict(event))[TELEMETRY_BINDING_KEY]
        self.assertEqual(twice, self.binding)
        self.assertTrue(verify_corpus_binding(twice))

    def test_full_redacted_snapshot_from_both_layers_stays_verifiable(self):
        fields = {"proposal_id": self.harness.proposal.proposal_id}
        attach_to_telemetry(fields, self.binding)
        telemetry = PromotionTelemetry()
        telemetry.record("promotion_proposed", **fields)
        safe_snapshot = HealthServer._redact_telemetry(telemetry.snapshot())
        carried = safe_snapshot["events"][0][TELEMETRY_BINDING_KEY]
        self.assertTrue(verify_corpus_binding(carried, corpus_report=_fake_report()))


class NearCollisionKeyCanaryTests(unittest.TestCase):
    def _observed_value_for(self, key):
        return _record_fields(**{key: "canary-value"})[key]

    def test_canary_skill_digests_plural_is_never_masked(self):
        self.assertEqual(self._observed_value_for("skill_digests"), "canary-value")

    def test_canary_contents_is_masked(self):
        self.assertEqual(self._observed_value_for("contents"), REDACTED_MARKER)

    def test_canary_my_content_key_is_masked(self):
        self.assertEqual(self._observed_value_for("my_content_key"), REDACTED_MARKER)

    def test_canary_contentx_is_masked(self):
        self.assertEqual(self._observed_value_for("contentx"), REDACTED_MARKER)

    def test_canary_mixed_case_content_digest_is_masked_under_original_cased_key(self):
        observed = _record_fields(Content_Digest="canary-value")
        self.assertEqual(set(observed), {"Content_Digest"})
        self.assertEqual(observed["Content_Digest"], REDACTED_MARKER)

    def test_canary_bare_digest_prefix_key_without_secret_substring_survives(self):
        self.assertEqual(self._observed_value_for("digest_only"), "canary-value")

    def test_canary_other_secret_family_members_stay_masked(self):
        self.assertEqual(self._observed_value_for("api_keys"), REDACTED_MARKER)
        self.assertEqual(self._observed_value_for("tokens"), REDACTED_MARKER)
        self.assertEqual(self._observed_value_for("secrets"), REDACTED_MARKER)


class DigestFailLoudContractTests(unittest.TestCase):
    REQUIRED_DIGEST_KEYS = frozenset({"skill_digest", "provenance_digest", "binding_digest", "corpus_report_digest"})

    def setUp(self):
        self.harness = _Harness()
        self.binding = bind_corpus_evidence(self.harness.proposal, _fake_report())

    def _redacted_digest_entries(self):
        fields = {
            "skill_digest": self.harness.proposal.content_digest,
            TELEMETRY_BINDING_KEY: self.binding,
            "content_digest": self.harness.proposal.content_digest,
            "content": "# secret skill body\n",
            "proposal_id": self.harness.proposal.proposal_id,
            "provenance_digest": self.harness.proposal.provenance_digest,
        }
        return list(_walk(_record_fields(**fields)))

    def test_content_digest_is_the_only_masked_digest_named_key_after_redaction(self):
        masked = sorted(key for key, value in self._redacted_digest_entries() if "digest" in key.casefold() and value == REDACTED_MARKER)
        self.assertEqual(masked, ["content_digest"])

    def test_required_binding_digest_keys_all_present_after_redaction(self):
        observed_keys = {key for key, _ in self._redacted_digest_entries()}
        missing = self.REQUIRED_DIGEST_KEYS - observed_keys
        self.assertEqual(missing, frozenset())

    def test_every_report_digest_retains_sha256_shape_after_redaction(self):
        report_entries = [(key, value) for key, value in self._redacted_digest_entries() if key.casefold().endswith("report_digest")]
        self.assertGreaterEqual(len(report_entries), 1)
        for key, value in report_entries:
            self.assertIsInstance(value, str, key)
            self.assertTrue(value.startswith("sha256:") and len(value) == 71, key)


if __name__ == "__main__":
    unittest.main()
