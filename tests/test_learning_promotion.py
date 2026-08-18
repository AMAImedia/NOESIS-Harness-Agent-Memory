import tempfile
import unittest
from pathlib import Path

from noesis_harness.learning_promotion import LearningPromotionError, LearningPromotionPipeline


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

    def test_immutable_promotion_signature_and_rollback(self):
        pipe = self.pipeline(); receipt = self.receipt(pipe)
        evaluation = pipe.evaluate(receipt.receipt_id, [{"case_id": "a", "passed": True}], evaluator_version="eval-1")
        proposal = pipe.propose(receipt.receipt_id, evaluation.evaluation_id, skill_name="safe-skill", content="# safe\n")
        pipe.approve(proposal.proposal_id, approved_by="owner", tests=lambda: True)
        promoted, signature = pipe.promote(proposal.proposal_id, content="# safe\n", verify=lambda path: path.read_text() == "# safe\n")
        self.assertEqual(promoted.state, "promoted")
        self.assertTrue(pipe.verify_signature({"proposal_id": proposal.proposal_id, "skill_name": "safe-skill", "version": promoted.version, "active": True}, signature))
        self.assertFalse(pipe.verify_signature({"proposal_id": proposal.proposal_id, "skill_name": "safe-skill", "version": "tampered", "active": True}, signature))
        self.assertTrue(pipe.active_version("safe-skill"))
        rolled = pipe.rollback(proposal.proposal_id)
        self.assertEqual(rolled.state, "rolled_back")
        self.assertEqual(pipe.active_version("safe-skill"), "")
        self.assertTrue((Path(pipe.root) / "safe-skill" / promoted.version / "SKILL.md").is_file())


if __name__ == "__main__":
    unittest.main()
