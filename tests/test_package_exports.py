import unittest
import noesis_harness


class PackageExportTests(unittest.TestCase):
    def test_nextgen_and_governance_exports(self):
        for name in ("AuditChain", "ContextManager", "IsolationBroker", "Gatekeeper", "DAGPlanner", "VaultProjector", "SkillGate", "ExecutionLadder"):
            self.assertTrue(hasattr(noesis_harness, name), name)


if __name__ == "__main__": unittest.main()
