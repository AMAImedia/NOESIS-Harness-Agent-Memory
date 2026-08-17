import tempfile
import unittest
from pathlib import Path

from noesis_harness.governance import (
    ActionRequest, DAGPlanner, ExecutionLadder, Gatekeeper, SkillGate,
    VaultNote, VaultProjector,
)
from noesis_harness.nextgen import CapabilityManifest


class GovernanceTests(unittest.TestCase):
    def test_gatekeeper_denies_and_stages_risky_action(self):
        gate = Gatekeeper()
        cap = CapabilityManifest(operations=("fs_write",), filesystem_roots=(tempfile.gettempdir(),))
        path = str(Path(tempfile.gettempdir()) / "x.txt")
        denied = gate.decide(ActionRequest("a", "fs_write", path, "write"), CapabilityManifest())
        self.assertEqual(denied["status"], "denied")
        staged = gate.decide(ActionRequest("a", "fs_write", path, "write"), cap, simulation={"would_write": True})
        self.assertEqual(staged["status"], "pending")
        self.assertTrue(staged["simulated"])
        approved = gate.decide(ActionRequest("a", "fs_write", path, "write"), cap, approved=True)
        self.assertEqual(approved["status"], "approved")

    def test_dag_planner_parallel_stages_and_cycle_rejection(self):
        planner = DAGPlanner(max_parallel=2)
        planner.add("a"); planner.add("b"); planner.add("c", ("a", "b"))
        stages = planner.stages()
        self.assertEqual(stages[0], ("a", "b"))
        self.assertEqual(stages[1], ("c",))
        cycle = DAGPlanner(); cycle.add("x", ("y",)); cycle.add("y", ("x",))
        with self.assertRaises(ValueError): cycle.stages()

    def test_vault_is_atomic_and_round_trips(self):
        with tempfile.TemporaryDirectory() as d:
            vault = VaultProjector(d)
            path = vault.write(VaultNote("project-1", "Project", "Decision body", ("project",), ("evt-1",)))
            self.assertTrue(path.exists())
            note = vault.read("project-1")
            self.assertEqual(note.body, "Decision body\n")
            self.assertEqual(note.source_ids, ("evt-1",))
            with self.assertRaises(ValueError): vault.write(VaultNote("../escape", "bad", "x"))

    def test_skill_gate_requires_tests_and_explicit_approval(self):
        with tempfile.TemporaryDirectory() as d:
            gate = SkillGate(d)
            p = gate.stage("safe-skill", "# Safe\nDo the safe thing.\n")
            with self.assertRaises(PermissionError): gate.decide(p.proposal_id, True, lambda: False)
            self.assertEqual(len(gate.pending()), 1)
            result = gate.decide(p.proposal_id, True, lambda: True)
            self.assertEqual(result.status, "approved")
            self.assertTrue((Path(d) / "safe-skill" / "SKILL.md").exists())

    def test_execution_ladder_does_not_fake_sandbox(self):
        ladder = ExecutionLadder()
        self.assertEqual(ladder.choose("workspace")["status"], "available")
        result = ladder.choose("sandbox")
        self.assertEqual(result["status"], "unavailable")
        self.assertTrue(result["safe"])


if __name__ == "__main__": unittest.main()

