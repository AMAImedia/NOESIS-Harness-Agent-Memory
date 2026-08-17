from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

from noesis_harness.child_execution import ChildExecutionRuntime, ExecutionRequest
from noesis_harness.context_firewall import ContextItem
from noesis_harness.gatekeeper import CapabilityRequest, Gatekeeper
from noesis_harness.resource_lineage import ObservationLedger
from noesis_harness.trust_plane import TrustPlane


class TrustPlaneTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.workspace = root / "workspace"
        self.workspace.mkdir()
        (self.workspace / "ok.py").write_text("print('trust-plane-ok')\n", encoding="utf-8")
        self.gate = Gatekeeper(str(root / "gate.jsonl"))
        self.lineage = ObservationLedger(str(root / "lineage.jsonl"))
        self.audit_path = root / "trust-audit.jsonl"
        self.plane = TrustPlane(self.gate, self.lineage, child_runtime=ChildExecutionRuntime(self.gate), audit_path=str(self.audit_path))

    def tearDown(self):
        self.tmp.cleanup()

    def _case(self, capability="memory.read", action="read", target="ok.py", side_effect="read", request_id=""):
        request = CapabilityRequest("s", "t", "agent-a", capability, action, target, side_effect, {}, request_id=request_id)
        rid = request.normalized_id()
        execution = ExecutionRequest(rid, (sys.executable, "ok.py"), str(self.workspace), (Path(sys.executable).name,))
        return request, execution

    def test_public_read_path_passes_all_layers(self):
        request, execution = self._case()
        decision = self.plane.run_skill(session_id="s", task_id="t", agent_id="agent-a", context_items=(ContextItem("public", "safe", "public", resource_id="public-1"),), request=request, execution=execution)
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.execution.status, "completed")
        self.assertEqual(decision.gate.status, "committed")
        self.assertEqual(decision.context.included_resource_ids, ("public-1",))

    def test_restricted_context_cannot_reach_gate_without_approval(self):
        request, execution = self._case(capability="skill.execute", action="run", side_effect="write")
        decision = self.plane.run_skill(session_id="s", task_id="t", agent_id="agent-a", context_items=(ContextItem("secret", "hidden", "restricted", resource_id="secret-1"),), request=request, execution=execution)
        self.assertFalse(decision.allowed)
        self.assertIn("lineage_egress_denied", decision.reason)
        self.assertIsNone(decision.gate)
        self.assertIsNone(decision.execution)
        self.assertEqual(decision.context.redacted_ids, ("secret",))

    def test_explicit_approval_allows_restricted_path_but_still_runs_child_boundary(self):
        request, execution = self._case(capability="skill.execute", action="run", side_effect="write")
        decision = self.plane.run_skill(session_id="s", task_id="t", agent_id="agent-a", context_items=(ContextItem("secret", "hidden", "restricted", resource_id="secret-1"),), request=request, execution=execution, explicit_approval=True)
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.gate.status, "committed")
        self.assertEqual(decision.execution.status, "completed")
        self.assertEqual(decision.context.included_resource_ids, ("secret-1",))

    def test_security_denial_precedes_approval(self):
        request, execution = self._case(capability="tool.invoke", action="run", target="../../etc/passwd", side_effect="external")
        decision = self.plane.run_skill(session_id="s", task_id="t", agent_id="agent-a", context_items=(ContextItem("public", "safe", "public"),), request=request, execution=execution, explicit_approval=True)
        self.assertFalse(decision.allowed)
        self.assertIn("gatekeeper_denied:security_policy_denied", decision.reason)
        self.assertIsNone(decision.execution)

    def test_audit_chain_records_denied_and_approved_without_raw_context(self):
        denied_request, denied_execution = self._case(capability="skill.execute", action="run", side_effect="write", request_id="denied")
        denied = self.plane.run_skill(session_id="s", task_id="t", agent_id="agent-a", context_items=(ContextItem("secret", "RAW-RESTRICTED-CONTENT", "restricted", resource_id="secret-1"),), request=denied_request, execution=denied_execution)
        self.assertFalse(denied.allowed)
        approved_request, approved_execution = self._case(capability="skill.execute", action="run", side_effect="write", request_id="approved")
        approved = self.plane.run_skill(session_id="s2", task_id="t2", agent_id="agent-a", context_items=(ContextItem("public", "safe", "public", resource_id="public-1"),), request=approved_request, execution=approved_execution, explicit_approval=True)
        self.assertTrue(approved.allowed)
        serialized = self.audit_path.read_text(encoding="utf-8")
        self.assertNotIn("RAW-RESTRICTED-CONTENT", serialized)
        self.assertEqual(serialized.count("trust_plane_decision"), 2)
        self.assertTrue(self.plane.verify_audit_chain())
        lines = [json.loads(line) for line in serialized.splitlines()]
        self.assertEqual([line["payload"]["prev_hash"] for line in lines][0], "0" * 64)
        self.assertNotEqual(lines[0]["payload"]["event_hash"], lines[1]["payload"]["event_hash"])


if __name__ == "__main__":
    unittest.main()
