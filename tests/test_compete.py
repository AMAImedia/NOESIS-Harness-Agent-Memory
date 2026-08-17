"""Tests for privacy, snapshot LWW, consolidation, procedures, compressor."""

import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from noesis_harness import (
    Memory, PrivacyFilter, ConsolidationWorker, ProcedureRunner,
    export_snapshot, import_snapshot, parse_procedure,
)


class _Tmp(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="noesis_compete_")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)


class TestPrivacy(_Tmp):
    def test_scrubs_email_and_secret(self):
        pf = PrivacyFilter()
        out = pf.scrub("mail me@x.com token sk-abcdefghijklmnopqrstuv")
        self.assertNotIn("me@x.com", out)
        self.assertIn("[EMAIL]", out)
        self.assertIn("[SECRET]", out)

    def test_save_uses_privacy(self):
        m = Memory(os.path.join(self.dir, "m.db"), privacy=PrivacyFilter())
        m.save("contact jane@corp.com")
        hits = m.recall("contact")
        self.assertTrue(hits)
        self.assertNotIn("jane@corp.com", hits[0]["fact"])


class TestCompressor(_Tmp):
    def test_compressor_applied(self):
        m = Memory(os.path.join(self.dir, "m.db"), compressor=lambda t: t.upper())
        m.save("quiet fact")
        self.assertEqual(m.profile()[0]["fact"], "QUIET FACT")


class TestSnapshot(_Tmp):
    def test_export_import_lww(self):
        a = Memory(os.path.join(self.dir, "a.db"))
        b = Memory(os.path.join(self.dir, "b.db"))
        mid = a.save("keep this")
        path = os.path.join(self.dir, "snap.json")
        self.assertGreater(export_snapshot(a, path), 0)
        n = import_snapshot(b, path)
        self.assertGreaterEqual(n, 1)
        self.assertTrue(any(h["id"] == mid for h in b.profile()))


class TestConsolidate(_Tmp):
    def test_merges_near_dupes(self):
        m = Memory(os.path.join(self.dir, "m.db"))
        m.save("Client wants Spanish dubbing!")
        m.save("client wants spanish dubbing")
        out = ConsolidationWorker(m, periods=0).run_once()
        self.assertEqual(out["merged"], 1)
        self.assertEqual(m.stats()["semantic"], 1)


class TestProcedures(_Tmp):
    def test_match_and_run(self):
        m = Memory(os.path.join(self.dir, "m.db"))
        m.save("when inbound spanish then reply in spanish", kind="procedural")
        parsed = parse_procedure("when inbound spanish then reply in spanish")
        self.assertEqual(parsed["action"], "reply in spanish")
        fired = []
        runner = ProcedureRunner(m, min_overlap=0.4)
        res = runner.run("inbound spanish lead", execute=lambda act, item: fired.append(act))
        self.assertTrue(res[0]["ok"])
        self.assertEqual(fired, ["reply in spanish"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
