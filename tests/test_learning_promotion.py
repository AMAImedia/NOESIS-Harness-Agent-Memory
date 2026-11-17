import dataclasses
import json
import sqlite3
import tempfile
import unittest
from unittest import mock
from pathlib import Path

from noesis_harness.learning_promotion import LearningPromotionError, LearningPromotionPipeline
from noesis_harness.promotion_integration import EvaluatorRegistry


class LearningPromotionTests(unittest.TestCase):
    def pipeline(self):
        return LearningPromotionPipeline(tempfile.mkdtemp(), b"promotion-test-key-2026")

    def receipt(self, pipe):
        return pipe.capture(
            experience_id="exp-1",
            agent_id="agent-a",
            scope="project:demo",
            source_digest="source-1",
            outcome="success",
            payload={"answer": "safe"},
            policy_digest="policy-1",
            created_at=1.0,
        )

    def test_duplicate_capture_evaluation_and_proposal_are_idempotent(self):
        pipe = self.pipeline(); receipt = self.receipt(pipe)
        self.assertEqual(pipe.capture(experience_id="exp-1", agent_id="agent-a", scope="project:demo", source_digest="source-1", outcome="success", payload={"answer": "safe"}, policy_digest="policy-1", created_at=2.0), receipt)
        evaluation = pipe.evaluate(receipt.receipt_id, [{"case_id": "a", "passed": True}], evaluator_version="eval-1")
        self.assertEqual(pipe.evaluate(receipt.receipt_id, [{"case_id": "a", "passed": True}], evaluator_version="eval-1"), evaluation)
        proposal = pipe.propose(receipt.receipt_id, evaluation.evaluation_id, skill_name="safe-skill", content="# safe\n")
        self.assertEqual(pipe.propose(receipt.receipt_id, evaluation.evaluation_id, skill_name="safe-skill", content="# safe\n"), proposal)
        with self.assertRaisesRegex(LearningPromotionError, "proposal_content_conflict"):
            pipe.propose(receipt.receipt_id, evaluation.evaluation_id, skill_name="safe-skill", content="# changed\n")

    def test_holdout_is_deterministic_and_requires_nonempty_all_pass(self):
        pipe = self.pipeline(); receipt = self.receipt(pipe)
        cases = [{"case_id": "b", "passed": True}, {"case_id": "a", "passed": True}]
        first = pipe.evaluate(receipt.receipt_id, cases, evaluator_version="eval-1")
        second = pipe.evaluate(receipt.receipt_id, reversed(cases), evaluator_version="eval-1")
        self.assertEqual(first.holdout_digest, second.holdout_digest)
        self.assertTrue(first.accepted)
        empty = pipe.evaluate(receipt.receipt_id, [], evaluator_version="eval-1")
        self.assertFalse(empty.accepted)

    def test_leakage_or_failed_case_blocks_proposal(self):
        pipe = self.pipeline(); receipt = self.receipt(pipe)
        evaluation = pipe.evaluate(receipt.receipt_id, [{"case_id": "a", "passed": True, "leaked": True}], evaluator_version="eval-1")
        with self.assertRaisesRegex(LearningPromotionError, "holdout_not_accepted"):
            pipe.propose(receipt.receipt_id, evaluation.evaluation_id, skill_name="safe-skill", content="# safe\n")

    def test_proposal_requires_explicit_approval_and_passing_tests(self):
        pipe = self.pipeline(); receipt = self.receipt(pipe)
        evaluation = pipe.evaluate(receipt.receipt_id, [{"case_id": "a", "passed": True}], evaluator_version="eval-1")
        proposal = pipe.propose(receipt.receipt_id, evaluation.evaluation_id, skill_name="safe-skill", content="# safe\n")
        with self.assertRaisesRegex(LearningPromotionError, "explicit_approval_required"):
            pipe.promote(proposal.proposal_id, content="# safe\n", verify=lambda _: True)
        with self.assertRaisesRegex(LearningPromotionError, "approval_tests_failed"):
            pipe.approve(proposal.proposal_id, approved_by="owner", tests=lambda: False)
        approved = pipe.approve(proposal.proposal_id, approved_by="owner", tests=lambda: True)
        self.assertEqual(approved.state, "approved")

    def test_digest_and_verification_failure_are_fail_closed(self):
        pipe = self.pipeline(); receipt = self.receipt(pipe)
        evaluation = pipe.evaluate(receipt.receipt_id, [{"case_id": "a", "passed": True}], evaluator_version="eval-1")
        proposal = pipe.propose(receipt.receipt_id, evaluation.evaluation_id, skill_name="safe-skill", content="# safe\n")
        pipe.approve(proposal.proposal_id, approved_by="owner", tests=lambda: True)
        with self.assertRaisesRegex(LearningPromotionError, "content_digest_mismatch"):
            pipe.promote(proposal.proposal_id, content="# changed\n", verify=lambda _: True)
        with self.assertRaisesRegex(LearningPromotionError, "promotion_verification_failed"):
            pipe.promote(proposal.proposal_id, content="# safe\n", verify=lambda _: False)
        self.assertEqual(pipe.active_version("safe-skill"), "")

    def test_restart_restores_receipts_evaluations_proposals_and_approval_state(self):
        pipe = self.pipeline(); receipt = self.receipt(pipe)
        evaluation = pipe.evaluate(receipt.receipt_id, [{"case_id": "a", "passed": True}], evaluator_version="eval-1")
        proposal = pipe.propose(receipt.receipt_id, evaluation.evaluation_id, skill_name="restart-skill", content="# restart\n")
        pipe.approve(proposal.proposal_id, approved_by="owner", tests=lambda: True)
        registry = EvaluatorRegistry(state=pipe.durable_state)
        registry.register("eval-1", lambda _: [{"case_id": "a", "passed": True}], manifest_digest="manifest-eval-1")
        reopened = LearningPromotionPipeline(str(pipe.root), b"promotion-test-key-2026")
        self.assertIn(receipt.receipt_id, reopened._receipts)
        self.assertIn(evaluation.evaluation_id, reopened._evaluations)
        self.assertEqual(reopened._proposals[proposal.proposal_id].state, "approved")
        reopened_registry = EvaluatorRegistry(state=reopened.durable_state)
        self.assertEqual(reopened_registry.manifests(), {"eval-1": "manifest-eval-1"})
        with self.assertRaisesRegex(LearningPromotionError, "evaluator_manifest_conflict"):
            reopened_registry.register("eval-1", lambda _: [], manifest_digest="tampered-manifest")

    def test_review_snapshot_is_bounded_redacted_and_provenance_bound(self):
        pipe = self.pipeline(); receipt = self.receipt(pipe)
        evaluation = pipe.evaluate(receipt.receipt_id, [{"case_id": "a", "passed": True}], evaluator_version="eval-1")
        proposal = pipe.propose(receipt.receipt_id, evaluation.evaluation_id, skill_name="review-skill", content="# secret-content\n")
        snapshot = pipe.review_snapshot(max_proposals=1)
        self.assertEqual(snapshot["schema_version"], "noesis.learning-review-snapshot.v1")
        self.assertTrue(snapshot["automatic_activation"] is False)
        item = snapshot["proposals"][0]
        self.assertEqual(item["provenance_status"], "verified")
        self.assertNotIn("secret-content", repr(snapshot))
        self.assertNotIn("answer", repr(snapshot))
        tampered = dataclasses.replace(proposal, content_digest="0" * 64)
        pipe._proposals[proposal.proposal_id] = tampered
        with self.assertRaisesRegex(LearningPromotionError, "proposal_provenance_mismatch"):
            pipe.approve(proposal.proposal_id, approved_by="reviewer", tests=lambda: True)
        self.assertEqual(pipe.review_snapshot()["proposals"][0]["provenance_status"], "mismatch")

    def test_review_snapshot_bound_and_missing_provenance_fail_closed(self):
        pipe = self.pipeline()
        with self.assertRaisesRegex(ValueError, "invalid_review_snapshot_bound"):
            pipe.review_snapshot(max_proposals=0)
        receipt = self.receipt(pipe)
        evaluation = pipe.evaluate(receipt.receipt_id, [{"case_id": "a", "passed": True}], evaluator_version="eval-1")
        proposal = pipe.propose(receipt.receipt_id, evaluation.evaluation_id, skill_name="legacy-skill", content="# legacy\n")
        pipe._proposals[proposal.proposal_id] = dataclasses.replace(proposal, provenance_digest="")
        with self.assertRaisesRegex(LearningPromotionError, "proposal_provenance_mismatch"):
            pipe.approve(proposal.proposal_id, approved_by="reviewer", tests=lambda: True)

    def test_activation_failure_leaves_signed_receipt_and_old_active_pointer(self):
        pipe = self.pipeline(); receipt = self.receipt(pipe)
        evaluation = pipe.evaluate(receipt.receipt_id, [{"case_id": "a", "passed": True}], evaluator_version="eval-1")
        proposal = pipe.propose(receipt.receipt_id, evaluation.evaluation_id, skill_name="crash-safe-skill", content="# safe\n")
        pipe.approve(proposal.proposal_id, approved_by="owner", tests=lambda: True)
        with mock.patch("noesis_harness.learning_promotion.os.replace", side_effect=OSError("simulated activation crash")):
            with self.assertRaises(OSError):
                pipe.promote(proposal.proposal_id, content="# safe\n", verify=lambda path: path.read_text() == "# safe\n")
        skill_root = Path(pipe.root) / "crash-safe-skill"
        versions = tuple(path for path in skill_root.iterdir() if path.is_dir())
        self.assertEqual(len(versions), 1)
        self.assertTrue((versions[0] / "PROMOTION_RECEIPT.json").is_file())
        self.assertEqual(pipe.active_version("crash-safe-skill"), "")
        self.assertEqual(pipe.durable_state.activation_journal(proposal.proposal_id)["status"], "prepared")
        self.assertEqual(pipe.durable_state.activation_readiness(proposal.proposal_id)["status"], "recovery_required")
        self.assertFalse(pipe.durable_state.activation_readiness(proposal.proposal_id)["automatic_retry"])
        reopened = LearningPromotionPipeline(str(pipe.root), b"promotion-test-key-2026")
        self.assertEqual(reopened.durable_state.activation_journal(proposal.proposal_id)["status"], "prepared")
        self.assertTrue(reopened.durable_state.activation_readiness(proposal.proposal_id)["recovery_required"])

    def test_activation_journal_tamper_is_rejected(self):
        pipe = self.pipeline(); receipt = self.receipt(pipe)
        evaluation = pipe.evaluate(receipt.receipt_id, [{"case_id": "a", "passed": True}], evaluator_version="eval-1")
        proposal = pipe.propose(receipt.receipt_id, evaluation.evaluation_id, skill_name="journal-skill", content="# safe\n")
        pipe.approve(proposal.proposal_id, approved_by="owner", tests=lambda: True)
        pipe.promote(proposal.proposal_id, content="# safe\n", verify=lambda path: True)
        db = sqlite3.connect(pipe.durable_state.path)
        try:
            row = db.execute("SELECT record_json FROM promotion_activation_journal WHERE proposal_id=?", (proposal.proposal_id,)).fetchone()
            tampered = json.loads(row[0]); tampered["status"] = "prepared"
            db.execute("UPDATE promotion_activation_journal SET record_json=? WHERE proposal_id=?", (json.dumps(tampered, sort_keys=True), proposal.proposal_id)); db.commit()
        finally:
            db.close()
        with self.assertRaisesRegex(LearningPromotionError, "activation_journal_integrity_failure"):
            pipe.durable_state.activation_journal(proposal.proposal_id)

    def test_immutable_promotion_signature_and_rollback(self):
        pipe = self.pipeline(); receipt = self.receipt(pipe)
        evaluation = pipe.evaluate(receipt.receipt_id, [{"case_id": "a", "passed": True}], evaluator_version="eval-1")
        proposal = pipe.propose(receipt.receipt_id, evaluation.evaluation_id, skill_name="safe-skill", content="# safe\n")
        pipe.approve(proposal.proposal_id, approved_by="owner", tests=lambda: True)
        promoted, signature = pipe.promote(proposal.proposal_id, content="# safe\n", verify=lambda path: path.read_text() == "# safe\n")
        self.assertEqual(promoted.state, "promoted")
        self.assertTrue(promoted.version.startswith("v1-"))
        manifest = (Path(pipe.root) / "safe-skill" / promoted.version / "VERSION.json").read_text(encoding="utf-8")
        self.assertIn('"immutable":true', manifest)
        self.assertTrue(pipe.verify_signature({"schema_version": "noesis.immutable-skill-promotion-receipt.v1", "proposal_id": proposal.proposal_id, "skill_name": "safe-skill", "version": promoted.version, "content_digest": proposal.content_digest, "provenance_digest": proposal.provenance_digest, "immutable": True, "active": True}, signature))
        self.assertTrue(pipe.verify_signature({"proposal_id": proposal.proposal_id, "skill_name": "safe-skill", "version": promoted.version, "active": True}, signature))
        self.assertFalse(pipe.verify_signature({"proposal_id": proposal.proposal_id, "skill_name": "safe-skill", "version": "tampered", "active": True}, signature))
        self.assertTrue(pipe.active_version("safe-skill"))
        rolled = pipe.rollback(proposal.proposal_id)
        self.assertEqual(rolled.state, "rolled_back")
        self.assertEqual(pipe.active_version("safe-skill"), "")
        self.assertTrue((Path(pipe.root) / "safe-skill" / promoted.version / "SKILL.md").is_file())
        self.assertTrue((Path(pipe.root) / "safe-skill" / promoted.version / "VERSION.json").is_file())
        promotion_receipt = (Path(pipe.root) / "safe-skill" / promoted.version / "PROMOTION_RECEIPT.json").read_text(encoding="utf-8")
        self.assertIn("noesis.immutable-skill-promotion-receipt.v1", promotion_receipt)
        self.assertIn(signature, promotion_receipt)


if __name__ == "__main__":
    unittest.main()
