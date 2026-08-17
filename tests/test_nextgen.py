import json
import os
import tempfile
import unittest
from pathlib import Path

from noesis_harness.nextgen import (
    AgentManifest, AuditChain, CapabilityDenied, CapabilityManifest,
    ContextManager, DurableCommandLedger, IsolationBroker, RunEnvelope,
)


class NextGenTests(unittest.TestCase):
    def test_audit_chain_and_tamper_detection(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "audit.jsonl"
            chain = AuditChain(str(path))
            chain.append("a", "read", {"path": "x"})
            chain.append("a", "write", {"path": "y"})
            self.assertTrue(chain.verify()["ok"])
            lines = path.read_text(encoding="utf-8").splitlines()
            event = json.loads(lines[1]); event["payload"]["path"] = "evil"
            lines[1] = json.dumps(event, separators=(",", ":"))
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            self.assertFalse(chain.verify()["ok"])

    def test_capability_manifest_is_deny_by_default_and_root_scoped(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            inside = root / "a.txt"
            outside = root.parent / "outside.txt"
            cap = CapabilityManifest(operations=("fs_read",), filesystem_roots=(str(root),))
            self.assertTrue(cap.allows("fs_read", str(inside)))
            self.assertFalse(cap.allows("fs_write", str(inside)))
            self.assertFalse(cap.allows("fs_read", str(outside)))

    def test_idempotent_command_ledger(self):
        with tempfile.TemporaryDirectory() as d:
            ledger = DurableCommandLedger(str(Path(d) / "state.db"))
            calls = []
            def fn():
                calls.append(1)
                return {"ok": True, "n": len(calls)}
            self.assertEqual(ledger.execute_once("c1", fn), ({"ok": True, "n": 1}, True))
            self.assertEqual(ledger.execute_once("c1", fn), ({"ok": True, "n": 1}, False))
            self.assertEqual(len(calls), 1)

    def test_broker_requires_explicit_shared_scope_and_tenant(self):
        with tempfile.TemporaryDirectory() as d:
            broker = IsolationBroker(str(Path(d) / "state.db"))
            parent = AgentManifest("parent", "director", private_scope="private:parent", writable_scopes=("shared",))
            child = AgentManifest("child", "researcher", parent_id="parent", private_scope="private:child", readable_scopes=("shared",))
            other = AgentManifest("other", "researcher", tenant_id="other", private_scope="private:other")
            for m in (parent, child, other): broker.register(m)
            with self.assertRaises(CapabilityDenied):
                broker.propose_memory("child", "parent", "private:parent", {"fact": "secret"})
            proposal = broker.propose_memory("child", "parent", "shared", {"fact": "evidence"})
            self.assertEqual(len(broker.list_proposals("parent")), 1)
            self.assertTrue(broker.decide_proposal("parent", proposal, True))
            with self.assertRaises(CapabilityDenied):
                broker.send("child", "other", "t", {"x": 1})

    def test_context_tree_compaction_preserves_sources_and_budget(self):
        with tempfile.TemporaryDirectory() as d:
            ctx = ContextManager(str(Path(d) / "state.db"))
            sid = ctx.create_session("agent")
            first = ctx.add(sid, "user", "A long source fact", kind="message", source_ids=("src-a",))
            second = ctx.add(sid, "assistant", "A response", parent_id=first.id)
            compact = ctx.compact(sid, second.id, "Summary of A", (first.id, second.id))
            lineage = ctx.lineage(sid)
            self.assertEqual(len(lineage), 3)
            self.assertEqual(compact.kind, "compaction")
            self.assertEqual(compact.source_ids, (first.id, second.id))
            ctx.set_block("agent", "policy", "short", 20)
            packed = ctx.pack(sid, 60, agent_id="agent")
            self.assertLessEqual(packed["used_chars"], 60)
            self.assertIn("Summary of A", packed["text"])

    def test_run_envelope_has_trace_and_identity(self):
        env = RunEnvelope.create("agent", "task", tenant_id="t")
        self.assertEqual(env.agent_id, "agent")
        self.assertEqual(env.tenant_id, "t")
        self.assertTrue(env.run_id and env.trace_id)


if __name__ == "__main__":
    unittest.main()

