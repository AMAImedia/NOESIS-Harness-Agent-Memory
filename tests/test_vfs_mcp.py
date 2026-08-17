"""Tests for VFS, session extract, MCP, recall20."""

import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from noesis_harness import Memory, ContextVfs, parse_uri, extract_session, McpServer
from benchmarks.recall20 import run as run_recall20


class _Tmp(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="noesis_vfs_")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)


class TestVfs(_Tmp):
    def test_l0_shorter_than_l2(self):
        m = Memory(os.path.join(self.dir, "m.db"))
        mid = m.save("A" * 80 + " important Spanish dubbing detail " + "B" * 80)
        vfs = ContextVfs(m, ref_dir=os.path.join(self.dir, "refs"))
        l0 = vfs.resolve(mid, "L0")
        l2 = vfs.resolve(mid, "L2")
        self.assertLess(len(l0["text"]), len(l2["text"]))
        self.assertIsNotNone(parse_uri(l0["uri"]))
        self.assertTrue(vfs.ls())


class TestSession(_Tmp):
    def test_extract(self):
        m = Memory(os.path.join(self.dir, "m.db"))
        m.observe("s1", "inbound", "need Spanish film dubbing soon")
        m.observe("s1", "note", "Spanish festival deadline Friday")
        out = extract_session(m, "s1")
        self.assertTrue(out["summary_id"])
        self.assertGreaterEqual(out["n_obs"], 2)
        self.assertTrue(m.recall("Spanish"))


class TestMcp(_Tmp):
    def test_tools_roundtrip(self):
        m = Memory(os.path.join(self.dir, "m.db"))
        srv = McpServer(memory=m)
        listed = srv.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        self.assertGreaterEqual(len(listed["result"]["tools"]), 2)
        srv.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                    "params": {"name": "memory_save",
                               "arguments": {"fact": "Nova needs Spanish dubbing"}}})
        rec = srv.handle({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                          "params": {"name": "memory_recall",
                                     "arguments": {"query": "Nova"}}})
        self.assertIn("Nova", rec["result"]["content"][0]["text"])


class TestRecall20(unittest.TestCase):
    def test_acc_at_least_80(self):
        out = run_recall20()
        self.assertGreaterEqual(out["acc"], 0.8, out["rows"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
