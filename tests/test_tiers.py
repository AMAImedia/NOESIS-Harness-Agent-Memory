"""Tests for four-tier memory semantics (working/episodic/semantic/procedural)."""

import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from noesis_harness import Memory


class _Tmp(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="noesis_tiers_")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)


class TestWorkingTier(_Tmp):
    def test_observe_stores_raw(self):
        m = Memory(os.path.join(self.dir, "m.db"))
        m.observe("s1", "inbound", "client needs dubbing")
        m.observe("s1", "analysis", "dubbing request detected")
        self.assertEqual(m.stats()["observations"], 2)

    def test_observe_scoped_by_session(self):
        m = Memory(os.path.join(self.dir, "m.db"))
        m.observe("s1", "inbound", "hello")
        m.observe("s2", "inbound", "world")
        self.assertEqual(m.stats()["observations"], 2)


class TestEpisodicTier(_Tmp):
    def test_summarize_stores(self):
        m = Memory(os.path.join(self.dir, "m.db"))
        m.summarize("s1", "user asked for Spanish dubbing")
        self.assertEqual(m.stats()["summaries"], 1)


class TestSemanticTier(_Tmp):
    def test_save_dedup_strengthens(self):
        m = Memory(os.path.join(self.dir, "m.db"))
        i1 = m.save("client needs Spanish dubbing", confidence=0.8)
        i2 = m.save("client needs Spanish dubbing", confidence=0.6)
        self.assertEqual(i1, i2)  # same fact -> same id (no duplicate)
        f = m.profile()[0]
        self.assertGreater(f["strength"], 1.0)  # strengthened

    def test_recall_kind_filter(self):
        m = Memory(os.path.join(self.dir, "m.db"))
        m.save("fact about dubbing", kind="semantic")
        m.save("procedure how to dub", kind="procedural")
        res = m.recall("dubbing", kind="semantic")
        self.assertTrue(all(r["kind"] == "semantic" for r in res))

    def test_confidence_roundtrip(self):
        m = Memory(os.path.join(self.dir, "m.db"))
        m.save("fact", confidence=0.7)
        self.assertAlmostEqual(m.profile()[0]["confidence"], 0.7)


class TestProceduralTier(_Tmp):
    def test_save_procedural(self):
        m = Memory(os.path.join(self.dir, "m.db"))
        m.save("WHEN client asks price THEN send pricing link", kind="procedural")
        stats = m.stats()
        self.assertEqual(stats["procedural"], 1)

    def test_procedural_kind_distinct(self):
        m = Memory(os.path.join(self.dir, "m.db"))
        m.save("fact one", kind="semantic")
        m.save("procedure one", kind="procedural")
        stats = m.stats()
        self.assertEqual(stats["semantic"], 1)
        self.assertEqual(stats["procedural"], 1)


class TestDecay(_Tmp):
    def test_decay_bounded_floor(self):
        m = Memory(os.path.join(self.dir, "m.db"))
        m.save("fact", confidence=0.9)
        for _ in range(100):
            m.decay()
        f = m.profile()[0]
        self.assertGreaterEqual(f["strength"], m.DECAY_FLOOR)

    def test_recall_strengthens(self):
        m = Memory(os.path.join(self.dir, "m.db"))
        m.save("client wants Spanish dubbing")
        before = m.profile()[0]["strength"]
        m.recall("Spanish")
        after = m.profile()[0]["strength"]
        self.assertGreaterEqual(after, before)


class TestOffload(_Tmp):
    def test_offload_creates_ref(self):
        m = Memory(os.path.join(self.dir, "m.db"))
        refs = os.path.join(self.dir, "refs")
        m.offload("s9", "# big log\n" * 10, refs)
        self.assertTrue(os.path.exists(os.path.join(refs, "s9.md")))

    def test_offload_adds_summary(self):
        m = Memory(os.path.join(self.dir, "m.db"))
        m.offload("s9", "log", os.path.join(self.dir, "refs"))
        self.assertEqual(m.stats()["summaries"], 1)


class TestVectorTier(_Tmp):
    def test_save_vector_falls_back_without_embedder(self):
        m = Memory(os.path.join(self.dir, "m.db"))
        m._vector_backend = "none"
        mid = m.save_vector("Spanish film dubbing quote", confidence=0.8)
        self.assertTrue(mid)
        hits = m.recall("Spanish")
        self.assertTrue(any("Spanish" in h["fact"] for h in hits))

    def test_cosine_and_rrf(self):
        m = Memory(os.path.join(self.dir, "m.db"))
        self.assertAlmostEqual(m._cosine([1.0, 0.0], [1.0, 0.0]), 1.0)
        self.assertLess(m._cosine([1.0, 0.0], [0.0, 1.0]), 0.01)
        fused = m._rrf_fuse(
            [{"id": "a", "fact": "bm25"}, {"id": "b", "fact": "both"}],
            [{"id": "b", "fact": "both"}, {"id": "c", "fact": "vec"}],
            3,
        )
        ids = [r["id"] for r in fused]
        self.assertIn("b", ids)
        self.assertEqual(len(fused), 3)

    def test_stats_has_vector_fields(self):
        m = Memory(os.path.join(self.dir, "m.db"))
        s = m.stats()
        self.assertIn("vector_embedded", s)
        self.assertIn("vector_backend", s)


if __name__ == "__main__":
    unittest.main(verbosity=2)