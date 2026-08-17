import tempfile
import time
import unittest
from pathlib import Path

from noesis_harness.evidence import EvidenceStore


class EvidenceTests(unittest.TestCase):
    def test_duplicate_merges_sources_without_duplicate_fact(self):
        with tempfile.TemporaryDirectory() as d:
            store = EvidenceStore(str(Path(d) / "memory.db"))
            first = store.add("Project uses SQLite", ["evt-1"], confidence=0.6)
            second = store.add("project uses sqlite", ["evt-2"], confidence=0.7)
            self.assertEqual(first, second)
            fact = store.get(first)
            self.assertEqual(fact.source_ids, ("evt-1", "evt-2"))
            self.assertEqual(fact.confidence, 0.7)

    def test_search_exposes_score_reason_and_freshness(self):
        with tempfile.TemporaryDirectory() as d:
            store = EvidenceStore(str(Path(d) / "memory.db"))
            now = 2_000_000_000.0
            old = store.add("Agent uses local memory only", ["old"], confidence=0.4, observed_at=now - 86400 * 90)
            other = store.add("Agent uses local memory safely", ["fresh"], confidence=0.5, observed_at=now)
            hits = store.search("local memory", now=now)
            self.assertTrue(hits)
            self.assertIn("reason", hits[0])
            self.assertIn("freshness", hits[0])
            self.assertEqual(hits[0]["fact_id"], other)

    def test_conflicts_are_pending_until_review(self):
        with tempfile.TemporaryDirectory() as d:
            store = EvidenceStore(str(Path(d) / "memory.db"))
            a = store.add("Model uses BF16", ["a"], confidence=0.8)
            b = store.add("Model uses NF4", ["b"], confidence=0.7)
            cid = store.mark_conflict(a, b, "precision disagreement")
            proposals = store.consolidation_proposals()
            self.assertEqual(len(proposals), 1)
            self.assertEqual(proposals[0]["status"], "pending")
            self.assertTrue(store.decide_conflict(cid, winner_id=a, resolution="source a is authoritative"))
            self.assertEqual(store.get(a).status, "active")
            self.assertEqual(store.get(b).status, "superseded")


if __name__ == "__main__": unittest.main()

